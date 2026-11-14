"""Version 5 face: real eye geometry behind the glasses, and a mouth that can open.

Eyes:  the painted lens areas are cut out of the AI head. Each side gets a clear tinted lens, an eye socket with
       eyelids, and an eyeball with iris and pupil.
Mouth: the lip line is cut open. The head gets a 'jaw' weight attribute, lips with thickness, a mouth cavity,
       teeth and a tongue.

Usage: scripts/blender.sh <parts.blend> --python scripts/v5_face.py -- <out.blend>
"""
import bpy, bmesh, sys, os, math, numpy as np
from pathlib import Path
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_lib import *

out_path = str(Path(sys.argv[sys.argv.index("--") + 1]).resolve())
head = D["Head"]


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


P, N, C = arrays(head)
# Front map of the face: colour and depth on a 1 mm grid.
X0, X1, Z0, Z1, CELL = -0.13, 0.11, 1.55, 1.80, 0.001
W, H = int((X1 - X0) / CELL), int((Z1 - Z0) / CELL)
fr = (N[:, 1] < -0.2) & (P[:, 0] > X0) & (P[:, 0] < X1) & (P[:, 2] > Z0) & (P[:, 2] < Z1)
ix = ((P[fr, 0] - X0) / CELL).astype(int); iz = ((P[fr, 2] - Z0) / CELL).astype(int); order = np.argsort(-P[fr, 1])
col = np.full((H, W, 3), np.nan); dep = np.full((H, W), np.nan)
col[iz[order], ix[order]] = C[fr][order]; dep[iz[order], ix[order]] = P[fr, 1][order]


def sample(x, z, r=3):
    i, k = int((x - X0) / CELL), int((z - Z0) / CELL)
    d = dep[k - r:k + r + 1, i - r:i + r + 1]; c = col[k - r:k + r + 1, i - r:i + r + 1]; m = ~np.isnan(d)
    return (float(np.median(d[m])), np.median(c[m], axis=0)) if m.any() else (None, None)


def skin_at(x, z):
    d, c = sample(x, z, 2)
    return c is not None and c[0] > 0.6 and c.mean() > 0.5


# ---------------------------------------------------------------- face landmarks
XC = -0.0095                                       # centre plane of the face
LENS_Z = 1.687
lenses = {}
for side, x_guess in ((-1, -0.0505), (1, 0.0305)):
    def edge(dx, dz, start=0.012, limit=0.05):
        s_ = start
        while s_ < limit and not (skin_at(x_guess + dx * s_, LENS_Z + dz * s_) and skin_at(x_guess + dx * (s_ + 0.002), LENS_Z + dz * (s_ + 0.002))): s_ += 0.001
        return s_
    xl, xr, zb = x_guess - edge(-1, 0), x_guess + edge(1, 0), LENS_Z - edge(0, -1)
    FRAME = 0.0045                                 # width of the painted frame
    a = (xr - xl) / 2 - FRAME; cx = (xl + xr) / 2; b = a * 0.70; cz = zb + FRAME + b
    yl, _ = sample(cx, cz, 4)
    lenses[side] = dict(cx=cx, cz=cz, a=a, b=b, y=yl)
    print(f"lens {'L' if side == 1 else 'R'}: dark area x {xl:.4f}..{xr:.4f} bottom {zb:.4f} -> opening centre ({cx:.4f}, {cz:.4f}) half size {a:.4f} x {b:.4f} depth {yl:.4f}")
