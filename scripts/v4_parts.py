"""Version 4 parts: replace the fused AI hands with clean CC0 hands, and add a clean striped tie.

Usage: scripts/blender.sh <assembled.blend> --python scripts/v4_parts.py -- <base_hand.blend> <out.blend>
"""
import bpy, bmesh, sys, os, math, numpy as np
from pathlib import Path
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_lib import *

argv = sys.argv[sys.argv.index("--") + 1:]
hand_path, out_path = (str(Path(a).resolve()) for a in argv[:2])
body, head = D["Body"], D["Head"]


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


P, N, C = arrays(body)
r, g, b = C[:, 0], C[:, 1], C[:, 2]; lum = C.mean(1)
skin = (r > 0.5) & (r > g * 1.2) & (g > b * 1.1)
SKIN_COL = np.median(C[skin], axis=0)
print("skin vertices on the body", int(skin.sum()), "skin colour", np.round(SKIN_COL * 255))

# ---------------------------------------------------------------- hands
with bpy.data.libraries.load(hand_path) as (src, dst): dst.objects = ["Hand_Base"]
base = dst.objects[0]
HB = np.array([v.co for v in base.data.vertices], dtype=np.float64)
HF = [tuple(p.vertices) for p in base.data.polygons]
top = HB[HB[:, 2] > HB[:, 2].max() - 0.012]; B0 = np.array([(top[:, 0].min() + top[:, 0].max()) / 2, (top[:, 1].min() + top[:, 1].max()) / 2, HB[:, 2].max()])
BASE_LEN = 0.205                                   # wrist crease to finger tip of the base hand
skin_mat = principled("Hand_Skin", tuple(float(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in SKIN_COL), 0.55,
                      Subsurface_Weight=0.15, Subsurface_Radius=(0.9, 0.4, 0.25), Subsurface_Scale=0.006)
wrists = {}; hand_info = []
shirt_mat = principled("Shirt", srgb("#F1EFEA"), 0.7, Sheen_Weight=0.1)
base_uv = {}                                           # UV of the base hand, for each face corner
for poly in base.data.polygons:
    for li in poly.loop_indices: base_uv[(poly.index, base.data.loops[li].vertex_index)] = tuple(base.data.uv_layers[0].data[li].uv)
for side, name in ((-1, "R"), (1, "L")):
    arm = side * P[:, 0] > 0.26
    A = P[arm]; mean = A.mean(0)
    w_, v_ = np.linalg.eigh(np.cov((A - mean).T)); d = v_[:, -1]
    if d[2] > 0: d = -d                             # the arm axis points down to the hand
    t = (P - mean) @ d
    ts = t[arm & skin]; t_w, t_tip = np.percentile(ts, 3), t[arm].max()
    ring = P[arm & (np.abs(t - t_w) < 0.012)]; Wc = ring.mean(0)
    k = (t_tip - t_w) / BASE_LEN
    # Cut the sleeve with a plane square to the arm. This gives a straight, clean sleeve end.
    t_c = t_w - 0.014; cut_pt = mean + d * t_c
    bm = bmesh.new(); bm.from_mesh(body.data); bm.verts.ensure_lookup_table()
    sel = [f_ for f_ in bm.faces if all(side * v.co.x > 0.26 for v in f_.verts)]
    geom = list({v for f_ in sel for v in f_.verts}) + list({e for f_ in sel for e in f_.edges}) + sel
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=Vector(cut_pt), plane_no=Vector(d), clear_outer=True, clear_inner=False)
    rim = np.array([v.co[:] for v in bm.verts if side * v.co.x > 0.26 and abs((np.array(v.co) - cut_pt) @ d) < 1e-4])
    bm.to_mesh(body.data); bm.free()
    # Shirt cuff: a short white tube that follows the shape of the sleeve end.
    rc = rim.mean(0); u_ax = np.cross(d, [0, 1, 0]); u_ax /= np.linalg.norm(u_ax); v_ax = np.cross(d, u_ax)
    rel = rim - rc; ang = np.arctan2(rel @ v_ax, rel @ u_ax); rad = np.hypot(rel @ u_ax, rel @ v_ax)
    NB = 40; bins = ((ang + math.pi) / (2 * math.pi) * NB).astype(int) % NB
    rb = np.array([rad[bins == i].max() if (bins == i).any() else np.nan for i in range(NB)])
    good = ~np.isnan(rb); rb = np.interp(np.arange(NB), np.where(good)[0], rb[good], period=NB)
    rb = np.convolve(np.concatenate([rb[-3:], rb, rb[:3]]), np.ones(7) / 7, mode="valid")
    verts, faces = [], []
    rings = [(0.90, -0.030), (0.90, 0.012), (0.87, 0.0135), (0.76, 0.012), (0.76, -0.006)]      # (radius factor, distance past the sleeve end)
    for i in range(NB):
        th = -math.pi + (i + 0.5) * 2 * math.pi / NB
        for fr, off in rings: verts.append(rc + d * off + fr * rb[i] * (math.cos(th) * u_ax + math.sin(th) * v_ax))
    nr = len(rings)
    for i in range(NB):
        i2 = (i + 1) % NB
        for j in range(nr - 1): faces.append((i * nr + j, i2 * nr + j, i2 * nr + j + 1, i * nr + j + 1))
    cuff = new_object("Shirt_Cuff." + name, verts, faces); cuff.data.materials.append(shirt_mat)
    m = cuff.modifiers.new("Subdivision", "SUBSURF"); m.levels = 1; m.render_levels = 2
    tt = np.array([0.0, -1.0, 0.0]); tt = tt - d * tt.dot(d); tt /= np.linalg.norm(tt)      # thumb direction: to the front
    pp = np.cross(tt, d)
    V = HB - B0
    if side == 1:
        V = V * np.array([-1, 1, 1]); R = np.stack([-tt, -pp, -d], axis=1)
    else:
        R = np.stack([tt, pp, -d], axis=1)
    W = (Wc - d * 0.035 * k) + k * (V @ R.T)
    faces = [f[::-1] for f in HF] if side == 1 else HF
    o = new_object("Hand." + name, W, faces)
    uvl = o.data.uv_layers.new(name="UVMap")
    for poly in o.data.polygons:
        for li in poly.loop_indices: uvl.data[li].uv = base_uv[(poly.index, o.data.loops[li].vertex_index)]
    at = o.data.attributes.new("base", "FLOAT_VECTOR", "POINT"); at.data.foreach_set("vector", HB.astype(np.float32).ravel())
    o.data.materials.append(skin_mat)
    m = o.modifiers.new("Subdivision", "SUBSURF"); m.levels = 1; m.render_levels = 2
    wrists[name] = (Wc, d, k)
    M4 = np.eye(4); M4[:3, :3] = k * (R @ np.diag([-1.0, 1, 1]) if side == 1 else R); M4[:3, 3] = (Wc - d * 0.035 * k) - M4[:3, :3] @ B0
    o["base_to_world"] = [float(x) for x in M4.ravel()]; o["arm_axis"] = [float(x) for x in d]; o["wrist"] = [float(x) for x in Wc]
    P, N, C = arrays(body); r, g, b = C[:, 0], C[:, 1], C[:, 2]; skin = (r > 0.5) & (r > g * 1.2) & (g > b * 1.1)
    print(f"hand {name}: wrist {np.round(Wc, 3)} sleeve rim vertices {len(rim)} mean rim radius {rb.mean():.3f} scale {k:.2f}")
