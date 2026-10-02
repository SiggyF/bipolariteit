from pipeline.tiling.build_pyramid import compute_global_point_ranks, thin_zoom_points_globally


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
