"""
Experiment voor issue #268 (homepage-videopreview, TikTok/Shorts-stijl):
snijdt uit een steekproef debatten telkens het meest "emotionele" fragment,
op de originele 16:9-beeldverhouding (geen crop), als losse mp4's +
manifest.json.

Selectie (issue-discussie): tag-gebaseerd, met interrupties als bonus. Een
argument scoort hoger naarmate het meer van deze tags heeft --
Debatzet-Gevoelens-Verwoorden (expliciet emotioneel beroep) en
Frame-Menselijk-Belang (human interest) wegen het zwaarst, Frame-Conflict
en Frame-Moraliteit lichter -- plus een bonus als er rond hetzelfde moment
een interrupter-event (data/debate_events/<debatdirect_id>.json) plaatsvond:
een proxy voor "reuring in de zaal", niet zelf een sentimentsignaal.

Bewust GEEN nieuwe LLM-pass: dit hergebruikt tags die tag_arguments.py al
heeft toegekend, dus geen extra kosten/latency voor deze steekproef.

Eerdere versie cropte naar verticaal 9:16 (spreker gelokaliseerd via een
lokaal vision-LLM, later vervangen door OpenCV-gezichtsdetectie) -- beide
bleken meer complexiteit dan waarde voor deze steekproef (zie
docs/handoff.md), dus laten we de crop hier los en tonen we de clip zoals
de bron 'm aanlevert.

Output: data/export/gepubliceerd/shorts/<debatdirect_id>.mp4 + manifest.json
in dezelfde map (debat, spreker, partij, citaat, tags, clip-venster) -- de
publieke data-submodule, zodat de frontend deze net als de rest van
data/export/gepubliceerd/ kan uitlezen. Committen/pushen gebeurt niet door
dit script; dat is een aparte, bewuste stap in die submodule.

Gebruik:
    uv run python -m scripts.build_shorts_sample [--limit 10] [--dry-run]

--dry-run schrijft alleen het manifest (geen ffmpeg-render) -- handig om de
selectie te controleren voordat je 10x een mp4 rendert.
"""

import argparse
import json
import logging
import subprocess
from datetime import datetime

import requests

from pipeline.check_video_urls import check_manifest
from pipeline.db import db
from pipeline.fetch_debate_events import DEBATE_EVENTS_DIR
from pipeline.paths import REPO_ROOT

logger = logging.getLogger(__name__)

OUTPUT_DIR = REPO_ROOT / "data" / "export" / "gepubliceerd" / "shorts"

# Tag -> gewicht. Hoger = sterker signaal voor een "emotioneel moment".
TAG_WEIGHTS = {
    "Debatzet-Gevoelens-Verwoorden": 3,
    "Frame-Menselijk-Belang": 3,
    "Frame-Conflict": 1,
    "Frame-Moraliteit": 1,
}

INTERRUPT_WINDOW_SECONDS = 20  # rond het argument, zowel voor als na
INTERRUPT_BONUS = 2

PRE_ROLL_SECONDS = 1.5
POST_ROLL_SECONDS = 1.0
MIN_CLIP_SECONDS = 8.0
MAX_CLIP_SECONDS = 18.0

# 960x540 i.p.v. de volle bronresolutie: dit is een gemuted-of-klein homepage-
# previewtegeltje (zoals YouTube's eigen hover-previews, die ook ruim onder
# de bron-resolutie zitten), geen vervanging van de echte debatpagina --
# scheelt in bestandsgrootte voor de (publieke, git-versiebeheerde)
# data-submodule zonder zichtbaar kwaliteitsverlies op een preview-tegel.
OUTPUT_WIDTH = 960
OUTPUT_HEIGHT = 540


