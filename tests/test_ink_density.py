import json

import numpy as np

from pipeline.tiling.ink import cell_counts, ink_block, merge_into_grid, summarize_zoom


def test_cell_counts_telt_alleen_niet_lege_cellen():
    # Twee punten in dezelfde cel, één ergens anders: twee niet-lege cellen.
    xs = np.array([10.0, 20.0, 3000.0])
    ys = np.array([10.0, 20.0, 3000.0])
    counts = cell_counts(xs, ys, extent=4096)
    assert sorted(counts.tolist()) == [1, 2]


def test_cell_counts_lege_tegel():
    assert len(cell_counts(np.zeros(0), np.zeros(0), extent=4096)) == 0


def test_cell_counts_klemt_punten_op_de_rand():
    # x == extent valt formeel buiten de laatste cel; moet geklemd worden.
    counts = cell_counts(np.array([4096.0]), np.array([4096.0]), extent=4096)
    assert counts.tolist() == [1]


def test_summarize_zoom_geeft_punten_per_pixel2():
    # Een cel van 16x16 px = 256 px2; 8 punten in één cel = 8/256 per px2.
    summary = summarize_zoom(3, [np.array([8, 8, 8])], tiles=1, points=24, cell_px=16)
    assert summary["per_px2_p50"] == 8 / 256
    assert summary["per_px2_max"] == 8 / 256
    assert summary["cells"] == 3


def test_summarize_zoom_zonder_cellen():
    summary = summarize_zoom(0, [], tiles=0, points=0)
    assert summary["per_px2_p90"] == 0.0
    assert summary["cells"] == 0


def test_merge_into_grid_behoudt_overige_sleutels(tmp_path):
    grid = tmp_path / "grid.json"
    grid.write_text(json.dumps({"tile_size": 256, "maxzoom": 8}))
    summaries = [summarize_zoom(3, [np.array([8, 8])], tiles=1, points=16)]
    merge_into_grid(grid, summaries)
    result = json.loads(grid.read_text())
    assert result["tile_size"] == 256
    assert result["ink"]["zooms"][0]["zoom"] == 3
    assert set(result["ink"]["zooms"][0]) == {"zoom", "tiles", "points", "per_px2_p50", "per_px2_p90", "per_px2_p99"}


def test_ink_block_vermeldt_de_meetinstellingen():
    block = ink_block([])
    assert block["render_tile_px"] == 512
    assert block["cell_px"] == 16
