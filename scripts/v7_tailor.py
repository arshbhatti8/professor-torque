"""Version 7 tailoring: modelled suit parts with real thickness and sharp edges, on top of the soft AI suit.

Parts: notch lapels, pocket flaps, chest pocket with a folded pocket square, jacket buttons, and trouser creases.
The AI mesh has almost no relief for these parts, so they are built as separate geometry.

Usage: scripts/blender.sh <parts.blend> --python scripts/v7_tailor.py -- <out.blend>
"""
import bpy, bmesh, sys, os, math, numpy as np
from pathlib import Path
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_lib import *

out_path = str(Path(sys.argv[sys.argv.index("--") + 1]).resolve())
body = D["Body"]


def arrays(o):
    me = o.data; n = len(me.vertices)
    P = np.empty(n * 3, dtype=np.float32); me.vertices.foreach_get("co", P); P = P.reshape(-1, 3).astype(np.float64)
    N = np.empty(n * 3, dtype=np.float32); me.vertices.foreach_get("normal", N); N = N.reshape(-1, 3).astype(np.float64)
    img = next(nd.image for nd in o.material_slots[0].material.node_tree.nodes if nd.type == "TEX_IMAGE")
    w, h = img.size; px = np.empty(w * h * 4, dtype=np.float32); img.pixels.foreach_get(px); px = px.reshape(h, w, 4)
    uv = np.empty(len(me.loops) * 2, dtype=np.float32); me.uv_layers[0].data.foreach_get("uv", uv); uv = uv.reshape(-1, 2)
    lv = np.empty(len(me.loops), dtype=np.int32); me.loops.foreach_get("vertex_index", lv)
    vuv = np.zeros((n, 2), dtype=np.float32); vuv[lv] = uv
    C = px[np.clip((vuv[:, 1] * h).astype(int), 0, h - 1), np.clip((vuv[:, 0] * w).astype(int), 0, w - 1), :3].astype(np.float64)
    return P, N, C


