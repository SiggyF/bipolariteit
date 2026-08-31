"""
Codering van plenair-map-punten naar MVT-tilebytes (mapbox_vector_tile), per
`(z, x, y)`-tile uit het grid in `pipeline.tiling.grid`. Zie module-docstring
van `pipeline.tiling.build_pyramid` voor de volledige pijplijn.

Puntvolgorde in de brondata (`data/export/plenair-map.json`, geschreven door
`scripts/experiment_umap_documents.py:write_frontend_export`): `id, x, y,
topic_idx, actor_idx, party_idx, debate_idx, soort_idx, published_at, text,
cluster[, cluster_levels]`. De lookup-tabellen (`topics`, `actors`, `parties`,
`debates`, `soorten`) worden hier al opgelost naar strings, zodat een tile op
zichzelf leesbaar is zonder de losse lookup-arrays erbij nodig te hebben
(issue #253: zo blijft `cluster` gewoon een van de properties, machine-
leesbaar per punt). Het optionele 12e element (alleen aanwezig bij N-laagse
clustering, zie experiment_umap_documents.py's `--cluster-level-sizes`) is
een lijst cluster-ids per niveau (grofste eerst) -- MVT-properties moeten
scalair zijn, dus die wordt hier uitgepakt naar losse `cluster_l0`,
`cluster_l1`, ... properties i.p.v. één geneste lijst.
"""

from typing import Any

import mapbox_vector_tile

LAYER_NAME = "points"


def point_to_feature(point: list, lookups: dict[str, list[str]]) -> dict[str, Any]:
    """Eén punt-rij -> een MVT-feature-dict (geometry + properties)."""
    pid, x, y, topic_idx, actor_idx, party_idx, debate_idx, soort_idx, published_at, text, cluster, *rest = point
    properties = {
        "id": pid,
        "topic": lookups["topics"][topic_idx],
        "actor": lookups["actors"][actor_idx],
        "party": lookups["parties"][party_idx],
        "debate": lookups["debates"][debate_idx],
        "soort": lookups["soorten"][soort_idx],
        "published_at": published_at,
        "text": text,
        "cluster": cluster,
    }
    if rest:
        for level_idx, level_cluster_id in enumerate(rest[0]):
            properties[f"cluster_l{level_idx}"] = level_cluster_id

    return {
        # Zonder expliciete `id` laat mapbox_vector_tile het MVT-feature-id-veld
        # ongezet, wat bij decode voor elke feature als 0 terugkomt -- sommige
        # GIS-tools (bv. QGIS' vector-tile-provider) gebruiken dat id om
        # features te dedupliceren/te cachen, en toonden zo alle punten
        # onterecht als één punt. `pid` is al uniek (document-id).
        "id": pid,
        "geometry": f"POINT({x} {y})",
        "properties": properties,
    }


def encode_tile(points: list[list], lookups: dict[str, list[str]], bounds: tuple[float, float, float, float]) -> bytes:
    """Encodeer de punten die in één tile vallen naar MVT-bytes.

    `bounds` is de tile-bbox in native grid-eenheden (uit
    `pipeline.tiling.grid.tile_bounds`); `mapbox_vector_tile` gebruikt die als
    `quantize_bounds` om wereld-coördinaten naar tile-lokale integer-extent te
    schalen.
    """
    features = [point_to_feature(p, lookups) for p in points]
    layers = [{"name": LAYER_NAME, "features": features}]
    return mapbox_vector_tile.encode(
        layers,
        default_options={"quantize_bounds": bounds},
    )
