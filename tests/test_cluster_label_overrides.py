"""Tests voor cluster label overrides en TOML configuratie."""

import json
import tomllib
from pathlib import Path
from click.testing import CliRunner
from scripts.apply_cluster_label_overrides import main


def test_cluster_label_overrides_toml():
    """Valideer dat cluster_label_overrides.toml syntactisch klopt en clusters bestaan."""
    config_path = Path("config/cluster_label_overrides.toml")
    assert config_path.exists()

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    assert "labels" in config
    assert "redundant" in config

    clusters_json = Path("data/export/plenair-map/plenair-map-clusters-full.json")
    if not clusters_json.exists():
        return

    with open(clusters_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    levels = data["levels"]
    cluster_keys = set()
    for lvl_idx, lvl_clusters in enumerate(levels):
        for c in lvl_clusters:
            cluster_keys.add(f"L{lvl_idx}-{c['cluster_id']}")

    for key in config["labels"].keys():
        assert key in cluster_keys, f"Cluster {key} uit TOML bestaat niet in clusters-full.json"

    for key in config["redundant"].keys():
        assert key in cluster_keys, f"Cluster {key} uit TOML bestaat niet in clusters-full.json"


def test_apply_cluster_label_overrides_cli():
    """Valideer dat de CLI tool zonder fouten draait (zonder geojson regeneratie)."""
    runner = CliRunner()
    result = runner.invoke(main, ["--no-export-geojson"])
    assert result.exit_code == 0
    assert "Succesvol bijgewerkt" in result.output
