"""
Inverse Terminology & TK Numbered Topics Grid Generator voor de A0-printkaart (issue #215).

Berekent een continu semantisch grid over de 2D UMAP-kaart:
    (x, y) gridcoördinaten -> ruimtelijke k-NN over 135k punten ->
    dominante hiërarchische clusternamen (niveau 0 t/m 4), top-termen en
    gekoppeld officieel TK-Kamerstukdossier (nummer + titel).

Gebruik:
    uv run python scripts/a0_map/generate_a0_inverse_terminology.py \
        data/export/a0-map/maps/plenair-map-full.json \
        data/export/a0-map/inverse_terminology_grid.geojson \
        --grid data/export/a0-map/maps/plenair-map-full-grid.json \
        --clusters data/export/a0-map/maps/plenair-map-clusters-full.json \
        --dossiers data/export/tk_kamerstukdossiers.json \
        --grid-nx 80 \
        --grid-ny 112
"""

import json
import logging
from collections import Counter
from pathlib import Path

import click
import numpy as np
from scipy.spatial import cKDTree
from sklearn.feature_extraction.text import TfidfVectorizer

from scripts.a0_map.export_clusters_geojson import make_rescaler, flat_rescale

logger = logging.getLogger(__name__)


def load_clusters_data(clusters_path: Path):
    raw = json.loads(clusters_path.read_text(encoding="utf-8"))
    levels = raw.get("levels", [raw.get("coarse", []), raw.get("fine", [])])
    return levels


def build_dossier_matcher(dossiers_path: Path):
    if not dossiers_path.exists():
        return None

    raw_dossiers = json.loads(dossiers_path.read_text(encoding="utf-8"))
    dossier_numbers = [d["nummer"] for d in raw_dossiers]
    dossier_titles = [d["titel"] for d in raw_dossiers]

    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        token_pattern=r"(?u)\b[a-zA-ZÀ-ÿ]{3,}\b",
    )
    dossier_matrix = vectorizer.fit_transform(dossier_titles)

    def match_dossier(query_text: str) -> tuple[int | None, str | None, float]:
        if not query_text.strip():
            return None, None, 0.0
        query_vec = vectorizer.transform([query_text])
        sims = (dossier_matrix * query_vec.T).toarray().ravel()
        best_idx = int(np.argmax(sims))
        best_score = float(sims[best_idx])
        if best_score < 0.10:
            return None, None, best_score
        return dossier_numbers[best_idx], dossier_titles[best_idx], round(best_score, 2)

    return match_dossier


