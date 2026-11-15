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


def olive(c):
    """Suit cloth: green is the largest channel. The limits are wide, so that cloth in shadow is also found."""
    m_ = c.mean(-1)
    return (c[..., 1] > c[..., 0] * 0.995) & (c[..., 1] > c[..., 2] * 1.10) & (m_ > 0.05) & (m_ < 0.62)
def brown(c): return (c[..., 0] > c[..., 1] * 1.3) & (c[..., 1] > c[..., 2] * 1.05) & (c.mean(-1) < 0.42)


# Height of each texture pixel on the model (0 = floor, 1 = top), drawn from the UV triangles.
V = np.asarray(mesh.vertices); F = np.asarray(mesh.faces); UV = np.asarray(mesh.visual.uv)
hn = (V[:, 1] - V[:, 1].min()) / np.ptp(V[:, 1])                     # glTF: +Y is up
H, W = a.shape[:2]; zmap = np.full((H, W), -1.0, dtype=np.float32)
pix = np.stack([UV[:, 0] * W, (1 - UV[:, 1]) * H], axis=1)
fz = hn[F].mean(1)
# Side distance of each pixel from the centre plane, as a part of the model height.
xn = np.abs(V[:, 0] - (V[:, 0].min() + V[:, 0].max()) / 2) / np.ptp(V[:, 1]); fx = xn[F].mean(1); xmap = np.full((H, W), -1.0, dtype=np.float32)
FN = np.asarray(mesh.face_normals); fmap = np.zeros((H, W), dtype=np.float32)                 # 1 where the surface looks to the front (glTF: +Z)
sxn = (V[:, 0] - (V[:, 0].min() + V[:, 0].max()) / 2) / np.ptp(V[:, 1]); fsx = sxn[F].mean(1); sxmap = np.zeros((H, W), dtype=np.float32)      # signed side distance
for tri, zz, xx_, nz, sx_ in zip(pix[F].astype(np.int32), fz, fx, FN[:, 2], fsx):
    cv2.fillConvexPoly(zmap, tri, float(zz)); cv2.fillConvexPoly(xmap, tri, float(xx_)); cv2.fillConvexPoly(fmap, tri, 1.0 if nz > 0.3 else 0.0); cv2.fillConvexPoly(sxmap, tri, float(sx_))
zmap = np.where(zmap < 0, cv2.dilate(zmap, np.ones((9, 9), np.uint8)), zmap); xmap = np.where(xmap < 0, cv2.dilate(xmap, np.ones((9, 9), np.uint8)), xmap)

out = f.copy()
# Zones with suit cloth only: the trouser legs, and the area below the arms (inner arms and the sides of the jacket).
# The paint model cannot see these areas well, so they get coloured dots. They show when an arm goes up.
legs_zone = ((zmap > 0.078) & (zmap < 0.45)) | ((zmap > 0.47) & (zmap < 0.80) & (xmap > 0.082) & (xmap < 0.222)) \
    | ((zmap >= 0.43) & (zmap < 0.52) & (xmap < 0.19))          # also the jacket hem
# Step 1, trouser legs: this area has only suit cloth. Each pixel with a different colour gets the suit colour.
conf = legs_zone & ~olive(f)
G_OLIVE = np.median(f[olive(f) & (zmap > 0.078) & (zmap < 0.45)], axis=0)
white = lambda c: c.min(-1) > 0.60
out[conf] = np.where(olive(w)[conf][:, None], w[conf], G_OLIVE)
# Step 2, all suit areas: a pixel that is different from the median of its near area gets that median.
m2 = cv2.medianBlur((np.clip(out, 0, 1) * 255).astype(np.uint8), 25).astype(np.float32) / 255
dev = np.abs(out - m2).max(-1)
dots = olive(m2) & olive(w) & ((dev > np.where(legs_zone, 0.03, 0.04)) | ~olive(out))
out[dots] = m2[dots]
# Step 3: larger flecks, only well inside the suit cloth (not near the shirt, the pocket square or other parts).
deep = cv2.erode((olive(w) & olive(m2)).astype(np.uint8), np.ones((41, 41), np.uint8)) > 0
for ksize in (45, 45):
    m4 = cv2.medianBlur((np.clip(out, 0, 1) * 255).astype(np.uint8), ksize).astype(np.float32) / 255
    big = deep & olive(m4) & (np.abs(out - m4).max(-1) > 0.028)
    out[big] = m4[big]; dots = dots | big
