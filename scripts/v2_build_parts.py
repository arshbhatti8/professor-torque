"""Stage 2 of the clean head: eyes, eyebrows, glasses, beard, moustache and skin material.

Usage: scripts/blender.sh <stage1.blend> --python scripts/v2_build_parts.py -- <out.blend>
"""
import bpy, bmesh, sys, math, os, numpy as np
from pathlib import Path
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_lib import *

out_path = str(Path(sys.argv[sys.argv.index("--") + 1]).resolve())
head = D["Head_Clean"]; eyeR, eyeL = D["Eye.R"], D["Eye.L"]
XC = (eyeR.location.x + eyeL.location.x) / 2          # centre plane of the face
EYE_Z = eyeR.location.z
tree = surface(head)
HP, HN, HF = eval_arrays(head)
print("face centre x", round(XC, 4), "eye z", round(EYE_Z, 4))

HAIR = srgb("#1C1513")

# ---------------------------------------------------------------- eyes
mat = principled("Eye", (1, 1, 1), 0.25, Coat_Weight=0.6, Coat_Roughness=0.05)
nt = mat.node_tree; b = nt.nodes["Principled BSDF"]
tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
comb = nt.nodes.new("ShaderNodeCombineXYZ"); nt.links.new(sep.outputs["X"], comb.inputs["X"]); nt.links.new(sep.outputs["Z"], comb.inputs["Y"])
ln = nt.nodes.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"; nt.links.new(comb.outputs[0], ln.inputs[0])
ramp = nt.nodes.new("ShaderNodeValToRGB"); cr = ramp.color_ramp
cr.elements[0].position = 0.0; cr.elements[0].color = (0.005, 0.005, 0.005, 1)
for pos, col in ((0.0085, (0.005, 0.005, 0.005, 1)), (0.0095, (*srgb("#4A2A14"), 1)), (0.0165, (*srgb("#3A200F"), 1)), (0.0178, (0.02, 0.012, 0.008, 1)), (0.0186, (0.93, 0.92, 0.90, 1))):
    e = cr.elements.new(pos); e.color = col
cr.elements[-1].position = 1.0; cr.elements[-1].color = (0.93, 0.92, 0.90, 1)
nt.links.new(ln.outputs["Value"], ramp.inputs[0])
# The back half of the eye is white.
front = nt.nodes.new("ShaderNodeMath"); front.operation = "LESS_THAN"; front.inputs[1].default_value = 0.0; nt.links.new(sep.outputs["Y"], front.inputs[0])
mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.inputs["A"].default_value = (0.93, 0.92, 0.90, 1)
nt.links.new(front.outputs[0], mix.inputs["Factor"]); nt.links.new(ramp.outputs["Color"], mix.inputs["B"]); nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
for e in (eyeR, eyeL):
    e.data.materials.clear(); e.data.materials.append(mat)

# ---------------------------------------------------------------- skin (simple colour for now; stage 3 bakes the texture)
skin = principled("Skin", srgb("#D79B74"), 0.48, Subsurface_Weight=0.2, Subsurface_Radius=(0.9, 0.4, 0.25), Subsurface_Scale=0.008)
head.data.materials.clear(); head.data.materials.append(skin)

# ---------------------------------------------------------------- eyebrows
def brow(side):
    # (distance from the centre plane, height) along the brow, from the inner end to the outer end
    pts = [(0.013, EYE_Z + 0.0235), (0.026, EYE_Z + 0.0295), (0.042, EYE_Z + 0.0325), (0.056, EYE_Z + 0.0300), (0.068, EYE_Z + 0.0235)]
    half_h = [0.0050, 0.0056, 0.0050, 0.0036, 0.0014]
    c = spline([(u, z, h) for (u, z), h in zip(pts, half_h)], 28)
    seg = 12; verts, faces = [], []
    for u, z, h in c:
        for k in range(seg):
            th = 2 * math.pi * k / seg
            x = XC + side * u; zz = z + h * math.cos(th)
            p, nrm = front_hit(tree, x, zz)
            if p is None: p, nrm = np.array([x, -0.1, zz]), np.array([0, -1, 0])
            verts.append(p + nrm * (0.0022 * math.sin(th) + 0.0004) * (h / 0.004) ** 0.5)
    n = len(c)
    for i in range(n - 1):
        for k in range(seg):
            k2 = (k + 1) % seg; faces.append((i * seg + k, i * seg + k2, (i + 1) * seg + k2, (i + 1) * seg + k))
    for i0 in (0, n - 1):
        cidx = len(verts); verts.append(np.mean(verts[i0 * seg:(i0 + 1) * seg], axis=0))
        for k in range(seg): faces.append((cidx, i0 * seg + k, i0 * seg + (k + 1) % seg))
    return verts, faces

