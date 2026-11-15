"""Version 4 rig: add an armature (body, arms, legs, fingers) and bind all parts to it.

The AI body is one fused surface, so the script computes its weights from the distance to the bones.
The clean CC0 hands get automatic weights from Blender.

Usage: scripts/blender.sh <parts.blend> --python scripts/v4_rig.py -- <out.blend> [--pose=<pose_test.png>]
"""
import bpy, sys, os, math, numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_lib import *

argv = sys.argv[sys.argv.index("--") + 1:]
out_path = str(Path(argv[0]).resolve())
body, head = D["Body"], D["Head"]

# ---------------------------------------------------------------- joints
J = {"hips": ((0, 0.02, 0.95), (0, 0.02, 1.08)), "spine": ((0, 0.02, 1.08), (0, 0.03, 1.25)), "chest": ((0, 0.03, 1.25), (0, 0.05, 1.46)),
     "neck": ((0, 0.045, 1.49), (0, 0.03, 1.585)), "head": ((0, 0.03, 1.585), (0, 0.02, 1.82))}
PARENT = {"spine": "hips", "chest": "spine", "neck": "chest", "head": "neck"}
FINGERS = {"thumb": [(0.035, 0.010, -0.070), (0.058, 0.028, -0.110), (0.070, 0.036, -0.130), (0.081, 0.042, -0.150)],
           "index": [(0.036, -0.002, -0.135), (0.036, -0.002, -0.165), (0.036, -0.002, -0.192), (0.036, -0.002, -0.216)],
           "middle": [(0.012, -0.002, -0.135), (0.012, -0.002, -0.170), (0.012, -0.002, -0.203), (0.012, -0.002, -0.235)],
           "ring": [(-0.012, -0.002, -0.135), (-0.012, -0.002, -0.167), (-0.012, -0.002, -0.197), (-0.012, -0.002, -0.225)],
           "pinky": [(-0.036, -0.002, -0.130), (-0.036, -0.002, -0.155), (-0.036, -0.002, -0.178), (-0.036, -0.002, -0.200)]}
if "mouth" in head.keys():                              # face bones: jaw and eyes
    mx, my, mz = head["mouth"]
    J["jaw"] = ((mx, my + 0.095, mz + 0.045), (mx, my - 0.002, mz - 0.050)); PARENT["jaw"] = "head"
    for sd in "LR":
        ec = np.array(D["Eye." + sd]["centre"]); J["eye." + sd] = (tuple(ec), tuple(ec + np.array([0, -0.03, 0]))); PARENT["eye." + sd] = "head"
for s, sd in ((1, "L"), (-1, "R")):
    hand = D["Hand." + sd]; M4 = np.array(hand["base_to_world"]).reshape(4, 4); W = np.array(hand["wrist"])
    tw = lambda p: tuple(M4[:3, :3] @ np.array(p) + M4[:3, 3])
    Sj = np.array([s * 0.20, 0.06, 1.40]); El = Sj + 0.5 * (W - Sj) + np.array([0, 0.012, 0])
    J["shoulder." + sd] = ((s * 0.04, 0.06, 1.455), tuple(Sj)); PARENT["shoulder." + sd] = "chest"
    J["upper_arm." + sd] = (tuple(Sj), tuple(El)); PARENT["upper_arm." + sd] = "shoulder." + sd
    J["forearm." + sd] = (tuple(El), tuple(W)); PARENT["forearm." + sd] = "upper_arm." + sd
    J["hand." + sd] = (tuple(W), tw((0.0, 0.0, -0.11))); PARENT["hand." + sd] = "forearm." + sd
    for fn, pts in FINGERS.items():
        for i in range(3):
            nm = f"{fn}.{i + 1:02d}.{sd}"; J[nm] = (tw(pts[i]), tw(pts[i + 1])); PARENT[nm] = "hand." + sd if i == 0 else f"{fn}.{i:02d}.{sd}"
    J["thigh." + sd] = ((s * 0.095, 0.03, 0.92), (s * 0.118, 0.035, 0.50)); PARENT["thigh." + sd] = "hips"
    J["shin." + sd] = ((s * 0.118, 0.035, 0.50), (s * 0.140, 0.055, 0.10)); PARENT["shin." + sd] = "thigh." + sd
    J["foot." + sd] = ((s * 0.140, 0.055, 0.10), (s * 0.155, -0.10, 0.03)); PARENT["foot." + sd] = "shin." + sd

