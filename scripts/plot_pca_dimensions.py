"""
Genereer een 5-panelen overzicht van de eerste 5 PCA-dimensies los op de kaart.
"""

import json
import logging
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
from sklearn.decomposition import PCA

logging.basicConfig(level=logging.INFO, format="%(message)s")

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

# 2. PCA fit
emb_full = np.load("data/embeddings/text-embedding-bge-m3_plenair-full.npz")
vectors = emb_full["vectors"]

pca = PCA(n_components=5, random_state=42)
pca.fit(vectors[is_sub])
coords = pca.transform(vectors)

var_ratios = pca.explained_variance_ratio_

# 3. Canvas grid instellingen (bijv. 800 x 1130 px voor elk paneel)
scale = 0.08
DPI = 300.0
MM_PER_INCH = 25.4
A0_WIDTH_MM = 841.0
A0_HEIGHT_MM = 1189.0
width_px = round(A0_WIDTH_MM / MM_PER_INCH * DPI * scale)
height_px = round(A0_HEIGHT_MM / MM_PER_INCH * DPI * scale)

hist_counts, _, _ = np.histogram2d(merc_x, merc_y, bins=[width_px, height_px], range=[[min_x, max_x], [min_y, max_y]])
hist_counts = np.flipud(hist_counts.T).astype(np.float64)

px_per_mm = (DPI * scale) / MM_PER_INCH
sigma_px = 3.2 * px_per_mm

smoothed_counts = gaussian_filter(hist_counts, sigma=sigma_px)
max_cnt = smoothed_counts.max()
norm_density = np.power(smoothed_counts / max_cnt, 0.45)
denom = gaussian_filter(hist_counts, sigma=sigma_px * 2.0) + 1e-3

# 4. Bereken kaarten per dimensie
pc_maps = []
sub_weight = is_sub.astype(np.float64)

for k in range(5):
    raw_k = coords[:, k]
    p5, p95 = np.percentile(raw_k[is_sub], 5), np.percentile(raw_k[is_sub], 95)
    k_norm = np.clip((raw_k - np.median(raw_k[is_sub])) / (p95 - p5) * 2.0, -1.0, 1.0)
    
    hist_k, _, _ = np.histogram2d(merc_x, merc_y, bins=[width_px, height_px], range=[[min_x, max_x], [min_y, max_y]], weights=k_norm)
    hist_k = np.flipud(hist_k.T).astype(np.float64)
    
    smoothed_k = gaussian_filter(hist_k, sigma=sigma_px * 2.0)
    interp_k = smoothed_k / denom
    pc_maps.append(interp_k)

# 5. Plot 5 panelen naast elkaar
fig, axes = plt.subplots(1, 5, figsize=(25, 7.5), facecolor="#fbf9f4")
cmap = plt.get_cmap("coolwarm")

# Labels per PC op basis van correlatie
pc_subtitles = [
    "Procedureel (-) vs Inhoud (+)",
    "Ruimte/Natuur (-) vs Samenleving (+)",
    "Financiën/Asiel (-) vs Klimaat/Natuur (+)",
    "Buitenland/Defensie (-) vs Binnenland (+)",
    "Sociaal/Zorg (-) vs Economie/Stelsel (+)"
]

for k, ax in enumerate(axes):
    ax.set_facecolor("#fbf9f4")
    val = pc_maps[k]
    
    # Alpha mask op basis van dichtheid
    alpha = np.clip(norm_density * 1.5, 0.0, 1.0)
    
    # Render met coolwarm colormap
    im = ax.imshow(val, cmap=cmap, vmin=-1.0, vmax=1.0, extent=[min_x, max_x, min_y, max_y])
    # Dichtheidsreliëf eroverheen mixen
    im.set_alpha(alpha)
    
    ax.set_title(f"PC {k+1} ({var_ratios[k]*100:.2f}% var)\n{pc_subtitles[k]}", 
                 fontsize=11.5, fontweight="bold", color="#22304e", pad=12, fontfamily="sans-serif")
    ax.axis("off")

# Gezamenlijke colorbar
cbar_ax = fig.add_axes([0.30, 0.06, 0.40, 0.025])
cbar = fig.colorbar(im, cax=cbar_ax, orientation="horizontal")
cbar.set_ticks([-1.0, 0.0, 1.0])
cbar.set_ticklabels(["Negatieve pool (-)", "Neutraal / Balans (0)", "Positieve pool (+)"])
cbar.ax.tick_params(labelsize=10, colors="#22304e")
cbar_ax.set_title("Relatieve semantische lading per dimensie", fontsize=10, color="#555047", pad=6)

plt.subplots_adjust(top=0.86, bottom=0.15, left=0.02, right=0.98, wspace=0.08)

out_path = Path("data/export/a0-map/pca_dimensions_comparison.png")
plt.savefig(out_path, dpi=200, facecolor=fig.get_facecolor(), bbox_inches="tight")
plt.close()

logging.info("5-panelen overzicht opgeslagen: %s", out_path)
