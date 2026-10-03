"""
Herbruikbaar dichtheidsraster voor de plenaire-kaart-punten, geport uit
`scripts/a0_map/generate_a0_density_raster.py` (dat script blijft bestaan
voor de A0-printposter-workflow, issue #215 -- dit is dezelfde kernlogica,
maar losgetrokken van de A0-specifieke 300dpi-afmetingen zodat `pipeline.
tiling.build_pyramid` 'm ook kan gebruiken voor dichtheidsbewuste thinning
en een optionele kaartlaag (issue #367).

Algoritme: 2D histogram-binning (`np.histogram2d`) + Gaussiaanse convolutie
(`scipy.ndimage.gaussian_filter`) -- functioneel een snelle KDE-benadering,
veel sneller dan een echte kernel-sommatie over 700k+ punten. Output is een
genormaliseerde, gamma-gecorrigeerde dichtheid in [0, 1] (geen ruwe counts,
geen log-schaal), zelfde conventie als het A0-script.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles
from scipy.ndimage import gaussian_filter

Bounds = tuple[float, float, float, float]  # (min_x, min_y, max_x, max_y)


@dataclass(frozen=True)
class DensityGrid:
    """Een dichtheidsraster plus de informatie om er (x, y) in Mercator-meters
    op terug te rekenen naar rij/kolom (zie `sample()`)."""

    values: np.ndarray  # float32, shape (height, width), [0, 1], rij 0 = noord
    bounds: Bounds

    def sample(self, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
        """Bilineaire sampling van de dichtheid op punten (xs, ys) in dezelfde
        CRS/eenheden als `bounds`. Punten buiten `bounds` worden geklemd op de
        dichtstbijzijnde rand (geen extrapolatie, geen NaN)."""
        min_x, min_y, max_x, max_y = self.bounds
        height, width = self.values.shape

        # Kolom loopt met x mee; rij loopt TEGEN y in (rij 0 = max_y, noord
        # boven), zelfde conventie als `compute_density_grid()` hieronder.
        col = (xs - min_x) / (max_x - min_x) * (width - 1)
        row = (max_y - ys) / (max_y - min_y) * (height - 1)
        col = np.clip(col, 0, width - 1)
        row = np.clip(row, 0, height - 1)

        col0 = np.floor(col).astype(np.int64)
        row0 = np.floor(row).astype(np.int64)
        col1 = np.minimum(col0 + 1, width - 1)
        row1 = np.minimum(row0 + 1, height - 1)
        fx = col - col0
        fy = row - row0

        v00 = self.values[row0, col0]
        v01 = self.values[row0, col1]
        v10 = self.values[row1, col0]
        v11 = self.values[row1, col1]
        top = v00 * (1 - fx) + v01 * fx
        bottom = v10 * (1 - fx) + v11 * fx
        return top * (1 - fy) + bottom * fy


def compute_density_grid(
    xs: np.ndarray,
    ys: np.ndarray,
    bounds: Bounds,
    width: int,
    height: int,
    sigma_px: float,
    gamma: float = 0.45,
) -> DensityGrid:
    """Zelfde histogram+Gaussian-blur+gamma-aanpak als
    `scripts/a0_map/generate_a0_density_raster.py::main()`, maar met expliciete
    resolutie/sigma i.p.v. afgeleid uit A0@300dpi-constantes."""
    min_x, min_y, max_x, max_y = bounds

    hist, _, _ = np.histogram2d(
        xs, ys,
        bins=[width, height],
        range=[[min_x, max_x], [min_y, max_y]],
    )
    # Transpose + flip: histogram2d geeft (x_bins, y_bins) met y oplopend;
    # een rasterafbeelding wil (rij, kolom) met rij 0 = noord (max_y).
    raster_counts = np.flipud(hist.T).astype(np.float32)

    smoothed = gaussian_filter(raster_counts, sigma=sigma_px)

    max_val = smoothed.max()
    if max_val > 0:
        normalized = smoothed / max_val
        transformed = np.power(normalized, gamma).astype(np.float32)
    else:
        transformed = smoothed

    return DensityGrid(values=transformed, bounds=bounds)


def write_cog(grid: DensityGrid, output_path: Path) -> None:
    """Schrijft `grid` als een echte, met `rio cogeo validate` controleerbare
    Cloud-Optimized GeoTIFF (EPSG:3857): eerst een gewone GeoTIFF in-memory
    opbouwen (rasterio `MemoryFile`), dan `rio_cogeo.cog_translate()` de
    tegel+overview-pyramide laten genereren via GDAL's eigen `AVERAGE`-
    resampling. Betrouwbaarder dan zelf een pyramide in numpy bouwen (eerder
    geprobeerd met kale `tifffile`-tags, maar niet spec-gevalideerd zonder
    GDAL-toolchain -- `rasterio`/`rio-cogeo` zijn daarom als dependency
    toegevoegd, issue #367)."""
    min_x, min_y, max_x, max_y = grid.bounds
    height, width = grid.values.shape
    scale_x = (max_x - min_x) / width
    scale_y = (max_y - min_y) / height
    transform = from_origin(min_x, max_y, scale_x, scale_y)

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": grid.values.dtype,
        "crs": "EPSG:3857",
        "transform": transform,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    dst_profile = cog_profiles.get("deflate")
    with MemoryFile() as mem:
        with mem.open(**profile) as dataset:
            dataset.write(grid.values, 1)
        with mem.open() as dataset:
            cog_translate(
                dataset,
                str(output_path),
                dst_profile,
                overview_resampling="average",
                web_optimized=False,
                quiet=True,
            )
