"""
Genereer een pixel-perfecte SVG van het CIELAB 2D kleurwiel met 100% consistente Libre Caslon typografie,
zonder (0,0), zonder box/kader rond PROCEDURE, en alle labels in dezelfde font, grootte en hoofdletterstijl.
"""

import base64
from pathlib import Path
import numpy as np
from PIL import Image

def lab2rgb_numpy(lab):
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
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

# 2D schijf met hoge resolutie (240x240)
N = 240
u = np.linspace(-1.0, 1.0, N)
v = np.linspace(-1.0, 1.0, N)
uu, vv = np.meshgrid(u, -v)
radius = np.sqrt(uu**2 + vv**2)
mask = radius <= 1.0

theta = np.radians(35.0)
u_rot = np.cos(theta) * uu - np.sin(theta) * vv
v_rot = np.sin(theta) * uu + np.cos(theta) * vv

max_chroma = 34.0
a = u_rot * max_chroma * radius
b = v_rot * max_chroma * radius
L = np.full_like(a, 70.0)

lab = np.stack([L, a, b], axis=-1)
rgb = (lab2rgb_numpy(lab) * 255.0).astype(np.uint8)
alpha = np.where(mask, 255, 0).astype(np.uint8)
rgba = np.dstack([rgb, alpha])

img = Image.fromarray(rgba)
disc_path = Path("data/export/a0-map/cielab_disc.png")
img.save(disc_path)

with open(disc_path, "rb") as f:
    b64_disc = base64.b64encode(f.read()).decode("ascii")

svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 380 135" width="380" height="135">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Libre+Caslon+Text:wght@700&amp;display=swap');
      
      .lab-axis {{ stroke: #22304e; stroke-width: 0.9; stroke-dasharray: 2.5, 2.5; opacity: 0.45; }}
      .lab-center {{ fill: #fbf9f4; stroke: #22304e; stroke-width: 1.6; }}
      
      /* Consistente typografie voor ALLE 5 labels */
      .label-all {{
        font-family: 'Libre Caslon Text', Georgia, serif;
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 0.4px;
      }}
      .label-klimaat {{ fill: #2d6b5e; text-anchor: middle; }}
      .label-asiel {{ fill: #2b567a; text-anchor: end; }}
      .label-financien {{ fill: #8a4834; text-anchor: start; }}
      .label-zorg {{ fill: #6a4975; text-anchor: middle; }}
      .label-proc {{ fill: #45587d; text-anchor: start; }}
    </style>
  </defs>

  <!-- CIELAB Disc geplaatst in het midden (x=190, y=66, diameter=96) -->
  <g transform="translate(142, 18)">
    <image href="data:image/png;base64,{b64_disc}" x="0" y="0" width="96" height="96" />
    
    <!-- Assenkruis door het centrum (48, 48) -->
    <line x1="4" y1="48" x2="92" y2="48" class="lab-axis" />
    <line x1="48" y1="4" x2="48" y2="92" class="lab-axis" />
    
    <!-- Centrum stip: Neutraal / Procedureel -->
    <circle cx="48" cy="48" r="3.2" class="lab-center" />
  </g>

  <!-- Alle 5 labels in identiek font, grootte en hoofdletterstijl -->
  <!-- Noord: Klimaat -->
  <text x="190" y="12" class="label-all label-klimaat">KLIMAAT &amp; NATUUR</text>
  
  <!-- West: Asiel -->
  <text x="134" y="69.5" class="label-all label-asiel">ASIEL &amp; BUITENLAND</text>
  
  <!-- Oost: Financiën -->
  <text x="246" y="69.5" class="label-all label-financien">FINANCIËN &amp; BESTUUR</text>
  
  <!-- Zuid: Zorg -->
  <text x="190" y="128" class="label-all label-zorg">ZORG &amp; ONDERWIJS</text>

  <!-- Pointerlijn naar neutraal centrum, zónder rechthoekskader/rand, puur tekst -->
  <polyline points="190,66 215,48 245,48" fill="none" stroke="#22304e" stroke-width="0.9" opacity="0.6" />
  <text x="249" y="51" class="label-all label-proc">PROCEDURE</text>
</svg>"""

out_svg = Path("data/export/a0-map/cielab_legend_widget.svg")
out_svg.write_text(svg_content, encoding="utf-8")
print(f"cielab_legend_widget.svg bijgewerkt: puur PROCEDURE zonder (0,0) en zonder kader!")