bpy.data.objects.remove(base)

# Hand texture: skin with lighter palms and finger nails, baked to the UV map of the hand.
nt = skin_mat.node_tree; bs = nt.nodes["Principled BSDF"]
an = nt.nodes.new("ShaderNodeAttribute"); an.attribute_name = "base"; sp = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(an.outputs["Vector"], sp.inputs[0])


def nmath(op, a_, b_=None):
    nd = nt.nodes.new("ShaderNodeMath"); nd.operation = op
    for i, v in enumerate((a_, b_)):
        if v is None: continue
        if isinstance(v, (int, float)): nd.inputs[i].default_value = v
        else: nt.links.new(v, nd.inputs[i])
    return nd.outputs[0]


def step(v, lo_, hi_):
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.interpolation_type = "SMOOTHSTEP"; nt.links.new(v, mr.inputs["Value"])
    mr.inputs["From Min"].default_value = lo_; mr.inputs["From Max"].default_value = hi_
    return mr.outputs["Result"]


nail = None
for xf, tip in ((0.036, -0.216), (0.012, -0.235), (-0.012, -0.225), (-0.036, -0.200)):
    mx = nmath("SUBTRACT", 1.0, step(nmath("ABSOLUTE", nmath("SUBTRACT", sp.outputs["X"], xf)), 0.0058, 0.0072))
    mz = nmath("MULTIPLY", step(sp.outputs["Z"], tip + 0.0025, tip + 0.0045), nmath("SUBTRACT", 1.0, step(sp.outputs["Z"], tip + 0.0150, tip + 0.0165)))
    my = nmath("SUBTRACT", 1.0, step(sp.outputs["Y"], -0.0030, 0.0000))        # the back of the finger
    one = nmath("MULTIPLY", nmath("MULTIPLY", mx, mz), my)
    nail = one if nail is None else nmath("MAXIMUM", nail, one)