dots = dots | conf
# Even suit cloth: replace the suit colour with a strongly blurred copy. This removes scratches, flecks and patches,
# and keeps the large light and dark areas. (Modelled parts now give the sharp edges, not the texture.)
# One constant colour. A blur does not work here: the texture is cut into many small pieces, and a blur in texture
# space gives each piece a different tone. This shows as light and dark patches on the model.
SUIT = np.median(out[olive(out) & (zmap > 0.45) & (zmap < 0.78)], axis=0)
suit_px = (olive(out) | (olive(m2) & ~brown(out) & (out.min(-1) < 0.60))) & (zmap > 0.050)
# Small dots of other colours inside the suit area: close the small holes of the suit area.
closed = cv2.morphologyEx(suit_px.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((23, 23), np.uint8)) > 0
holes = closed & ~suit_px & (zmap > 0.050) & ~white(out)
suit_px = suit_px | holes
out[suit_px] = SUIT
print("suit colour", np.round(SUIT * 255), "suit pixels", int(suit_px.sum()))
# Shirt: small olive, grey and skin-colour flecks in the white area get the white of their near area.
white = lambda c: c.min(-1) > 0.60
m3 = cv2.medianBlur((np.clip(out, 0, 1) * 255).astype(np.uint8), 31).astype(np.float32) / 255
fleck = white(m3) & white(w) & ~white(out) & (zmap > 0.45)
out[fleck] = m3[fleck]; dots = dots | fleck
# Shoes: one even brown, with a little of the old light and dark.
shoe = (zmap >= 0) & (zmap < 0.050)
# The band above the shoes is the trouser hem: suit cloth, not shoe leather.
hem = (zmap >= 0.050) & (zmap < 0.080) & ~olive(out)
out[hem] = SUIT
G_BROWN = np.median(f[shoe & brown(f)], axis=0)
lum = f[shoe].mean(-1, keepdims=True) / max(float(G_BROWN.mean()), 1e-3)
out[shoe] = G_BROWN * np.clip(0.75 + 0.25 * lum, 0.6, 1.25)
print("suit pixels corrected", int(dots.sum()), "shoe pixels", int(shoe.sum()), "of", a.shape[0] * a.shape[1])
# A second texture for the shirt front: between the lapels, all that is not suit cloth becomes clean white. This removes
# the blurred AI tie and the dark dots next to it. The build uses it after it has measured the AI tie (the modelled tie covers that area).
if "--shirt_tex" in sys.argv:
    G_WHITE = np.median(out[white(out) & (zmap > 0.66) & (zmap < 0.80) & (xmap < 0.04)], axis=0)
    zone = (zmap > 0.655) & (zmap < 0.83) & (xmap < 0.043) & (fmap > 0.5)
    # White: all that is not suit cloth, and also small olive flecks whose near area is white.
    vzone = zone & (~olive(out) | white(m2) | white(m3))
    shirt = out.copy(); shirt[vzone] = G_WHITE
    # Clean lapel edge: measure the white shirt width at each height, fit a smooth curve for each side, and paint by that curve.
    hs, xl, xr = [], [], []
    for h0 in np.arange(0.660, 0.800, 0.005):
        row = (np.abs(zmap - h0) < 0.004) & (fmap > 0.5) & (np.abs(sxmap) < 0.06) & white(shirt)
        if row.sum() < 50: continue
        hs.append(h0); xl.append(np.percentile(sxmap[row], 6)); xr.append(np.percentile(sxmap[row], 94))
    if len(hs) >= 8:
        pl, pr = np.polyfit(hs, xl, 2), np.polyfit(hs, xr, 2)
        band = (zmap > 0.660) & (zmap < 0.797) & (fmap > 0.5) & (np.abs(sxmap) < 0.075)
        el, er = np.polyval(pl, zmap), np.polyval(pr, zmap)
        inside = band & (sxmap > el + 0.0008) & (sxmap < er - 0.0008)
        near_out = band & ~inside & (sxmap > el - 0.010) & (sxmap < er + 0.010) & ~olive(shirt)
        shirt[inside] = G_WHITE; shirt[near_out] = np.where(olive(m2)[near_out][:, None], m2[near_out], G_OLIVE)
        print("lapel edge: rows", len(hs), "shirt half width bottom/top", round(float((xr[0] - xl[0]) / 2), 4), round(float((xr[-1] - xl[-1]) / 2), 4))
    # Top of the body next to the neck: the modelled collar is there, so rough AI collar and skin pieces become suit cloth.
    top = (zmap > 0.806) & (xmap > 0.034)
    shirt[top] = SUIT
    # Sleeve ends: a modelled cuff replaces the AI cuff, so the sleeve end becomes suit cloth. (The build measures the hands on the first texture.)
    sl = (zmap > 0.49) & (zmap < 0.57) & (xmap > 0.222) & ~olive(shirt)
    shirt[sl] = SUIT
    Image.fromarray((np.clip(shirt, 0, 1) * 255 + 0.5).astype(np.uint8)).save(sys.argv[sys.argv.index("--shirt_tex") + 1]); print("shirt front pixels made white", int(vzone.sum()))
img = Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8))
mesh.visual.material.baseColorTexture = img
mesh.export(dst)
if tex_out: img.save(tex_out)
print("WROTE", dst)
