import json
import sqlite3

from pipeline.tiling import build_pyramid
from pipeline.tiling.build_pyramid import compute_global_point_ranks, load_video_hrefs, thin_zoom_points_globally


def _points(ids):
    # Vorm van een punt: (id, x, y, ...) -- alleen id doet ertoe voor thinning.
    return [(i, 0.0, 0.0) for i in ids]


def _flat_weights(points):
    # Gewicht 1.0 overal == dezelfde rangorde als de oude puur-hash-gebaseerde
    # versie (zie `point_priority()`'s docstring in build_pyramid.py).
    return {point[0]: 1.0 for point in points}


def test_thin_zoom_points_globally_keeps_more_from_dense_tile_than_sparse():
    dense = _points(range(0, 4000))
    sparse = _points(range(4000, 4400))
    grouped = {1: dense, 2: sparse}
    all_points = dense + sparse
    ranks = compute_global_point_ranks(all_points, _flat_weights(all_points))

    thinned = thin_zoom_points_globally(grouped, ranks, max_points_per_tile=100)

    # Budget = 2 tiles * 100 = 200 van de 4400 punten totaal (~4,5%). Beide
    # tiles houden ongeveer diezelfde fractie over (~4,5% van hun eigen
    # aantal, ruime marge voor hash-ruis bij deze steekproefgrootte) i.p.v.
    # allebei plat afgekapt op 100 (de oude per-tile-cap-vertekening zou de
    # dunne tile ongemoeid laten en de dichte op exact 100 afkappen).
    assert len(thinned[1]) + len(thinned[2]) <= 200
    dense_fraction = len(thinned[1]) / len(dense)
    sparse_fraction = len(thinned[2]) / len(sparse)
    assert abs(dense_fraction - sparse_fraction) < 0.03
    assert len(thinned[2]) < len(sparse)  # de dunne tile wordt ook uitgedund, niet vrijgesteld


def test_thin_zoom_points_globally_is_zoom_monotone():
    all_points = _points(range(0, 5000))
    ranks = compute_global_point_ranks(all_points, _flat_weights(all_points))

    # Grof niveau: alles in 1 tile. Fijn niveau: dezelfde punten over 8 tiles
    # verdeeld (elk 625 punten) -- budget schaalt dus mee met het aantal tiles.
    coarse = {1: all_points}
    fine = {i: all_points[i * 625 : (i + 1) * 625] for i in range(8)}

    kept_coarse = {p[0] for pts in thin_zoom_points_globally(coarse, ranks, 100).values() for p in pts}
    kept_fine = {p[0] for pts in thin_zoom_points_globally(fine, ranks, 100).values() for p in pts}

    assert kept_coarse <= kept_fine


def test_thin_zoom_points_globally_no_thinning_when_under_budget():
    points = _points(range(0, 50))
    grouped = {1: points}
    ranks = compute_global_point_ranks(points, _flat_weights(points))

    thinned = thin_zoom_points_globally(grouped, ranks, max_points_per_tile=100)

    assert len(thinned[1]) == 50


def _connect_with_row_factory(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _fake_documents_db(tmp_path, rows):
    db_path = tmp_path / "fake.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE documents (
            id INTEGER PRIMARY KEY, video_url TEXT, published_at TEXT,
            speaker_event_anchor_at TEXT, turn_type TEXT, is_voorzitter_turn INTEGER
        )"""
    )
    conn.executemany(
        "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?)",
        [(r["id"], r["video_url"], r["published_at"], None, "spreker", 0) for r in rows],
    )
    conn.commit()
    conn.close()
    return db_path


def test_load_video_hrefs_prefers_curated_internal_link_over_computed_external(tmp_path, monkeypatch):
    # issue: na de overstap op MVT-meegecodeerde video-links (#356-vervolg)
    # gingen alle links naar Debat Direct, ook voor de ~5300 document-id's
    # waarvoor plenair-map-videos.json een gecureerde interne
    # /debatten/{id}/-link had. load_video_hrefs() moet die curated-entry
    # laten winnen en alleen voor de rest zelf de externe link berekenen.
    db_path = _fake_documents_db(
        tmp_path,
        rows=[
            {"id": 1, "video_url": "https://stream.example/abc/video", "published_at": "2026-01-01T10:00:00"},
            {"id": 2, "video_url": "https://stream.example/def/video", "published_at": "2026-01-01T10:00:00"},
        ],
    )
    monkeypatch.setattr(build_pyramid.db, "connect", lambda: _connect_with_row_factory(db_path))

    videos_json_path = tmp_path / "plenair-map-videos.json"
    videos_json_path.write_text(json.dumps({"1": {"href": "/debatten/abc123/", "is_internal": True}}))

    hrefs = load_video_hrefs({1, 2}, videos_json_path)

    assert hrefs[1] == "/debatten/abc123/"  # curated interne link, niet herberekend
    assert hrefs[2].startswith("https://stream.example/")  # geen curated entry -> externe link berekend


def test_load_video_hrefs_without_videos_json_falls_back_to_computed_links(tmp_path, monkeypatch):
    db_path = _fake_documents_db(
        tmp_path,
        rows=[{"id": 1, "video_url": "https://stream.example/abc/video", "published_at": "2026-01-01T10:00:00"}],
    )
    monkeypatch.setattr(build_pyramid.db, "connect", lambda: _connect_with_row_factory(db_path))

    hrefs = load_video_hrefs({1}, tmp_path / "ontbreekt.json")

    assert hrefs[1].startswith("https://stream.example/")