_, SKIN = sample(XC - 0.06, 1.645, 3)
SKIN_LIN = tuple(float(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in SKIN)
print("skin colour", np.round(SKIN * 255))


def outline(a, b, th, grow=1.0):
    """Lens opening: a rounded rectangle, a little wider at the top."""
    c, s_ = math.cos(th), math.sin(th); nexp = 3.2 if s_ > 0 else 2.8
    x = a * math.copysign(abs(c) ** (2 / nexp), c); z = b * math.copysign(abs(s_) ** (2 / nexp), s_)
    return grow * x * (1 + 0.05 * z / b), grow * z


def inside_outline(a, b, x, z, grow=1.0):
    nexp = np.where(z > 0, 3.2, 2.8); xx = x / (1 + 0.05 * z / b)
    return (np.abs(xx) / (a * grow)) ** nexp + (np.abs(z) / (b * grow)) ** nexp < 1


# ---------------------------------------------------------------- cut the lens areas out of the head
bm = bmesh.new(); bm.from_mesh(head.data); bm.faces.ensure_lookup_table()
kill = []
for f_ in bm.faces:
    c = f_.calc_center_median()
    for L in lenses.values():
        lx, lz = np.float64(c.x - L["cx"]), np.float64(c.z - L["cz"])
        if not inside_outline(L["a"], L["b"], lx, lz, 0.97): continue
        # Remove the lens front, its back, and hidden inner surfaces. Go less deep near the rim, so that the side of the face stays.
        rim = max(abs(lx) / L["a"], abs(lz) / L["b"])
        if -0.012 < c.y - L["y"] < 0.0025 + 0.034 * max(0.0, 1 - rim) ** 0.7: kill.append(f_); break
bmesh.ops.delete(bm, geom=kill, context="FACES")
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
bm.to_mesh(head.data); bm.free()
print("lens faces removed from the head", len(kill))

# ---------------------------------------------------------------- materials
lens_mat = principled("Glasses_Lens", (0.020, 0.016, 0.014), 0.05, Alpha=0.80, Coat_Weight=0.4, Coat_Roughness=0.03); lens_mat.blend_method = "BLEND"
skin_mat = principled("Eye_Socket_Skin", tuple(x * 0.92 for x in SKIN_LIN), 0.55, Subsurface_Weight=0.15, Subsurface_Radius=(0.9, 0.4, 0.25), Subsurface_Scale=0.006)
lid_mat = principled("Eyelid_Inner", tuple(x * 0.45 for x in SKIN_LIN), 0.6)
lash_mat = principled("Eyelash", srgb("#1A1210"), 0.5)
# Eye texture: pupil, iris and white, by the angle from the front of the eye.
TW, TH = 256, 512; ang = (np.arange(TH) + 0.5) / TH * math.pi
rowc = np.empty((TH, 3), dtype=np.float32)
PUPIL, IRIS, LIMB = 0.22, 0.50, 0.545
for i, al in enumerate(ang):
    if al < PUPIL: c = (0.004, 0.004, 0.004)
    elif al < IRIS:
        t = (al - PUPIL) / (IRIS - PUPIL); a0, a1 = np.array(srgb("#7A4A22")), np.array(srgb("#3F240F")); c = tuple(a0 * (1 - t) + a1 * t)
    elif al < LIMB: c = (0.012, 0.008, 0.006)
    else: c = (0.90, 0.89, 0.87)
    rowc[i] = c
eimg_px = np.ones((TH, TW, 4), dtype=np.float32); eimg_px[:, :, :3] = rowc[:, None, :]
tex_dir = Path(out_path).parent.parent.parent / "output" / "textures"; tex_dir.mkdir(parents=True, exist_ok=True)
eimg = bpy.data.images.new("eye_iris", TW, TH); eimg.pixels.foreach_set(eimg_px.ravel())
eimg.filepath_raw = str(tex_dir / "eye_iris.png"); eimg.file_format = "PNG"; eimg.save(); eimg.pack()      # save first: an image that is not saved is lost
eye_mat = principled("Eye", (1, 1, 1), 0.2, Coat_Weight=0.7, Coat_Roughness=0.04)
etx = eye_mat.node_tree.nodes.new("ShaderNodeTexImage"); etx.image = eimg; etx.extension = "EXTEND"
eye_mat.node_tree.links.new(etx.outputs["Color"], eye_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])

