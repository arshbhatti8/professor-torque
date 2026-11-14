"""Stage 1 of the clean head: fit the CC0 stylized head (clean quads, UV map) to the AI head shape.

The script opens the assembled character, adds the base head and its eyes, moves them to the AI head,
and then pulls the visible skin areas to the AI surface. The old AI head parts go to a hidden collection.

Usage: scripts/blender.sh <character.blend> --python scripts/v2_fit_head.py -- <base_head.blend> <out.blend>
"""
import bpy, sys, numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:]
base_path, out_path = (str(Path(a).resolve()) for a in argv[:2])
S = 0.86                                   # uniform scale of the base head


def co(o):
    a = np.empty(len(o.data.vertices) * 3, dtype=np.float32); o.data.vertices.foreach_get("co", a)
    return a.reshape(-1, 3).astype(np.float64)


def bvh(o):
    me = o.data
    return BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [tuple(p.vertices) for p in me.polygons])


D = bpy.data.objects
lens = co(D["Lenses"]); xc = (lens[:, 0].min() + lens[:, 0].max()) / 2
lens_c = [lens[lens[:, 0] < xc].mean(0), lens[lens[:, 0] >= xc].mean(0)]
skin_pts = co(D["Head"])
mid = skin_pts[(np.abs(skin_pts[:, 0] - xc) < 0.006) & (skin_pts[:, 2] > 1.64) & (skin_pts[:, 2] < 1.70)]
nose_tip = mid[mid[:, 1].argmin()]
print("AI xc", round(xc, 4), "nose tip", np.round(nose_tip, 4), "lens centres", np.round(lens_c, 4))

# Add the base head.
with bpy.data.libraries.load(base_path) as (src, dst):
    dst.objects = list(src.objects)
col = bpy.data.collections["Professor_Torque"]
for o in dst.objects: col.objects.link(o)
head = D["GEO-head_stylized"]; eyes = [D["GEO-head_stylized.eye.R"], D["GEO-head_stylized.eye.L"]]
bpy.context.view_layer.update()
for e in eyes:                             # remove the parent link and keep the position
    M = e.matrix_world.copy(); e.parent = None; e.matrix_world = M
P = co(head) + np.array(head.matrix_world.translation)
head.matrix_world.identity()
E = [np.array(e.matrix_world.translation) for e in eyes]
eye_r = float(np.linalg.norm(co(eyes[0]), axis=1).max())
cb = (E[0] + E[1]) / 2
base_tip = P[np.abs(P[:, 0]) < 0.006]; base_tip = base_tip[base_tip[:, 1].argmin()]
ear = (np.abs(P[:, 0]) > 0.102) & (P[:, 2] > 0.63) & (P[:, 2] < 0.78)      # flatten the wide stylized ears
P[ear, 0] = np.sign(P[ear, 0]) * (0.102 + 0.45 * (np.abs(P[ear, 0]) - 0.102))
EYE_Z = 1.703
ct = np.array([xc, nose_tip[1] - S * (base_tip[1] - cb[1]), EYE_Z])
P0 = P.copy()
P = ct + S * (P - cb)
E = [ct + S * (e - cb) for e in E]; eye_r *= S
print("eye centres", np.round(E, 4), "eye radius", round(eye_r, 4))

# Mesh neighbours for the smooth warp.
me = head.data; n = len(me.vertices)
ed = np.empty(len(me.edges) * 2, dtype=np.int32); me.edges.foreach_get("vertices", ed); ed = ed.reshape(-1, 2)
deg = np.bincount(ed.ravel(), minlength=n).astype(np.float64)


def neighbour_mean(d):
    acc = np.zeros_like(d)
    np.add.at(acc, ed[:, 0], d[ed[:, 1]]); np.add.at(acc, ed[:, 1], d[ed[:, 0]])
    return acc / np.maximum(deg, 1)[:, None]


def normals(P):
    me.vertices.foreach_set("co", P.astype(np.float32).ravel()); me.update()
    a = np.empty(n * 3, dtype=np.float32); me.vertices.foreach_get("normal", a)
    return a.reshape(-1, 3).astype(np.float64)


skin_bvh, beard_bvh, turban_bvh = bvh(D["Head"]), bvh(D["Beard_Moustache"]), bvh(D["Turban"])
BEARD_INSET = 0.008
# The edges of the AI skin area are rough. Do not use targets near these edges.
from mathutils.kdtree import KDTree
sm = D["Head"].data
ecount = {}
for poly in sm.polygons:
    for k in poly.edge_keys: ecount[k] = ecount.get(k, 0) + 1
bverts = sorted({v for k, c in ecount.items() if c == 1 for v in k})
edge_kd = KDTree(len(bverts))
for j, v in enumerate(bverts): edge_kd.insert(sm.vertices[v].co, j)
edge_kd.balance()
EDGE_CLEAR = 0.006


