"""
Controleert of de opgeslagen documents.raw_video_url-manifesten nog echt
afspeelbaar zijn: haalt het masterplaylist op (zoals hls.js dat ook doet) en
daarna de eerste video-rendition (Stream(01)/... e.d.) eruit, en meldt het
als die niet met een geldige #EXTM3U-playlist antwoordt.

Aanleiding: issue #152 -- het debat van 2026-07-01 (stikstof) speelt niet af.
Uitgezocht: het masterplaylist (index.m3u8) laadt prima, maar alle vijf
video-renditions (Stream(01) t/m Stream(05)) geven HTTP 400 terug
("Index was out of range...", een serverfout bij de Tweede Kamer zelf) --
alleen de audio-only rendition (Stream(06)) werkt nog. hls.js herkent dit
zelf al als fatale fout (na het doorproberen van alle renditions, enkele
seconden), dus de frontend toont dan al de foutmelding in VideoPlayer.vue.
Dit script is voor het pro-actief signaleren van zulke kapotte manifesten
zónder een browser te hoeven opstarten, bv. periodiek op de bestaande set.

Bewust geen ffprobe/ffmpeg-dependency (zie docs/tk-data-sources-overview.md
5e voor eenzelfde afweging bij thumbnails): een HTTP GET + de eerste regels
van de playlist controleren is genoeg om exact dit faalpatroon (en generieke
404/500's) te detecteren, zonder een binary te vereisen die hier nog nergens
anders nodig is. ffprobe zou wel dieper kunnen controleren (segmenten
daadwerkelijk decoderen), maar dat is voor dit doel overkill.

Gebruik:
    uv run python -m pipeline.check_video_urls [--topic stikstof] [--limit N]
"""

import argparse
import logging
import re
from urllib.parse import urljoin

import requests

from pipeline.db import db

logger = logging.getLogger(__name__)

_STREAM_INF_RE = re.compile(r"#EXT-X-STREAM-INF:[^\n]*\n([^\n]+)")


def first_video_level_uri(master_playlist_text):
    """Eerste video-rendition-URI (relatief) uit een masterplaylist -- dezelfde
    die hls.js bij een auto-kwaliteitskeuze als eerste probeert. `None` als er
    geen enkele #EXT-X-STREAM-INF-regel in staat."""
    match = _STREAM_INF_RE.search(master_playlist_text)
    if match is None:
        return None
    return match.group(1).strip()


def fetch_distinct_video_urls(conn, topic_slug=None):
    """(raw_video_url, debatdirect_id, topic_slug) per distinct debat, meest
    recent gecontroleerd eerst -- zodat --limit tijdens handmatig onderzoek de
    nieuwste (en dus meest waarschijnlijk nog relevante) debatten pakt."""
    query = """
        SELECT d.raw_video_url, d.debatdirect_id, t.slug AS topic_slug,
               MAX(d.raw_video_url_checked_at) AS checked_at
        FROM documents d
        JOIN topics t ON t.id = d.topic_id
        WHERE d.raw_video_url IS NOT NULL
    """
    params = ()
    if topic_slug:
        query += " AND t.slug = ?"
        params = (topic_slug,)
    query += " GROUP BY d.raw_video_url ORDER BY checked_at DESC"
    return conn.execute(query, params).fetchall()


def check_manifest(session, master_url):
    """Controleert één debat: master + eerste video-rendition. Geeft een dict
    terug met wat er precies mis was (`None` als alles goed is), zodat de
    aanroeper zelf bepaalt hoe te rapporteren/loggen."""
    try:
        resp = session.get(master_url, timeout=15)
    except requests.RequestException as exc:
        return f"master onbereikbaar: {exc}"
    if resp.status_code != 200 or not resp.text.startswith("#EXTM3U"):
        return f"master ongeldig: HTTP {resp.status_code}, body begint met {resp.text[:80]!r}"

    level_uri = first_video_level_uri(resp.text)
    if level_uri is None:
        return "master bevat geen enkele video-rendition (#EXT-X-STREAM-INF)"
    level_url = urljoin(master_url, level_uri)

    try:
        resp = session.get(level_url, timeout=15)
    except requests.RequestException as exc:
        return f"eerste rendition onbereikbaar: {exc}"
    if resp.status_code != 200 or not resp.text.startswith("#EXTM3U"):
        return f"eerste rendition ongeldig: HTTP {resp.status_code}, body begint met {resp.text[:80]!r}"

    return None


def check_all(topic_slug=None, limit=None):
    conn = db.connect()
    try:
        rows = fetch_distinct_video_urls(conn, topic_slug)
    finally:
        conn.close()

    if limit is not None:
        rows = rows[:limit]

    session = requests.Session()
    broken = []
    for row in rows:
        problem = check_manifest(session, row["raw_video_url"])
        if problem is not None:
            broken.append((row["debatdirect_id"], row["topic_slug"], row["raw_video_url"], problem))
            logger.warning("KAPOT topic=%s debatdirect_id=%s: %s", row["topic_slug"], row["debatdirect_id"], problem)

    logger.info("Klaar: %d/%d debatten kapot.", len(broken), len(rows))
    return broken


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", help="topic-slug, bv. stikstof (default: alle topics)")
    parser.add_argument("--limit", type=int, help="alleen de N meest recent gecontroleerde debatten (handig om snel te testen)")
    args = parser.parse_args()
    check_all(topic_slug=args.topic, limit=args.limit)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