@click.command()
@click.argument("points_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("output_path", type=click.Path(dir_okay=False, path_type=Path))
@click.option("--grid", "grid_path", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None, help="Pad naar plenair-map-full-grid.json voor WGS84/EPSG:3857 uitlijning.")
@click.option("--flat", is_flag=True, default=False, help="Schrijf in rauwe UMAP-coördinaten zonder Mercator-rescaling.")
@click.option("--clusters", "clusters_path", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=Path("data/export/a0-map/maps/plenair-map-clusters-full.json"), help="Pad naar plenair-map-clusters-full.json.")
@click.option("--dossiers", "dossiers_path", type=click.Path(dir_okay=False, path_type=Path), default=Path("data/export/tk_kamerstukdossiers.json"), help="Pad naar tk_kamerstukdossiers.json.")
@click.option("--grid-nx", type=int, default=80, help="Aantal grid-cellen in de breedte (default: 80).")
@click.option("--grid-ny", type=int, default=112, help="Aantal grid-cellen in de hoogte (default: 112).")
@click.option("--k-neighbors", type=int, default=30, help="Aantal buren per gridpunt (default: 30).")
@click.option("--min-density", type=int, default=4, help="Minimaal aantal punten binnen bereik (default: 4).")
def main(
    points_path: Path,
    output_path: Path,
    grid_path: Path | None,
    flat: bool,
    clusters_path: Path,
    dossiers_path: Path,
    grid_nx: int,
    grid_ny: int,
    k_neighbors: int,
    min_density: int,
):
    """Genereer een consistent semantisch grid over de plenaire kaart."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not flat and grid_path is None:
        raise click.UsageError("Specificeer --grid of gebruik --flat voor rauwe coördinaten.")

    levels = load_clusters_data(clusters_path)
    logger.info("%d clusterniveaus geladen uit %s", len(levels), clusters_path)

    dossier_matcher = build_dossier_matcher(dossiers_path)
    if dossier_matcher:
        logger.info("Dossier-matcher geïnitialiseerd met TK-dossiers uit %s", dossiers_path)

    raw_data = json.loads(points_path.read_text(encoding="utf-8"))
    points = raw_data["points"]
    topics = raw_data["topics"]

    xs = np.array([p[1] for p in points], dtype=np.float64)
    ys = np.array([p[2] for p in points], dtype=np.float64)
    topic_indices = np.array([p[3] for p in points], dtype=np.int32)
    # p[11] is de [c0, c1, c2, c3, c4] cluster-index per niveau
    hierarchies = [p[11] if len(p) > 11 else [] for p in points]

    xy = np.column_stack([xs, ys])
    tree = cKDTree(xy)

    grid_dict = None if flat else json.loads(grid_path.read_text(encoding="utf-8"))
    rescale = flat_rescale if flat else make_rescaler(grid_dict)

    x_min, x_max = xs.min(), xs.max()
    y_min, y_max = ys.min(), ys.max()

    gx = np.linspace(x_min, x_max, grid_nx)
    gy = np.linspace(y_min, y_max, grid_ny)

    logger.info("Berekenen van semantisch grid over %dx%d (%d cellen)...", grid_nx, grid_ny, grid_nx * grid_ny)

    features = []
    cell_id = 0

    for yi in gy:
        for xi in gx:
            cell_id += 1
            query_pt = np.array([xi, yi])
            dists, idxs = tree.query(query_pt, k=k_neighbors)

            if dists[0] > 0.8:
                continue

            valid_mask = dists < 1.2
            valid_idxs = idxs[valid_mask]
            valid_dists = dists[valid_mask]

            if len(valid_idxs) < min_density:
                continue

            # Gaussian spatial weights
            sigma = 0.4
            weights = np.exp(-(valid_dists ** 2) / (2 * sigma ** 2))

            # Bepaal dominante topic
            neighbor_topics = [topics[topic_indices[i]] for i in valid_idxs if topic_indices[i] < len(topics)]
            top_topic = Counter(neighbor_topics).most_common(1)[0][0] if neighbor_topics else "plenair"

            # Bepaal dominante clusternamen per niveau
            level_cluster_names = {}
            cluster_terms_list = []
            for lvl in range(min(5, len(levels))):
                lvl_clusters = levels[lvl]
                c_counts = Counter()
                for doc_idx, weight in zip(valid_idxs, weights):
                    h = hierarchies[doc_idx]
                    if lvl < len(h) and h[lvl] != -1 and h[lvl] < len(lvl_clusters):
                        c_counts[h[lvl]] += weight

                if c_counts:
                    top_cid, _ = c_counts.most_common(1)[0]
                    c_obj = lvl_clusters[top_cid]
                    c_name = c_obj["name"]
                    level_cluster_names[f"cluster_l{lvl}"] = c_name
                    if c_obj.get("terms"):
                        cluster_terms_list.extend(c_obj["terms"])
                else:
                    level_cluster_names[f"cluster_l{lvl}"] = ""

            # Bepaal meest karakteristieke termen uit de clusters
            term_counter = Counter(cluster_terms_list)
            top_terms = [t.capitalize() for t, _ in term_counter.most_common(3)]

            # Match met TK-genummerde dossiers op basis van de clusternamen en termen
            dossier_query = " ".join([
                level_cluster_names.get("cluster_l4", ""),
                level_cluster_names.get("cluster_l3", ""),
                level_cluster_names.get("cluster_l2", ""),
                " ".join(top_terms),
            ]).strip()

            dossier_nr, dossier_titel, dossier_score = (None, None, 0.0)
            if dossier_matcher and dossier_query:
                dossier_nr, dossier_titel, dossier_score = dossier_matcher(dossier_query)

            primary_label = level_cluster_names.get("cluster_l3") or level_cluster_names.get("cluster_l2") or level_cluster_names.get("cluster_l0") or (top_terms[0] if top_terms else "")

            geo_pt = rescale([xi, yi])
            feature = {
                "type": "Feature",
                "id": f"grid-{cell_id}",
                "geometry": {
                    "type": "Point",
                    "coordinates": [geo_pt[0], geo_pt[1]],
                },
                "properties": {
                    "cell_id": cell_id,
                    "grid_x": round(float(xi), 4),
                    "grid_y": round(float(yi), 4),
                    "label": primary_label,
                    "topic": top_topic,
                    "cluster_l0": level_cluster_names.get("cluster_l0", ""),
                    "cluster_l1": level_cluster_names.get("cluster_l1", ""),
                    "cluster_l2": level_cluster_names.get("cluster_l2", ""),
                    "cluster_l3": level_cluster_names.get("cluster_l3", ""),
                    "cluster_l4": level_cluster_names.get("cluster_l4", ""),
                    "term_1": top_terms[0] if len(top_terms) > 0 else "",
                    "term_2": top_terms[1] if len(top_terms) > 1 else "",
                    "term_3": top_terms[2] if len(top_terms) > 2 else "",
                    "density": len(valid_idxs),
                    "tk_dossier_nr": dossier_nr,
                    "tk_dossier_titel": dossier_titel,
                    "tk_dossier_match_score": dossier_score,
                },
            }
            features.append(feature)

    output_geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output_geojson, ensure_ascii=False), encoding="utf-8")
    logger.info("Semantisch grid geschreven: %s (%d actieve cellen)", output_path, len(features))


if __name__ == "__main__":
    main()
