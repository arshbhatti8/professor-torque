"""Render quick head previews (front, three-quarter, side) and join them into one sheet.

Usage: scripts/blender.sh <file.blend> --python scripts/v2_preview_head.py -- <sheet.png> [--clay] [--hide=Name1,Name2] [--show=Name] [--views=0,35,90] [--span=0.42] [--z=1.70]
"""
import bpy, sys, math, os
from pathlib import Path
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:]
sheet = Path(argv[0]).resolve(); opt = {a.split("=")[0]: (a.split("=")[1] if "=" in a else "1") for a in argv[1:]}
views = [float(v) for v in opt.get("--views", "0,35,90").split(",")]
span = float(opt.get("--span", "0.42")); zc = float(opt.get("--z", "1.70")); res = int(opt.get("--res", "800"))
scene = bpy.context.scene
for n in opt.get("--hide", "").split(","):
    for o in bpy.data.objects:
        if n and o.name.startswith(n): o.hide_render = True
for n in opt.get("--show", "").split(","):
    for o in bpy.data.objects:
        if n and o.name.startswith(n):
            o.hide_render = False
            for c in o.users_collection: c.hide_render = False
if "--clay" in opt:
    mat = bpy.data.materials.new("clay"); mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (0.55, 0.55, 0.55, 1); b.inputs["Roughness"].default_value = 0.6
    for o in bpy.data.objects:
        if o.type == "MESH": o.data.materials.clear(); o.data.materials.append(mat)
world = scene.world or bpy.data.worlds.new("World"); scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.45, 0.52, 0.65, 1); bg.inputs[1].default_value = 0.35
def look_at(o, t): o.rotation_euler = (Vector(t) - o.location).to_track_quat("-Z", "Y").to_euler()
T = (float(opt.get("--x", "0")), float(opt.get("--y", "0")), zc)
for name, loc, size, power in (("Key", (-1.2, -1.8, zc + 0.9), 1.2, 40), ("Fill", (1.6, -1.4, zc + 0.1), 2.0, 12), ("Rim", (1.0, 1.5, zc + 0.8), 1.0, 25)):
    L = bpy.data.objects.new("PV_" + name, bpy.data.lights.new(name, "AREA")); L.data.size = size; L.data.energy = power; L.location = loc
    look_at(L, T); scene.collection.objects.link(L)
scene.render.engine = "CYCLES"; scene.cycles.samples = int(opt.get("--samples", "48")); scene.cycles.use_denoising = True
prefs = bpy.context.preferences.addons["cycles"].preferences; prefs.compute_device_type = "OPTIX"; prefs.get_devices()
for d in prefs.devices: d.use = d.type == "OPTIX"
scene.cycles.device = "GPU"; scene.view_settings.view_transform = "Standard"
cam = bpy.data.objects.new("PV_Cam", bpy.data.cameras.new("PV_Cam")); scene.collection.objects.link(cam); scene.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = span; scene.render.resolution_x = scene.render.resolution_y = res
tmp = []
for az in views:
    a = math.radians(az); cam.location = Vector(T) + Vector((math.sin(a), -math.cos(a), 0)) * 3; look_at(cam, T)
    p = str(sheet.with_name(f"_{sheet.stem}_{int(az)}.png")); scene.render.filepath = p; bpy.ops.render.render(write_still=True); tmp.append(p)
W = res * len(tmp); buf = [0.0] * (W * res * 4)
import numpy as np
out = np.zeros((res, W, 4), dtype=np.float32)
for i, p in enumerate(tmp):
    im = bpy.data.images.load(p); a = np.empty(res * res * 4, dtype=np.float32); im.pixels.foreach_get(a)
    out[:, i * res:(i + 1) * res] = a.reshape(res, res, 4); bpy.data.images.remove(im); os.remove(p)
img = bpy.data.images.new("sheet", W, res); img.pixels.foreach_set(out.ravel()); img.filepath_raw = str(sheet); img.file_format = "PNG"; img.save()
print("SHEET", sheet)
