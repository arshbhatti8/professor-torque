"""Correct the texture colours of a painted AI mesh so that the jacket and the shirt get the reference colours.

The paint model gives dark colours. This script finds the jacket (olive) and shirt (white) pixels in the texture
and applies one power-curve correction for each colour channel. The head and the body then have the same suit colours.

Usage: colour_match.py <in.glb> <out.glb> [--tex out_texture.png]
"""
import sys, numpy as np, trimesh
from PIL import Image

src, dst = sys.argv[1], sys.argv[2]
tex_out = sys.argv[sys.argv.index("--tex") + 1] if "--tex" in sys.argv else None
JACKET, SHIRT, TURBAN = np.array([0x5A, 0x66, 0x45]) / 255, np.array([0xF1, 0xEF, 0xEA]) / 255, np.array([0x8E, 0x12, 0x38]) / 255
anchor = "turban" if "--turban" in sys.argv else "jacket"      # the dark anchor colour: turban for the head, jacket for the body


def lin(c): return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def enc(c): return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.clip(c, 0, None) ** (1 / 2.4) - 0.055)


mesh = trimesh.load(src, force="mesh", process=False)
tex = mesh.visual.material.baseColorTexture.convert("RGB")
a = lin(np.asarray(tex, dtype=np.float64) / 255)
r, g, b = a[..., 0], a[..., 1], a[..., 2]; lum = a.mean(-1); sat = a.max(-1) - a.min(-1)
used = lum > 0.002
jacket = used & (g > r * 1.08) & (g > b * 1.25) & (lum < 0.25)
if anchor == "turban": jacket = used & (r > g * 2.2) & (r > b * 1.4) & (lum > 0.01)
shirt = used & (lum > np.percentile(lum[used], 93)) & (sat < 0.12 * a.max(-1) + 0.02)
mj, ms = np.median(a[jacket], axis=0), np.median(a[shirt], axis=0)
print(anchor, "pixels", int(jacket.sum()), "median", np.round(enc(mj) * 255), "| shirt pixels", int(shirt.sum()), "median", np.round(enc(ms) * 255))
tj, ts = lin(TURBAN if anchor == "turban" else JACKET), lin(SHIRT)
# A power curve for each channel: black stays black, and the two anchor colours go to their targets.
gamma = np.clip(np.log(ts / tj) / np.log(ms / mj), 0.6, 1.6); gain = ts / ms ** gamma; off = gamma
if "--gain" in sys.argv:                      # one brightness gain only: the shirt goes to white, hues stay
    gamma = np.ones(3); off = gamma; gain = np.full(3, ts.mean() / ms.mean())
out = np.clip(gain * a ** gamma, 0, 1)
img = Image.fromarray((enc(out) * 255 + 0.5).astype(np.uint8))
mesh.visual.material.baseColorTexture = img
mesh.visual.material.metallicFactor = 0.0; mesh.visual.material.roughnessFactor = 0.75
mesh.export(dst)
if tex_out: img.save(tex_out)
print("WROTE", dst, "gain", np.round(gain, 2), "gamma", np.round(off, 2), "texture", img.size)