arm_data = bpy.data.armatures.new("Rig"); rig = bpy.data.objects.new("Rig", arm_data); collection().objects.link(rig)
bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode="EDIT")
for name, (h, t) in J.items():
    eb = arm_data.edit_bones.new(name); eb.head = h; eb.tail = t
for name, par in PARENT.items():
    eb = arm_data.edit_bones[name]; eb.parent = arm_data.edit_bones[par]
    eb.use_connect = (Vector(eb.head) - Vector(eb.parent.tail)).length < 1e-4
# IK control bones (they do not deform the mesh): move a hand or a foot, and the arm or the leg follows.
for sd in "LR":
    for ctl, src_bone in (("hand_ik." + sd, "forearm." + sd), ("foot_ik." + sd, "shin." + sd)):
        eb = arm_data.edit_bones.new(ctl); tail = Vector(J[src_bone][1]); eb.head = tail; eb.tail = tail + Vector((0, 0.08, 0)); eb.use_deform = False
bpy.ops.object.mode_set(mode="OBJECT")
for sd in "LR":
    for ctl, src_bone in (("hand_ik." + sd, "forearm." + sd), ("foot_ik." + sd, "shin." + sd)):
        c = rig.pose.bones[src_bone].constraints.new("IK"); c.target = rig; c.subtarget = ctl; c.chain_count = 2; c.use_stretch = False
        rig.pose.bones[ctl].custom_shape_scale_xyz = (1.5, 1.5, 1.5)
rig.show_in_front = True
print("bones", len(arm_data.bones))


def co(o):
    a = np.empty(len(o.data.vertices) * 3, dtype=np.float32); o.data.vertices.foreach_get("co", a); return a.reshape(-1, 3).astype(np.float64)


def set_weights(o, names, Wt, minimum=0.01):
    for vg in list(o.vertex_groups): o.vertex_groups.remove(vg)
    for j, nm in enumerate(names):
        idx = np.where(Wt[:, j] > minimum)[0]
        if not len(idx): continue
        vg = o.vertex_groups.new(name=nm)
        for i in idx: vg.add([int(i)], float(Wt[i, j]), "REPLACE")
    m = o.modifiers.new("Armature", "ARMATURE"); m.object = rig
    while o.modifiers[0] != m: bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_move_up(modifier=m.name)
    o.parent = rig


def seg_dist(P, a, b):
    a, b = np.array(a), np.array(b); ab = b - a
    t = np.clip(((P - a) @ ab) / ab.dot(ab), 0, 1)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1)


# ---------------------------------------------------------------- body weights
BODY_BONES = ["hips", "spine", "chest"] + [f"{b}.{sd}" for sd in "LR" for b in ("shoulder", "upper_arm", "forearm", "thigh", "shin", "foot")]
# Join the double vertices at the texture seams (the UV map stays, because it is stored for each face corner), and
# remove the imported custom normals. Without this, the surface shows dark dots and lines after a change of the shape.
import bmesh
bmw = bmesh.new(); bmw.from_mesh(body.data); n0 = len(bmw.verts)
bmesh.ops.remove_doubles(bmw, verts=bmw.verts, dist=2e-5); bmw.to_mesh(body.data); bmw.free()
bpy.ops.object.select_all(action="DESELECT"); body.select_set(True); bpy.context.view_layer.objects.active = body
if body.data.has_custom_normals: bpy.ops.mesh.customdata_custom_splitnormals_clear()
body.data.polygons.foreach_set("use_smooth", np.ones(len(body.data.polygons), dtype=bool)); body.data.update()
print("body: joined", n0 - len(body.data.vertices), "double vertices")
P = co(body); n = len(P)
Dm = np.stack([seg_dist(P, *J[b]) for b in BODY_BONES], axis=1)
Wt = 1.0 / (Dm ** 2 + 1e-5) ** 2

# Arm or torso? Distance through the air is wrong here: the side of the jacket is near the arm bone, and it then moves
# with the arm. So the script labels each vertex by its distance along the surface, from seed areas on the forearms and
# on the centre of the torso. The border is then at the shoulder and the armpit.
import heapq
key = np.round(P / 2e-5).astype(np.int64)
_, inv = np.unique(key, axis=0, return_inverse=True); inv = inv.ravel(); nm = inv.max() + 1
Pm = np.zeros((nm, 3)); Pm[inv] = P
me = body.data; ed = np.empty(len(me.edges) * 2, dtype=np.int32); me.edges.foreach_get("vertices", ed); ed = inv[ed.reshape(-1, 2)]
ed = np.unique(np.sort(ed, axis=1), axis=0); ed = ed[ed[:, 0] != ed[:, 1]]
elen = np.linalg.norm(Pm[ed[:, 0]] - Pm[ed[:, 1]], axis=1)
adj = [[] for _ in range(nm)]
for (a_, b_), l_ in zip(ed, elen): adj[a_].append((b_, l_)); adj[b_].append((a_, l_))


