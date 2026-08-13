"""
Confrontatie-as-export: combineert Gemini's structurering van een topic
(data/export/argument-docs/<slug>-gemini-tree.json, zie
pipeline/prompts/argument_tree_gemini.md) met de volledige argumentgegevens
uit de database, tot de JSON die de nieuwe ArgumentTree.vue (pro links,
contra rechts, gestapeld in confrontatie-"banden") nodig heeft.

GEEN LLM-call, GEEN inhoud verzonnen -- puur een mechanische samenvoeging.
Vervangt pipeline/build_argument_tree.py (de oude aanpak liep vast op de
contextlimiet van een lokaal model bij grote topics, zie PR #48); het
Gemini-traject via export_argument_doc.py + een handmatige Gemini-stap is de
opvolger.

Het `thema` per band en de `samenvatting` per gebundelde node/groep komen,
indien aanwezig, letterlijk uit de Gemini-tree (zie
pipeline/prompts/argument_tree_gemini.md, stap 3) -- dit script verzint geen
tekst, het geeft alleen door wat Gemini al leverde. Ontbreken deze velden
(oudere gemini-tree.json zonder stap-3-output), dan valt `thema` terug op een
mechanische samenvoeging van de twee gists ("Confrontatie N"-achtig
placeholder-gedrag) en blijft `samenvatting` leeg.

Gebruik:
    uv run python -m pipeline.build_confrontatie_export --topic stikstof
"""

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from pipeline.build_static_data import _speaker_event_url
from pipeline.db import db
from pipeline.periodes import PeriodeIndex

logger = logging.getLogger(__name__)

GEMINI_TREE_DIR = Path(__file__).parent.parent / "data" / "export" / "argument-docs"
TREE_EXPORT_DIR = Path(__file__).parent.parent / "data" / "export" / "argument-trees"


def _flatten_stance(nodes, stance, registry, top_level, group_index_start=0):
    """Indexeert elk argument-knooppunt (los of lid van een coördinatieve
    groep) in `registry` (id -> {gist, stance, children, top_id}), en
    verzamelt de top-level entries (losse argumenten + groepen) in
    `top_level` voor de "buiten de confrontatie"-sectie.

    `top_id` is de top-level voorouder van een knoop: voor een top-level
    argument is dat zijn eigen id, voor een genest (subordinatief) kind het
    id van de voorouder waar het onder hangt. Dat is precies wat de
    band-opbouw hieronder nodig heeft om te bepalen of een knoop al "ergens
    woont" (zie _build_bands)."""
    group_index = group_index_start
    for node in nodes:
        if "argument_id" in node:
            nid = node["argument_id"]
            children = node.get("children") or []
            child_ids = [c["argument_id"] for c in children if "argument_id" in c]
            registry[nid] = {
                "id": nid, "gist": node["gist"], "samenvatting": node.get("samenvatting"),
                "stance": stance, "children": child_ids, "top_id": nid,
            }
            top_level.append({"kind": "argument", "id": nid})
            _mark_descendants(children, stance, registry, top_id=nid)
        elif "label" in node:
            member_ids = []
            for member in node.get("arguments", []):
                mid = member["argument_id"]
                # Een groepslid heeft geen eigen "kaart" op groepsniveau (de
                # groep zelf leeft alleen in losse_groepen) -- wordt het lid
                # los weersproken, dan is het lid zelf de top-level voorouder
                # voor de band-opbouw, net als een gewoon top-level argument.
                registry[mid] = {
                    "id": mid, "gist": member["gist"], "samenvatting": None, "stance": stance, "children": [],
                    "top_id": mid,
                }
                member_ids.append(mid)
            top_level.append({
                "kind": "group", "label": node["label"], "samenvatting": node.get("samenvatting"),
                "member_ids": member_ids,
            })
            group_index += 1
        else:
            raise ValueError(f"onbekende knoopvorm in Gemini-tree: {node!r}")
    return group_index


def _mark_descendants(nodes, stance, registry, top_id):
    for node in nodes:
        if "argument_id" not in node:
            continue
        nid = node["argument_id"]
        children = node.get("children") or []
        child_ids = [c["argument_id"] for c in children if "argument_id" in c]
        registry[nid] = {
            "id": nid, "gist": node["gist"], "samenvatting": None, "stance": stance,
            "children": child_ids, "top_id": top_id,
        }
        _mark_descendants(children, stance, registry, top_id)