v1, f1 = brow(-1); v2, f2 = brow(1)
brows = new_object("Eyebrows", v1 + v2, f1 + [tuple(i + len(v1) for i in f) for f in f2])
brows.data.materials.append(principled("Hair", HAIR, 0.55))
m = brows.modifiers.new("Subdivision", "SUBSURF"); m.levels = 1; m.render_levels = 2

# ---------------------------------------------------------------- glasses
LENS_DX = 0.0452                 # lens centre: distance from the centre plane
LENS_Z = EYE_Z - 0.0075          # lens centre height
A, B = 0.0295, 0.0205            # half width and half height of the lens opening
eye_front = eyeR.location.y - 0.0388 * eyeR.scale.y
bridge_p, _ = front_hit(tree, XC, LENS_Z + 0.008)
Y0 = min(eye_front - 0.011, bridge_p[1] - 0.0015)          # front plane position of the frame at the centre
WRAP = 1.6                                                  # how much the frame curves around the face
DEPTH = 0.0045
print("glasses plane y", round(Y0, 4), "eye front", round(eye_front, 4), "bridge", np.round(bridge_p, 4))


def lens_outline(grow_side, grow_top, grow_bot, count=64):
    """Outline of a lens opening (grown by the given rim widths), in lens coordinates (to the outside, up)."""
    pts = []
    for k in range(count):
        th = 2 * math.pi * k / count; c, s = math.cos(th), math.sin(th)
        nexp = 3.6 if s > 0 else 3.0                                    # square top, round bottom
        x = (A + grow_side) * math.copysign(abs(c) ** (2 / nexp), c)
        z = (B + (grow_top if s > 0 else grow_bot)) * math.copysign(abs(s) ** (2 / nexp), s)
        x *= 1 + 0.07 * (z / B)                                         # wider at the top
        x += 0.0012 * (z / B)                                           # the top leans to the outside
        pts.append((x, z))
    return pts


def place(side, lx, lz, depth):
    x = XC + side * (LENS_DX + lx); z = LENS_Z + lz
    y = Y0 + WRAP * (x - XC) ** 2 + depth
    return (x, y, z)


verts, faces = [], []
lens_v, lens_f = [], []
for side in (-1, 1):
    inner = lens_outline(0, 0, 0); outer = lens_outline(0.0052, 0.0066, 0.0046)
    n = len(inner); base = len(verts)
    for ring, d in ((outer, 0.0), (inner, 0.0), (inner, DEPTH), (outer, DEPTH)):
        verts += [place(side, x, z, d) for x, z in ring]
    for r in range(4):
        r2 = (r + 1) % 4
        for k in range(n):
            k2 = (k + 1) % n
            faces.append((base + r * n + k, base + r * n + k2, base + r2 * n + k2, base + r2 * n + k))
    lb = len(lens_v); lens_v += [place(side, x * 1.01, z * 1.01, DEPTH * 0.45) for x, z in inner] + [place(side, 0, 0, DEPTH * 0.45 - 0.0012)]
    lens_f += [(lb + n, lb + k, lb + (k + 1) % n) for k in range(n)]

# Bridge between the two rims.
bz0, bz1 = 0.0035, 0.0125; bx = LENS_DX - A - 0.0040
path = [(XC + t * bx, Y0 + WRAP * (t * bx) ** 2 + DEPTH / 2 - 0.0012 * (1 - t * t), LENS_Z + (bz0 + bz1) / 2 + 0.0015 * (1 - t * t)) for t in np.linspace(-1, 1, 9)]
tv, tf = tube(path, [(bz1 - bz0) / 2 * (1 + 0.25 * abs(t)) for t in np.linspace(-1, 1, 9)], [DEPTH / 2 * 0.9] * 9, up=(0, -1, 0), seg=10)
faces += [tuple(i + len(verts) for i in f) for f in tf]; verts += [tuple(v) for v in tv]
# Temples: from the outer top corners back to the ears.
ear_y = 0.0
for side in (-1, 1):
    start = np.array(place(side, A + 0.0030, B * 0.55, DEPTH / 2))
    endx = XC + side * 0.079
    path = spline([start, start + np.array([side * 0.004, 0.012, 0.0]), (endx, start[1] + 0.05, start[2] + 0.001), (endx, start[1] + 0.10, start[2] - 0.004)], 14)
    tv, tf = tube(path, [0.0034 - 0.0012 * i / 13 for i in range(14)], [0.0016] * 14, up=(1, 0, 0), seg=8)
    tv = np.array(tv); a = np.cross(np.array([0, 1, 0]), np.array([1, 0, 0]))
    faces += [tuple(i + len(verts) for i in f) for f in tf]; verts += [tuple(v) for v in tv]
