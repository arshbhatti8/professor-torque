"""Animate Professor Torque for the voice line: lip sync, blinks, head and hand gestures. Then render frames.

Usage: scripts/blender.sh <rigged.blend> --python scripts/v6_animate.py -- <timing.json> <frames folder> [--frames=a-b] [--step=n] [--save=<animated.blend>] [--samples=48]
The script renders PNG frames. Join them with the audio with ffmpeg after the render.
"""
import bpy, bmesh, sys, os, json, math, numpy as np
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion

argv = sys.argv[sys.argv.index("--") + 1:]
timing = json.load(open(Path(argv[0]).resolve(), encoding="utf-8")); frames_dir = Path(argv[1]).resolve(); frames_dir.mkdir(parents=True, exist_ok=True)
opt = {a.split("=")[0]: a.split("=")[1] for a in argv[2:] if "=" in a}
FPS = 24; scene = bpy.context.scene; scene.render.fps = FPS
END = int(math.ceil(timing["duration"] * FPS)); scene.frame_start = 1; scene.frame_end = END
D = bpy.data.objects; rig = D["Rig"]; head = D["Head"]
fr = lambda sec: 1 + sec * FPS
for pb in rig.pose.bones: pb.rotation_mode = "QUATERNION"


def key_rot(bone, world_axis, deg, sec, extra=None):
    """Turn a bone about a world axis (in the rest pose frame), and set a key."""
    pb = rig.pose.bones[bone]; ax = (pb.bone.matrix_local.to_3x3().inverted() @ Vector(world_axis)).normalized()
    q = Quaternion(ax, math.radians(deg))
    if extra: q = extra @ q
    pb.rotation_quaternion = q; pb.keyframe_insert("rotation_quaternion", frame=fr(sec)); return q


def key_ik(ctl, pos, sec):
    pb = rig.pose.bones[ctl]; rest = pb.bone.matrix_local
    pb.location = rest.to_3x3().inverted() @ (Vector(pos) - rest.translation); pb.keyframe_insert("location", frame=fr(sec))


def key_shape(obj, name, value, sec):
    kb = obj.data.shape_keys.key_blocks[name]; kb.value = value; kb.keyframe_insert("value", frame=fr(sec))


# ---------------------------------------------------------------- lip sync
OPEN = set("æɑAIWʌɐa"); EE = set("ɛiɪe"); OO = set("OɔuʊYw"); MID = set("əɜɚᵊ"); CLOSED = set("mbp"); FV = set("fv")
events = [(0.0, 0, 0, 0)]
for w in timing["words"]:
    ph = [c for c in w["phonemes"] if c not in "ˈˌː "]
    if not any(c.isalpha() or c in "æɑʌɐɛɪɔʊəɜɚᵊɹʃʒθðŋɡɾ" for c in ph):
        events.append((w["start"] + 0.04, 0, 0, 0)); continue
    dur = (w["end"] - w["start"]) / len(ph)
    for i, c in enumerate(ph):
        t = w["start"] + (i + 0.5) * dur
        if c in OPEN: v = (0.85, 0.15, 0.0)
        elif c in EE: v = (0.40, 0.75, 0.0)
        elif c in OO: v = (0.50, 0.0, 0.95)
        elif c in MID: v = (0.35, 0.1, 0.1)
        elif c in CLOSED: v = (0.0, 0.0, 0.0)
        elif c in FV: v = (0.08, 0.2, 0.0)
        else: v = (0.18, 0.25, 0.0)
        events.append((t, *v))
    events.append((w["end"] + 0.06, 0.05, 0, 0))
events.append((timing["duration"], 0, 0, 0))
merged = []
for e in events:                                        # keys must not be nearer than 1.5 frames
    if merged and e[0] - merged[-1][0] < 1.5 / FPS: merged[-1] = (merged[-1][0], *[max(a_, b_) for a_, b_ in zip(merged[-1][1:], e[1:])])
    else: merged.append(e)
JAW_MAX = 11.0
for t, jaw, wide, oo in merged:
    key_rot("jaw", (1, 0, 0), jaw * JAW_MAX, t)
    key_shape(head, "mouth_wide", wide * 0.9, t); key_shape(head, "mouth_o", oo * 0.9, t)
print("lip sync keys", len(merged))
W = {i: w for i, w in enumerate(timing["words"])}
word_start = lambda text, n=0: [w["start"] for w in timing["words"] if w["text"].lower() == text.lower()][n]

# ---------------------------------------------------------------- smile and blinks
for t, v in ((0.0, 0.25), (0.6, 0.7), (1.9, 0.5), (4.3, 0.6), (5.0, 0.3), (7.1, 0.7), (7.8, 0.3), (10.6, 0.9), (11.4, 0.4), (13.9, 0.8), (timing["duration"], 0.6)):
    key_shape(head, "mouth_smile", v, t)
