"""
Hoge-resolutie 4-bands RGBA kleurdichtheidsraster voor de A0-printposter.

Combineert:
- PC 2 & PC 3 van de 1024D BGE-M3 embeddings geprojecteerd op CIELAB (a*, b*)
- Procedurele filtering: Moties en Kamervoorzitter gedempt naar neutraal zilvergrijs
- Continue 2D Gaussian Kernel Density Estimation (KDE) voor de luminantie L*
- Band 4 (Alpha): Opaciteit gekoppeld aan de dichtheid (L -> A), zodat de kaart
  volledig transparant overvloeit in het papier zonder harde witte randen.

Ondersteunt georeferencing via World File (.tfw) + .prj (EPSG:3857) voor directe
integratie in QGIS.

Gebruik:
    uv run python scripts/a0_map/generate_a0_color_raster.py \
        data/export/plenair-map-full.json \
        data/export/a0-map/density_color_a0_300dpi.tif \
        --grid data/export/plenair-map-full-grid.json \
        --scale 1.0 \
        --sigma-mm 3.2
"""

import json
import logging
from pathlib import Path

import click
import matplotlib.colors as mcolors
import numpy as np
from scipy.ndimage import gaussian_filter
from sklearn.decomposition import PCA
import tifffile

logger = logging.getLogger(__name__)

A0_WIDTH_MM = 841.0
A0_HEIGHT_MM = 1189.0
DPI = 300.0
MM_PER_INCH = 25.4
A0_WIDTH_PX = round(A0_WIDTH_MM / MM_PER_INCH * DPI)
A0_HEIGHT_PX = round(A0_HEIGHT_MM / MM_PER_INCH * DPI)

WEB_MERCATOR_HALF_EXTENT = 20037508.342789244
EPSG_3857_WKT = (
    'PROJCS["WGS 84 / Pseudo-Mercator",'
    'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],'
    'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]],'
    'PROJECTION["Mercator_1SP"],PARAMETER["central_meridian",0],'
    'PARAMETER["scale_factor",1],PARAMETER["false_easting",0],'
    'PARAMETER["false_northing",0],UNIT["metre",1]]'
)


def lab2rgb_numpy(lab: np.ndarray) -> np.ndarray:
    """Vectorized D65 CIELAB naar sRGB conversie [0.0, 1.0]."""
    L = lab[..., 0]
    a = lab[..., 1]
    b = lab[..., 2]

    fy = (L + 16.0) / 116.0
    fx = a / 500.0 + fy
    fz = fy - b / 200.0

    delta = 6.0 / 29.0
    def f_inv(t):
        return np.where(t > delta, t**3, 3.0 * (delta**2) * (t - 4.0 / 29.0))

    X = 0.95047 * f_inv(fx)
    Y = 1.00000 * f_inv(fy)
    Z = 1.08883 * f_inv(fz)

    R_lin =  3.2404542 * X - 1.5371385 * Y - 0.4985314 * Z
    G_lin = -0.9692660 * X + 1.8760108 * Y + 0.0415560 * Z
    B_lin =  0.0556434 * X - 0.2040259 * Y + 1.0572252 * Z

    def gamma_srgb(c):
        return np.where(c > 0.0031308, 1.055 * (np.maximum(c, 0.0)**(1.0 / 2.4)) - 0.055, 12.92 * c)

    R = gamma_srgb(R_lin)
    G = gamma_srgb(G_lin)
    B = gamma_srgb(B_lin)

    return np.clip(np.stack([R, G, B], axis=-1), 0.0, 1.0)


def load_points_and_grid(points_path: Path, grid_path: Path | None, flat: bool):
    raw_points = json.loads(points_path.read_text(encoding="utf-8"))
    points = raw_points["points"]
    xs = np.array([p[1] for p in points], dtype=np.float64)
    ys = np.array([p[2] for p in points], dtype=np.float64)
    l0_ids = np.array([p[10] if len(p) > 10 else -1 for p in points], dtype=np.int32)

    if flat or grid_path is None:
        return xs, ys, l0_ids, (xs.min(), ys.min(), xs.max(), ys.max())

    grid_data = json.loads(grid_path.read_text(encoding="utf-8"))
    left, bottom, right, top = grid_data["extent"]
    span_x = right - left
    span_y = top - bottom

    merc_x = -WEB_MERCATOR_HALF_EXTENT + ((xs - left) / span_x) * 2.0 * WEB_MERCATOR_HALF_EXTENT
    merc_y = -WEB_MERCATOR_HALF_EXTENT + ((ys - bottom) / span_y) * 2.0 * WEB_MERCATOR_HALF_EXTENT
    bounds = (
        -WEB_MERCATOR_HALF_EXTENT,
        -WEB_MERCATOR_HALF_EXTENT,
        WEB_MERCATOR_HALF_EXTENT,
        WEB_MERCATOR_HALF_EXTENT,
    )
    return merc_x, merc_y, l0_ids, bounds