def surface_distance(seeds):
    dist = np.full(nm, np.inf); heap = []
    for s_ in seeds: dist[s_] = 0.0; heap.append((0.0, int(s_)))
    heapq.heapify(heap)
    while heap:
        d_, u = heapq.heappop(heap)
        if d_ > dist[u]: continue
        for v_, l_ in adj[u]:
            nd = d_ + l_
            if nd < dist[v_]: dist[v_] = nd; heapq.heappush(heap, (nd, int(v_)))
    return dist


torso_seed = np.where((np.abs(Pm[:, 0]) < 0.09) & (Pm[:, 2] > 0.95) & (Pm[:, 2] < 1.45))[0]
d_torso = surface_distance(torso_seed)
label = np.zeros(nm, dtype=np.int8)                       # 0 = torso and legs, 1 = left arm, -1 = right arm
for sgn, sd in ((1, "L"), (-1, "R")):
    fa = seg_dist(Pm, *J["forearm." + sd]) < 0.07
    d_arm = surface_distance(np.where(fa)[0])
    # The upper arm starts a little outside of the equal-distance line, so that the shoulder pad stays with the torso.
    label[(d_arm + 0.045 < d_torso) & (sgn * Pm[:, 0] > 0.12)] = sgn
print("arm vertices:", int((label == 1).sum()), int((label == -1).sum()), "of", nm)
# The AI surface of the sleeves is bumpy, and the bumps show as light and dark flecks when the arms move.
# Make the sleeves smooth (the sleeve ends stay as they are, for the cuffs).
pin = np.zeros(nm, dtype=bool)
for sd in "LR": pin |= np.linalg.norm(Pm - np.array(J["forearm." + sd][1]), axis=1) < 0.035
sm = (label != 0) & ~pin
degm = np.bincount(ed.ravel(), minlength=nm).astype(np.float64)[:, None]
for _ in range(10):
    acc = np.zeros_like(Pm); np.add.at(acc, ed[:, 0], Pm[ed[:, 1]]); np.add.at(acc, ed[:, 1], Pm[ed[:, 0]])
    avg = acc / np.maximum(degm, 1); Pm[sm] = 0.5 * Pm[sm] + 0.5 * avg[sm]
for _ in range(2):                                        # a light smooth step for the rest of the suit
    acc = np.zeros_like(Pm); np.add.at(acc, ed[:, 0], Pm[ed[:, 1]]); np.add.at(acc, ed[:, 1], Pm[ed[:, 0]])
    avg = acc / np.maximum(degm, 1); rest_ = (label == 0) & (Pm[:, 2] < 1.50) & ~((Pm[:, 2] > 0.86) & (Pm[:, 2] < 0.98))      # not the jacket hem: it must stay sharp
    Pm[rest_] = 0.6 * Pm[rest_] + 0.4 * avg[rest_]
# Smooth normals: the AI surface has small bumps that show as light and dark patches. Take the normals from a much
# smoother copy of the surface. The shape and the outline stay, and the light on the cloth becomes even.
Ps = Pm.copy()
for _ in range(25):
    acc = np.zeros_like(Ps); np.add.at(acc, ed[:, 0], Ps[ed[:, 1]]); np.add.at(acc, ed[:, 1], Ps[ed[:, 0]])
    Ps = 0.5 * Ps + 0.5 * acc / np.maximum(degm, 1)