def build_bands_and_losse(gemini_tree):
    """Zuivere functie (geen DB) die de Gemini-tree omzet naar banden +
    "losse" (niet-weersproken) argumenten/groepen. Zie moduledocstring voor
    de band-regels; kernidee: één band per oppositie-paar, geankerd op de
    top-level voorouder van elke kant. Ligt die voorouder al vast als de
    "echte kaart" van een eerdere band (bv. omdat een ander kind van
    dezelfde voorouder al eerder een oppositie had), dan krijgt deze band
    een verwijskaart (`ref`) naar die eerdere band in plaats van een
    duplicaat -- exact de aanpak die in de ontwerpgids "cross-band" heet."""
    registry = {}
    pro_top, contra_top = [], []
    _flatten_stance(gemini_tree.get("pro", {}).get("nodes", []), "pro", registry, pro_top)
    _flatten_stance(gemini_tree.get("contra", {}).get("nodes", []), "contra", registry, contra_top)

    claimed = {}  # top_id -> band-index waar deze voorouder al een "echte kaart" heeft
    bands = []

    for opp in gemini_tree.get("oppositions", []):
        a_id, b_id = opp["argument_a_id"], opp["argument_b_id"]
        a, b = registry.get(a_id), registry.get(b_id)
        if a is None or b is None:
            raise ValueError(f"oppositie verwijst naar onbekend argument_id: {opp!r}")
        if a["stance"] == b["stance"]:
            raise ValueError(f"oppositie tussen twee argumenten met dezelfde stance: {opp!r}")
        pro_side, contra_side = (a, b) if a["stance"] == "pro" else (b, a)

        band_index = len(bands)
        pro_slot = _resolve_slot(pro_side, claimed, band_index)
        contra_slot = _resolve_slot(contra_side, claimed, band_index)
        # `thema` komt idealiter van Gemini (het daadwerkelijke geschilpunt,
        # zie argument_tree_gemini.md stap 3). Ontbreekt het (oudere
        # gemini-tree.json zonder dit veld), val terug op de mechanische
        # samenvoeging van de twee gists -- geen nieuwe tekst verzinnen.
        thema = opp.get("thema") or f"{pro_side['gist']} vs {contra_side['gist']}"
        bands.append(
            {
                "nummer": band_index + 1,
                "thema": thema,
                "pro": pro_slot,
                "contra": contra_slot,
                "oppositie": {"argument_a_id": a_id, "argument_b_id": b_id, "relation_type": opp["relation_type"]},
            }
        )

    banded_top_ids = {top_id for top_id, band_index in claimed.items()}
    losse_groepen = [
        entry
        for entry in pro_top + contra_top
        if entry["kind"] == "group" and not any(mid in banded_top_ids for mid in entry["member_ids"])
    ]
    losse_argumenten = [
        entry["id"]
        for entry in pro_top + contra_top
        if entry["kind"] == "argument" and entry["id"] not in banded_top_ids
    ]

    return {"registry": registry, "bands": bands, "losse_groepen": losse_groepen, "losse_argumenten": losse_argumenten}


def _resolve_slot(side, claimed, band_index):
    """`side` is de registry-entry van de daadwerkelijk weersproken knoop
    (kan genest zijn). De "echte kaart" hoort altijd bij de top-level
    voorouder (met diens eigen kinderen als onderbouwing eronder) -- de
    eerste keer dat die voorouder voorkomt. Komt dezelfde voorouder later
    nogmaals voor (bv. omdat een ánder kind van hem apart wordt weersproken),
    dan krijgt die latere band een verwijskaart (`ref`) naar de band waar de
    echte kaart al staat, met een lijn naar de daadwerkelijk weersproken
    (mogelijk geneste) knoop -- de "cross-band"-route uit de ontwerpgids.
    `kids` wordt door de caller ingevuld zodra de registry-lookup voorhanden
    is (zie build_export)."""
    top_id = side["top_id"]
    if top_id not in claimed:
        claimed[top_id] = band_index
        return {"type": "node", "id": top_id, "kids": []}
    return {"type": "ref", "ref_id": side["id"], "band_nummer": claimed[top_id] + 1}


def fetch_arguments_by_id(conn, argument_ids):
    """Volledige argumentgegevens (citaat, spreker, tags, claims, links)
    voor precies de id's die in de Gemini-tree voorkomen -- zelfde
    veldenset als export_argument_doc.py::fetch_stance_arguments, maar
    gefilterd op id's i.p.v. op stance/datum/limit."""
    if not argument_ids:
        return {}
    placeholders = ",".join("?" * len(argument_ids))
    rows = conn.execute(
        f"""SELECT ar.id, ar.quote_text, ar.typology, ar.stance, ac.name AS actor_name, ac.party AS actor_party,
                   d.tweedekamer_activiteit_url, d.video_url, d.published_at
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
            "speaker_video_url": _speaker_event_url(row["video_url"], row["published_at"]),
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


def build_export(conn, topic_row, gemini_tree, vanaf):
    result = build_bands_and_losse(gemini_tree)
    registry, bands = result["registry"], result["bands"]

    all_ids = list(registry.keys())
    arguments = fetch_arguments_by_id(conn, all_ids)
    for nid, entry in registry.items():
        if nid not in arguments:
            raise ValueError(f"argument_id {nid} uit de Gemini-tree niet gevonden in de database")
        arguments[nid]["gist"] = entry["gist"]
        arguments[nid]["samenvatting"] = entry["samenvatting"]

    for band in bands:
        for side_key in ("pro", "contra"):
            slot = band[side_key]
            if slot is not None and slot["type"] == "node":
                slot["kids"] = registry[slot["id"]]["children"]

    twijfelachtige_classificaties = gemini_tree.get("twijfelachtige_classificaties", [])
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
        "--gemini-tree", default=None,
        help="pad naar de Gemini-tree JSON (default: data/export/argument-docs/<topic>-gemini-tree.json)",
    )
    parser.add_argument(
        "--vanaf", default=None, help="ISO-datum; overschrijft [verwerking].vanaf uit data/politieke-periodes.toml"
    )
    parser.add_argument("--out", default=None, help="uitvoerpad (default: data/export/argument-trees/<topic>.json)")
    parser.add_argument("--dry-run", action="store_true", help="niets wegschrijven, alleen printen")
    args = parser.parse_args()

    gemini_tree_path = Path(args.gemini_tree) if args.gemini_tree else GEMINI_TREE_DIR / f"{args.topic}-gemini-tree.json"
    if not gemini_tree_path.exists():
        raise SystemExit(f"Gemini-tree niet gevonden: {gemini_tree_path}")
    gemini_tree = json.loads(gemini_tree_path.read_text())

    conn = db.connect()
    topic_row = conn.execute("SELECT id, slug, name, description FROM topics WHERE slug = ?", (args.topic,)).fetchone()
    if topic_row is None:
        raise SystemExit(f"onbekende topic-slug: {args.topic}")

    vanaf = args.vanaf if args.vanaf is not None else PeriodeIndex().drempel

    export = build_export(conn, topic_row, gemini_tree, vanaf)
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