for t in (0.35, 2.3, 4.7, 7.5, 9.1, 11.2, 14.2):
    for sd in "LR":
        so = D["Eye_Socket." + sd]
        for dt, v in ((-0.08, 0.0), (0.0, 1.0), (0.06, 1.0), (0.17, 0.0)): key_shape(so, "blink", v, t + dt)

# ---------------------------------------------------------------- head, eyes and body
for t, yaw, nod, tilt in ((0.0, 0, 0, 0), (0.9, 4, 6, 3), (1.4, 5, -3, 4), (2.2, 2, 0, 0), (3.0, -5, 3, -2), (3.9, -3, -2, -3), (4.6, 0, 2, 0), (5.3, 6, -2, 3), (6.4, -6, 0, -2),
                          (7.3, 0, 3, 0), (8.2, 5, 0, 3), (9.3, -4, -3, -2), (10.2, -2, 5, 0), (11.0, 0, 0, 0), (11.8, 6, 2, 3), (12.8, 3, 5, 2), (13.6, -3, 0, -2), (14.6, 0, 0, 0)):
    q = Quaternion((0, 0, 1), math.radians(yaw)) @ Quaternion((1, 0, 0), math.radians(nod)) @ Quaternion((0, 1, 0), math.radians(tilt))
    pb = rig.pose.bones["head"]; R = pb.bone.matrix_local.to_3x3()
    pb.rotation_quaternion = (R.inverted() @ q.to_matrix() @ R).to_quaternion(); pb.keyframe_insert("rotation_quaternion", frame=fr(t))
for t, yaw in ((0.0, 0), (2.8, 0), (3.1, 8), (3.9, 8), (4.3, 0), (8.0, 0), (8.3, -7), (9.0, -7), (9.4, 0), (14.5, 0)):
    for sd in "LR": key_rot("eye." + sd, (0, 0, 1), yaw, t)
for t, lean, turn_ in ((0.0, 0, 0), (1.2, 2, 3), (2.6, 0, 0), (5.6, 3, -3), (7.2, 0, 0), (9.6, 2, 3), (11.0, 0, 0), (12.6, 3, -2), (14.6, 0, 0)):
    key_rot("chest", (1, 0, 0), lean, t, extra=None); key_rot("spine", (0, 0, 1), turn_, t)

REST = {sd: Vector(rig.pose.bones["hand_ik." + sd].bone.matrix_local.translation) for sd in "LR"}
DOWN = {"R": Vector((-0.30, -0.02, 0.90)), "L": Vector((0.30, -0.02, 0.90))}           # arms relaxed at the sides
hello = word_start("Hello")
R_KEYS = [(0.0, DOWN["R"]), (hello - 0.25, DOWN["R"]), (hello + 0.20, (-0.40, -0.16, 1.50))]
for i in range(6): R_KEYS.append((hello + 0.36 + i * 0.16, (-0.40 + (0.07 if i % 2 == 0 else -0.05), -0.17, 1.52)))       # the wave
R_KEYS += [(hello + 1.45, (-0.38, -0.16, 1.46)), (hello + 2.1, DOWN["R"]), (word_start("Welcome") - 0.2, DOWN["R"]), (word_start("Welcome") + 0.35, (-0.44, -0.24, 1.12)),
           (word_start("Torque", 1) + 0.6, (-0.44, -0.24, 1.12)), (word_start("machines") - 0.5, (-0.20, -0.30, 1.26)), (word_start("real") - 0.1, (-0.22, -0.30, 1.24)),
           (word_start("satisfaction") + 0.15, (-0.30, -0.26, 1.50)), (word_start("satisfaction") + 1.1, (-0.30, -0.26, 1.50)), (word_start("Today") + 0.2, DOWN["R"]), (timing["duration"], DOWN["R"])]
L_KEYS = [(0.0, DOWN["L"]), (word_start("I") - 0.2, DOWN["L"]), (word_start("Professor"), (0.10, -0.20, 1.30)), (word_start("Torque") + 0.6, (0.10, -0.20, 1.30)),
          (word_start("Welcome") - 0.2, DOWN["L"] + Vector((0, 0, 0.05))), (word_start("Welcome") + 0.35, (0.44, -0.24, 1.12)), (word_start("Torque", 1) + 0.6, (0.44, -0.24, 1.12)),
          (word_start("machines") - 0.5, (0.20, -0.30, 1.26)), (word_start("real") - 0.1, (0.22, -0.30, 1.24)), (word_start("satisfaction") + 0.3, DOWN["L"]),
          (word_start("Today") - 0.1, DOWN["L"]), (word_start("how") - 0.2, (0.26, -0.36, 1.20)), (word_start("gear"), (0.30, -0.34, 1.26)), (word_start("works") + 0.5, (0.28, -0.36, 1.22)),
          (timing["duration"] - 0.3, DOWN["L"])]
