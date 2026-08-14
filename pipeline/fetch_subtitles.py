"""
Haalt de Nederlandse WebVTT-ondertitel-track van Debat Direct's ruwe
HLS-manifest op en cachet die op disk, per debat (documents.debatdirect_id,
zie pipeline/enrich_video_url.py). Voorbereidende stap voor het zin-precies
matchen van quote_text tegen ondertitel-cues (arguments.start_seconds/
end_seconds, zie docs/design/videoplayer/README.md "Spannes verrijken") --
dat matchen zelf gebeurt in een latere stap, dit script haalt alleen op.

Route (zie docs/tk-data-sources-overview.md 5b voor de volledige uitleg):
1. `https://api.debatdirect.tweedekamer.nl/debates/{debatdirect_id}` geeft
   `video.vodUrl` (het ruwe HLS-manifest) en `startsAt`/`endsAt` terug --
   geen locationId-naar-manifest-padnaam-vertaling nodig.
2. Het manifest bevat alleen een SUBTITLES-track als `start`/`end`
   query-params zijn meegegeven (anders ontbreekt de ondertitel-renditie
   stilzwijgend). De API's eigen `startsAt`/`endsAt`-notatie (zonder
   dubbele punt in de offset) volstaat; de server normaliseert dat zelf.
3. De SUBTITLES-`URI` in dat manifest wijst naar een sub-playlist
   (`subtitles/nl-pol_VOD.m3u8?...`) met daarin weer een relatieve
   `.vtt`-URI voor het hele debat in één bestand.

Bewust géén tijdcode-omrekening hier: de cues in het VTT-bestand staan op
een eigen, niet bij nul beginnende klok (WebVTT `X-TIMESTAMP-MAP`) die niet
gelijk is aan seconden-sinds-videobegin -- zie de aantekening in
docs/tk-data-sources-overview.md 5b. Dat omrekenen (calibreren op een
bekend ankerpunt) is aan de matching-stap, niet aan het ophalen.

Cachet naar data/subtitles/<debatdirect_id>.vtt (niet ingecheckt, zie
.gitignore) en slaat een debat over waarvoor die file al bestaat -- geen
database-boekhouding nodig, het bestand zelf is de idempotentie-vlag.

Gebruik:
    uv run python -m pipeline.fetch_subtitles [--topic stikstof] [--force]
"""

import argparse
import logging
import re
import time
from datetime import datetime, timezone
from urllib.parse import quote, urljoin

import requests

from pipeline.db import db
from pipeline.paths import REPO_ROOT

logger = logging.getLogger(__name__)

DEBATE_API_URL = "https://api.debatdirect.tweedekamer.nl/debates/{id}"
SUBTITLES_DIR = REPO_ROOT / "data" / "subtitles"

_SUBTITLE_URI_RE = re.compile(r'#EXT-X-MEDIA:TYPE=SUBTITLES.*?URI="([^"]+)"')


def fetch_pending_debates(conn, topic_id):
    """Distincte debatdirect_id's binnen dit topic, met een vlag of
    raw_video_url nog op minstens één documentrij van die debatdirect_id
    ontbreekt. De VTT-cache zelf staat op disk, niet in de database -- die
    check doet de aanroeper (_fetch_topic) apart, via het cachebestand."""
    rows = conn.execute(
        """SELECT debatdirect_id,
                  MAX(CASE WHEN raw_video_url IS NULL THEN 1 ELSE 0 END) AS needs_raw_video_url
           FROM documents
           WHERE topic_id = ? AND debatdirect_id IS NOT NULL
           GROUP BY debatdirect_id
           ORDER BY debatdirect_id""",
        (topic_id,),
    ).fetchall()
    return [(row["debatdirect_id"], bool(row["needs_raw_video_url"])) for row in rows]


def fetch_debate_detail(session, debatdirect_id):
    resp = session.get(DEBATE_API_URL.format(id=debatdirect_id), timeout=15)
    resp.raise_for_status()
    return resp.json()


def find_subtitle_manifest_url(manifest_text, base_url):
    match = _SUBTITLE_URI_RE.search(manifest_text)
    if match is None:
        return None
    return urljoin(base_url, match.group(1))


def find_vtt_url(subtitle_playlist_text, base_url):
    for line in subtitle_playlist_text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return urljoin(base_url, line)
    return None


# De CDN (Akamai) blijkt de .vtt-respons een aantal seconden te cachen
# gekeyed op path alleen, de querystring (start/end) genegeerd -- twee
# activiteiten in dezelfde zaal op dezelfde dag, kort na elkaar opgevraagd,
# kregen zo allebei de VTT van de eerst-opgevraagde activiteit terug, ondanks
# een correcte, verschillende sub-playlist-URI per debat. Reproduceerbaar
# bevestigd: identieke content bij <5s tussen requests op hetzelfde pad,
# correcte (verschillende) content bij 12s. Een cache-bustende extra
# query-param bleek NIET te helpen (nog steeds gecachet op path), dus alleen
# een throttle per onderliggend pad (datum+zaal, gedeeld door alle
# activiteiten van diezelfde vergadering) lost dit betrouwbaar op.
_MIN_SECONDS_BETWEEN_SAME_PATH_FETCH = 20


def build_manifest_url(vod_url, starts_at, ends_at):
    """Het afspeelbare HLS-manifest voor één debat: zonder start/end-params
    ontbreekt de SUBTITLES-track stilzwijgend (zie moduledocstring). Dit is
    zowel de URL die we in documents.raw_video_url persisteren als de URL
    die we bevragen voor de ondertitel-sub-playlist hieronder."""
    return f"{vod_url}&start={quote(starts_at, safe='')}&end={quote(ends_at, safe='')}"


