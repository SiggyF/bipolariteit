"""
Test met:
1. Dimensieselectie (PC2 & PC3 ipv PC1, want PC1 is de procedurele as)
2. Kleurwiel rotatie (hoek theta voor optimale semantische kleuren)
3. Dichtheid-demping voor Moties & Voorzitter (zodat ze zacht zilver/grijs worden ipv zwarte inktvlekken)
"""

import json
import logging
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
from sklearn.decomposition import PCA
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(message)s")


def lab2rgb_numpy(lab: np.ndarray) -> np.ndarray:
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


# 1. Laad data
points_path = Path("data/export/plenair-map-full.json")
grid_path = Path("data/export/plenair-map-full-grid.json")

raw_points = json.loads(points_path.read_text(encoding="utf-8"))
points = raw_points["points"]
xs = np.array([p[1] for p in points], dtype=np.float64)
ys = np.array([p[2] for p in points], dtype=np.float64)
l0_ids = np.array([p[10] if len(p) > 10 else -1 for p in points], dtype=np.int32)

is_sub = ~np.isin(l0_ids, [1, 3])

grid_data = json.loads(grid_path.read_text(encoding="utf-8"))
left, bottom, right, top = grid_data["extent"]
span_x = right - left
span_y = top - bottom

WEB_MERCATOR_HALF_EXTENT = 20037508.342789244
merc_x = -WEB_MERCATOR_HALF_EXTENT + ((xs - left) / span_x) * 2.0 * WEB_MERCATOR_HALF_EXTENT
merc_y = -WEB_MERCATOR_HALF_EXTENT + ((ys - bottom) / span_y) * 2.0 * WEB_MERCATOR_HALF_EXTENT
bounds = (-WEB_MERCATOR_HALF_EXTENT, -WEB_MERCATOR_HALF_EXTENT, WEB_MERCATOR_HALF_EXTENT, WEB_MERCATOR_HALF_EXTENT)

min_x, min_y, max_x, max_y = bounds

# 2. Fit PCA
emb_full = np.load("data/embeddings/text-embedding-bge-m3_plenair-full.npz")
vectors = emb_full["vectors"]

pca = PCA(n_components=5, random_state=42)
pca.fit(vectors[is_sub])
coords = pca.transform(vectors)

# We gebruiken PC2 en PC3: hierop zijn Moties en Voorzitter van nature nagenoeg (0, 0)!
# PC2 = coords[:, 1], PC3 = coords[:, 2]
raw_u = coords[:, 1]
raw_v = coords[:, 2]

# Roteer de assen voor een mooie kleurverdeling (bijv. theta = 35 graden)
theta = np.radians(35.0)
u_rot = np.cos(theta) * raw_u - np.sin(theta) * raw_v
v_rot = np.sin(theta) * raw_u + np.cos(theta) * raw_v

# Robuuste normalisatie
sub_u = u_rot[is_sub]
sub_v = v_rot[is_sub]
p5_u, p95_u = np.percentile(sub_u, 5), np.percentile(sub_u, 95)
p5_v, p95_v = np.percentile(sub_v, 5), np.percentile(sub_v, 95)

u_norm = np.clip((u_rot - np.median(sub_u)) / (p95_u - p5_u) * 2.0, -1.0, 1.0)
v_norm = np.clip((v_rot - np.median(sub_v)) / (p95_v - p5_v) * 2.0, -1.0, 1.0)

# Dichtheid gewichten: geef Moties & Voorzitter een gewicht van 0.35 zodat ze niet zwart worden!
density_weights = np.where(is_sub, 1.0, 0.35)

# 3. Canvas resolutie
scale = 0.20
DPI = 300.0
MM_PER_INCH = 25.4
A0_WIDTH_MM = 841.0
A0_HEIGHT_MM = 1189.0
width_px = round(A0_WIDTH_MM / MM_PER_INCH * DPI * scale)
height_px = round(A0_HEIGHT_MM / MM_PER_INCH * DPI * scale)

# Gewogen dichtheid
hist_counts, _, _ = np.histogram2d(merc_x, merc_y, bins=[width_px, height_px], range=[[min_x, max_x], [min_y, max_y]], weights=density_weights)
hist_counts = np.flipud(hist_counts.T).astype(np.float64)

# Inhoudelijke gewichten
sub_weight = is_sub.astype(np.float64)
hist_sub, _, _ = np.histogram2d(merc_x, merc_y, bins=[width_px, height_px], range=[[min_x, max_x], [min_y, max_y]], weights=sub_weight)
hist_sub = np.flipud(hist_sub.T).astype(np.float64)

hist_u, _, _ = np.histogram2d(merc_x, merc_y, bins=[width_px, height_px], range=[[min_x, max_x], [min_y, max_y]], weights=u_norm * sub_weight)
hist_u = np.flipud(hist_u.T).astype(np.float64)

hist_v, _, _ = np.histogram2d(merc_x, merc_y, bins=[width_px, height_px], range=[[min_x, max_x], [min_y, max_y]], weights=v_norm * sub_weight)
hist_v = np.flipud(hist_v.T).astype(np.float64)

px_per_mm = (DPI * scale) / MM_PER_INCH
sigma_px = 3.2 * px_per_mm

smoothed_counts = gaussian_filter(hist_counts, sigma=sigma_px)
smoothed_sub = gaussian_filter(hist_sub, sigma=sigma_px * 1.5)
smoothed_u = gaussian_filter(hist_u, sigma=sigma_px * 2.0)
smoothed_v = gaussian_filter(hist_v, sigma=sigma_px * 2.0)

denom = gaussian_filter(hist_counts, sigma=sigma_px * 2.0) + 1e-3
interp_a = smoothed_u / denom
interp_b = smoothed_v / denom

substantive_ratio = smoothed_sub / (smoothed_counts + 1e-3)
substantive_ratio = np.clip(substantive_ratio, 0.0, 1.0)

max_val = smoothed_counts.max()
norm_density = np.power(smoothed_counts / max_val, 0.45)

# 4. CIELAB Constructie
# L*: zakt van 100 naar ~30 op inhoudelijke pieken, maar blijft veel lichter op de gedempte Moties/Voorzitter!
L = 100.0 - 70.0 * norm_density

# a* en b*: maximaal op inhoudelijke debatten, nul op Moties/Voorzitter
max_chroma = 32.0
chroma_mask = np.power(norm_density, 0.7) * np.power(substantive_ratio, 2.0)
a = interp_a * max_chroma * chroma_mask
b = interp_b * max_chroma * chroma_mask

lab_image = np.stack([L, a, b], axis=-1)

rgb_image = lab2rgb_numpy(lab_image)
rgb_uint8 = np.clip(rgb_image * 255.0, 0, 255).astype(np.uint8)

out_png = Path("data/export/a0-map/pca_color_rotated_preview.png")
Image.fromarray(rgb_uint8).save(out_png)
logging.info("Rotated PCA preview opgeslagen: %s", out_png)
