"""Range-of-motion check for the rig. Run it after each rebuild, before a new animation.

The script puts the character in a set of extreme poses. For each pose it measures how much the suit surface
stretches, and it reports a fail if the stretch is too large. With --sheet it also renders each pose to a picture,
so that a person can look for visual defects.

Usage: scripts/blender.sh <rigged.blend> --python scripts/v6_pose_check.py -- [--sheet=<folder>]
"""
import bpy, sys, math, numpy as np
from pathlib import Path
from mathutils import Vector, Quaternion

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
opt = {a.split("=")[0]: a.split("=")[1] for a in argv if "=" in a}
D = bpy.data.objects; rig = D["Rig"]; body = D["Body"]
for pb in rig.pose.bones: pb.rotation_mode = "QUATERNION"


def reset():
    for pb in rig.pose.bones: pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    for o in D:
        if o.type == "MESH" and o.data.shape_keys:
            for k in o.data.shape_keys.key_blocks[1:]: k.value = 0


def rot(bone, axis, deg):
    pb = rig.pose.bones[bone]; ax = (pb.bone.matrix_local.to_3x3().inverted() @ Vector(axis)).normalized()
    pb.rotation_quaternion = Quaternion(ax, math.radians(deg)) @ pb.rotation_quaternion


def ik(ctl, pos):
    pb = rig.pose.bones[ctl]; rest = pb.bone.matrix_local; pb.location = rest.to_3x3().inverted() @ (Vector(pos) - rest.translation)


POSES = {
    "rest": lambda: None,
    "arms_down": lambda: (ik("hand_ik.R", (-0.28, 0.0, 0.90)), ik("hand_ik.L", (0.28, 0.0, 0.90))),
    "arms_up": lambda: (ik("hand_ik.R", (-0.30, -0.05, 1.85)), ik("hand_ik.L", (0.30, -0.05, 1.85))),
    "arms_forward": lambda: (ik("hand_ik.R", (-0.20, -0.52, 1.38)), ik("hand_ik.L", (0.20, -0.52, 1.38))),
    "arms_out": lambda: (ik("hand_ik.R", (-0.70, 0.0, 1.40)), ik("hand_ik.L", (0.70, 0.0, 1.40))),
    "arms_across": lambda: (ik("hand_ik.R", (0.12, -0.26, 1.28)), ik("hand_ik.L", (-0.12, -0.24, 1.18))),
    "wave": lambda: (ik("hand_ik.R", (-0.40, -0.16, 1.52)), ik("hand_ik.L", (0.28, 0.0, 0.90))),
    "head_turn": lambda: (rot("head", (0, 0, 1), 40), rot("neck", (0, 0, 1), 15)),
    "head_nod": lambda: (rot("head", (1, 0, 0), 22), rot("neck", (1, 0, 0), 10)),
    "twist_lean": lambda: (rot("spine", (0, 0, 1), 20), rot("chest", (1, 0, 0), 12)),
    "step": lambda: (ik("foot_ik.R", (-0.14, -0.30, 0.18)), ik("foot_ik.L", (0.14, 0.18, 0.14))),
    "talk_blink": lambda: (rot("jaw", (1, 0, 0), 12), [setattr(D["Eye_Socket." + s].data.shape_keys.key_blocks["blink"], "value", 1.0) for s in "LR"]),
}
me = body.data; n = len(me.vertices)
ed = np.empty(len(me.edges) * 2, dtype=np.int32); me.edges.foreach_get("vertices", ed); ed = ed.reshape(-1, 2)


def body_coords():
    dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); m = ev.to_mesh()
    a = np.empty(len(m.vertices) * 3, dtype=np.float32); m.vertices.foreach_get("co", a); ev.to_mesh_clear(); return a.reshape(-1, 3).astype(np.float64)


reset(); bpy.context.view_layer.update(); P0 = body_coords(); L0 = np.linalg.norm(P0[ed[:, 0]] - P0[ed[:, 1]], axis=1)
unweighted = sum(1 for v in me.vertices if not v.groups)
print(f"CHECK body vertices without weights: {unweighted}  ->  {'PASS' if unweighted == 0 else 'FAIL'}")
# Edge stretch factor at the 99.9 percent level: below 3 is a pass, 3 to 5 is a warning (look at the picture), above 5 is a fail.
PASS_P999, FAIL_P999, FAIL_BAD = 3.0, 5.0, 0.004
fails = unweighted > 0
if "--sheet" in opt:
    out = Path(opt["--sheet"]).resolve(); out.mkdir(parents=True, exist_ok=True)
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = 24; sc.cycles.use_denoising = True
    prefs = bpy.context.preferences.addons["cycles"].preferences; prefs.compute_device_type = "OPTIX"; prefs.get_devices()
    for d in prefs.devices: d.use = d.type == "OPTIX"
    sc.cycles.device = "GPU"; sc.render.resolution_x, sc.render.resolution_y = 640, 800
    world = sc.world or bpy.data.worlds.new("World"); sc.world = world; world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.6, 0.65, 0.75, 1); world.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    if sc.camera is None:
        cam = bpy.data.objects.new("Check_Cam", bpy.data.cameras.new("Check_Cam")); sc.collection.objects.link(cam); sc.camera = cam
        L = bpy.data.objects.new("Check_Light", bpy.data.lights.new("Check_Light", "AREA")); L.data.size = 3; L.data.energy = 350; L.location = (-2, -3.5, 3); sc.collection.objects.link(L)
        L.rotation_euler = (Vector((0, 0, 1.2)) - L.location).to_track_quat("-Z", "Y").to_euler()
    cam = sc.camera; cam.location = (0.6, -4.3, 1.35); cam.data.lens = 50
    cam.rotation_euler = (Vector((0, 0, 1.12)) - cam.location).to_track_quat("-Z", "Y").to_euler()
for name, fn in POSES.items():
    reset(); fn(); bpy.context.view_layer.update()
    P = body_coords(); ratio = np.linalg.norm(P[ed[:, 0]] - P[ed[:, 1]], axis=1) / np.maximum(L0, 1e-9)
    p999 = float(np.percentile(ratio, 99.9)); bad = float(((ratio > 4) | (ratio < 0.25)).mean())
    grade = "FAIL" if (p999 >= FAIL_P999 or bad >= FAIL_BAD) else ("WARN" if p999 >= PASS_P999 else "PASS"); fails = fails or grade == "FAIL"
    print(f"CHECK {name:13s} stretch 99.9%: {p999:5.2f}  bad edges: {bad * 100:5.2f}%  ->  {grade}")
    if "--sheet" in opt:
        sc.render.filepath = str(out / f"{name}.png"); bpy.ops.render.render(write_still=True)
print("CHECK RESULT:", "FAIL" if fails else "PASS")