body.data.vertices.foreach_set("co", Ps[inv].astype(np.float32).ravel()); body.data.update()
nrm_s = np.empty(n * 3, dtype=np.float32); body.data.vertices.foreach_get("normal", nrm_s); nrm_s = nrm_s.reshape(-1, 3)
P = Pm[inv]; body.data.vertices.foreach_set("co", P.astype(np.float32).ravel()); body.data.update()
nrm_g = np.empty(n * 3, dtype=np.float32); body.data.vertices.foreach_get("normal", nrm_g); nrm_g = nrm_g.reshape(-1, 3)
keep_geo = (P[:, 2] > 1.50) | (P[:, 2] < 0.14)            # the neck rim and the shoes keep their own normals
nrm_s[keep_geo] = nrm_g[keep_geo]
body.data.normals_split_custom_set_from_vertices([tuple(v) for v in nrm_s])
lab = label[inv]
for j, b in enumerate(BODY_BONES):
    arm_bone = b.startswith(("upper_arm", "forearm")); sgn = 1 if b.endswith(".L") else -1
    if arm_bone: Wt[lab != sgn, j] = 0                    # arm bones move only the arm
    else: Wt[lab != 0, j] = 0                             # all other bones do not move the arms
    if b.endswith(".L"): Wt[P[:, 0] < -0.02, j] = 0
    if b.endswith(".R"): Wt[P[:, 0] > 0.02, j] = 0
    if b.startswith(("thigh", "shin", "foot")): Wt[P[:, 2] > 1.02, j] = 0
    if b in ("spine", "chest") or b.startswith("shoulder"): Wt[P[:, 2] < 0.80, j] = 0
tot = Wt.sum(1, keepdims=True); Wt = np.where(tot > 0, Wt / np.maximum(tot, 1e-12), 0)
# The AI mesh has double vertices at the texture seams. Vertices at the same position must get the same weights,
# or the surface tears open in a pose. So the smooth step works on merged positions.
cnt = np.bincount(inv, minlength=nm).astype(np.float64)[:, None]
Wm = np.zeros((nm, Wt.shape[1])); np.add.at(Wm, inv, Wt); Wm /= cnt
deg = np.bincount(ed.ravel(), minlength=nm).astype(np.float64)[:, None]
for _ in range(70):                                     # smooth the weights along the surface (a wide blend at the shoulder and the hip)
    acc = np.zeros_like(Wm); np.add.at(acc, ed[:, 0], Wm[ed[:, 1]]); np.add.at(acc, ed[:, 1], Wm[ed[:, 0]])
    Wm = 0.5 * Wm + 0.5 * acc / np.maximum(deg, 1)
Wt = Wm[inv]
print("body: merged", n - nm, "double vertices for the weights")
Wt[Wt < 0.02] = 0; Wt /= Wt.sum(1, keepdims=True)
set_weights(body, BODY_BONES, Wt)
print("body weights done")

# ---------------------------------------------------------------- modelled suit parts follow the suit surface below them
from mathutils.kdtree import KDTree
Pb_final = co(body); kd = KDTree(len(Pb_final))
for i_, p_ in enumerate(Pb_final): kd.insert(p_, i_)
kd.balance()


def bind_like_body(o):
    """Each vertex gets the weights of the nearest suit vertex, so that the part moves with the suit and does not slide."""
    Po = co(o); idx = np.array([kd.find(p_)[1] for p_ in Po])
    set_weights(o, BODY_BONES, Wt[idx])


for o in [o for o in D if o.type == "MESH" and o.name.startswith(("Suit_", "Pocket_Square"))]: bind_like_body(o)
print("suit parts bound:", [o.name for o in D if o.name.startswith(("Suit_", "Pocket_Square"))])

# ---------------------------------------------------------------- head, tie
P = co(head); z, y = P[:, 2], P[:, 1]
h = np.maximum(smoothstep(1.565, 1.615, z), smoothstep(-0.045, -0.065, y))        # the face and the beard follow the head
c = (1 - smoothstep(1.535, 1.575, z)) * (1 - h)
if "jaw" in J:
    jw = np.empty(len(P), dtype=np.float32); head.data.attributes["jaw"].data.foreach_get("value", jw); jw = jw.astype(np.float64)
    set_weights(head, ["head", "jaw", "neck", "chest"], np.stack([h * (1 - jw), h * jw, np.clip(1 - h - c, 0, 1), c], axis=1), minimum=0.004)
    mz = head["mouth"][2]
    for sd in "LR":
        for nm_, bone in (("Lens." + sd, "head"), ("Eye_Socket." + sd, "head"), ("Glasses_Rim." + sd, "head"), ("Eye." + sd, "eye." + sd)):
            set_weights(D[nm_], [bone], np.ones((len(D[nm_].data.vertices), 1)))
    for nm_, bone in (("Teeth_Upper", "head"), ("Teeth_Lower", "jaw"), ("Tongue", "jaw")):
        set_weights(D[nm_], [bone], np.ones((len(D[nm_].data.vertices), 1)))
    Pb = co(D["Mouth_Cavity"]); tj = smoothstep(mz + 0.002, mz - 0.006, Pb[:, 2])      # the lower half of the cavity follows the jaw
    set_weights(D["Mouth_Cavity"], ["jaw", "head"], np.stack([tj, 1 - tj], axis=1))