# ---------------------------------------------------------------- lens, eye socket and eyeball for each side
NT = 72; EYE_R = 0.018; SOCKET_DEPTH = 0.0095
EYE_A, EYE_UP, EYE_LO = 0.0128, 0.0078, 0.0056      # eye opening: half width, height above and below the centre
eye_info = {}
for side, L in lenses.items():
    nm = "L" if side == 1 else "R"; cx, cz, a, b, yl = L["cx"], L["cz"], L["a"], L["b"], L["y"]
    ex, ez = cx - side * 0.0015, cz + 0.0015            # eye centre: a little to the nose and up in the lens
    wrap = lambda x: 0.9 * (x - XC) ** 2                 # the lens area curves back a little to the sides

    # Lens: a thin tinted sheet in the frame opening.
    verts, faces = [(cx, yl - 0.0008 + wrap(cx), cz)], []
    rings = (0.35, 0.7, 1.03)
    for g in rings:
        for k in range(NT):
            x, z = outline(a, b, 2 * math.pi * k / NT, g); verts.append((cx + x, yl - 0.0006 + wrap(cx + x), cz + z))
    for k in range(NT): faces.append((0, 1 + k, 1 + (k + 1) % NT))
    for r_ in range(len(rings) - 1):
        for k in range(NT):
            k2 = (k + 1) % NT; faces.append((1 + r_ * NT + k, 1 + (r_ + 1) * NT + k, 1 + (r_ + 1) * NT + k2, 1 + r_ * NT + k2))
    o = new_object("Lens." + nm, verts, faces); o.data.materials.append(lens_mat)

    # Eye socket: skin that goes back from the frame to the eyelids, with an almond opening for the eye.
    def eye_edge(th):
        c, s_ = math.cos(th), math.sin(th)
        return EYE_A * c, (EYE_UP if s_ > 0 else EYE_LO) * s_ + 0.0012 * c * side * -1      # outer corner a little lower: a friendly look
    verts, faces = [], []
    RS = 9
    for k in range(NT):
        th = 2 * math.pi * k / NT; xo, zo = outline(a, b, th, 1.04); xi, zi = eye_edge(th)
        for r_ in range(RS):
            t = r_ / (RS - 1)                               # 0 at the eye opening, 1 at the frame
            x = (ex - cx) * (1 - t) + xi * (1 - t) + xo * t; z = (ez - cz) * (1 - t) + zi * (1 - t) + zo * t
            depth = SOCKET_DEPTH * (1 - t) ** 1.4 + 0.0008
            verts.append((cx + x, yl + depth + wrap(cx + x), cz + z))
        verts.append((ex + xi * 0.97, yl + SOCKET_DEPTH + 0.0008 + 0.0055 + wrap(ex + xi), ez + zi * 0.97))       # eyelid edge, back
    R1 = RS + 1
    for k in range(NT):
        k2 = (k + 1) % NT
        for r_ in range(RS - 1): faces.append((k * R1 + r_, k * R1 + r_ + 1, k2 * R1 + r_ + 1, k2 * R1 + r_))
        faces.append((k * R1 + RS, k * R1 + 0, k2 * R1 + 0, k2 * R1 + RS))
    o = new_object("Eye_Socket." + nm, verts, faces)
    o.data.materials.append(skin_mat); o.data.materials.append(lid_mat); o.data.materials.append(lash_mat)
    for poly in o.data.polygons:
        k = poly.index // RS; r_ = poly.index % RS; th = 2 * math.pi * (k + 0.5) / NT
        if r_ == RS - 1: poly.material_index = 1                                  # the back edge of the eyelid
        elif r_ == 0 and 0.12 < th < math.pi - 0.12: poly.material_index = 2      # lash line on the upper eyelid
    m = o.modifiers.new("Subdivision", "SUBSURF"); m.levels = 1; m.render_levels = 1

    # Eyeball.
    ec = np.array([ex, yl + SOCKET_DEPTH + 0.0018 + EYE_R + wrap(ex), ez])
    NRg, NSg = 24, 32; verts, faces, uvs = [], [], []
    for i in range(NRg + 1):
        al = math.pi * i / NRg
        for j in range(NSg + 1):
            be = 2 * math.pi * j / NSg
            verts.append(ec + EYE_R * np.array([math.sin(al) * math.cos(be), -math.cos(al), math.sin(al) * math.sin(be)])); uvs.append((j / NSg, (i + 0.5) / (NRg + 1)))
    for i in range(NRg):
        for j in range(NSg):
            p0 = i * (NSg + 1) + j; faces.append((p0, p0 + 1, p0 + NSg + 2, p0 + NSg + 1))
    o = new_object("Eye." + nm, verts, faces); uvl = o.data.uv_layers.new(name="UVMap")
    for loop in o.data.loops: uvl.data[loop.index].uv = uvs[loop.vertex_index]
    o.data.materials.append(eye_mat); o["centre"] = [float(x) for x in ec]
    eye_info[nm] = ec
    print(f"eye {nm}: centre {np.round(ec, 4)}")

