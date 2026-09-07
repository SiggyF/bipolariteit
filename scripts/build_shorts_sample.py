"""
Experiment voor issue #268 (homepage-videopreview, TikTok/Shorts-stijl):
snijdt uit een steekproef debatten telkens het meest "emotionele" fragment,
gecropt naar verticaal 9:16, als losse mp4's + manifest.json.

Selectie (issue-discussie): tag-gebaseerd, met interrupties als bonus. Een
argument scoort hoger naarmate het meer van deze tags heeft --
Debatzet-Gevoelens-Verwoorden (expliciet emotioneel beroep) en
Frame-Menselijk-Belang (human interest) wegen het zwaarst, Frame-Conflict
en Frame-Moraliteit lichter -- plus een bonus als er rond hetzelfde moment
een interrupter-event (data/debate_events/<debatdirect_id>.json) plaatsvond:
een proxy voor "reuring in de zaal", niet zelf een sentimentsignaal.

Bewust GEEN nieuwe LLM-pass: dit hergebruikt tags die tag_arguments.py al
heeft toegekend, dus geen extra kosten/latency voor deze steekproef.

Video-crop: een vaste center-crop naar 9:16 bleek in de praktijk onbetrouwbaar
-- de TK-camera volgt niet altijd het spreekgestoelte (commissiezalen,
brede tafelopstellingen), dus de spreker viel regelmatig buiten een simpele
middelste crop (empirisch gevonden op meerdere zalen, zie git-historie van
dit bestand). Een lokaal vision-LLM (qwen via LM Studio) is hiervoor ook
geprobeerd, maar bleek in de praktijk te traag/instabiel voor een
batch-script (minutenlange hangs, lege antwoorden) -- vervangen door OpenCV's
ingebouwde Haar-cascade gezichtsdetectie (haarcascade_frontalface_default.xml,
gebundeld met opencv-python-headless, zie cv2.data.haarcascades -- LET OP:
opencv-python-headless is expliciet <5 gepind, want CascadeClassifier bestaat
niet meer in OpenCV 5.x): lokaal, deterministisch, milliseconden per frame,
geen netwerk-afhankelijkheid.

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
import tempfile
from datetime import datetime
from pathlib import Path

import cv2
import requests

from pipeline.check_video_urls import check_manifest
from pipeline.db import db
from pipeline.fetch_debate_events import DEBATE_EVENTS_DIR
from pipeline.paths import REPO_ROOT

logger = logging.getLogger(__name__)

OUTPUT_DIR = REPO_ROOT / "data" / "export" / "gepubliceerd" / "shorts"

FACE_CASCADE_PATH = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"

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

# 720x1280 i.p.v. volle 1080x1920: dit is een gemuted-of-klein homepage-
# previewtegeltje (zoals YouTube's eigen hover-previews, die ook ruim onder
# de bron-resolutie zitten), geen vervanging van de echte debatpagina --
# scheelt ~2-3x in bestandsgrootte voor de (publieke, git-versiebeheerde)
# data-submodule zonder zichtbaar kwaliteitsverlies op een preview-tegel.
OUTPUT_WIDTH = 720
OUTPUT_HEIGHT = 1280


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
          -- Alleen hoofdredes vanaf het spreekgestoelte, geen interrupties:
          -- de camera volgt bij een interruptie de roving mic op de eigen
          -- zitplaats, niet de spreker, dus een center-crop snijdt daar
          -- vaak de verkeerde persoon uit beeld (empirisch gevonden op
          -- argument 4632, Michiel van Nispen).
          AND d.turn_type = 'woordvoerder'
          -- Alleen de plenaire zaal: daar filmt de camera altijd de ene
          -- spreker op het spreekgestoelte van dichtbij, dus "grootste
          -- gezicht in beeld" is daar betrouwbaar de spreker. In
          -- commissiezalen (Troelstrazaal, Groen van Prinstererzaal,
          -- Klompezaal, ...) zitten meerdere mensen aan een tafel in beeld;
          -- daar bleek het grootste gezicht regelmatig een ander
          -- Kamerlid/de griffier te zijn, niet de spreker (empirisch
          -- gevonden op meerdere gerenderde clips, zie git-historie).
          AND d.raw_video_url LIKE '%/plenairezaal/%'
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


def extract_frame(raw_video_url, timestamp_seconds, output_path):
    """Eén enkel frame uit het ONgecropte 16:9-bronbeeld op
    `timestamp_seconds` -- de gezichtspositie die OpenCV hierop vindt wordt
    later (zie build_crop_x_expr) uitgedrukt als fractie van de breedte, dus
    onafhankelijk van de uiteindelijke exportresolutie. Volle resolutie
    (geen scale=480 meer, was zuinig-op-vision-tokens voor de vervangen
    LLM-aanpak) -- een Haar-cascade heeft meer pixels nodig om kleine/verre
    gezichten te vinden."""
    command = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{timestamp_seconds:.2f}",
        "-extension_picky",
        "0",
        "-i",
        raw_video_url,
        "-frames:v",
        "1",
        "-update",
        "1",
        str(output_path),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)


class FaceDetectionError(Exception):
    """Geen gezicht gevonden op het frame. Bewust geen fallback naar een
    gegokte center-crop -- de aanroeper slaat deze clip dan over."""


_face_cascade = None


def get_face_cascade():
    """Lazy-loaded, één keer per proces -- cv2.CascadeClassifier inladen
    kost duidelijk meetbare tijd, niet iets om per clip te herhalen."""
    global _face_cascade
    if _face_cascade is None:
        _face_cascade = cv2.CascadeClassifier(str(FACE_CASCADE_PATH))
        if _face_cascade.empty():
            raise RuntimeError(f"kon Haar-cascade niet laden: {FACE_CASCADE_PATH}")
    return _face_cascade


def detect_speaker_x_fraction(frame_path):
    """Grootste gedetecteerde gezicht op `frame_path` (áls meerdere mensen in
    beeld zijn, is de spreker vrijwel altijd degene die het dichtst bij de
    camera/lectern staat en dus het grootste gezicht heeft -- geen aparte
    "wie spreekt er" classificatie nodig, i.t.t. de vervangen LLM-aanpak).
    Geeft de horizontale positie van het midden van dat gezicht terug als
    fractie (0.0-1.0) van de framebreedte. Gooit FaceDetectionError als er
    geen enkel gezicht gevonden wordt."""
    image = cv2.imread(str(frame_path))
    if image is None:
        raise FaceDetectionError(f"kon frame niet lezen: {frame_path}")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = get_face_cascade().detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
    if len(faces) == 0:
        raise FaceDetectionError("geen gezicht gevonden")
    x, _y, w, _h = max(faces, key=lambda face: face[2] * face[3])
    width = image.shape[1]
    return (x + w / 2) / width


def build_crop_x_expr(x_fraction):
    """ffmpeg-filterexpressie voor de linker-x van de 9:16-crop, gecentreerd
    op x_fraction*iw (het door het vision-model aangewezen gezicht) --
    geclampt zodat de crop nooit buiten het bronbeeld valt. Komma's binnen
    min()/max() moeten ge-escaped worden (\\,) -- de -vf-waarde wordt eerst
    op ongeëscapete komma's gesplitst in een filterketen (crop=...,scale=...),
    dus een letterlijke "," in dit expressie-argument brak dat eerder in
    losse, ongeldige filternamen."""
    expr = f"min(max((iw*{x_fraction:.4f})-out_w/2,0),iw-out_w)"
    return expr.replace(",", "\\,")


def render_clip(raw_video_url, start_seconds, duration_seconds, output_path, x_fraction):
    """Snijdt en cropt met ffmpeg direct uit het HLS-manifest -- geen aparte
    downloadstap. Crop naar 9:16 gecentreerd op x_fraction (zie
    detect_speaker_x_fraction/moduledocstring), daarna geschaald naar
    OUTPUT_WIDTH x OUTPUT_HEIGHT."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    crop_x = build_crop_x_expr(x_fraction)
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
        f"crop=ih*9/16:ih:{crop_x}:0,scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}",
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

        # Eén frame aan het begin van het clip-venster is genoeg om de
        # spreker te lokaliseren -- geen losse frames door de hele clip heen
        # nodig, de camera staat binnen zo'n korte clip vrijwel altijd stil.
        with tempfile.TemporaryDirectory() as tmp_dir:
            frame_path = Path(tmp_dir) / "frame.png"
            try:
                extract_frame(entry["row"]["raw_video_url"], start, frame_path)
                x_fraction = detect_speaker_x_fraction(frame_path)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FaceDetectionError) as exc:
                logger.error("Crop-detectie mislukt voor %s, clip overgeslagen: %s", entry["row"]["debatdirect_id"], exc)
                continue
        logger.info("crop x_fraction=%.3f voor %s", x_fraction, entry["row"]["debatdirect_id"])

        try:
            render_clip(entry["row"]["raw_video_url"], start, duration, output_path, x_fraction)
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