else:
    set_weights(head, ["head", "neck", "chest"], np.stack([h, np.clip(1 - h - c, 0, 1), c], axis=1))
bind_like_body(D["Tie"])                              # the tie lies on the shirt and moves with it
for nm_ in [n_ for n_ in ("Tie_Knot", "Shirt_Collar", "Neck_Base") if n_ in D]:
    set_weights(D[nm_], ["chest"], np.ones((len(D[nm_].data.vertices), 1)))
for sd in "LR":
    cf = D["Shirt_Cuff." + sd]; set_weights(cf, ["forearm." + sd], np.ones((len(cf.data.vertices), 1)))

# ---------------------------------------------------------------- hands: automatic weights
for sd in "LR":
    hand = D["Hand." + sd]
    bpy.ops.object.select_all(action="DESELECT"); hand.select_set(True); rig.select_set(True); bpy.context.view_layer.objects.active = rig
    res = bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    names = [g.name for g in hand.vertex_groups]
    bad = [g for g in hand.vertex_groups if not g.name.endswith("." + sd)]
    for g in bad: hand.vertex_groups.remove(g)
    weighted = sum(1 for v in hand.data.vertices if len(v.groups))
    print(f"hand {sd}: auto weights {res}, groups {len(hand.vertex_groups)}, weighted vertices {weighted}/{len(hand.data.vertices)}")
    if weighted < len(hand.data.vertices):              # reserve method: distance weights
        HB = [b for b in J if b.endswith("." + sd) and (b.startswith(("hand", "thumb", "index", "middle", "ring", "pinky")))]
        P = co(hand); Dm = np.stack([seg_dist(P, *J[b]) for b in HB], axis=1); Wt = 1.0 / (Dm ** 2 + 1e-6) ** 2; Wt /= Wt.sum(1, keepdims=True)
        for m in [m for m in hand.modifiers if m.type == "ARMATURE"]: hand.modifiers.remove(m)
        set_weights(hand, HB, Wt); print("hand", sd, "used distance weights")
    am = next(m for m in hand.modifiers if m.type == "ARMATURE")
    while hand.modifiers[0] != am: bpy.context.view_layer.objects.active = hand; bpy.ops.object.modifier_move_up(modifier=am.name)

bpy.ops.wm.save_as_mainfile(filepath=out_path)
print("SAVED", out_path)

# ---------------------------------------------------------------- pose test
pose_png = next((a.split("=")[1] for a in argv[1:] if a.startswith("--pose=")), None)
if pose_png:
    def turn(bone, axis, deg_):
        pb = rig.pose.bones[bone]; bpy.context.view_layer.update()
        piv = pb.matrix.translation.copy()
        pb.matrix = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(deg_), 4, axis) @ Matrix.Translation(-piv) @ pb.matrix
        bpy.context.view_layer.update()

    def move(ctl, pos):
        pb = rig.pose.bones[ctl]; M = pb.matrix.copy(); M.translation = Vector(pos); pb.matrix = M; bpy.context.view_layer.update()

    move("hand_ik.R", (-0.27, 0.03, 0.93))               # right arm down at the side (IK)
    move("hand_ik.L", (0.40, -0.36, 1.46))               # left hand up to the front (IK)
    move("foot_ik.R", (-0.14, -0.16, 0.15))              # a step with the right foot (IK)
    hb = rig.pose.bones["hand.L"]; bpy.context.view_layer.update()
    A = (hb.matrix @ hb.bone.matrix_local.inverted()).to_3x3()
    M4 = np.array(D["Hand.L"]["base_to_world"]).reshape(4, 4)
    axis = A @ Vector(M4[:3, 0]).normalized(); palm = A @ Vector(M4[:3, 1]).normalized()
    for f in ("middle", "ring", "pinky"):                # the left hand points with the index finger
        for i in (1, 2, 3):
            pb = rig.pose.bones[f"{f}.{i:02d}.L"]; bpy.context.view_layer.update()
            d0 = (pb.tail - pb.head).normalized(); sign = 1 if (Matrix.Rotation(0.3, 3, axis) @ d0).dot(palm) > d0.dot(palm) else -1
            turn(pb.name, axis, sign * 60)
    if "jaw" in J:
        turn("jaw", "X", 11)                             # open the mouth
        turn("eye.L", "Z", 12); turn("eye.R", "Z", 12)   # look to the side
    turn("head", "Z", 18)
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(out_path).with_name(Path(out_path).stem + "_pose.blend")))
    print("POSE SAVED")