palm = nmath("MULTIPLY", step(sp.outputs["Y"], 0.002, 0.012), 0.35)
SK = tuple(bs.inputs["Base Color"].default_value[:3])
mixp = nt.nodes.new("ShaderNodeMix"); mixp.data_type = "RGBA"; mixp.inputs["A"].default_value = (*SK, 1); mixp.inputs["B"].default_value = (min(SK[0] * 1.12, 1), SK[1] * 1.25, SK[2] * 1.35, 1)
nt.links.new(palm, mixp.inputs["Factor"])
mixn = nt.nodes.new("ShaderNodeMix"); mixn.data_type = "RGBA"; mixn.inputs["B"].default_value = (min(SK[0] * 1.10, 1), SK[1] * 1.45, SK[2] * 1.75, 1)
nt.links.new(nmath("MULTIPLY", nail, 0.85), mixn.inputs["Factor"]); nt.links.new(mixp.outputs["Result"], mixn.inputs["A"])
himg = bpy.data.images.new("hand_skin_1k", 1024, 1024)
em = nt.nodes.new("ShaderNodeEmission"); nt.links.new(mixn.outputs["Result"], em.inputs["Color"])
outn = nt.nodes["Material Output"]; nt.links.new(em.outputs[0], outn.inputs["Surface"])
tximg = nt.nodes.new("ShaderNodeTexImage"); tximg.image = himg; nt.nodes.active = tximg
sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = 4; sc.cycles.device = "CPU"; sc.render.bake.margin = 16
hr = D["Hand.R"]; bpy.ops.object.select_all(action="DESELECT"); hr.select_set(True); bpy.context.view_layer.objects.active = hr
print("hand texture bake", bpy.ops.object.bake(type="EMIT"))
himg.pack()
nt.links.new(bs.outputs[0], outn.inputs["Surface"]); nt.links.new(tximg.outputs["Color"], bs.inputs["Base Color"])
for nd in [nd for nd in nt.nodes if nd.type in ("MATH", "MIX", "EMISSION", "ATTRIBUTE", "SEPXYZ", "MAP_RANGE")]: nt.nodes.remove(nd)

# ---------------------------------------------------------------- shirt and tie areas on the chest
P, N, C = arrays(body); r, g, b = C[:, 0], C[:, 1], C[:, 2]; lum = C.mean(1)
chest = (np.abs(P[:, 0]) < 0.12) & (P[:, 2] > 1.15) & (P[:, 2] < 1.56) & (N[:, 1] < -0.3)
white = C.min(1) > 0.62
olive = (g > r * 1.03) & (g > b * 1.2)
rows = []; white_rows = []
for z0 in np.arange(1.16, 1.56, 0.006):
    row = chest & (np.abs(P[:, 2] - z0) < 0.004)
    wx = P[row & white, 0]
    if len(wx) < 6: continue
    x0, x1 = np.percentile(wx, 3), np.percentile(wx, 97); white_rows.append((z0, x0, x1))
    dark = row & ~white & ~olive & (lum < 0.5) & (P[:, 0] > x0) & (P[:, 0] < x1)
    if dark.sum() >= 4:
        dx = P[dark, 0]; rows.append((z0, np.percentile(dx, 3), np.percentile(dx, 97)))