def write_world_files(output_tif: Path, bounds: tuple[float, float, float, float], width_px: int, height_px: int, flat: bool):
    min_x, min_y, max_x, max_y = bounds
    dx = (max_x - min_x) / width_px
    dy = -(max_y - min_y) / height_px
    top_left_x = min_x + 0.5 * dx
    top_left_y = max_y + 0.5 * dy

    tfw_content = f"{dx:.8f}\n0.0\n0.0\n{dy:.8f}\n{top_left_x:.8f}\n{top_left_y:.8f}\n"
    tfw_path = output_tif.with_suffix(".tfw")
    tfw_path.write_text(tfw_content, encoding="utf-8")

    if not flat:
        prj_path = output_tif.with_suffix(".prj")
        prj_path.write_text(EPSG_3857_WKT, encoding="utf-8")


@click.command()
@click.argument("points_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("output_path", type=click.Path(dir_okay=False, path_type=Path))
@click.option("--embeddings", "emb_path", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=Path("data/embeddings/text-embedding-bge-m3_plenair-full.npz"), help="Pad naar de BGE-M3 embeddings.")
@click.option("--grid", "grid_path", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None, help="Pad naar plenair-map-full-grid.json voor EPSG:3857 georeferencing.")
@click.option("--flat", is_flag=True, default=False, help="Schrijf in rauwe UMAP-coördinaten zonder Mercator-projectie.")
@click.option("--scale", type=float, default=1.0, help="Schaalfactor van A0-resolutie (1.0 = 300dpi, 0.2 = preview).")
@click.option("--sigma-mm", type=float, default=3.2, help="Gaussian filter sigma in millimeters op de A0-kaart.")
@click.option("--max-chroma", type=float, default=34.0, help="Maximale CIELAB kleurverzadiging.")
def main(points_path: Path, output_path: Path, emb_path: Path, grid_path: Path | None, flat: bool, scale: float, sigma_mm: float, max_chroma: float):
    """Genereer een 4-bands RGBA semantische kleurdichtheids-GeoTIFF voor de A0-kaart."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not flat and grid_path is None:
        raise click.UsageError("Specificeer --grid of gebruik --flat voor rauwe coördinaten.")

    # 1. Laad punten en geografische grenzen
    xs, ys, l0_ids, bounds = load_points_and_grid(points_path, grid_path, flat)
    min_x, min_y, max_x, max_y = bounds

    # Procedurele mask: L0-1 (Moties) en L0-3 (Voorzitter)
    is_sub = ~np.isin(l0_ids, [1, 3])
    logger.info("Spreekbeurten: %d totaal (%d inhoudelijk, %d procedureel gedempt)", len(xs), np.sum(is_sub), np.sum(~is_sub))

    # 2. Fit PCA uitsluitend op inhoudelijke embeddings
    logger.info("Laden van embeddings: %s", emb_path)
    emb_data = np.load(emb_path)
    vectors = emb_data["vectors"]

    logger.info("Fitten van PCA op %d inhoudelijke vectoren...", np.sum(is_sub))
    pca = PCA(n_components=5, random_state=42)
    pca.fit(vectors[is_sub])
    coords = pca.transform(vectors)

    # We gebruiken PC 1 voor saturatie en PC 2 & PC 3 met 35 graden rotatie voor a* en b*
    pc1 = coords[:, 0]
    pc2 = coords[:, 1]
    pc3 = coords[:, 2]

    p30_pc1 = float(np.percentile(pc1, 30))
    logger.info("PC 1 drempel (30e percentiel parlementair geneuzel): %.4f", p30_pc1)

    theta = np.radians(35.0)
    u_rot = np.cos(theta) * pc2 - np.sin(theta) * pc3
    v_rot = np.sin(theta) * pc2 + np.cos(theta) * pc3

    sub_u = u_rot[is_sub]
    sub_v = v_rot[is_sub]
    p5_u, p95_u = np.percentile(sub_u, 5), np.percentile(sub_u, 95)
    p5_v, p95_v = np.percentile(sub_v, 5), np.percentile(sub_v, 95)

    u_norm = np.clip((u_rot - np.median(sub_u)) / (p95_u - p5_u) * 2.0, -1.0, 1.0)
    v_norm = np.clip((v_rot - np.median(sub_v)) / (p95_v - p5_v) * 2.0, -1.0, 1.0)

    # 3. Bereken raster resolutie
    width_px = max(100, round(A0_WIDTH_PX * scale))
    height_px = max(100, round(A0_HEIGHT_PX * scale))
    logger.info("Canvas resolutie: %dx%d px (schaal=%.2f, DPI=%.0f)", width_px, height_px, scale, DPI * scale)

    # Dichtheidsgewichten: Moties & Voorzitter op 0.35 gewicht zodat ze zacht grafietgrijs worden
    density_weights = np.where(is_sub, 1.0, 0.35)
    hist_counts, _, _ = np.histogram2d(xs, ys, bins=[width_px, height_px], range=[[min_x, max_x], [min_y, max_y]], weights=density_weights)
    hist_counts = np.flipud(hist_counts.T).astype(np.float32)

    sub_weight = is_sub.astype(np.float32)
    hist_sub, _, _ = np.histogram2d(xs, ys, bins=[width_px, height_px], range=[[min_x, max_x], [min_y, max_y]], weights=sub_weight)
    hist_sub = np.flipud(hist_sub.T).astype(np.float32)

    hist_u, _, _ = np.histogram2d(xs, ys, bins=[width_px, height_px], range=[[min_x, max_x], [min_y, max_y]], weights=(u_norm * sub_weight).astype(np.float32))
    hist_u = np.flipud(hist_u.T).astype(np.float32)

    hist_v, _, _ = np.histogram2d(xs, ys, bins=[width_px, height_px], range=[[min_x, max_x], [min_y, max_y]], weights=(v_norm * sub_weight).astype(np.float32))
    hist_v = np.flipud(hist_v.T).astype(np.float32)

    hist_pc1, _, _ = np.histogram2d(xs, ys, bins=[width_px, height_px], range=[[min_x, max_x], [min_y, max_y]], weights=pc1.astype(np.float32))
    hist_pc1 = np.flipud(hist_pc1.T).astype(np.float32)

    # 4. Smoothing via Gaussian filter
    px_per_mm = (DPI * scale) / MM_PER_INCH
    sigma_px = max(0.5, sigma_mm * px_per_mm)
    logger.info("Convolutie: sigma=%.1f mm (%.2f pixels)", sigma_mm, sigma_px)

    smoothed_counts = gaussian_filter(hist_counts, sigma=sigma_px)
    smoothed_sub = gaussian_filter(hist_sub, sigma=sigma_px * 1.5)
    smoothed_u = gaussian_filter(hist_u, sigma=sigma_px * 2.0)
    smoothed_v = gaussian_filter(hist_v, sigma=sigma_px * 2.0)
    smoothed_pc1 = gaussian_filter(hist_pc1, sigma=sigma_px * 2.0)

    denom = gaussian_filter(hist_counts, sigma=sigma_px * 2.0) + 1e-3
    interp_u = smoothed_u / denom
    interp_v = smoothed_v / denom
    interp_pc1 = smoothed_pc1 / denom

    substantive_ratio = np.clip(smoothed_sub / (smoothed_counts + 1e-3), 0.0, 1.0)
    max_val = smoothed_counts.max()
    norm_density = np.power(smoothed_counts / max_val, 0.45)

    # 5. CIELAB Constructie
    # L* (Luminantie) hangt samen met density: 100 (wit) tot ~30 (donkerste toppen)
    L = 100.0 - 70.0 * norm_density

    # a* en b*: gekoppeld aan geroteerde PC 2 & 3, met warme versterking op positief a*
    a = np.where(interp_u > 0, interp_u * 1.5, interp_u) * max_chroma
    b = interp_v * max_chroma

    lab = np.stack([L, a, b], axis=-1)
    rgb_raw = lab2rgb_numpy(lab)

    # 6. Naar HSV en saturatie (S) moduleren met PC 1:
    # Eerste 30% van PC 1 is parlementair geneuzel (S = 0, zacht grafietgrijs)
    # Vanaf p30 verloopt de saturatie via tanh(8 * max(0, PC1 - p30)) asymptotisch naar volle verzadiging
    hsv = mcolors.rgb_to_hsv(rgb_raw)
    delta_pc1 = np.maximum(0.0, interp_pc1 - p30_pc1)
    sat_factor = np.tanh(8.0 * delta_pc1)
    hsv[..., 1] = np.clip(hsv[..., 1] * sat_factor, 0.0, 1.0)
    rgb = mcolors.hsv_to_rgb(hsv)

    # 7. Alpha kanaal (L -> A):
    # Waar geen debatten zijn is Alpha = 0 (volledig transparant).
    # Waar debatten zijn loopt Alpha vloeiend op met de dichtheid (1.0 - L/100).
    alpha_norm = np.clip(np.power(norm_density, 0.75), 0.0, 1.0)
    alpha_uint8 = np.round(alpha_norm * 255.0).astype(np.uint8)

    rgb_uint8 = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)

    # 4-bands RGBA samenstellen
    rgba = np.dstack([rgb_uint8, alpha_uint8])

    # 7. Wegschrijven naar deflate-gecomprimeerde GeoTIFF
    output_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Wegschrijven naar RGBA GeoTIFF: %s", output_path)
    tifffile.imwrite(
        output_path,
        rgba,
        photometric="rgb",
        compression="deflate",
    )
    write_world_files(output_path, bounds, width_px, height_px, flat)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info("Succesvol gegenereerd: %s (%.2f MB, %dx%d px, 4 bands RGBA)", output_path, size_mb, width_px, height_px)


if __name__ == "__main__":
    main()
