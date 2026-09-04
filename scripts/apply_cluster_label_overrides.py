"""
Pas clusterlabel-overrides en redundantie toe op plenair-map-clusters-full.json
en re-exporteer de GeoJSON-bestanden voor de kaartvisualisatie.

Gebruik:
    uv run python scripts/apply_cluster_label_overrides.py
"""

import json
import subprocess
import sys
import tomllib
from pathlib import Path
import click


@click.command()
@click.option(
    "--config-path",
    type=click.Path(exists=True, path_type=Path),
    default=Path("config/cluster_label_overrides.toml"),
    help="Pad naar het TOML-configuratiebestand met overrides.",
)
@click.option(
    "--clusters-json",
    type=click.Path(exists=True, path_type=Path),
    default=Path("data/export/plenair-map-clusters-full.json"),
    help="Pad naar plenair-map-clusters-full.json.",
)
@click.option(
    "--grid-json",
    type=click.Path(path_type=Path),
    default=Path("data/export/plenair-map-full-grid.json"),
    help="Pad naar plenair-map-full-grid.json voor WGS84 GeoJSON export.",
)
@click.option(
    "--export-geojson/--no-export-geojson",
    default=True,
    help="Of scripts/export_clusters_geojson.py automatisch gedraaid moet worden.",
)
def main(config_path: Path, clusters_json: Path, grid_json: Path, export_geojson: bool):
    """Lees label overrides uit TOML en werk plenair-map-clusters-full.json bij."""
    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    labels = config.get("labels", {})
    redundants = config.get("redundant", {})

    with open(clusters_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    levels = data["levels"]

    # Indexeer clusters per (level, cluster_id)
    cluster_index = {}
    for lvl_idx, lvl_clusters in enumerate(levels):
        for c in lvl_clusters:
            cluster_index[(lvl_idx, c["cluster_id"])] = c

    # Pas label-wijzigingen toe
    renamed_count = 0
    for key, new_name in labels.items():
        parts = key.split("-")
        lvl = int(parts[0][1:])
        cid = int(parts[1])
        c = cluster_index.get((lvl, cid))
        if not c:
            raise KeyError(f"Cluster {key} niet gevonden in {clusters_json}")

        old_name = c["name"]
        if old_name != new_name:
            c["name"] = new_name
            renamed_count += 1
            # Werk ook parent_name bij in de kinderen op het volgende niveau
            if lvl + 1 < len(levels):
                for child in levels[lvl + 1]:
                    if child.get("parent_id") == cid:
                        child["parent_name"] = new_name

    # Pas redundantie-wijzigingen toe
    redundant_count = 0
    for key, is_redundant in redundants.items():
        parts = key.split("-")
        lvl = int(parts[0][1:])
        cid = int(parts[1])
        c = cluster_index.get((lvl, cid))
        if not c:
            raise KeyError(f"Cluster {key} niet gevonden in {clusters_json}")

        if c.get("redundant_with_parent") != is_redundant:
            c["redundant_with_parent"] = is_redundant
            redundant_count += 1

    # Schrijf bijgewerkte JSON terug
    with open(clusters_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    click.echo(
        f"Succesvol bijgewerkt: {renamed_count} clusters hernoemd, {redundant_count} redundantie-statussen aangepast."
    )

    if export_geojson:
        geojson_wgs84 = clusters_json.with_suffix(".geojson")
        geojson_flat = clusters_json.parent / f"{clusters_json.stem}-flat.geojson"

        # 1. WGS84 export (voor PMTiles/web viewers)
        cmd_wgs84 = [
            sys.executable,
            "scripts/export_clusters_geojson.py",
            str(clusters_json),
            str(geojson_wgs84),
            "--grid",
            str(grid_json),
        ]
        click.echo(f"Genereren van {geojson_wgs84.name}...")
        res = subprocess.run(cmd_wgs84, capture_output=True, text=True)
        if res.returncode != 0:
            click.echo(res.stderr, err=True)
            res.check_returncode()

        # 2. Flat export (voor QGIS A0-printkaart compositie)
        cmd_flat = [
            sys.executable,
            "scripts/export_clusters_geojson.py",
            str(clusters_json),
            str(geojson_flat),
            "--flat",
        ]
        click.echo(f"Genereren van {geojson_flat.name}...")
        res_flat = subprocess.run(cmd_flat, capture_output=True, text=True)
        if res_flat.returncode != 0:
            click.echo(res_flat.stderr, err=True)
            res_flat.check_returncode()

        click.echo("GeoJSON-bestanden succesvol opnieuw gegenereerd!")


if __name__ == "__main__":
    main()