rows = np.array(rows); white_rows = np.array(white_rows)
zr = rows[:, 0]; cx = (rows[:, 1] + rows[:, 2]) / 2; hw = (rows[:, 2] - rows[:, 1]) / 2
Z_BOT = float(zr.min()) - 0.004
cfit = np.polyfit(zr, cx, 1)
for z0 in np.arange(Z_BOT, 1.10, -0.006):                # below the last white row, follow the dark tie to the jacket button
    row = chest & (np.abs(P[:, 2] - z0) < 0.004) & (np.abs(P[:, 0] - np.polyval(cfit, z0)) < 0.03) & ~olive & ~white
    if row.sum() < 4: break
    Z_BOT = z0 - 0.004
mid = (zr > zr.min() + 0.03) & (zr < zr.max() - 0.03); hfit = np.polyfit(zr[mid], hw[mid], 1)
body_tree = surface(body)
NAVY, RED, CREAM = srgb("#1B2748"), srgb("#B9523C"), srgb("#E2DBCB")

# ---------------------------------------------------------------- collar measurements on the head mesh
HPc, HNc, HCc = arrays(head)
hl = HCc.mean(1); hsat = HCc.max(1) - HCc.min(1)
is_shirt = (hsat < 0.13) & (hl > 0.36) & (HPc[:, 2] < 1.63)             # the AI collar: white, or grey in shadow
is_skin = (HCc[:, 0] > 0.45) & (HCc[:, 0] > HCc[:, 1] * 1.15) & (HCc[:, 1] > HCc[:, 2] * 1.05)
hwhite = (HCc.min(1) > 0.62) & (HPc[:, 2] < 1.63)                       # clear white only, for the measurements
back_top = float(np.percentile(HPc[hwhite & (HPc[:, 1] > 0.03), 2], 92))
neck = is_skin & (HPc[:, 2] > back_top + 0.002) & (HPc[:, 2] < back_top + 0.012) & (HPc[:, 1] > 0.0)
CXc = float((HPc[neck, 0].min() + HPc[neck, 0].max()) / 2); half_w = float((HPc[neck, 0].max() - HPc[neck, 0].min()) / 2)
CYc = float(HPc[neck, 1].max() - half_w * 0.95)
phi_v = np.arctan2(HPc[:, 0] - CXc, -(HPc[:, 1] - CYc)); radv = np.hypot(HPc[:, 0] - CXc, HPc[:, 1] - CYc)      # phi: 0 = front, pi = back
NBc = 36; binc = ((phi_v + math.pi) / (2 * math.pi) * NBc).astype(int) % NBc
bin_phi = -math.pi + (np.arange(NBc) + 0.5) * 2 * math.pi / NBc
z_m = np.full(NBc, np.nan); r_m = np.full(NBc, np.nan)
for i in range(NBc):
    if abs(bin_phi[i]) < 1.0: continue                                  # the beard hides the front
    selw = hwhite & (binc == i) & (radv < half_w * 1.6)
    if selw.sum() > 10: z_m[i] = np.percentile(HPc[selw, 2], 92)
    seln = is_skin & (binc == i) & (HPc[:, 2] > back_top + 0.002) & (HPc[:, 2] < back_top + 0.012) & (abs(bin_phi[i]) > 1.6)
    if seln.sum() > 5: r_m[i] = np.percentile(radv[seln], 80)
good = ~np.isnan(z_m); z_back = float(np.median(z_m[good & (np.abs(bin_phi) > 2.5)])); z_side = float(np.median(z_m[good & (np.abs(bin_phi) < 1.7)]))
z_front = min(z_side - 0.006, z_back - 0.010)
collar_top = lambda ph: z_back - (z_back - z_front) * ((1 + math.cos(ph)) / 2) ** 1.5
goodr = ~np.isnan(r_m); r_neck = float(np.median(r_m[goodr]))
RXc, RYc = half_w + 0.006, r_neck * 0.92 + 0.006
print("collar: neck centre", round(CXc, 3), round(CYc, 3), "neck half width", round(half_w, 3), "collar top back/side/front", round(z_back, 3), round(z_side, 3), round(z_front, 3))
# Remove the AI collar from the head mesh. The modelled collar replaces it.
dropc = is_shirt & (HPc[:, 2] < z_back + 0.006)
bm = bmesh.new(); bm.from_mesh(head.data); bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[v for v, kd in zip(bm.verts, dropc) if kd], context="VERTS"); bm.to_mesh(head.data); bm.free()
print("AI collar vertices removed from the head", int(dropc.sum()))

