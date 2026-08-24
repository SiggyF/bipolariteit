"""
Enrichmentstap: vult documents.video_url en documents.debatdirect_id via
Debat Direct's agenda-API, geen LLM. Idem aan `tkconv`'s aanpak (zie
docs/tk-data-sources-overview.md #4): queryt Debat Direct op debatdatum,
matcht de kandidaat met de dichtstbijzijnde starttijd t.o.v.
documents.activiteit_aanvangstijd, met een duur-ratio-sanitycheck als extra
filter tegen een verkeerde match. debatdirect_id is nodig voor de
ondertitel-sync-stap (pipeline/fetch_subtitles.py).

Gebruikt `https://cdn.debatdirect.tweedekamer.nl/api/agenda/{date}` (niet in
docs/tk-data-sources-overview.md, ontdekt tijdens issue #198-vervolg): geeft
de volledige dagagenda in één call terug (i.p.v. de gepagineerde `/search`),
inclusief `startedAt`/`endedAt` (werkelijke i.p.v. geplande tijden). Wordt
per unieke datum gecached binnen een run, want meerdere activiteiten delen
vaak dezelfde datum.

Matching gebeurt op activiteit-niveau (elke groep documenten met dezelfde
(activiteit_aanvangstijd, activiteit_eindtijd) hoort bij één Kamerdebat),
niet per document -- anders zou elk document in hetzelfde debat een aparte
zoekopdracht kosten voor exact dezelfde uitkomst.

Idempotent via documents.debatdirect_id IS NULL; een debat waarvoor geen
bevredigende match gevonden wordt, blijft NULL (geen gok, geen foutieve link).

Gebruik:
    uv run python -m pipeline.enrich_video_url [--topic stikstof|plenair] [--dry-run] [--limit N]

Zonder --topic: alle topics plus de documenten zonder topic ("overig
plenair" op de plenaire kaart), zodat een nieuw topic of een topic waarvoor
deze stap nog nooit gedraaid is niet stilzwijgend achterblijft (zie issue
#83). Draait ook automatisch mee in `make export`. --topic plenair verwerkt
losstaand alleen de topic_id IS NULL-documenten (bv. voor een steekproef via
--limit voordat de volledige ~144k-batch gedraaid wordt).
"""

import argparse
import logging
from datetime import datetime, timedelta

import requests

from pipeline.db import db

logger = logging.getLogger(__name__)

AGENDA_URL = "https://cdn.debatdirect.tweedekamer.nl/api/agenda/{date}"

# Een kandidaat moet binnen dit venster starten t.o.v. onze activiteit_aanvangstijd
# om als match te tellen -- ruim boven de "2 min vs. ~3 uur"-disambiguatie die al
# eerder empirisch bevestigd is (zie docs/tk-data-sources-overview.md #5), maar
# strikt genoeg om nooit een compleet ander debat te pakken.
MAX_START_DIFF_SECONDS = 5 * 60
# Duur-ratio-sanitycheck (zoals tkconv doet): een kandidaat wiens duur meer dan
# een factor 2 afwijkt van onze eigen duur is vermoedelijk het verkeerde debat,
# ook als de starttijd toevallig dichtbij ligt.
MAX_DURATION_RATIO = 2.0

# Debat Direct indexeert een vergadering onder de kalenderdag waarop ze begon,
# niet de dag van elk afzonderlijk moment erin. Een laat-avondvergadering met
# stemmingen die over middernacht doorloopt, krijgt dus als aanvangstijd bv.
# "2023-07-07T01:04:12" (ná middernacht) terwijl Debat Direct 'm indexeert
# onder "2023-07-06". Zoek daarom ook de vorige kalenderdag mee als onze
# aanvangstijd vroeg in de nacht valt (zie issue #83).
EARLY_HOUR_THRESHOLD = 6