def fetch_candidates(conn):
    """Eén rij per (argument, debat) met alles wat nodig is om te scoren en
    te renderen -- alleen argumenten met een tijdspanne, een afspeelbare
    videobron én minstens één van de emotie-tags."""
    placeholders = ",".join("?" for _ in TAG_WEIGHTS)
    query = f"""
        SELECT
            a.id AS argument_id,
            a.quote_text,
            a.start_seconds,
            a.end_seconds,
            d.debatdirect_id,
            d.raw_video_url,
            d.tweedekamer_activiteit_url,
            act.name AS spreker,
            act.party AS partij,
            t.slug AS topic_slug,
            t.name AS topic_name
        FROM arguments a
        JOIN documents d ON d.id = a.document_id
        JOIN actors act ON act.id = a.actor_id
        JOIN topics t ON t.id = a.topic_id
        WHERE a.start_seconds IS NOT NULL
          AND a.end_seconds IS NOT NULL
          AND d.raw_video_url IS NOT NULL
          AND d.debatdirect_id IS NOT NULL
          AND a.id IN (
              SELECT argument_id FROM argument_tags WHERE tag_sleutel IN ({placeholders})
          )
    """
    rows = conn.execute(query, list(TAG_WEIGHTS)).fetchall()

    tag_rows = conn.execute(
        f"SELECT argument_id, tag_sleutel FROM argument_tags WHERE tag_sleutel IN ({placeholders})",
        list(TAG_WEIGHTS),
    ).fetchall()
    tags_by_argument = {}
    for row in tag_rows:
        tags_by_argument.setdefault(row["argument_id"], []).append(row["tag_sleutel"])

    return rows, tags_by_argument


def load_interrupter_seconds(debatdirect_id):
    """video_seconds van alle interrupter-events voor dit debat, of None als
    er geen (bruikbare) events-cache is -- dan telt de interruptiebonus
    simpelweg niet mee, dat is geen reden om het debat over te slaan."""
    cache_path = DEBATE_EVENTS_DIR / f"{debatdirect_id}.json"
    if not cache_path.exists():
        return None
    events_json = json.loads(cache_path.read_text())
    started_at = datetime.fromisoformat(events_json["startedAt"])
    seconds = []
    for event in events_json.get("events", []):
        if event.get("eventType") != "interrupter":
            continue
        event_start_raw = event.get("eventStart")
        if not event_start_raw:
            continue
        seconds.append((datetime.fromisoformat(event_start_raw) - started_at).total_seconds())
    return seconds


def score_argument(row, tags, interrupter_seconds):
    score = sum(TAG_WEIGHTS[tag] for tag in tags)
    if interrupter_seconds:
        window_start = row["start_seconds"] - INTERRUPT_WINDOW_SECONDS
        window_end = row["end_seconds"] + INTERRUPT_WINDOW_SECONDS
        if any(window_start <= s <= window_end for s in interrupter_seconds):
            score += INTERRUPT_BONUS
    return score


def pick_best_per_debate(rows, tags_by_argument):
    """Beste (hoogst scorende) argument per debat -- diversiteit over
    debatten is belangrijker dan meerdere clips uit hetzelfde debat voor
    deze steekproef."""
    interrupter_cache = {}
    best_by_debate = {}
    for row in rows:
        tags = tags_by_argument.get(row["argument_id"], [])
        debatdirect_id = row["debatdirect_id"]
        if debatdirect_id not in interrupter_cache:
            interrupter_cache[debatdirect_id] = load_interrupter_seconds(debatdirect_id)
        score = score_argument(row, tags, interrupter_cache[debatdirect_id])

        current = best_by_debate.get(debatdirect_id)
        if current is None or score > current["score"]:
            best_by_debate[debatdirect_id] = {"row": row, "tags": tags, "score": score}

    return sorted(best_by_debate.values(), key=lambda entry: entry["score"], reverse=True)


def clip_window(row):
    """(start, duration) in seconden voor de ffmpeg-render: het argument zelf
    plus een korte pre-/post-roll, geclampt tussen MIN/MAX_CLIP_SECONDS zodat
    zowel een kort tussenwerpsel als een lang betoog een bruikbare short
    oplevert."""
    start = max(0.0, row["start_seconds"] - PRE_ROLL_SECONDS)
    end = row["end_seconds"] + POST_ROLL_SECONDS
    duration = end - start
    duration = min(max(duration, MIN_CLIP_SECONDS), MAX_CLIP_SECONDS)
    return start, duration