def targets(P, reach):
    N = normals(P)
    T = np.zeros_like(P); W = np.zeros(n)
    for i in range(n):
        p = Vector(P[i]); x, y, z = P[i]
        if y > 0.02 or z > 1.775: continue                     # the back and the top are hidden
        if abs(x - xc) > 0.07 and y > -0.045: continue         # ears: no target
        in_lens = any(abs(x - c[0]) < 0.037 and 1.668 < z < 1.732 for c in lens_c) and y < -0.06
        in_bridge = abs(x - xc) < 0.014 and 1.688 < z < 1.732
        in_mouth = abs(x - xc) < 0.042 and 1.595 < z < 1.652 and y < -0.07    # the moustache hides the AI mouth
        if in_mouth: continue
        hit = skin_bvh.find_nearest(p, reach)
        if hit[0] is not None and not in_lens and not in_bridge and hit[1].dot(Vector(N[i])) > 0.3 \
                and edge_kd.find(hit[0])[2] > EDGE_CLEAR:
            T[i] = hit[0]; W[i] = 1.0; continue
        hit = beard_bvh.find_nearest(p, reach * 1.5)
        if hit[0] is not None and z < 1.66 and hit[1].dot(Vector(N[i])) > 0.2:
            T[i] = np.array(hit[0]) - BEARD_INSET * np.array(hit[1]); W[i] = 0.08
    return T, W


for it, (reach, lam, relax) in enumerate([(0.03, 4.0, 60), (0.02, 2.0, 50), (0.015, 1.0, 40), (0.01, 0.6, 40), (0.008, 0.4, 30)]):
    T, W = targets(P, reach)
    d = np.where(W[:, None] > 0, T - P, 0.0); dt = d.copy()
    for _ in range(relax):
        d = (W[:, None] * dt + lam * neighbour_mean(d)) / (W[:, None] + lam)
    P = P + d
    print(f"fit pass {it}: targets={int((W > 0).sum())} mean move={np.linalg.norm(d, axis=1).mean() * 1000:.2f} mm")

# The base head is symmetric. Make the fitted head symmetric again to remove small lumps.
kd0 = KDTree(n)
for i, v in enumerate(P0): kd0.insert(v, i)
kd0.balance()
mirror = np.array([kd0.find((-v[0], v[1], v[2]))[1] for v in P0])
Pm = P[mirror].copy(); Pm[:, 0] = 2 * xc - Pm[:, 0]
P = 0.5 * (P + Pm)

# Keep the hidden skull inside the turban.
N = normals(P); moved = 0
for i in range(n):
    hit = turban_bvh.find_nearest(Vector(P[i]), 0.03)
    if hit[0] is None: continue
    q, nt = np.array(hit[0]), np.array(hit[1])
    if (P[i] - q).dot(nt) > -0.004 and (P[i][2] > 1.745 or P[i][1] > -0.03):
        P[i] = q - 0.005 * nt; moved += 1
print("skull vertices moved inside the turban:", moved)
for _ in range(3):                                           # relax the hidden area only
    hid = (P[:, 2] > 1.76) | (P[:, 1] > 0.0)
    P[hid] = 0.5 * P[hid] + 0.5 * (neighbour_mean(P)[hid])

# Eyelids must not cut the eyeballs.
for c in E:
    v = P - c; r = np.linalg.norm(v, axis=1); inside = r < eye_r * 1.01
    P[inside] = c + v[inside] / r[inside, None] * eye_r * 1.012
me.vertices.foreach_set("co", P.astype(np.float32).ravel()); me.update()
for e, c in zip(eyes, E):
    e.matrix_world.identity(); e.location = c; e.scale = (S, S, S)

head.name = "Head_Clean"; head.data.name = "Head_Clean"
eyes[0].name, eyes[1].name = "Eye.R", "Eye.L"
for o in [head] + eyes:
    o.data.polygons.foreach_set("use_smooth", np.ones(len(o.data.polygons), dtype=bool))
    m = o.modifiers.new("Subdivision", "SUBSURF"); m.levels = 2; m.render_levels = 2

# Keep the AI head parts as a hidden reference.
ref = bpy.data.collections.new("AI_Reference"); bpy.context.scene.collection.children.link(ref)
for name in ("Head", "Glasses", "Lenses", "Beard_Moustache", "Collar"):
    o = D[name]; col.objects.unlink(o); ref.objects.link(o); o.name = "AI_" + name; o.hide_render = True; o.hide_viewport = True
ref.hide_render = True
for o in [o for o in D if o.name.startswith(("Backdrop", "Key", "Fill", "Rim", "Top", "Camera"))]:
    bpy.data.objects.remove(o)
bpy.ops.wm.save_as_mainfile(filepath=out_path)
print("SAVED", out_path)