# ---------------------------------------------------------------- mouth: cut the lip line
MOUTH_Z, MOUTH_HW = 1.609, 0.026
y_lip, _ = sample(XC, MOUTH_Z, 2)
print("mouth line z", MOUTH_Z, "lip depth", round(y_lip, 4))
bm = bmesh.new(); bm.from_mesh(head.data); bm.faces.ensure_lookup_table()
box = [f_ for f_ in bm.faces if abs(f_.calc_center_median().x - XC) < MOUTH_HW + 0.002 and abs(f_.calc_center_median().z - MOUTH_Z) < 0.006
       and f_.calc_center_median().y < y_lip + 0.02 and f_.normal.y < 0.2]
geom = list({v for f_ in box for v in f_.verts}) + list({e for f_ in box for e in f_.edges}) + box
bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, MOUTH_Z), plane_no=(0, 0, 1))
on_line = lambda v: abs(v.co.z - MOUTH_Z) < 1e-5 and abs(v.co.x - XC) < MOUTH_HW and v.co.y < y_lip + 0.02
slit = [e for e in bm.edges if on_line(e.verts[0]) and on_line(e.verts[1])]
bmesh.ops.split_edges(bm, edges=slit)
bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table()
tag = bm.verts.layers.int.new("lip")                                   # 1 = lower lip edge, 2 = upper lip edge
rim_lo, rim_up = [], []
for e in bm.edges:
    if e.is_boundary and on_line(e.verts[0]) and on_line(e.verts[1]):
        below = e.link_faces[0].calc_center_median().z < MOUTH_Z
        (rim_lo if below else rim_up).append(e)
        for v in e.verts: v[tag] = 1 if below else 2
inner_mat_index = len(head.data.materials)
for rim, dz, code in ((rim_lo, -0.0025, 1), (rim_up, 0.0025, 2)):       # lips with thickness: turn the edge to the inside
    res = bmesh.ops.extrude_edge_only(bm, edges=rim)
    for g in res["geom"]:
        if isinstance(g, bmesh.types.BMVert): g.co += Vector((0, 0.007, dz)); g[tag] = code
        elif isinstance(g, bmesh.types.BMFace): g.material_index = inner_mat_index
print("mouth: slit edges", len(slit), "lower rim", len(rim_lo), "upper rim", len(rim_up))
# Jaw weight for each vertex of the head.
jw = bm.verts.layers.float.new("jaw_w")
for v in bm.verts:
    x, y, z = v.co; dx = abs(x - XC); below = MOUTH_Z - z
    inside = max(0.0, 1 - (dx / (MOUTH_HW + 0.001)) ** 2) ** 0.8        # the opening is widest at the centre and closes at the corners
    chin = float(smoothstep(0.0, 0.03, below))
    w_ = max(inside if below > 0 else 0.0, chin) * float(smoothstep(-0.050, -0.085, y))
    if v[tag] == 1: w_ = inside
    elif v[tag] == 2: w_ = 0.0
    v[jw] = w_ if z > 1.50 else 0.0
