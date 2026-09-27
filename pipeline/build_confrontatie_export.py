"""
Confrontatie-as-export: combineert de argumentenboom-pipeline-output
(data/export/argument-docs/<slug>-gemini-tree.json, zie
pipeline/prompts/argument_tree_gemini.md +
pipeline/prompts/boomredactie_rebuttal_detection.md/boomredactie_support_check.md
+ pipeline/confrontatie_tree.py -- samen "de redactiestap", zie
scripts/argument_tree/agy_run_confrontatie_tree.py) met de volledige argumentgegevens uit
de database, tot de JSON die de nieuwe ArgumentTree.vue (pro links, contra
rechts, gestapeld in confrontatie-"banden") nodig heeft.

GEEN LLM-call, GEEN inhoud verzonnen -- puur een mechanische samenvoeging.
Vervangt pipeline/build_argument_tree.py (de oude aanpak liep vast op de
contextlimiet van een lokaal model bij grote topics, zie PR #48).

Invoerformaat (pipeline/schemas/argument_tree.schema.json): een platte
lijst `nodes` en een lijst getypeerde `relations` (support/conflict, AIF-
kern, zie pipeline/schemas/argument_relations.schema.json). Een support-
relatie bepaalt de ouder/kind-structuur (`kids`); een conflict-relatie
levert een band op. `stance` van elk argument komt uit de database, niet uit
de tree-JSON -- die kent alleen argument_id's, geen kant-indeling.

Gebruik:
    uv run python -m pipeline.build_confrontatie_export --topic stikstof
"""

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from pipeline.db import db
from pipeline.periodes import PeriodeIndex

logger = logging.getLogger(__name__)

GEMINI_TREE_DIR = Path(__file__).parent.parent / "data" / "export" / "argument-docs"
TREE_EXPORT_DIR = Path(__file__).parent.parent / "data" / "export" / "argument-trees"


def _build_registry(tree, stance_by_id):
    """Eén rij per node uit de tree: gist/samenvatting uit de tree zelf,
    stance uit de database (de tree-JSON kent geen kant-indeling), children
    en top_id afgeleid uit de support-relaties. `children` is een platte
    lijst kid-objecten ({id, scheme, reden}, zie
    pipeline/schemas/argument_tree.schema.json): zowel een simpele
    onderbouwing (1 premisse) als een coördinatieve steungroep (meerdere
    premissen die een target gezamenlijk dragen) leveren kid-kaarten op,
    geen apart begrip in de export. `reden` is de korte, per-relatie
    onderbouwing van de redactiecheck (issue #252) -- waarom dit argument
    aantoonbaar een reden geeft om de ouder te geloven."""
    registry = {}
    for node in tree["nodes"]:
        nid = node["argument_id"]
        if nid not in stance_by_id:
            raise ValueError(f"argument_id {nid} uit de argumentenboom niet gevonden in de database")
        registry[nid] = {
            "id": nid, "gist": node["gist"], "samenvatting": node.get("samenvatting"),
            "stance": stance_by_id[nid], "children": [], "parent_id": None,
        }

    for relation in tree["relations"]:
        if relation["relation_type"] != "support":
            continue
        target_id = relation["target_argument_id"]
        for premise_id in relation["premise_argument_ids"]:
            registry[target_id]["children"].append({
                "id": premise_id,
                "scheme": relation.get("scheme"),
                "reden": relation.get("reden", ""),
                "sterkte": relation.get("sterkte"),
            })
            registry[premise_id]["parent_id"] = target_id

    for entry in registry.values():
        top = entry
        while top["parent_id"] is not None:
            top = registry[top["parent_id"]]
        entry["top_id"] = top["id"]

    return registry