def fetch_pending_activiteiten(conn, topic_id, limit=None):
    """Distincte (aanvangstijd, eindtijd)-paren zonder debatdirect_id, met de
    document-id's die bijgewerkt moeten worden zodra een match gevonden is.
    Sleutel op debatdirect_id i.p.v. video_url zodat rijen die al vóór dit
    veld bestonden (video_url dus al gevuld) hier ook doorheen lopen -- dit
    dient meteen als backfill voor debatdirect_id, zonder los script.

    topic_id=None betekent topic_id IS NULL: documenten zonder topic
    ("overig plenair" op de plenaire kaart), niet gedekt door een van de
    vier gecureerde topics. limit beperkt het aantal activiteiten (niet
    documenten) -- handig voor een steekproef voordat de volle batch draait."""
    topic_clause = "topic_id IS NULL" if topic_id is None else "topic_id = ?"
    params = () if topic_id is None else (topic_id,)
    rows = conn.execute(
        f"""SELECT id, activiteit_aanvangstijd, activiteit_eindtijd
           FROM documents
           WHERE {topic_clause} AND debatdirect_id IS NULL AND activiteit_aanvangstijd IS NOT NULL
           ORDER BY id""",
        params,
    ).fetchall()

    groups = {}
    for row in rows:
        key = (row["activiteit_aanvangstijd"], row["activiteit_eindtijd"])
        if limit is not None and key not in groups and len(groups) >= limit:
            continue
        groups.setdefault(key, []).append(row["id"])
    return groups


def _parse_dt(value):
    # Debat Direct: "2026-07-01T13:35:26+0200" (geen ':' in de offset).
    # Onze eigen kolommen: "2026-07-01T13:35:26" (naive, lokale VLOS-tijd).
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def search_dates_for(aanvangstijd):
    """Kalenderdagen om op Debat Direct te doorzoeken voor een gegeven
    activiteit_aanvangstijd. Meestal alleen die dag zelf; bij een vroege
    starttijd (over-middernacht-vergadering) ook de dag ervoor, want Debat
    Direct indexeert zo'n vergadering onder de dag waarop ze begon."""
    start_dt = _parse_dt(aanvangstijd)
    date_str = aanvangstijd[:10]
    if start_dt is not None and start_dt.hour < EARLY_HOUR_THRESHOLD:
        previous_day = (start_dt.date() - timedelta(days=1)).isoformat()
        return [previous_day, date_str]
    return [date_str]


def fetch_agenda(session, date_str):
    """Volledige dagagenda in één call (geen paginering nodig, i.t.t. de
    oudere `/search`-aanpak). Lege/onbekende datums geven netjes
    `{"debates": []}` terug (bevestigd, ook voor duidelijk absurde datums)."""
    resp = session.get(AGENDA_URL.format(date=date_str), timeout=15)
    resp.raise_for_status()
    return resp.json().get("debates", [])


def find_best_match(candidates, our_start, our_end):
    our_start_dt = _parse_dt(our_start)
    our_end_dt = _parse_dt(our_end)
    if our_start_dt is None:
        return None
    our_duration = (our_end_dt - our_start_dt).total_seconds() if our_end_dt else None

    best, best_diff = None, None
    for cand in candidates:
        # startedAt/endedAt (werkelijke tijden, agenda-API) zijn nauwkeuriger
        # dan startsAt/endsAt (geplande tijden) -- gebruik ze als aanwezig.
        cand_start_dt = _parse_dt(cand.get("startedAt") or cand.get("startsAt"))
        if cand_start_dt is None:
            continue
        diff = abs((cand_start_dt.replace(tzinfo=None) - our_start_dt).total_seconds())
        if diff > MAX_START_DIFF_SECONDS:
            continue

        if our_duration and our_duration > 0:
            cand_end_dt = _parse_dt(cand.get("endedAt") or cand.get("endsAt"))
            if cand_end_dt:
                cand_duration = (cand_end_dt.replace(tzinfo=None) - cand_start_dt.replace(tzinfo=None)).total_seconds()
                if cand_duration <= 0:
                    continue
                ratio = max(cand_duration, our_duration) / min(cand_duration, our_duration)
                if ratio > MAX_DURATION_RATIO:
                    continue

        if best is None or diff < best_diff:
            best, best_diff = cand, diff
    return best


def build_video_url(candidate):
    category_ids = candidate.get("categoryIds") or []
    if not category_ids or not candidate.get("locationId") or not candidate.get("slug") or not candidate.get("debateDate"):
        return None
    return (
        f"https://debatdirect.tweedekamer.nl/{candidate['debateDate']}/"
        f"{category_ids[0]}/{candidate['locationId']}/{candidate['slug']}/video"
    )


PLENAIR_KEYWORD = "plenair"  # magic --topic-waarde voor topic_id IS NULL ("overig plenair")


