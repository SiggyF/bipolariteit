from scripts.publish_huggingface import REDUCER_GLOB, select_bundle_files


def _bundle(tmp_path):
    for name in ("plenair-map-full.pmtiles", "plenair-map-full-grid.json", "umap-reducer-full.joblib"):
        (tmp_path / name).write_bytes(b"x")
    (tmp_path / "submap").mkdir()
    return tmp_path


def test_reducer_wordt_standaard_overgeslagen(tmp_path):
    files, skipped = select_bundle_files(_bundle(tmp_path))
    assert [f.name for f in files] == ["plenair-map-full-grid.json", "plenair-map-full.pmtiles"]
    assert [f.name for f in skipped] == ["umap-reducer-full.joblib"]


def test_reducer_kan_expliciet_mee(tmp_path):
    files, skipped = select_bundle_files(_bundle(tmp_path), include_reducer=True)
    assert "umap-reducer-full.joblib" in [f.name for f in files]
    assert skipped == []


def test_glob_dekt_elk_label(tmp_path):
    (tmp_path / "umap-reducer-v2.joblib").write_bytes(b"x")
    (tmp_path / "plenair-map-full.pmtiles").write_bytes(b"x")
    files, skipped = select_bundle_files(tmp_path)
    assert [f.name for f in skipped] == ["umap-reducer-v2.joblib"]
    assert REDUCER_GLOB == "umap-reducer-*.joblib"