P, N, C = arrays(body); r, g, b = C[:, 0], C[:, 1], C[:, 2]; lum = C.mean(1)
olive = (g > r * 1.03) & (g > b * 1.2); white = C.min(1) > 0.60
OLIVE = np.median(C[olive & (P[:, 2] > 0.9) & (P[:, 2] < 1.5)], axis=0)
to_lin = lambda c: tuple(float(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c)
tree = surface(body)


def cloth(name, colour, rough=0.75):
    """Cloth material with a fine weave bump."""
    m = principled(name, colour, rough, Sheen_Weight=0.15)
    nt = m.node_tree; bs = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1400; nz.inputs["Detail"].default_value = 2
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.10; bp.inputs["Distance"].default_value = 0.0006
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"]); nt.links.new(nz.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], bs.inputs["Normal"])
    return m


suit = cloth("Suit_Cloth", to_lin(OLIVE))
# The same weave bump on the AI suit, so that the modelled parts and the suit look like the same cloth.
bm_ = body.material_slots[0].material; nt = bm_.node_tree; bs = nt.nodes["Principled BSDF"]
if not bs.inputs["Normal"].links:
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1400; nz.inputs["Detail"].default_value = 2
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.10; bp.inputs["Distance"].default_value = 0.0006
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"]); nt.links.new(nz.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], bs.inputs["Normal"])


def solid(name, grid, lift, thickness, material, y_fallback=-0.1, jump=0.012):
    """A solid part from a grid of (x, z) points. The top surface lies 'lift' in front of the body. The side walls are flat-shaded: sharp edges."""
    R, Cn = len(grid), len(grid[0]); top, bot = [], []; last = y_fallback
    for row in grid:
        for (x, z, extra) in row:
            q, _ = front_hit(tree, x, z); ys = q[1] if q is not None else last
            if abs(ys - last) > jump and last != y_fallback: ys = last            # a jump in depth: the ray hit a different part (for example the sleeve)
            last = ys
            top.append((x, ys - lift - extra, z)); bot.append((x, ys - lift - extra + thickness, z))
    verts = top + bot; faces = []; smooth = []; nt_ = len(top)
    for i in range(R - 1):
        for j in range(Cn - 1):
            a, b_, c, d = i * Cn + j, i * Cn + j + 1, (i + 1) * Cn + j + 1, (i + 1) * Cn + j
            faces.append((a, b_, c, d)); smooth.append(True); faces.append((nt_ + d, nt_ + c, nt_ + b_, nt_ + a)); smooth.append(True)
    edge = [(i, 0) for i in range(R)] + [(R - 1, j) for j in range(1, Cn)] + [(i, Cn - 1) for i in range(R - 2, -1, -1)] + [(0, j) for j in range(Cn - 2, 0, -1)]
    for k in range(len(edge)):
        (i1, j1), (i2, j2) = edge[k], edge[(k + 1) % len(edge)]; a, b_ = i1 * Cn + j1, i2 * Cn + j2
        faces.append((a, b_, nt_ + b_, nt_ + a)); smooth.append(False)
    o = new_object(name, verts, faces); o.data.materials.append(material)
    o.data.polygons.foreach_set("use_smooth", np.array(smooth, dtype=bool)); o.data.update()
    return o


# ---------------------------------------------------------------- the V opening of the jacket
rows = []
for z0 in np.arange(1.16, 1.53, 0.005):
    sel = (np.abs(P[:, 2] - z0) < 0.004) & (np.abs(P[:, 0]) < 0.12) & (N[:, 1] < -0.3) & white
    if sel.sum() >= 5: rows.append((z0, np.percentile(P[sel, 0], 4), np.percentile(P[sel, 0], 96)))
rows = np.array(rows); wide = (rows[:, 2] - rows[:, 1]) > 0.012
zr, xl, xr = rows[wide, 0], rows[wide, 1], rows[wide, 2]
ZB = float(zr.min()) - 0.022; XB = float((xl[:4].mean() + xr[:4].mean()) / 2)             # the closure point of the jacket (top button)
fit = {s: np.polyfit(zr - ZB, (xe - XB) * s, 2, w=np.where(zr < 1.47, 1.0, 0.3)) for s, xe in ((-1, xl), (1, xr))}
# The two lapels must be symmetrical: use the mean of the two measured sides.
half_w = lambda z: 0.5 * (max(0.0, float(np.polyval(fit[1], z - ZB))) + max(0.0, float(np.polyval(fit[-1], z - ZB)))) * min(1.0, (z - ZB) / 0.03)
XB = float(0.5 * (XB + 0.5 * (xl.mean() + xr.mean())))
edge_x = lambda s, z: XB + s * half_w(z)
print("jacket closure point", round(XB, 4), round(ZB, 4), "V half width at z 1.40:", round(edge_x(1, 1.40) - XB, 4), round(XB - edge_x(-1, 1.40), 4))

# ---------------------------------------------------------------- lapels (notch lapel with a collar piece)
Z_PT, Z_GORGE, Z_COL, Z_TOP = 1.405, 1.430, 1.446, 1.500


def lapel_width(z):
    if z <= Z_PT: return 0.062 * ((z - ZB) / (Z_PT - ZB)) ** 0.82
    if z <= Z_GORGE: return np.interp(z, [Z_PT, Z_GORGE], [0.062, 0.030])          # the top edge of the lapel (gorge line)
    if z <= Z_COL: return np.interp(z, [Z_GORGE, Z_COL], [0.030, 0.047])           # the bottom edge of the collar
    return np.interp(z, [Z_COL, Z_TOP], [0.047, 0.026])


for s, nm in ((-1, "R"), (1, "L")):
    grid = []
    for z in np.concatenate([np.linspace(ZB + 0.004, Z_PT, 70), np.linspace(Z_PT, Z_COL, 28)[1:], np.linspace(Z_COL, Z_TOP, 30)[1:]]):
        wo = lapel_width(float(z)); xe = edge_x(s, float(z)); row = []
        for c in range(9):
            w_ = -0.0025 + (wo + 0.0025) * c / 8
            row.append((xe + s * w_, float(z), 0.0030 * math.exp(-max(w_, 0) / 0.012)))      # the lapel roll: thicker at the inner edge
        grid.append(row)
    solid("Suit_Lapel." + nm, grid, 0.0038, 0.0034, suit, jump=1.0)

# ---------------------------------------------------------------- pocket flaps
for s, nm in ((-1, "R"), (1, "L")):
    cx, cz, hw, hh = XB + s * 0.100, 1.040, 0.038, 0.019; grid = []
    for v in np.linspace(0, 1, 14):
        rowhw = hw * (1 - 0.10 * smoothstep(0.65, 1.0, v) ** 2); row = []
        for u in (np.linspace(-1, 1, 15) if s == 1 else np.linspace(1, -1, 15)):      # start each row at the body centre side
            x = cx + u * rowhw; z = cz + hh - v * 2 * hh - s * u * 0.006 - 0.004 * smoothstep(0.6, 1.0, v) * (1 - u * u) * 0
            row.append((x, z, 0.0012 * v))
        grid.append(row)
    solid("Suit_Pocket_Flap." + nm, grid, 0.0030, 0.0030, suit)

# ---------------------------------------------------------------- chest pocket and pocket square
navy = (b > r * 1.15) & (lum < 0.33) & (P[:, 2] > 1.30) & (P[:, 2] < 1.43) & (np.abs(P[:, 0]) > 0.05) & (np.abs(P[:, 0]) < 0.16) & (N[:, 1] < -0.3)
if navy.sum() > 20:
    px0, px1 = np.percentile(P[navy, 0], 5), np.percentile(P[navy, 0], 95); pz0 = float(np.percentile(P[navy, 2], 8))
    print("pocket square found at x", round(px0, 3), round(px1, 3), "z", round(pz0, 3))
else:
    px0, px1, pz0 = 0.112, 0.148, 1.329; print("pocket square: position from the first measurement")
Wp = px1 - px0; Hs = 0.030
grid = [[(px0 - 0.005 + (Wp + 0.010) * u, pz0 - 0.011 + 0.011 * v + (u - 0.5) * 0.004, 0.0) for u in np.linspace(0, 1, 10)] for v in np.linspace(0, 1, 4)]
solid("Suit_Chest_Pocket", grid, 0.0030, 0.0028, suit)
prof = lambda u: float(np.interp(u, [0, 0.12, 0.30, 0.50, 0.74, 0.92, 1.0], [0.30, 0.72, 1.0, 0.62, 0.92, 0.55, 0.25]))      # two points of the folded square
grid = [[(px0 + Wp * u, pz0 + (u - 0.5) * 0.004 + Hs * prof(u) * v, 0.0015 * math.sin(math.pi * u) * v) for u in np.linspace(0, 1, 25)] for v in np.linspace(0, 1, 8)]
solid("Pocket_Square", grid, 0.0042, 0.0030, cloth("Pocket_Square", srgb("#1B2748"), 0.6))

# ---------------------------------------------------------------- buttons
btn_mat = principled("Suit_Button", srgb("#2A2018"), 0.35, Coat_Weight=0.3)
for i, (bx, bz) in enumerate(((XB + 0.004, ZB - 0.012), (XB + 0.004, ZB - 0.098))):
    q, nrm = front_hit(tree, bx, bz); c0 = q + np.array([0, -0.0030, 0]); verts, faces = [], []; SEGB = 20
    for ring, (rr_, dy) in enumerate(((0.0088, 0.002), (0.0088, -0.0008), (0.0070, -0.0022), (0.0, -0.0016))):
        for k in range(SEGB):
            th = 2 * math.pi * k / SEGB; verts.append(c0 + np.array([rr_ * math.cos(th), dy, rr_ * math.sin(th)]))
    for ring in range(3):
        for k in range(SEGB): faces.append((ring * SEGB + k, ring * SEGB + (k + 1) % SEGB, (ring + 1) * SEGB + (k + 1) % SEGB, (ring + 1) * SEGB + k))
    o = new_object(f"Suit_Button.{i + 1}", verts, faces); o.data.materials.append(btn_mat)
    bmb = bmesh.new(); bmb.from_mesh(o.data); bmesh.ops.remove_doubles(bmb, verts=bmb.verts, dist=1e-6); bmb.to_mesh(o.data); bmb.free()

# ---------------------------------------------------------------- front edges of the jacket below the buttons
for s, nm in ((-1, "R"), (1, "L")):
    zs = np.arange(ZB - 0.004, 0.925, -0.006) if s == 1 else np.arange(ZB - 0.118, 0.925, -0.006)       # the left front lies on top
    grid = []
    for z in zs:
        xc_ = XB + s * (0.0015 + 0.040 * float(smoothstep(ZB - 0.115, 0.925, z)) ** 1.6)
        grid.append([(xc_ + du, float(z), e) for du, e in ((-0.0030, -0.0010), (-0.0012, 0.0004), (0.0, 0.0012), (0.0012, 0.0004), (0.0030, -0.0010))])
    solid("Suit_Front_Edge." + nm, grid, 0.0008, 0.0022, suit)

# ---------------------------------------------------------------- trouser creases
for s, nm in ((-1, "R"), (1, "L")):
    pts = []
    for z in np.arange(0.84, 0.125, -0.012):
        sl = P[(np.abs(P[:, 2] - z) < 0.006) & (s * P[:, 0] > 0.02) & (s * P[:, 0] < 0.24)]
        if len(sl) < 10: continue
        fr_ = sl[sl[:, 1] < sl[:, 1].min() + 0.012]; pts.append((float(np.median(fr_[:, 0])), float(z)))
    pts = np.array(pts); pf = np.polyfit(pts[:, 1], pts[:, 0], 2)                # a smooth crease line
    grid = [[(float(np.polyval(pf, z)) + du, float(z), e) for du, e in ((-0.0030, -0.0012), (-0.0012, 0.0002), (0.0, 0.0012), (0.0012, 0.0002), (0.0030, -0.0012))] for z in np.arange(0.84, 0.125, -0.008)]
    solid("Suit_Crease." + nm, grid, 0.0006, 0.0020, suit)

# ---------------------------------------------------------------- trouser hems: a band with a sharp lower edge at each ankle
Z_HEM = 0.050 * 1.88                                         # the height where the shoe colour stops in the texture
for s, nm in ((-1, "R"), (1, "L")):
    NBh = 40; rings = []
    for z0 in (Z_HEM - 0.006, Z_HEM + 0.012, Z_HEM + 0.034):
        sl = P[(np.abs(P[:, 2] - z0) < 0.006) & (s * P[:, 0] > 0.02) & (s * P[:, 0] < 0.26)]
        c = np.array([(sl[:, 0].min() + sl[:, 0].max()) / 2, (sl[:, 1].min() + sl[:, 1].max()) / 2])
        ang = np.arctan2(sl[:, 1] - c[1], sl[:, 0] - c[0]); rad = np.hypot(sl[:, 0] - c[0], sl[:, 1] - c[1])
        bins = ((ang + math.pi) / (2 * math.pi) * NBh).astype(int) % NBh
        rb = np.array([rad[bins == i].max() if (bins == i).any() else np.nan for i in range(NBh)])
        good = ~np.isnan(rb); rb = np.interp(np.arange(NBh), np.where(good)[0], rb[good], period=NBh)
        rb = np.convolve(np.concatenate([rb[-3:], rb, rb[:3]]), np.ones(7) / 7, mode="valid")
        rings.append((z0, c, rb))
    verts, faces = [], []
    layers = [(0, 1.045, 0.0), (0, 1.085, 0.0), (1, 1.070, 0.0), (2, 1.035, 0.0)]          # (ring, radius factor, unused): the lower edge is thick and sharp
    for i in range(NBh):
        th = -math.pi + (i + 0.5) * 2 * math.pi / NBh
        for ri, fac, _ in layers:
            z0, c, rb = rings[ri]; verts.append((c[0] + fac * rb[i] * math.cos(th), c[1] + fac * rb[i] * math.sin(th), z0))
    nl = len(layers)
    for i in range(NBh):
        i2 = (i + 1) % NBh
        for j in range(nl - 1): faces.append((i * nl + j, i2 * nl + j, i2 * nl + j + 1, i * nl + j + 1))
    o = new_object("Suit_Trouser_Hem." + nm, verts, faces, smooth=False); o.data.materials.append(suit)
    sm_ = np.ones(len(o.data.polygons), dtype=bool); sm_[0::(nl - 1)] = False                 # the lower edge face is flat: a sharp edge
    o.data.polygons.foreach_set("use_smooth", sm_); o.data.update()

bpy.ops.wm.save_as_mainfile(filepath=out_path)
print("SAVED", out_path)