# ---------------------------------------------------------------- tie
kz1 = z_front - 0.004; kz0 = kz1 - 0.036                                # knot: top and bottom
Z_TOP = kz0 + 0.014
def tie_centre(z): return float(np.polyval(cfit, min(z, zr.max()))) if z < zr.max() else float(np.interp(z, [zr.max(), kz1], [np.polyval(cfit, zr.max()), CXc]))
def tie_half(z):
    base_hw = float(np.clip(np.polyval(hfit, z), 0.013, 0.034)) + 0.003
    return min(base_hw, max((z - Z_BOT) * 0.55 + 0.001, 0.0005))            # the tie goes to a point at the jacket button
print("tie z", round(Z_BOT, 3), round(Z_TOP, 3), "knot z", round(kz0, 3), round(kz1, 3))
ROWS, COLS = 70, 9; verts, faces, uvs = [], [], []
for ri in range(ROWS):
    z = Z_TOP + (Z_BOT - Z_TOP) * ri / (ROWS - 1); hwz = tie_half(z); cxz = tie_centre(z)
    for c in range(COLS):
        tcol = -1 + 2 * c / (COLS - 1); x = cxz + tcol * hwz
        q, _ = front_hit(body_tree, x, z); ys = q[1] if q is not None else (verts[-1][1] if verts else -0.07)
        lift = 0.0002 if abs(tcol) == 1 else 0.0030 + 0.0022 * (1 - tcol * tcol)
        verts.append((x, ys - lift, z)); uvs.append(((tcol + 1) / 2, 0.86 * (1 - ri / (ROWS - 1))))
for ri in range(ROWS - 1):
    for c in range(COLS - 1): faces.append((ri * COLS + c, ri * COLS + c + 1, (ri + 1) * COLS + c + 1, (ri + 1) * COLS + c))
