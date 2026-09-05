"""
Vergelijking van:
1. Optie 1: PC 2 + PC 3
2. Optie 2: PC 4 + PC 5
3. Optie 3: Mix van (PC 2 + PC 3) met (PC 4 + PC 5)
"""

import json
import logging
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
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
points_path = Path("data/export/a0-map/maps/plenair-map-full.json")
grid_path = Path("data/export/a0-map/maps/plenair-map-full-grid.json")

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

pca = PCA(n_components=6, random_state=42)
pca.fit(vectors[is_sub])
coords = pca.transform(vectors)

pc2 = coords[:, 1]
pc3 = coords[:, 2]
pc4 = coords[:, 3]
pc5 = coords[:, 4]

def normalize_comp(vec):
    sub = vec[is_sub]
    p5, p95 = np.percentile(sub, 5), np.percentile(sub, 95)
    return np.clip((vec - np.median(sub)) / (p95 - p5) * 2.0, -1.0, 1.0)

n_pc2 = normalize_comp(pc2)
n_pc3 = normalize_comp(pc3)
n_pc4 = normalize_comp(pc4)
n_pc5 = normalize_comp(pc5)

# Optie 1: PC 2 + PC 3 (geroteerd)
theta_1 = np.radians(35.0)
u_1 = normalize_comp(np.cos(theta_1) * n_pc2 - np.sin(theta_1) * n_pc3)
v_1 = normalize_comp(np.sin(theta_1) * n_pc2 + np.cos(theta_1) * n_pc3)

# Optie 2: PC 4 + PC 5 (geroteerd 30 graden)
theta_2 = np.radians(30.0)
u_2 = normalize_comp(np.cos(theta_2) * n_pc4 - np.sin(theta_2) * n_pc5)
v_2 = normalize_comp(np.sin(theta_2) * n_pc4 + np.cos(theta_2) * n_pc5)

# Optie 3: Mix van (2+3) en (4+5) -> 65% (PC2/PC3) + 35% (PC4/PC5)
u_3 = normalize_comp(0.65 * u_1 + 0.35 * u_2)
v_3 = normalize_comp(0.65 * v_1 + 0.35 * v_2)

recipes = [
    ("Optie 1: PC 2 + PC 3", u_1, v_1, "Bestuur, Economie & Fysieke Transitie"),
    ("Optie 2: PC 4 + PC 5", u_2, v_2, "Buitenland/Veiligheid & Crisis/Zorg"),
    ("Optie 3: Mix (2+3) & (4+5)", u_3, v_3, "Gecombineerde Synthese (65% / 35%)")
]

# 3. Canvas resolutie
scale = 0.12
DPI = 300.0
MM_PER_INCH = 25.4
A0_WIDTH_MM = 841.0
A0_HEIGHT_MM = 1189.0
width_px = round(A0_WIDTH_MM / MM_PER_INCH * DPI * scale)
height_px = round(A0_HEIGHT_MM / MM_PER_INCH * DPI * scale)

density_weights = np.where(is_sub, 1.0, 0.35)
hist_counts, _, _ = np.histogram2d(merc_x, merc_y, bins=[width_px, height_px], range=[[min_x, max_x], [min_y, max_y]], weights=density_weights)
hist_counts = np.flipud(hist_counts.T).astype(np.float64)

sub_weight = is_sub.astype(np.float64)
hist_sub, _, _ = np.histogram2d(merc_x, merc_y, bins=[width_px, height_px], range=[[min_x, max_x], [min_y, max_y]], weights=sub_weight)
hist_sub = np.flipud(hist_sub.T).astype(np.float64)

px_per_mm = (DPI * scale) / MM_PER_INCH
sigma_px = 3.2 * px_per_mm

smoothed_counts = gaussian_filter(hist_counts, sigma=sigma_px)
smoothed_sub = gaussian_filter(hist_sub, sigma=sigma_px * 1.5)
denom = gaussian_filter(hist_counts, sigma=sigma_px * 2.0) + 1e-3

substantive_ratio = np.clip(smoothed_sub / (smoothed_counts + 1e-3), 0.0, 1.0)
max_val = smoothed_counts.max()
norm_density = np.power(smoothed_counts / max_val, 0.45)

L = 100.0 - 70.0 * norm_density

rendered_images = []

for title, u_arr, v_arr, desc in recipes:
    hist_u, _, _ = np.histogram2d(merc_x, merc_y, bins=[width_px, height_px], range=[[min_x, max_x], [min_y, max_y]], weights=u_arr * sub_weight)
    hist_u = np.flipud(hist_u.T).astype(np.float64)
    
    hist_v, _, _ = np.histogram2d(merc_x, merc_y, bins=[width_px, height_px], range=[[min_x, max_x], [min_y, max_y]], weights=v_arr * sub_weight)
    hist_v = np.flipud(hist_v.T).astype(np.float64)
    
    interp_u = gaussian_filter(hist_u, sigma=sigma_px * 2.0) / denom
    interp_v = gaussian_filter(hist_v, sigma=sigma_px * 2.0) / denom
    
    max_chroma = 34.0
    chroma_mask = np.power(norm_density, 0.7) * np.power(substantive_ratio, 2.0)
    a = interp_u * max_chroma * chroma_mask
    b = interp_v * max_chroma * chroma_mask
    
    lab = np.stack([L, a, b], axis=-1)
    rgb = np.clip(lab2rgb_numpy(lab) * 255.0, 0, 255).astype(np.uint8)
    rendered_images.append((title, desc, rgb))

# 4. Plot 3 panelen naast elkaar
fig, axes = plt.subplots(1, 3, figsize=(21, 8.5), facecolor="#fbf9f4")

for idx, (title, desc, rgb) in enumerate(rendered_images):
    ax = axes[idx]
    ax.set_facecolor("#fbf9f4")
    ax.imshow(rgb)
    ax.set_title(f"{title}\n{desc}", fontsize=12, fontweight="bold", color="#22304e", pad=12, fontfamily="sans-serif")
    ax.axis("off")

plt.subplots_adjust(top=0.88, bottom=0.04, left=0.02, right=0.98, wspace=0.06)

out_png = Path("data/export/a0-map/pca_mixes_23_vs_45.png")
plt.savefig(out_png, dpi=200, facecolor=fig.get_facecolor(), bbox_inches="tight")
plt.close()

logging.info("Vergelijking (2+3) vs (4+5) opgeslagen: %s", out_png)
