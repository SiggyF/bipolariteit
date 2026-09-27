"""
Bouwt data/export/plenair-map/plenair-map-videos.json vanuit documents.video_url --
vult "overig plenair"-documenten (topic_id IS NULL) aan die nog ontbraken
(zie issue #198-vervolg): er bestond geen generator-script voor dit bestand
in de repo, het origineel is verloren gegaan zonder ooit gecommit te zijn.

Bewust minimaal gescopet: schrijft alleen externe Debat Direct-deep-links
(is_internal=false), via hetzelfde bevestigd werkende `?event=`-formaat als
pipeline/build_static_data.py::_speaker_event_url (zie
docs/tk-data-sources-overview.md 5a) -- niet het `?pdt=`-formaat dat in de
verloren data stond, want dat is nooit als werkend bevestigd. Of een debat
ook een interne /debatten/{slug}/-pagina heeft wordt in de frontend bepaald
via debateId(raw_video_url)-matching tegen data/export/topics/*.json
(frontend/src/lib/debateId.ts) -- dat hier repliceren zou onnodig risico op
een verkeerde match toevoegen. In plaats daarvan: merge met het bestaande
bestand, bestaande entries (incl. is_internal=true voor de 4 gecureerde
topics) blijven ongemoeid, alleen ontbrekende document-id's worden
toegevoegd.

Gebruik:
    uv run python scripts/export_plenair_map_videos.py [--dry-run]
"""

import argparse
import json
import logging
from pathlib import Path

from pipeline.build_static_data import _speaker_event_url
from pipeline.db import db

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# data/export/plenair-map/ bundelt alle plenair-map-exportbestanden bij
# elkaar (issue #316) i.p.v. los tussen de rest van data/export/.
EXPORT_DIR = Path(__file__).parent.parent / "data" / "export" / "plenair-map"
EXPORT_PATH = EXPORT_DIR / "plenair-map-videos.json"
# data/export/plenair-map/plenair-map.json (niet frontend/public/data, dat
# mirrort de bipolariteit-data-submodule/gepubliceerd en loopt achter tot de
# volgende publicatie -- bv. PR #196's abortus-datumrangefix, 13->197
# punten, staat hier al wel in maar is nog niet gepubliceerd).
POINTS_PATH = EXPORT_DIR / "plenair-map.json"


def load_point_ids(points_path):
    raw = json.loads(points_path.read_text())
    return {row[0] for row in raw["points"]}


def build_entries(conn, point_ids):
    """point_ids: de document-id's die daadwerkelijk als punt in
    plenair-map.json voorkomen. Zonder deze filter zou dit bestand alle
    ~187k documenten met video_url bevatten i.p.v. de ~39k die de kaart
    ooit opvraagt (documenten die door pipeline/plenary_map/cluster.py's
    percentiel-trimming/sampling nooit een punt worden, zijn hier
    onnodige bagage) -- op schaal het verschil tussen een 3 MB en een
    50+ MB bestand."""
    rows = conn.execute(
        """SELECT id, video_url, published_at, speaker_event_anchor_at, turn_type, is_voorzitter_turn
           FROM documents
           WHERE video_url IS NOT NULL"""
    ).fetchall()

    entries = {}
    for row in rows:
        if row["id"] not in point_ids:
            continue
        href = _speaker_event_url(
            row["video_url"],
            row["published_at"],
            anchor_at=row["speaker_event_anchor_at"],
            turn_type=row["turn_type"],
            is_voorzitter_turn=bool(row["is_voorzitter_turn"]),
        )
        if href is None:
            continue
        entries[str(row["id"])] = {
            "href": href,
            "label": "Bekijk spreekbeurt op Debat Direct",
            "is_internal": False,
        }
    return entries


def export(dry_run=False, points_path=POINTS_PATH):
    point_ids = load_point_ids(points_path)
    conn = db.connect()
    try:
        new_entries = build_entries(conn, point_ids)
    finally:
        conn.close()

    existing = json.loads(EXPORT_PATH.read_text()) if EXPORT_PATH.exists() else {}
    added = 0
    for doc_id, entry in new_entries.items():
        if doc_id not in existing:
            existing[doc_id] = entry
            added += 1

    logger.info(
        "%d document(en) met video_url, %d nieuw toegevoegd (%d bestonden al), totaal %d entries.",
        len(new_entries), added, len(new_entries) - added, len(existing),
    )
    if dry_run:
        logger.info("(--dry-run: niets weggeschreven naar %s)", EXPORT_PATH)
        return

    EXPORT_PATH.write_text(json.dumps(existing, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    logger.info("Geschreven naar %s", EXPORT_PATH)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    export(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