tie = new_object("Tie", verts, faces)
uvl = tie.data.uv_layers.new(name="UVMap")
for loop in tie.data.loops: uvl.data[loop.index].uv = uvs[loop.vertex_index]
TW, TH = 512, 2048; img = np.zeros((TH, TW, 4), dtype=np.float32)
vv = (np.arange(TH) + 0.5) / TH; uu = (np.arange(TW) + 0.5) / TW; zz = Z_BOT + (Z_TOP - Z_BOT) * vv / 0.86
hwa = np.array([tie_half(min(z, Z_TOP)) for z in zz]); xx = (2 * uu[None, :] - 1) * hwa[:, None]
phase = ((xx + zz[:, None]) / 0.021) % 1.0
col = np.empty((TH, TW, 3), dtype=np.float32); col[:] = NAVY
col[(phase > 0.70) & (phase < 0.80)] = RED; col[(phase > 0.86) & (phase < 0.92)] = CREAM
img[:, :, :3] = col; img[:, :, 3] = 1
tex_dir = Path(out_path).parent.parent.parent / "output" / "textures"; tex_dir.mkdir(parents=True, exist_ok=True)
old = bpy.data.images.get("tie_stripes")
if old: bpy.data.images.remove(old)
im = bpy.data.images.new("tie_stripes", TW, TH); im.pixels.foreach_set(img.ravel()); im.filepath_raw = str(tex_dir / "tie_stripes.png"); im.file_format = "PNG"; im.save(); im.pack()
tm = principled("Tie_Silk", NAVY, 0.42, Sheen_Weight=0.2)
tx = tm.node_tree.nodes.new("ShaderNodeTexImage"); tx.image = im
tm.node_tree.links.new(tx.outputs["Color"], tm.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
tie.data.materials.append(tm)
m = tie.modifiers.new("Subdivision", "SUBSURF"); m.levels = 1; m.render_levels = 1

# ---------------------------------------------------------------- shirt collar: a clean modelled collar at the join
zw, x0w, x1w = white_rows[:, 0], white_rows[:, 1], white_rows[:, 2]
NA = 96; verts, faces = [], []
for kk in range(NA):
    phi = -math.pi + 2 * math.pi * kk / NA; a_deg = abs(math.degrees(phi))
    ztop = collar_top(phi) + 0.004
    hh = np.interp(a_deg, [0, 5, 7, 38, 60, 180], [0.0015, 0.0015, 0.022, 0.072, 0.018, 0.016])
    flare = np.interp(a_deg, [0, 7, 38, 60, 180], [0.001, 0.004, 0.016, 0.005, 0.004])
    sx, sy = math.sin(phi), -math.cos(phi)
    for j, (grow, z) in enumerate(((0.0, ztop - 0.085), (0.0008, ztop), (0.0015 + flare * 0.5, ztop - hh * 0.5), (0.0015 + flare, ztop - hh))):
        p = np.array([CXc + (RXc + grow) * sx, CYc + (RYc + grow) * sy, z])
        if j >= 2 and a_deg < 100:                                  # the collar leaf lies on the shirt, between the lapels
            q, _ = front_hit(body_tree, p[0], p[2])
            if q is not None and zw.min() < p[2] < zw.max() and np.interp(p[2], zw, x0w) + 0.003 < p[0] < np.interp(p[2], zw, x1w) - 0.003:
                p[1] = min(p[1], q[1] - 0.002)
        verts.append(p)
for kk in range(NA):
    k2 = (kk + 1) % NA
    for j in range(3): faces.append((kk * 4 + j, k2 * 4 + j, k2 * 4 + j + 1, kk * 4 + j + 1))
collar = new_object("Shirt_Collar", verts, faces)
collar.data.materials.append(bpy.data.materials["Shirt"])
m = collar.modifiers.new("Solidify", "SOLIDIFY"); m.thickness = 0.0018; m.offset = 1
m = collar.modifiers.new("Subdivision", "SUBSURF"); m.levels = 1; m.render_levels = 2

# ---------------------------------------------------------------- tie knot: a tapered knot between the collar leaves
kc = CXc; ky = CYc - RYc - 0.005
SEG, RINGS = 16, 7; kv, kf, kuv = [], [], []
for ri in range(RINGS):
    tq = ri / (RINGS - 1); z = kz0 + (kz1 - kz0) * tq
    hwk = (0.0150 + 0.0075 * tq) * (1 - 0.18 * (2 * tq - 1) ** 6); dk = 0.0085 + 0.0035 * math.sin(math.pi * min(tq * 1.1, 1))
    for sg in range(SEG):
        th = 2 * math.pi * sg / SEG; cth, sth = math.cos(th), math.sin(th)
        x = hwk * math.copysign(abs(cth) ** (2 / 2.8), cth); y = dk * math.copysign(abs(sth) ** (2 / 2.2), sth)
        kv.append((kc + x, ky - y * (1.0 if sth > 0 else 0.5), z)); kuv.append((0.5 + 0.5 * x / 0.0225, 0.90 + 0.08 * tq))
for ri in range(RINGS - 1):
    for sg in range(SEG): kf.append((ri * SEG + sg, ri * SEG + (sg + 1) % SEG, (ri + 1) * SEG + (sg + 1) % SEG, (ri + 1) * SEG + sg))
for r0 in (0, RINGS - 1):
    ci = len(kv); kv.append((kc, ky, kz0 if r0 == 0 else kz1)); kuv.append((0.5, 0.9))
    for sg in range(SEG): kf.append((ci, r0 * SEG + sg, r0 * SEG + (sg + 1) % SEG))
knot = new_object("Tie_Knot", kv, kf)
uvk = knot.data.uv_layers.new(name="UVMap")
for loop in knot.data.loops: uvk.data[loop.index].uv = kuv[loop.vertex_index]
knot.data.materials.append(tm)
m = knot.modifiers.new("Subdivision", "SUBSURF"); m.levels = 1; m.render_levels = 2

bpy.ops.wm.save_as_mainfile(filepath=out_path)
print("SAVED", out_path)