glasses = new_object("Glasses", verts, faces)
glasses.data.materials.append(principled("Glasses_Frame", (0.012, 0.012, 0.014), 0.28, Coat_Weight=0.5, Coat_Roughness=0.1))
mb = glasses.modifiers.new("Bevel", "BEVEL"); mb.width = 0.0009; mb.segments = 3; mb.limit_method = "ANGLE"; mb.angle_limit = math.radians(50)
glasses.data.polygons.foreach_set("use_smooth", np.ones(len(glasses.data.polygons), dtype=bool))
lenses = new_object("Lenses", lens_v, lens_f)
lm = principled("Glasses_Lens", (0.012, 0.013, 0.016), 0.06, Alpha=0.88, Coat_Weight=0.3, Coat_Roughness=0.03)
lm.blend_method = "BLEND"; lenses.data.materials.append(lm)

# ---------------------------------------------------------------- beard
MOUTH_Z = EYE_Z - 0.078


def beard_field(P):
    """Positive inside the beard area, in metres from the beard edge (approximate)."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]; u = np.abs(x - XC); dz = z - EYE_Z
    line = np.interp(u, [0, 0.030, 0.045, 0.060, 0.072, 0.080, 0.090], [-0.078, -0.078, -0.074, -0.060, -0.040, -0.016, 0.02])
    fA = line - dz                                                           # below the cheek line
    clear = 1 - ((u / 0.030) ** 2 + ((dz + 0.091) / 0.0165) ** 2)            # skin around the lower lip
    fsoul = np.minimum(0.004 + 0.35 * np.clip(-0.094 - dz, 0, 0.02) - u, -0.0935 - dz)                             # soul patch under the lip
    fM = np.minimum(np.minimum(0.030 - u, dz + 0.072), -0.058 - dz)          # upper lip, under the moustache
    core = np.maximum(np.maximum(np.minimum(fA, -clear * 0.01), fsoul), fM)
    fY = -0.022 - y                                                          # stop in front of the ear
    fN = dz - (-0.125 + (y + 0.115) * 0.45 - 0.006)                          # stop under the jaw
    return np.minimum(np.minimum(core, fY), fN)


f = beard_field(HP)
faces = [fc for fc in HF if max(f[i] for i in fc) > 0]
used = sorted({i for fc in faces for i in fc}); remap = {v: k for k, v in enumerate(used)}
nbr = {}
for fc in faces:
    for a, b2 in zip(fc, fc[1:] + fc[:1]):
        nbr.setdefault(a, set()).add(b2); nbr.setdefault(b2, set()).add(a)
BP = HP.copy()
for v in used:                                     # move the outside vertices to the beard edge: this gives a clean edge
    if f[v] <= 0:
        ins = [w for w in nbr[v] if f[w] > 0]
        if ins:
            w = max(ins, key=lambda k: f[k]); t = (0 - f[v]) / (f[w] - f[v])
            BP[v] = HP[v] + (HP[w] - HP[v]) * t
edge = [v for v in used if f[v] <= 0]; eset = set(edge)
for _ in range(8):                                 # make the edge line smooth
    newp = {}
    for v in edge:
        nb = [w for w in nbr[v] if w in eset]
        if len(nb) >= 2: newp[v] = 0.5 * BP[v] + 0.5 * np.mean([BP[w] for w in nb], axis=0)
    for v, q in newp.items(): BP[v] = q
fb = np.maximum(beard_field(BP), 0); fb[edge] = 0
u = np.abs(BP[:, 0] - XC); dz = BP[:, 2] - EYE_Z
taper = smoothstep(0, 0.006, fb)
thick = (0.0035 + 0.0050 * smoothstep(-0.045, -0.105, dz)) * taper
chin = np.clip(1 - (u / 0.068) ** 2, 0, 1) * smoothstep(-0.078, -0.112, dz) * taper
BP = BP + HN * thick[:, None] + chin[:, None] * np.array([0, -0.004, -0.020])
beard = new_object("Beard", [BP[v] for v in used], [tuple(remap[i] for i in fc) for fc in faces])
hair = bpy.data.materials["Hair"]
nt = hair.node_tree; bs = nt.nodes["Principled BSDF"]                      # fine hair texture as a bump
tcn = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (420, 420, 70)
nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.0; nz.inputs["Detail"].default_value = 3
bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 1.0; bp.inputs["Distance"].default_value = 0.0012
nt.links.new(tcn.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
nt.links.new(nz.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], bs.inputs["Normal"])
bs.inputs["Sheen Weight"].default_value = 0.3
beard.data.materials.append(hair)
ms = beard.modifiers.new("Smooth", "CORRECTIVE_SMOOTH"); ms.iterations = 4; ms.factor = 0.5
msub = beard.modifiers.new("Subdivision", "SUBSURF"); msub.levels = 1; msub.render_levels = 1
print("beard faces", len(faces))

# ---------------------------------------------------------------- moustache
def moustache(side):
    pts = [(0.000, -0.0600), (0.010, -0.0615), (0.022, -0.0650), (0.034, -0.0680), (0.045, -0.0680), (0.055, -0.0630), (0.061, -0.0550), (0.059, -0.0470), (0.052, -0.0440)]
    ra = [0.0046, 0.0050, 0.0049, 0.0046, 0.0042, 0.0037, 0.0031, 0.0023, 0.0010]
    c = spline([(u, z, r) for (u, z), r in zip(pts, ra)], 40)
    path, rr = [], []
    for u, dzz, r in c:
        x = XC + side * u; z = EYE_Z + dzz
        p, nrm = front_hit(tree, x, z)
        if p is None: p, nrm = path[-1].copy(), np.array([side * 0.5, -0.85, 0])
        path.append(p + nrm * r * 0.45); rr.append(max(r, 0.0004))
    return tube(path, rr, [r * 0.62 for r in rr], up=(0, -1, 0), seg=14)

v1, f1 = moustache(-1); v2, f2 = moustache(1)
mo = new_object("Moustache", list(v1) + list(v2), f1 + [tuple(i + len(v1) for i in fc) for fc in f2])
mo.data.materials.append(hair)
m = mo.modifiers.new("Subdivision", "SUBSURF"); m.levels = 1; m.render_levels = 2

# ---------------------------------------------------------------- chest: one clean jacket and shirt surface
jacket, shirt, tie_ai = D["Jacket"], D["Shirt"], D["Tie"]
OLIVE = None


def set_attr(o, name, value):
    a = o.data.attributes.get(name) or o.data.attributes.new(name, "FLOAT", "POINT")
    a.data.foreach_set("value", np.full(len(o.data.vertices), value, dtype=np.float32))


# Split the cuffs from the chest part of the shirt.
me = shirt.data; co_s = np.empty(len(me.vertices) * 3, dtype=np.float32); me.vertices.foreach_get("co", co_s); co_s = co_s.reshape(-1, 3)
cuff_v = (np.abs(co_s[:, 0]) > 0.2) | (co_s[:, 2] < 1.15)
cuffs = shirt.copy(); cuffs.data = shirt.data.copy(); cuffs.name = "Shirt_Cuffs"; collection().objects.link(cuffs)
for o, drop in ((cuffs, ~cuff_v), (shirt, cuff_v)):
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[v for v, k in zip(bm.verts, drop) if k], context="VERTS"); bm.to_mesh(o.data); bm.free()
ja = np.empty(len(jacket.data.vertices) * 4, dtype=np.float32); jacket.data.color_attributes["albedo"].data.foreach_get("color", ja)
OLIVE = np.median(ja.reshape(-1, 4), axis=0)
# Jacket faces at the old label edge can have one white shirt vertex. Give these vertices the jacket colour.
jme = jacket.data; part = np.empty(len(jme.vertices), dtype=np.int32); jme.attributes["part"].data.foreach_get("value", part)
jco = np.empty(len(jme.vertices) * 3, dtype=np.float32); jme.vertices.foreach_get("co", jco); jco = jco.reshape(-1, 3)
fixv = np.isin(part, (10, 11)) & (np.abs(jco[:, 0]) < 0.2) & (jco[:, 2] > 1.15)
ja2 = ja.reshape(-1, 4).copy(); ja2[fixv] = OLIVE
jme.color_attributes["albedo"].data.foreach_set("color", ja2.ravel())
print("jacket vertices with a shirt colour corrected:", int(fixv.sum()))
set_attr(jacket, "shirt", 0.0)
for o in (shirt, tie_ai):
    set_attr(o, "shirt", 1.0)
    o.data.color_attributes["albedo"].data.foreach_set("color", np.tile(OLIVE, len(o.data.vertices)).astype(np.float32))
bpy.ops.object.select_all(action="DESELECT")
for o in (jacket, shirt, tie_ai): o.select_set(True)
print('before join', len(jacket.data.vertices), len(shirt.data.vertices), len(tie_ai.data.vertices))
bpy.context.view_layer.objects.active = jacket; print('join', bpy.ops.object.join())
bm = bmesh.new(); bm.from_mesh(jacket.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5); bm.to_mesh(jacket.data); bm.free()
me = jacket.data; n = len(me.vertices)
co_j = np.empty(n * 3, dtype=np.float32); me.vertices.foreach_get("co", co_j); co_j = co_j.reshape(-1, 3).astype(np.float64)
# The shirt area is a clean V shape between the lapels (measured from the AI labels), not the rough AI label edge.
zj = co_j[:, 2]
wv = np.interp(zj, [1.245, 1.27, 1.30, 1.44, 1.47, 1.52, 1.56, 1.60], [0.0, 0.022, 0.038, 0.073, 0.070, 0.050, 0.040, 0.040])
fV = np.where((zj > 1.245) & (co_j[:, 1] < 0.0), wv - np.abs(co_j[:, 0] + 0.005), -1.0)
nrm_j = np.empty(n * 3, dtype=np.float32); me.vertices.foreach_get("normal", nrm_j); nrm_j = nrm_j.reshape(-1, 3)
mask = np.clip(0.5 + fV / 0.008, 0, 1)
me.attributes["shirt"].data.foreach_set("value", mask.astype(np.float32))
jm = jacket.material_slots[0].material; nt = jm.node_tree; bs = nt.nodes["Principled BSDF"]
att = nt.nodes.new("ShaderNodeAttribute"); att.attribute_name = "shirt"
rp = nt.nodes.new("ShaderNodeValToRGB"); rp.color_ramp.elements[0].position = 0.47; rp.color_ramp.elements[1].position = 0.53
mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs["B"].default_value = (*srgb("#F1EFEA"), 1)
old = bs.inputs["Base Color"].links[0].from_socket
nt.links.new(att.outputs["Fac"], rp.inputs[0]); nt.links.new(rp.outputs["Color"], mx.inputs["Factor"])
nt.links.new(old, mx.inputs["A"]); nt.links.new(mx.outputs["Result"], bs.inputs["Base Color"])
while len(jacket.data.materials) > 1: jacket.data.materials.pop()
me.polygons.foreach_set("material_index", np.zeros(len(me.polygons), dtype=np.int32))
# Remove the rough cut top of the body inside the shirt collar. The collar closes this area.
neck = HP[np.abs(HP[:, 2] - 1.565) < 0.006]
CX, CY = (neck[:, 0].min() + neck[:, 0].max()) / 2, (neck[:, 1].min() + neck[:, 1].max()) / 2
RX, RY = (neck[:, 0].max() - neck[:, 0].min()) / 2 + 0.0035, (neck[:, 1].max() - neck[:, 1].min()) / 2 + 0.0035
rr2 = ((co_j[:, 0] - CX) / (RX * 1.02)) ** 2 + ((co_j[:, 1] - CY) / (RY * 1.02)) ** 2
drop = ((rr2 < 1) & (zj > 1.548)) | ((zj > 1.562) & (rr2 < 2.2))
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[v for v, k in zip(bm.verts, drop) if k], context="VERTS"); bm.to_mesh(me); bm.free()
print("body top vertices removed", int(drop.sum()))
body_tree = surface(jacket)

# ---------------------------------------------------------------- shirt collar
print("neck centre", round(CX, 4), round(CY, 4), "collar radii", round(RX, 4), round(RY, 4))
NA = 96; verts, faces = [], []
for k in range(NA):
    phi = 2 * math.pi * k / NA; a = abs(math.degrees(math.atan2(math.sin(phi), math.cos(phi))))
    ztop = 1.580 + 0.010 * (1 - math.cos(phi)) / 2
    h = np.interp(a, [0, 5, 7, 38, 60, 180], [0.0015, 0.0015, 0.022, 0.082, 0.018, 0.016])
    flare = np.interp(a, [0, 7, 38, 60, 180], [0.001, 0.004, 0.016, 0.004, 0.003])
    sx, sy = math.sin(phi), -math.cos(phi)
    ring = [(RX, RY, 1.52), (RX + 0.0008, RY + 0.0008, ztop), (RX + 0.0015 + flare * 0.5, RY + 0.0015 + flare * 0.5, ztop - h * 0.5), (RX + 0.0015 + flare, RY + 0.0015 + flare, ztop - h)]
    for j, (rx, ry, z) in enumerate(ring):
        p = np.array([CX + rx * sx, CY + ry * sy, z])
        if j >= 2 and a < 100:                                   # the collar leaf lies on the chest
            q, _ = front_hit(body_tree, p[0], p[2])
            if q is not None:
                wz = np.interp(p[2], [1.245, 1.27, 1.30, 1.44, 1.47, 1.52, 1.56, 1.60], [0.0, 0.022, 0.038, 0.073, 0.070, 0.050, 0.040, 0.040])
                if abs(p[0] + 0.005) < wz - 0.003: p[1] = min(p[1], q[1] - 0.002)       # on the shirt: lie on the chest

        verts.append(p)
for k in range(NA):
    k2 = (k + 1) % NA
    for j in range(3): faces.append((k * 4 + j, k2 * 4 + j, k2 * 4 + j + 1, k * 4 + j + 1))
collar = new_object("Shirt_Collar", verts, faces)
collar.data.materials.append(principled("Shirt", srgb("#F1EFEA"), 0.7, Sheen_Weight=0.1))
m = collar.modifiers.new("Solidify", "SOLIDIFY"); m.thickness = 0.0018; m.offset = 1
m = collar.modifiers.new("Subdivision", "SUBSURF"); m.levels = 1; m.render_levels = 2

# ---------------------------------------------------------------- tie
NAVY, RED, CREAM = srgb("#1B2748"), srgb("#B9523C"), srgb("#E2DBCB")
Z_TOP, Z_BOT, ROWS, COLS = 1.534, 1.238, 60, 9
def tie_centre(z): return np.interp(z, [1.25, 1.53], [-0.003, CX])
def tie_half(z): return min(np.interp(z, [1.27, 1.52], [0.0275, 0.0135]), max(0.41 * (z - 1.243) - 0.002, 0.0005))
verts, faces, uvs = [], [], []
for r in range(ROWS):
    z = Z_TOP + (Z_BOT - Z_TOP) * r / (ROWS - 1); hw = tie_half(z); cxz = tie_centre(z)
    for c in range(COLS):
        t = -1 + 2 * c / (COLS - 1)
        x = cxz + t * hw; q, _ = front_hit(body_tree, x, z)
        ys = q[1] if q is not None else -0.05
        lift = 0.0002 if abs(t) == 1 else 0.0030 + 0.0020 * (1 - t * t)
        verts.append((x, ys - lift, z)); uvs.append(((t + 1) / 2, 1 - r / (ROWS - 1)))
for r in range(ROWS - 1):
    for c in range(COLS - 1): faces.append((r * COLS + c, r * COLS + c + 1, (r + 1) * COLS + c + 1, (r + 1) * COLS + c))
tie = new_object("Tie", verts, faces)
uvl = tie.data.uv_layers.new(name="UVMap")
for loop in tie.data.loops: uvl.data[loop.index].uv = uvs[loop.vertex_index]
# Stripe texture: thin red and cream lines at 45 degrees.
TW, TH = 512, 2048; img = np.zeros((TH, TW, 4), dtype=np.float32)
vv = (np.arange(TH) + 0.5) / TH; uu = (np.arange(TW) + 0.5) / TW
zz = Z_BOT + (Z_TOP - Z_BOT) * vv
hw = np.array([tie_half(z) for z in zz]); xx = (2 * uu[None, :] - 1) * hw[:, None]
phase = ((xx + zz[:, None]) / 0.021) % 1.0
col = np.empty((TH, TW, 3), dtype=np.float32); col[:] = NAVY
col[(phase > 0.70) & (phase < 0.80)] = RED; col[(phase > 0.86) & (phase < 0.92)] = CREAM
img[:, :, :3] = col; img[:, :, 3] = 1
tex_dir = Path(out_path).parent.parent.parent / "output" / "textures"; tex_dir.mkdir(parents=True, exist_ok=True)
im = bpy.data.images.new("tie_stripes", TW, TH); im.pixels.foreach_set(img.ravel()); im.filepath_raw = str(tex_dir / "tie_stripes.png"); im.file_format = "PNG"; im.save()
tm = principled("Tie_Silk", NAVY, 0.42, Sheen_Weight=0.2)
tx = tm.node_tree.nodes.new("ShaderNodeTexImage"); tx.image = im
tm.node_tree.links.new(tx.outputs["Color"], tm.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
tie.data.materials.append(tm)
m = tie.modifiers.new("Subdivision", "SUBSURF"); m.levels = 1; m.render_levels = 1
# Knot.
ky = CY - RY - 0.010; kz1, kz0 = 1.572, 1.530
kv = []
for z, hwk, dk in ((kz1, 0.0185, 0.011), (kz0, 0.0125, 0.010)):
    for sx_, sy_ in ((-1, -1), (1, -1), (1, 1), (-1, 1)): kv.append((CX + sx_ * hwk, ky + sy_ * dk, z))
knot = new_object("Tie_Knot", kv, [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)])
knot.data.materials.append(principled("Tie_Knot", NAVY, 0.42, Sheen_Weight=0.2))
m = knot.modifiers.new("Subdivision", "SUBSURF"); m.levels = 2; m.render_levels = 3

# ---------------------------------------------------------------- skin texture (4096 px, baked to the UV map of the head)
midv = HP[(np.abs(HP[:, 0] - XC) < 0.004) & (HN[:, 1] < -0.3) & (HP[:, 2] > EYE_Z - 0.081) & (HP[:, 2] < EYE_Z - 0.063)]
slit = midv[midv[:, 1].argmax()]; MZ = float(slit[2])
print("mouth line z", round(MZ, 4), "(estimate was", round(MOUTH_Z, 4), ")")
SKIN, LIP, BLUSH = srgb("#D79B74"), srgb("#B36C5A"), srgb("#D4866A")
nt = skin.node_tree; bs = nt.nodes["Principled BSDF"]
geo = nt.nodes.new("ShaderNodeNewGeometry"); sp = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(geo.outputs["Position"], sp.inputs[0])


def math(op, a, b=None, c=None):
    nd = nt.nodes.new("ShaderNodeMath"); nd.operation = op
    for i, v in enumerate((a, b, c)):
        if v is None: continue
        if isinstance(v, (int, float)): nd.inputs[i].default_value = v
        else: nt.links.new(v, nd.inputs[i])
    return nd.outputs[0]


def blob(cx, cz, rx, rz_up, rz_down, soft):
    """1 inside an ellipse around (cx, cz) in the front view, with a soft edge."""
    dx = math("DIVIDE", math("SUBTRACT", sp.outputs["X"], cx), rx)
    dzr = math("SUBTRACT", sp.outputs["Z"], cz)
    dzn = math("MAXIMUM", math("DIVIDE", dzr, rz_up), math("DIVIDE", dzr, -rz_down))
    d2 = math("ADD", math("MULTIPLY", dx, dx), math("MULTIPLY", dzn, dzn))
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.interpolation_type = "SMOOTHSTEP"; nt.links.new(d2, mr.inputs["Value"])
    mr.inputs["From Min"].default_value = 1.0 - soft; mr.inputs["From Max"].default_value = 1.0; mr.inputs["To Min"].default_value = 1.0; mr.inputs["To Max"].default_value = 0.0
    return mr.outputs["Result"]


def mixc(fac, a, b):
    nd = nt.nodes.new("ShaderNodeMix"); nd.data_type = "RGBA"
    nt.links.new(fac, nd.inputs["Factor"])
    for key, v in (("A", a), ("B", b)):
        if isinstance(v, tuple): nd.inputs[key].default_value = (*v, 1)
        else: nt.links.new(v, nd.inputs[key])
    return nd.outputs["Result"]


front_only = math("LESS_THAN", sp.outputs["Y"], -0.06)
lip = math("MULTIPLY", math("MULTIPLY", blob(XC, MZ - 0.0005, 0.0235, 0.0058, 0.0105, 0.35), 0.8), front_only)
cheek = math("MULTIPLY", math("MULTIPLY", math("ADD", blob(XC - 0.047, EYE_Z - 0.040, 0.026, 0.02, 0.02, 0.95), blob(XC + 0.047, EYE_Z - 0.040, 0.026, 0.02, 0.02, 0.95)), 0.35), front_only)
nose = math("MULTIPLY", math("MULTIPLY", blob(XC, EYE_Z - 0.034, 0.014, 0.012, 0.012, 0.95), 0.25), front_only)
col = mixc(lip, mixc(nose, mixc(cheek, SKIN, BLUSH), BLUSH), LIP)
tex_dir.mkdir(parents=True, exist_ok=True)
timg = bpy.data.images.new("head_skin_4k", 4096, 4096); timg.generated_color = (*SKIN, 1)
em = nt.nodes.new("ShaderNodeEmission"); nt.links.new(col, em.inputs["Color"])
outn = nt.nodes["Material Output"]; nt.links.new(em.outputs[0], outn.inputs["Surface"])
tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = timg; nt.nodes.active = tx
sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = 4; sc.cycles.device = "CPU"
bpy.ops.object.select_all(action="DESELECT"); head.select_set(True); bpy.context.view_layer.objects.active = head
sc.render.bake.margin = 24
print("bake", bpy.ops.object.bake(type="EMIT"))
timg.filepath_raw = str(tex_dir / "head_skin_4k.png"); timg.file_format = "PNG"; timg.save()
nt.links.new(bs.outputs[0], outn.inputs["Surface"]); nt.links.new(tx.outputs["Color"], bs.inputs["Base Color"])
for nd in [nd for nd in nt.nodes if nd.type in ("MATH", "MIX", "EMISSION", "NEW_GEOMETRY", "SEPXYZ", "MAP_RANGE")]: nt.nodes.remove(nd)

# ---------------------------------------------------------------- turban: clean the rough open edge
tb = D["Turban"]; bm = bmesh.new(); bm.from_mesh(tb.data)
# Remove small loose pieces.
seen = set(); islands = []
for v in bm.verts:
    if v in seen: continue
    stack, isl = [v], []
    seen.add(v)
    while stack:
        a_ = stack.pop(); isl.append(a_)
        for e in a_.link_edges:
            o_ = e.other_vert(a_)
            if o_ not in seen: seen.add(o_); stack.append(o_)
    islands.append(isl)
big = max(len(i) for i in islands)
small = [v for isl in islands if len(isl) < 0.02 * big for v in isl]
bmesh.ops.delete(bm, geom=small, context="VERTS")
for _ in range(3):                                   # remove thin spikes: boundary faces with two boundary edges
    spikes = [f_ for f_ in bm.faces if sum(1 for e in f_.edges if e.is_boundary) >= 2]
    if not spikes: break
    bmesh.ops.delete(bm, geom=spikes, context="FACES")
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
for _ in range(12):                                  # make the boundary line smooth
    newco = {}
    for v in bm.verts:
        if not v.is_boundary: continue
        nb = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
        if len(nb) == 2: newco[v] = v.co * 0.5 + (nb[0].co + nb[1].co) * 0.25
    for v, c_ in newco.items(): v.co = c_
print("turban: removed", len(small), "loose vertices")
bm.to_mesh(tb.data); bm.free()

# ---------------------------------------------------------------- eye texture (baked, so that the GLB file keeps the iris)
emat = bpy.data.materials["Eye"]; nt = emat.node_tree; bs = nt.nodes["Principled BSDF"]
src_col = bs.inputs["Base Color"].links[0].from_socket
eimg = bpy.data.images.new("eye_1k", 1024, 1024)
em = nt.nodes.new("ShaderNodeEmission"); nt.links.new(src_col, em.inputs["Color"])
outn = nt.nodes["Material Output"]; nt.links.new(em.outputs[0], outn.inputs["Surface"])
tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = eimg; nt.nodes.active = tx
bpy.ops.object.select_all(action="DESELECT"); eyeR.select_set(True); bpy.context.view_layer.objects.active = eyeR
print("eye bake", bpy.ops.object.bake(type="EMIT"))
eimg.filepath_raw = str(tex_dir / "eye_1k.png"); eimg.file_format = "PNG"; eimg.save()
nt.links.new(bs.outputs[0], outn.inputs["Surface"]); nt.links.new(tx.outputs["Color"], bs.inputs["Base Color"])
for nd in [nd for nd in nt.nodes if nd.type in ("MATH", "MIX", "EMISSION", "TEX_COORD", "SEPXYZ", "COMBXYZ", "VECT_MATH", "VALTORGB")]: nt.nodes.remove(nd)

# The old AI head parts are not necessary in the final file.
ref = bpy.data.collections.get("AI_Reference")
if ref:
    for o in list(ref.objects): bpy.data.objects.remove(o)
    bpy.data.collections.remove(ref)
bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
for im_ in (timg, eimg, im): im_.pack()

bpy.ops.wm.save_as_mainfile(filepath=out_path)
print("SAVED", out_path)
