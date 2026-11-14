"""Remove small dots from the suit texture and make the shoe colour even.

The paint model leaves small light, dark and coloured dots on the olive suit, and a mottled colour on the shoes.
The script compares each pixel with the median of its area. On the suit, a pixel that is very different gets the
median colour. On the shoes, all pixels move to the median colour.

Usage: clean_texture.py <in.glb> <out.glb> [--tex out.png]
"""
import sys, numpy as np, trimesh, cv2
from PIL import Image

src, dst = sys.argv[1], sys.argv[2]
tex_out = sys.argv[sys.argv.index("--tex") + 1] if "--tex" in sys.argv else None
mesh = trimesh.load(src, force="mesh", process=False)
a = np.asarray(mesh.visual.material.baseColorTexture.convert("RGB"))
med = cv2.medianBlur(a, 25); wide = cv2.medianBlur(cv2.resize(a, (512, 512), interpolation=cv2.INTER_AREA), 21)
wide = cv2.resize(wide, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_LINEAR)
f, m, w = a.astype(np.float32) / 255, med.astype(np.float32) / 255, wide.astype(np.float32) / 255


def olive(c): return (c[..., 1] > c[..., 0] * 1.03) & (c[..., 1] > c[..., 2] * 1.2)
def brown(c): return (c[..., 0] > c[..., 1] * 1.3) & (c[..., 1] > c[..., 2] * 1.05) & (c.mean(-1) < 0.42)


# Height of each texture pixel on the model (0 = floor, 1 = top), drawn from the UV triangles.
V = np.asarray(mesh.vertices); F = np.asarray(mesh.faces); UV = np.asarray(mesh.visual.uv)
hn = (V[:, 1] - V[:, 1].min()) / np.ptp(V[:, 1])                     # glTF: +Y is up
H, W = a.shape[:2]; zmap = np.full((H, W), -1.0, dtype=np.float32)
pix = np.stack([UV[:, 0] * W, (1 - UV[:, 1]) * H], axis=1)
fz = hn[F].mean(1)
for tri, zz in zip(pix[F].astype(np.int32), fz): cv2.fillConvexPoly(zmap, tri, float(zz))
zmap = np.where(zmap < 0, cv2.dilate(zmap, np.ones((9, 9), np.uint8)), zmap)

out = f.copy()
legs_zone = (zmap > 0.078) & (zmap < 0.45)
# Step 1, trouser legs: this area has only suit cloth. Each pixel with a different colour gets the suit colour.
conf = legs_zone & ~olive(f)
G_OLIVE = np.median(f[olive(f) & legs_zone], axis=0)
out[conf] = np.where(olive(w)[conf][:, None], w[conf], G_OLIVE)
# Step 2, all suit areas: a pixel that is different from the median of its near area gets that median.
m2 = cv2.medianBlur((np.clip(out, 0, 1) * 255).astype(np.uint8), 25).astype(np.float32) / 255
dev = np.abs(out - m2).max(-1)
dots = olive(m2) & olive(w) & ((dev > np.where(legs_zone, 0.03, 0.07)) | ~olive(out))
out[dots] = m2[dots]
dots = dots | conf
# Shirt: small olive, grey and skin-colour flecks in the white area get the white of their near area.
white = lambda c: c.min(-1) > 0.60
m3 = cv2.medianBlur((np.clip(out, 0, 1) * 255).astype(np.uint8), 31).astype(np.float32) / 255
fleck = white(m3) & white(w) & ~white(out) & (zmap > 0.45)
out[fleck] = m3[fleck]; dots = dots | fleck
# Shoes: one even brown, with a little of the old light and dark.
shoe = (zmap >= 0) & (zmap < 0.060)
G_BROWN = np.median(f[shoe & brown(f)], axis=0)
lum = f[shoe].mean(-1, keepdims=True) / max(float(G_BROWN.mean()), 1e-3)
out[shoe] = G_BROWN * np.clip(0.75 + 0.25 * lum, 0.6, 1.25)
print("suit pixels corrected", int(dots.sum()), "shoe pixels", int(shoe.sum()), "of", a.shape[0] * a.shape[1])
img = Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8))
mesh.visual.material.baseColorTexture = img
mesh.export(dst)
if tex_out: img.save(tex_out)
print("WROTE", dst)