bm.to_mesh(head.data); bm.free()
at = head.data.attributes.get("jaw") or head.data.attributes.new("jaw", "FLOAT", "POINT")
src = head.data.attributes["jaw_w"]; vals = np.empty(len(head.data.vertices), dtype=np.float32); src.data.foreach_get("value", vals); at.data.foreach_set("value", vals)
head.data.materials.append(principled("Lip_Inner", srgb("#7A3A30"), 0.45))

# ---------------------------------------------------------------- mouth cavity, teeth and tongue
MC = np.array([XC, y_lip + 0.030, MOUTH_Z - 0.004])
verts, faces = [], []
NRb, NSb = 12, 24
for i in range(NRb + 1):
    al = math.pi * i / NRb
    for j in range(NSb):
        be = 2 * math.pi * j / NSb
        verts.append(MC + np.array([0.030 * math.sin(al) * math.cos(be), 0.030 * math.sin(al) * math.sin(be) * (1.0 if math.sin(be) > 0 else 0.75), 0.024 * math.cos(al)]))
for i in range(NRb):
    for j in range(NSb):
        j2 = (j + 1) % NSb; faces.append((i * NSb + j, (i + 1) * NSb + j, (i + 1) * NSb + j2, i * NSb + j2))      # normals to the inside
bag = new_object("Mouth_Cavity", verts, faces); bag.data.materials.append(principled("Mouth_Cavity", srgb("#2A0E0C"), 0.6))
bm = bmesh.new(); bm.from_mesh(bag.data); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(bag.data); bm.free()


def teeth(name, z_a, z_b, half, bulge):
    verts, faces = [], []; NTt = 24
    for k in range(NTt + 1):
        t = -1 + 2 * k / NTt; x = XC + t * half; yb = y_lip + 0.0085 + bulge * t * t
        for (zz, yo) in ((z_a, 0.0), (z_b, 0.0), (z_b, 0.004), (z_a, 0.004)): verts.append((x, yb + yo, zz))
    for k in range(NTt):
        for q in range(4): faces.append((k * 4 + q, k * 4 + (q + 1) % 4, (k + 1) * 4 + (q + 1) % 4, (k + 1) * 4 + q))
    o = new_object(name, verts, faces); o.data.materials.append(principled("Teeth", srgb("#EDE8DC"), 0.25, Coat_Weight=0.3))
    return o


teeth("Teeth_Upper", MOUTH_Z + 0.0085, MOUTH_Z - 0.0030, 0.021, 0.013)
teeth("Teeth_Lower", MOUTH_Z - 0.0110, MOUTH_Z - 0.0035, 0.019, 0.012)
verts, faces = [], []
TC = np.array([XC, y_lip + 0.026, MOUTH_Z - 0.0090])
for i in range(9):
    al = math.pi * i / 8
    for j in range(16):
        be = 2 * math.pi * j / 16; verts.append(TC + np.array([0.015 * math.sin(al) * math.cos(be), 0.018 * math.cos(al), 0.0045 * math.sin(al) * math.sin(be)]))
for i in range(8):
    for j in range(16): faces.append((i * 16 + j, i * 16 + (j + 1) % 16, (i + 1) * 16 + (j + 1) % 16, (i + 1) * 16 + j))
tongue = new_object("Tongue", verts, faces); tongue.data.materials.append(principled("Tongue", srgb("#B8574F"), 0.4))
head["mouth"] = [float(XC), float(y_lip), float(MOUTH_Z)]

bpy.ops.wm.save_as_mainfile(filepath=out_path)
print("SAVED", out_path)