def enrich(topic_keyword, dry_run=False, limit=None):
    conn = db.connect()
    try:
        if topic_keyword == PLENAIR_KEYWORD:
            _enrich_topic(conn, None, dry_run=dry_run, limit=limit)
            return
        topic_row = conn.execute("SELECT id FROM topics WHERE slug = ?", (topic_keyword,)).fetchone()
        if topic_row is None:
            raise SystemExit(f"onbekende topic-slug: {topic_keyword}")
        _enrich_topic(conn, topic_row["id"], dry_run=dry_run, limit=limit)
    finally:
        conn.close()


def enrich_all(dry_run=False, limit=None):
    """Alle topics in één keer, plus de documenten zonder topic ("overig
    plenair"), zodat een nieuw topic of een topic met verouderde
    video_url-dekking nooit los onthouden hoeft te worden -- zie issue #83
    (39% ontbrekende video_url's kwam doordat deze stap per topic
    handmatig gedraaid moest worden en dat voor nieuwe topics niet
    gebeurd was)."""
    conn = db.connect()
    try:
        topic_rows = conn.execute("SELECT id, slug FROM topics ORDER BY slug").fetchall()
        for topic_row in topic_rows:
            logger.info("=== topic: %s ===", topic_row["slug"])
            _enrich_topic(conn, topic_row["id"], dry_run=dry_run, limit=limit)
        logger.info("=== topic: (geen topic / overig plenair) ===")
        _enrich_topic(conn, None, dry_run=dry_run, limit=limit)
    finally:
        conn.close()


def _enrich_topic(conn, topic_id, dry_run=False, limit=None):
    groups = fetch_pending_activiteiten(conn, topic_id, limit=limit)
    if not groups:
        logger.info("Geen documenten zonder debatdirect_id met een bekende activiteit_aanvangstijd.")
        return

    session = requests.Session()
    agenda_by_date = {}  # datum-string -> debates, hergebruikt tussen activiteiten van dezelfde dag

    def agenda_for(date_str):
        if date_str not in agenda_by_date:
            try:
                agenda_by_date[date_str] = fetch_agenda(session, date_str)
            except requests.RequestException as exc:
                logger.error("Agenda-opvraag mislukt voor %s: %s", date_str, exc)
                agenda_by_date[date_str] = []
        return agenda_by_date[date_str]

    matched, unmatched = 0, 0
    for (aanvangstijd, eindtijd), document_ids in groups.items():
        date_strs = search_dates_for(aanvangstijd)
        candidates_by_key = {}
        for date_str in date_strs:
            for cand in agenda_for(date_str):
                key = (cand.get("slug"), cand.get("startsAt"))
                candidates_by_key[key] = cand
        candidates = list(candidates_by_key.values())

        best = find_best_match(candidates, aanvangstijd, eindtijd)
        if best is None:
            unmatched += 1
            logger.warning("Geen match voor activiteit %s–%s (%d documenten, %d kandidaten op die datum)",
                            aanvangstijd, eindtijd, len(document_ids), len(candidates))
            continue

        video_url = build_video_url(best)
        if video_url is None:
            unmatched += 1
            logger.warning("Match gevonden voor %s maar velden ontbreken om een URL te bouwen: %s", aanvangstijd, best.get("name"))
            continue

        matched += 1
        logger.info("Match: %s -> %s (%r, %d documenten)", aanvangstijd, video_url, best.get("name"), len(document_ids))
        if not dry_run:
            conn.executemany(
                "UPDATE documents SET video_url = ?, debatdirect_id = ? WHERE id = ?",
                [(video_url, best.get("id"), doc_id) for doc_id in document_ids],
            )

    if not dry_run:
        conn.commit()

    logger.info("Klaar: %d activiteiten gematcht, %d zonder match (van %d totaal).", matched, unmatched, len(groups))
    if dry_run:
        logger.info("(--dry-run: niets weggeschreven naar de database)")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--topic",
        help=f"topic-slug, bv. stikstof, of '{PLENAIR_KEYWORD}' voor documenten zonder topic (default: alle topics + {PLENAIR_KEYWORD})",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, help="beperk tot de eerste N activiteiten (voor een steekproef)")
    args = parser.parse_args()
    if args.topic:
        enrich(args.topic, dry_run=args.dry_run, limit=args.limit)
    else:
        enrich_all(dry_run=args.dry_run, limit=args.limit)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
