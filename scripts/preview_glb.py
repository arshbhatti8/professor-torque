"""Render a GLB model from several angles into one sheet. The camera frames the model automatically.

Usage: scripts/blender.sh --python scripts/preview_glb.py -- <model.glb> <sheet.png> [--views=0,35,90,180] [--res=800] [--zoom=1.0] [--zc=0.5]
--zc is the vertical centre of the frame as a part of the model height (0 = bottom, 1 = top).
"""
import bpy, sys, math, os, numpy as np
from pathlib import Path
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:]
model, sheet = str(Path(argv[0]).resolve()), Path(argv[1]).resolve()
opt = {a.split("=")[0]: a.split("=")[1] for a in argv[2:] if "=" in a}
views = [float(v) for v in opt.get("--views", "0,35,90,180").split(",")]; res = int(opt.get("--res", "800"))
zoom = float(opt.get("--zoom", "1.0")); zc = float(opt.get("--zc", "0.5"))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=model)
scene = bpy.context.scene
meshes = [o for o in scene.objects if o.type == "MESH"]
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo = Vector(min(p[i] for p in pts) for i in range(3)); hi = Vector(max(p[i] for p in pts) for i in range(3)); size = hi - lo
T = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z + size.z * zc)); h = max(size)
print("STATS faces", sum(len(o.data.polygons) for o in meshes), "size", tuple(round(s, 3) for s in size))
world = bpy.data.worlds.new("World"); scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.5, 0.55, 0.65, 1); bg.inputs[1].default_value = 0.55
def look_at(o, t): o.rotation_euler = (Vector(t) - o.location).to_track_quat("-Z", "Y").to_euler()
for name, d, power in (("Key", (-0.6, -0.9, 0.5), 22), ("Fill", (0.8, -0.7, 0.1), 9), ("Rim", (0.5, 0.8, 0.5), 14)):
    L = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA")); L.data.size = h; L.data.energy = power * h * h
    L.location = T + Vector(d) * h * 2; look_at(L, T); scene.collection.objects.link(L)
scene.render.engine = "CYCLES"; scene.cycles.samples = 48; scene.cycles.use_denoising = True
prefs = bpy.context.preferences.addons["cycles"].preferences; prefs.compute_device_type = "OPTIX"; prefs.get_devices()
for d in prefs.devices: d.use = d.type == "OPTIX"
scene.cycles.device = "GPU"; scene.view_settings.view_transform = "Standard"
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); scene.collection.objects.link(cam); scene.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = h * 1.08 / zoom; scene.render.resolution_x = scene.render.resolution_y = res
out = np.zeros((res, res * len(views), 4), dtype=np.float32)
for i, az in enumerate(views):
    a = math.radians(az); cam.location = T + Vector((math.sin(a), -math.cos(a), 0)) * h * 4; look_at(cam, T); cam.data.clip_end = h * 20
    p = str(sheet.with_name(f"_{sheet.stem}_{i}.png")); scene.render.filepath = p; bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(p); buf = np.empty(res * res * 4, dtype=np.float32); im.pixels.foreach_get(buf)
    out[:, i * res:(i + 1) * res] = buf.reshape(res, res, 4); bpy.data.images.remove(im); os.remove(p)
img = bpy.data.images.new("sheet", res * len(views), res); img.pixels.foreach_set(out.ravel()); img.filepath_raw = str(sheet); img.file_format = "PNG"; img.save()
print("SHEET", sheet)