for sd, keys in (("R", R_KEYS), ("L", L_KEYS)):
    for t, p in keys: key_ik("hand_ik." + sd, p, t)
# The right hand points up at 'real satisfaction': three fingers curl.
M4 = np.array(D["Hand.R"]["base_to_world"]).reshape(4, 4); curl_axis = Vector(M4[:3, 0]).normalized(); palm = Vector(M4[:3, 1]).normalized()
ts = word_start("satisfaction")
for f in ("middle", "ring", "pinky", "thumb"):
    for i in (1, 2, 3):
        b = f"{f}.{i:02d}.R"; pb = rig.pose.bones[b]; d0 = (pb.bone.tail_local - pb.bone.head_local).normalized()
        sign = 1 if (Matrix.Rotation(0.3, 3, curl_axis) @ d0).dot(palm) > d0.dot(palm) else -1
        amount = 62 if f != "thumb" else 25
        for t, a_ in ((ts - 0.35, 0), (ts + 0.1, amount), (ts + 1.05, amount), (ts + 1.6, 0)): key_rot(b, tuple(curl_axis), sign * a_, t)
for act in bpy.data.actions:
    for fc in act.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = "BEZIER"; kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"

# ---------------------------------------------------------------- stage, light and camera
stage = bpy.data.collections.new("Stage"); scene.collection.children.link(stage)
bm = bmesh.new()
prof = [(-6, 0)] + [(2.5 + 1.5 * math.sin(a), 1.5 - 1.5 * math.cos(a)) for a in [i * math.pi / 2 / 16 for i in range(17)]] + [(4, 7)]
rows = [[bm.verts.new((x, y, z)) for (y, z) in prof] for x in (-9, 9)]
for i in range(len(prof) - 1): bm.faces.new((rows[0][i], rows[0][i + 1], rows[1][i + 1], rows[1][i]))
me = bpy.data.meshes.new("Backdrop"); bm.to_mesh(me); bm.free()
for p in me.polygons: p.use_smooth = True
bd = bpy.data.objects.new("Backdrop", me); stage.objects.link(bd)
mat = bpy.data.materials.new("Backdrop"); mat.use_nodes = True
b = mat.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (0.20, 0.27, 0.40, 1); b.inputs["Roughness"].default_value = 0.9; me.materials.append(mat)
world = scene.world or bpy.data.worlds.new("World"); scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.55, 0.62, 0.75, 1); bg.inputs[1].default_value = 0.14


def look_at(o, target): o.rotation_euler = (Vector(target) - o.location).to_track_quat("-Z", "Y").to_euler()


for name, loc, size, power, colour in (("Key", (-2.2, -3.2, 3.0), 2.2, 200, (1.0, 0.95, 0.88)), ("Fill", (3.0, -2.6, 1.6), 3.5, 70, (0.85, 0.92, 1.0)),
                                       ("Rim", (1.8, 2.6, 3.0), 1.5, 140, (1.0, 0.97, 0.92)), ("Top", (0.0, -0.4, 4.2), 2.5, 35, (1.0, 1.0, 1.0))):
    L = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA")); L.data.size = size; L.data.energy = power; L.data.color = colour; L.location = loc
    look_at(L, (0, 0, 1.25)); stage.objects.link(L)
cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera")); stage.objects.link(cam); scene.camera = cam
cam.location = (0.10, -3.7, 1.42); look_at(cam, (0.0, 0.0, 1.31)); cam.data.lens = 58
scene.render.engine = "CYCLES"; scene.cycles.samples = int(opt.get("--samples", "48")); scene.cycles.use_denoising = True
prefs = bpy.context.preferences.addons["cycles"].preferences; prefs.compute_device_type = "OPTIX"; prefs.get_devices()
for d in prefs.devices: d.use = d.type == "OPTIX"
scene.cycles.device = "GPU"; scene.view_settings.view_transform = "Standard"; scene.render.use_persistent_data = True
scene.render.resolution_x, scene.render.resolution_y = 1280, 720; scene.render.image_settings.file_format = "PNG"; scene.render.use_stamp = False
if "--save" in opt:
    scene.render.filepath = "//frames/"; bpy.ops.wm.save_as_mainfile(filepath=str(Path(opt["--save"]).resolve())); print("SAVED", opt["--save"])

a, b_ = (int(x) for x in opt.get("--frames", f"1-{END}").split("-")); step = int(opt.get("--step", "1"))
print("ANIMATION frames", END, "render", a, "to", b_, "step", step)
for f in range(a, b_ + 1, step):
    out = frames_dir / f"{f:04d}.png"
    if out.exists(): continue
    scene.frame_set(f); scene.render.filepath = str(out); bpy.ops.render.render(write_still=True)
print("RENDER DONE")