def build_bands_and_losse(tree, stance_by_id):
    """Zuivere functie (geen DB) die de argumentenboom omzet naar banden +
    "losse" (niet-weersproken) argumenten/groepen. Kernidee: één band per
    conflict-relatie, geankerd op de top-level voorouder van elke kant. Ligt
    die voorouder al vast als de "echte kaart" van een eerdere band (bv.
    omdat een ander kind van dezelfde voorouder al eerder een conflict had),
    dan krijgt deze band een verwijskaart (`ref`) naar die eerdere band in
    plaats van een duplicaat -- exact de aanpak die in de ontwerpgids
    "cross-band" heet."""
    registry = _build_registry(tree, stance_by_id)

    claimed = {}  # top_id -> band-index waar deze voorouder al een "echte kaart" heeft
    bands = []

    for relation in tree["relations"]:
        if relation["relation_type"] != "conflict":
            continue
        if len(relation["premise_argument_ids"]) != 1:
            raise ValueError(f"conflict-relatie met meer dan 1 premisse wordt nog niet ondersteund: {relation!r}")
        a_id, b_id = relation["premise_argument_ids"][0], relation["target_argument_id"]
        a, b = registry.get(a_id), registry.get(b_id)
        if a is None or b is None:
            raise ValueError(f"conflict-relatie verwijst naar onbekend argument_id: {relation!r}")
        if a["stance"] == b["stance"]:
            raise ValueError(f"conflict-relatie tussen twee argumenten met dezelfde stance: {relation!r}")
        pro_side, contra_side = (a, b) if a["stance"] == "pro" else (b, a)

        band_index = len(bands)
        pro_slot = _resolve_slot(pro_side, claimed, band_index)
        contra_slot = _resolve_slot(contra_side, claimed, band_index)
        # `thema` komt idealiter uit de structureringsstap (het daadwerkelijke
        # geschilpunt). Ontbreekt het, val terug op de mechanische
        # samenvoeging van de twee gists -- geen nieuwe tekst verzinnen.
        thema = relation.get("thema") or f"{pro_side['gist']} vs {contra_side['gist']}"
        bands.append(
            {
                "nummer": band_index + 1,
                "thema": thema,
                "pro": pro_slot,
                "contra": contra_slot,
                "oppositie": {
                    "argument_a_id": a_id,
                    "argument_b_id": b_id,
                    "scheme": relation.get("scheme"),
                    "reden": relation.get("reden", ""),
                    "sterkte": relation.get("sterkte"),
                },
            }
        )

    banded_top_ids = {top_id for top_id, band_index in claimed.items()}
    top_level = [
        {"kind": "argument", "id": entry["id"]}
        for entry in registry.values()
        if entry["parent_id"] is None
    ]
    group_member_ids = set()
    for groep in tree.get("coordinatieve_groepen", []):
        for mid in groep["argument_ids"]:
            if mid not in registry:
                raise ValueError(f"coordinatieve_groepen verwijst naar argument_id {mid} dat niet in nodes[] staat")
            group_member_ids.add(mid)

    losse_groepen = [
        {
            "kind": "group",
            "label": groep["label"],
            "samenvatting": groep.get("samenvatting"),
            "member_ids": groep["argument_ids"],
        }
        for groep in tree.get("coordinatieve_groepen", [])
        if not any(mid in banded_top_ids for mid in groep["argument_ids"])
    ]
    # Een groepslid dat zelf ook in een band zit heeft daar al zijn eigen
    # kaart (zie hierboven); staat het in geen enkele band, dan leeft het
    # uitsluitend via de groepsbundel hierboven -- nooit ook nog los als
    # eigen "losse_argumenten"-entry, dat zou het lid dubbel tonen.
    losse_argumenten = [
        entry["id"]
        for entry in top_level
        if entry["id"] not in banded_top_ids and entry["id"] not in group_member_ids
    ]

    return {"registry": registry, "bands": bands, "losse_groepen": losse_groepen, "losse_argumenten": losse_argumenten}


def _resolve_slot(side, claimed, band_index):
    """`side` is de registry-entry van het daadwerkelijk weersproken
    argument (kan genest zijn). De "echte kaart" hoort altijd bij de
    top-level voorouder (met diens eigen kinderen als onderbouwing eronder)
    -- de eerste keer dat die voorouder voorkomt. Komt dezelfde voorouder
    later nogmaals voor (bv. omdat een ánder kind van hem apart wordt
    weersproken), dan krijgt die latere band een verwijskaart (`ref`) naar
    de band waar de echte kaart al staat, met een lijn naar het daadwerkelijk
    weersproken (mogelijk geneste) argument -- de "cross-band"-route uit de
    ontwerpgids. `kids` wordt door de caller ingevuld zodra de
    registry-lookup voorhanden is (zie build_export)."""
    top_id = side["top_id"]
    if top_id not in claimed:
        claimed[top_id] = band_index
        return {"type": "node", "id": top_id, "kids": []}
    return {"type": "ref", "ref_id": side["id"], "band_nummer": claimed[top_id] + 1}


def fetch_arguments_by_id(conn, argument_ids):
    """Volledige argumentgegevens (citaat, spreker, tags, claims, links)
    voor precies de id's die in de argumentenboom voorkomen -- zelfde
    veldenset als export_argument_doc.py::fetch_stance_arguments, maar
    gefilterd op id's i.p.v. op stance/datum/limit."""
    if not argument_ids:
        return {}
    placeholders = ",".join("?" * len(argument_ids))
    rows = conn.execute(
        f"""SELECT ar.id, ar.quote_text, ar.typology, ar.stance, ar.start_seconds, ac.name AS actor_name, ac.party AS actor_party,
                   d.tweedekamer_activiteit_url, d.raw_video_url
            FROM arguments ar
            JOIN actors ac ON ac.id = ar.actor_id
            JOIN documents d ON d.id = ar.document_id
            WHERE ar.id IN ({placeholders})""",
        argument_ids,
    ).fetchall()

    tags_by_argument = {}
    for tag in conn.execute(
        f"""SELECT at.argument_id, t.sleutel
            FROM argument_tags at
            JOIN tags t ON t.sleutel = at.tag_sleutel
            WHERE at.argument_id IN ({placeholders}) AND t.active = 1""",
        argument_ids,
    ).fetchall():
        tags_by_argument.setdefault(tag["argument_id"], []).append(tag["sleutel"])

    claims_by_argument = {}
    for claim in conn.execute(
        f"""SELECT c.argument_id, c.claim_text, c.attributed_source_text
            FROM claims c
            WHERE c.argument_id IN ({placeholders})""",
        argument_ids,
    ).fetchall():
        claims_by_argument.setdefault(claim["argument_id"], []).append(
            {"claim_text": claim["claim_text"], "attributed_source_text": claim["attributed_source_text"]}
        )

    arguments = {}
    for row in rows:
        arguments[row["id"]] = {
            "id": row["id"],
            "citaat": row["quote_text"],
            "typologie": row["typology"],
            "stance": row["stance"],
            "spreker": row["actor_name"],
            "partij": row["actor_party"],
            "tags": tags_by_argument.get(row["id"], []),
            "claims": claims_by_argument.get(row["id"], []),
            "tweedekamer_activiteit_url": row["tweedekamer_activiteit_url"],
            "raw_video_url": row["raw_video_url"],
            "start_seconds": row["start_seconds"],
        }
    return arguments