def render_clip(raw_video_url, start_seconds, duration_seconds, output_path):
    """Snijdt met ffmpeg direct uit het HLS-manifest -- geen aparte
    downloadstap, geen crop: schaalt de originele 16:9-beeldverhouding naar
    OUTPUT_WIDTH x OUTPUT_HEIGHT."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start_seconds:.2f}",
        # De TK-CDN serveert segmenten als "Segment(...).m4v"/".m4a", maar de
        # inhoud detecteert als het generieke mov/mp4-format -- ffmpeg 8's
        # standaard "extension_picky"-check op de hls-demuxer verwerpt die
        # mismatch als (potentiële) extensie-verwarring en faalt hard
        # ("Invalid data found when processing input"), terwijl de segmenten
        # zelf prima geldig zijn (empirisch geverifieerd: -c copy speelt af).
        "-extension_picky",
        "0",
        "-i",
        raw_video_url,
        "-t",
        f"{duration_seconds:.2f}",
        "-vf",
        f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "28",
        "-c:a",
        "aac",
        "-b:a",
        "96k",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    logger.info("ffmpeg: %s -> %s", raw_video_url, output_path)
    subprocess.run(command, check=True, capture_output=True, text=True)


def build_manifest_entry(entry):
    row = entry["row"]
    start, duration = clip_window(row)
    return {
        "debatdirect_id": row["debatdirect_id"],
        "topic_slug": row["topic_slug"],
        "topic_name": row["topic_name"],
        "spreker": row["spreker"],
        "partij": row["partij"],
        "citaat": row["quote_text"],
        "tags": entry["tags"],
        "score": entry["score"],
        "tweedekamer_activiteit_url": row["tweedekamer_activiteit_url"],
        "clip_start_seconds": round(start, 2),
        "clip_duration_seconds": round(duration, 2),
        "bestand": f"{row['debatdirect_id']}.mp4",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=10, help="aantal debatten in de steekproef (default: 10)")
    parser.add_argument("--dry-run", action="store_true", help="alleen manifest.json schrijven, geen ffmpeg-render")
    args = parser.parse_args()

    conn = db.connect()
    try:
        rows, tags_by_argument = fetch_candidates(conn)
    finally:
        conn.close()

    if not rows:
        logger.warning("Geen kandidaat-argumenten gevonden (emotie-tags %s).", list(TAG_WEIGHTS))
        return

    all_ranked = pick_best_per_debate(rows, tags_by_argument)

    # Sommige HLS-manifesten zijn server-side kapot (issue #152: video-renditions
    # geven HTTP 400, alleen de audio-only rendition werkt nog) -- zo'n debat
    # overslaan i.p.v. een clip zonder beeld op te leveren, en de volgende
    # kandidaat proberen tot --limit haalbare debatten bereikt is.
    session = requests.Session()
    ranked = []
    for entry in all_ranked:
        if len(ranked) >= args.limit:
            break
        problem = check_manifest(session, entry["row"]["raw_video_url"])
        if problem is not None:
            logger.warning("Overgeslagen (kapot manifest) %s: %s", entry["row"]["debatdirect_id"], problem)
            continue
        ranked.append(entry)

    logger.info("%d/%d debatten geselecteerd (van %d kandidaat-argumenten).", len(ranked), len(all_ranked), len(rows))

    manifest = []
    for entry in ranked:
        manifest_entry = build_manifest_entry(entry)
        logger.info(
            "score=%d %s (%s, %s): %.60s...",
            entry["score"],
            entry["row"]["debatdirect_id"],
            entry["row"]["spreker"],
            entry["row"]["partij"],
            entry["row"]["quote_text"],
        )
        if args.dry_run:
            # In een dry-run is er geen mp4 om naar te verwijzen -- de
            # selectie zelf inspecteren kan dan alleen via de logregel
            # hierboven, niet via manifest.json (zie ook onderstaande
            # "alleen daadwerkelijk gerenderde clips" voor de niet-dry-run).
            manifest.append(manifest_entry)
            continue

        start, duration = clip_window(entry["row"])
        output_path = OUTPUT_DIR / manifest_entry["bestand"]

        try:
            render_clip(entry["row"]["raw_video_url"], start, duration, output_path)
        except subprocess.CalledProcessError as exc:
            logger.error("ffmpeg faalde voor %s: %s", entry["row"]["debatdirect_id"], exc.stderr[-2000:])
            continue

        # Pas nu toevoegen: alleen debatten met een daadwerkelijk gerenderde
        # mp4 horen in het manifest, anders verwijst het naar een bestand dat
        # niet bestaat (zie de mislukte-detectie/ffmpeg-continues hierboven).
        manifest.append(manifest_entry)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    logger.info("Manifest geschreven: %s", OUTPUT_DIR / "manifest.json")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
