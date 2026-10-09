import numpy as np
from shapely.geometry import shape

from scripts.a0_map.export_clusters_geojson import flat_rescale
from scripts.a0_map.generate_actor_party_contours import build_contours, canonical_party


def _data():
    rng = np.random.default_rng(0)
    # Achtergrond: brede wolk. Partij A spreekt extra in een kleine hoek.
    background = rng.normal(0, 3, size=(20000, 2))
    cluster = rng.normal([4, 4], 0.4, size=(3000, 2))
    pts = []
    for i, (x, y) in enumerate(background):
        pts.append([i, x, y, 0, 1, 1])
    for i, (x, y) in enumerate(cluster):
        pts.append([100000 + i, x, y, 0, 0, 0])
    return {"actors": ["Specialist", "Generalist"], "parties": ["A", "B"], "points": pts}


def test_canonical_party_alias():
    assert canonical_party("Nieuw Sociaal Contract") == "NSC"
    assert canonical_party("VVD") == "VVD"


def test_contour_ligt_om_oververtegenwoordigd_gebied():
    parties, actors = build_contours(_data(), flat_rescale, bins=100, sigma=2.0, min_points=1000)
    features = [f for f in parties["features"] if f["properties"]["party"] == "A"]
    assert {f["properties"]["threshold"] for f in features} <= {1.5, 3.0}
    geom = shape(features[0]["geometry"])
    assert geom.contains(shape({"type": "Point", "coordinates": [4, 4]}))
    assert not geom.contains(shape({"type": "Point", "coordinates": [-4, -4]}))


def test_groepen_onder_minimum_krijgen_geen_contour():
    parties, actors = build_contours(_data(), flat_rescale, bins=100, sigma=2.0, min_points=5000)
    assert "A" not in {f["properties"]["party"] for f in parties["features"]}
    assert "Specialist" not in {f["properties"]["actor"] for f in actors["features"]}


def test_drempels_zijn_genest():
    parties, _ = build_contours(_data(), flat_rescale, bins=100, sigma=2.0, min_points=1000)
    by_threshold = {f["properties"]["threshold"]: shape(f["geometry"]) for f in parties["features"] if f["properties"]["party"] == "A"}
    if 3.0 in by_threshold:
        assert by_threshold[1.5].buffer(1e-6).contains(by_threshold[3.0])