def fetch_topic_stats(conn, topic_id, vanaf):
    stats = {}
    for stance in ("pro", "contra", "unclear"):
        stats[stance] = conn.execute(
            """SELECT COUNT(*) c FROM arguments ar
               JOIN documents d ON d.id = ar.document_id
               WHERE ar.topic_id = ? AND ar.stance = ? AND d.published_at >= ?""",
            (topic_id, stance, vanaf),
        ).fetchone()["c"]
    return stats


def build_export(conn, topic_row, tree, vanaf):
    all_ids = [node["argument_id"] for node in tree["nodes"]]
    arguments = fetch_arguments_by_id(conn, all_ids)
    stance_by_id = {nid: arg["stance"] for nid, arg in arguments.items()}

    result = build_bands_and_losse(tree, stance_by_id)
    registry, bands = result["registry"], result["bands"]

    for nid, entry in registry.items():
        arguments[nid]["gist"] = entry["gist"]
        arguments[nid]["samenvatting"] = entry["samenvatting"]

    for band in bands:
        for side_key in ("pro", "contra"):
            slot = band[side_key]
            if slot is not None and slot["type"] == "node":
                slot["kids"] = registry[slot["id"]]["children"]

    twijfelachtige_classificaties = tree.get("twijfelachtige_classificaties", [])
    topic_stats = fetch_topic_stats(conn, topic_row["id"], vanaf)

    return {
        "slug": topic_row["slug"],
        "name": topic_row["name"],
        "topic_description": topic_row["description"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "totaal_argumenten": sum(topic_stats.values()),
            "aantal_pro": topic_stats["pro"],
            "aantal_contra": topic_stats["contra"],
            "aantal_geselecteerd": len(all_ids),
        },
        "arguments": arguments,
        "bands": bands,
        "losse_groepen": result["losse_groepen"],
        "losse_argumenten": result["losse_argumenten"],
        "twijfelachtige_classificaties": twijfelachtige_classificaties,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", required=True, help="topic-slug, bv. stikstof")
    parser.add_argument(
        "--tree", dest="tree_path", default=None,
        help="pad naar de argumentenboom-JSON (default: data/export/argument-docs/<topic>-gemini-tree.json)",
    )
    parser.add_argument(
        "--vanaf", default=None, help="ISO-datum; overschrijft [verwerking].vanaf uit config/politieke-periodes.toml"
    )
    parser.add_argument("--out", default=None, help="uitvoerpad (default: data/export/argument-trees/<topic>.json)")
    parser.add_argument("--dry-run", action="store_true", help="niets wegschrijven, alleen printen")
    args = parser.parse_args()

    tree_path = Path(args.tree_path) if args.tree_path else GEMINI_TREE_DIR / f"{args.topic}-gemini-tree.json"
    if not tree_path.exists():
        raise SystemExit(f"argumentenboom niet gevonden: {tree_path}")
    tree = json.loads(tree_path.read_text())

    conn = db.connect()
    topic_row = conn.execute("SELECT id, slug, name, description FROM topics WHERE slug = ?", (args.topic,)).fetchone()
    if topic_row is None:
        raise SystemExit(f"onbekende topic-slug: {args.topic}")

    vanaf = args.vanaf if args.vanaf is not None else PeriodeIndex().drempel

    export = build_export(conn, topic_row, tree, vanaf)
    conn.close()

    logger.info(
        "topic=%s %d argumenten geselecteerd, %d confrontatie-banden, %d losse groepen, %d losse argumenten",
        topic_row["slug"], export["stats"]["aantal_geselecteerd"], len(export["bands"]),
        len(export["losse_groepen"]), len(export["losse_argumenten"]),
    )

    if args.dry_run:
        print(json.dumps(export, ensure_ascii=False, indent=2))
        logger.info("(--dry-run: niets weggeschreven)")
        return

    out_path = Path(args.out) if args.out else TREE_EXPORT_DIR / f"{args.topic}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(export, ensure_ascii=False, indent=2))
    logger.info("Confrontatie-export -> %s", out_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