def fetch_subtitle_vtt(session, vod_url, starts_at, ends_at, last_fetch_by_path):
    """Haalt de VTT-inhoud op voor één debat, of None als er geen
    ondertitel-track beschikbaar is (bv. debat zonder live-ondertiteling).
    `last_fetch_by_path` (vod-pad zonder querystring -> laatste fetch-tijd,
    time.monotonic()) wordt door de aanroeper gedeeld tussen debatten, zodat
    de throttle hierboven ook geldt tussen opeenvolgende debatten op
    hetzelfde pad, niet alleen binnen één fetch."""
    manifest_url = build_manifest_url(vod_url, starts_at, ends_at)
    vod_path = vod_url.split("?")[0]
    last_fetch = last_fetch_by_path.get(vod_path)
    if last_fetch is not None:
        wait = _MIN_SECONDS_BETWEEN_SAME_PATH_FETCH - (time.monotonic() - last_fetch)
        if wait > 0:
            time.sleep(wait)

    resp = session.get(manifest_url, timeout=15)
    resp.raise_for_status()

    subtitle_playlist_url = find_subtitle_manifest_url(resp.text, manifest_url)
    if subtitle_playlist_url is None:
        return None

    resp = session.get(subtitle_playlist_url, timeout=15)
    resp.raise_for_status()

    vtt_url = find_vtt_url(resp.text, subtitle_playlist_url)
    if vtt_url is None:
        return None

    resp = session.get(vtt_url, timeout=60)
    last_fetch_by_path[vod_path] = time.monotonic()
    resp.raise_for_status()
    return resp.text


def fetch(topic_keyword, force=False):
    conn = db.connect()
    topic_row = conn.execute("SELECT id FROM topics WHERE slug = ?", (topic_keyword,)).fetchone()
    if topic_row is None:
        raise SystemExit(f"onbekende topic-slug: {topic_keyword}")
    try:
        _fetch_topic(conn, topic_row["id"], force=force, last_fetch_by_path={})
    finally:
        conn.close()


def fetch_all(force=False):
    conn = db.connect()
    # Eén dict over alle topics heen: dezelfde zaal kan op dezelfde dag
    # debatten van verschillende topics bevatten, en de CDN-cache-bug (zie
    # fetch_subtitle_vtt) is per pad, niet per topic.
    last_fetch_by_path = {}
    try:
        topic_rows = conn.execute("SELECT id, slug FROM topics ORDER BY slug").fetchall()
        for topic_row in topic_rows:
            logger.info("=== topic: %s ===", topic_row["slug"])
            _fetch_topic(conn, topic_row["id"], force=force, last_fetch_by_path=last_fetch_by_path)
    finally:
        conn.close()


def _fetch_topic(conn, topic_id, last_fetch_by_path, force=False):
    debates = fetch_pending_debates(conn, topic_id)
    if not debates:
        logger.info("Geen documenten met een debatdirect_id.")
        return

    SUBTITLES_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    fetched, cached, skipped_no_subs, failed, raw_urls_saved = 0, 0, 0, 0, 0

    for debatdirect_id, needs_raw_video_url in debates:
        cache_path = SUBTITLES_DIR / f"{debatdirect_id}.vtt"
        needs_vtt = force or not cache_path.exists()
        # raw_video_url en de VTT-cache zijn onafhankelijk idempotent -- een
        # debat met een verse cache maar een nog lege raw_video_url (bv.
        # documenten toegevoegd ná een eerdere run) moet toch nog een keer
        # de detail-API bevragen, en andersom.
        if not needs_vtt and not needs_raw_video_url:
            cached += 1
            continue

        try:
            detail = fetch_debate_detail(session, debatdirect_id)
            vod_url = detail.get("video", {}).get("vodUrl")
            starts_at, ends_at = detail.get("startsAt"), detail.get("endsAt")
            if not vod_url or not starts_at or not ends_at:
                logger.warning("Debat %s mist video.vodUrl/startsAt/endsAt, overgeslagen.", debatdirect_id)
                failed += 1
                continue

            if needs_raw_video_url:
                manifest_url = build_manifest_url(vod_url, starts_at, ends_at)
                conn.execute(
                    "UPDATE documents SET raw_video_url = ?, raw_video_url_checked_at = ? WHERE debatdirect_id = ?",
                    (manifest_url, datetime.now(timezone.utc).isoformat(), debatdirect_id),
                )
                conn.commit()
                raw_urls_saved += 1

            if not needs_vtt:
                continue

            vtt_text = fetch_subtitle_vtt(session, vod_url, starts_at, ends_at, last_fetch_by_path)
        except requests.RequestException as exc:
            logger.error("Ophalen mislukt voor debat %s: %s", debatdirect_id, exc)
            failed += 1
            continue

        if vtt_text is None:
            logger.info("Geen ondertitel-track voor debat %s.", debatdirect_id)
            skipped_no_subs += 1
            continue

        cache_path.write_text(vtt_text)
        fetched += 1
        logger.info("Opgeslagen: %s (%d bytes)", cache_path.relative_to(REPO_ROOT), len(vtt_text))

    logger.info(
        "Klaar: %d opgehaald, %d al gecached, %d zonder ondertitel-track, %d mislukt, "
        "%d raw_video_url opgeslagen (van %d debatten).",
        fetched, cached, skipped_no_subs, failed, raw_urls_saved, len(debates),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", help="topic-slug, bv. stikstof (default: alle topics)")
    parser.add_argument("--force", action="store_true", help="ook debatten met een bestaande cache-file opnieuw ophalen")
    args = parser.parse_args()
    if args.topic:
        fetch(args.topic, force=args.force)
    else:
        fetch_all(force=args.force)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
