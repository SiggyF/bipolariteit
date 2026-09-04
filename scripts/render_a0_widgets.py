"""
Rendert de A0 printkaart HTML-widgets (colofon en legenda) naar ultra-hoge-resolutie 300 DPI PNGs
met behulp van headless Google Chrome.

Gebruik:
    uv run python scripts/render_a0_widgets.py
"""

import subprocess
import sys
from pathlib import Path
import click

CHROME_BIN = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


@click.command()
@click.option(
    "--widgets-dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path("data/export/a0-map"),
    help="Map met de HTML widgets en doel-PNGs.",
)
@click.option(
    "--scale-factor",
    type=int,
    default=3,
    help="Device scale factor voor ultra-scherpe 300 DPI printkwaliteit.",
)
def main(widgets_dir: Path, scale_factor: int):
    """Rendert colofon.html en legenda.html naar PNG met exacte afmetingen."""
    if not CHROME_BIN.exists():
        raise FileNotFoundError(f"Google Chrome niet gevonden op {CHROME_BIN}")

    targets = [
        {
            "name": "Colofon",
            "html": widgets_dir / "colofon.html",
            "png": widgets_dir / "colofon.png",
            "window_size": "1460,700",
        },
        {
            "name": "Legenda",
            "html": widgets_dir / "legenda.html",
            "png": widgets_dir / "legenda.png",
            "window_size": "700,1050",
        },
    ]

    for t in targets:
        html_path = t["html"].resolve()
        png_path = t["png"].resolve()
        window_size = t["window_size"]

        cmd = [
            str(CHROME_BIN),
            "--headless",
            "--disable-gpu",
            "--default-background-color=00000000",
            "--hide-scrollbars",
            f"--force-device-scale-factor={scale_factor}",
            f"--window-size={window_size}",
            f"--screenshot={png_path}",
            f"file://{html_path}",
        ]

        click.echo(f"Rendert {t['name']} ({png_path.name}) met window-size {window_size}...")
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            click.echo(res.stderr, err=True)
            res.check_returncode()

        click.echo(f"  ✓ {t['name']} succesvol opgeslagen op {png_path.name}")

    click.echo("Alle A0 printkaart widgets zijn succesvol gerenderd!")


if __name__ == "__main__":
    main()
