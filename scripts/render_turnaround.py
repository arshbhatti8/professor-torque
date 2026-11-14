"""Import a model and render it from fixed angles for review.

Usage: scripts/blender.sh --python scripts/render_turnaround.py -- <model> <output folder> [--clay]
The model can be .glb, .gltf, .fbx, .obj, or .blend. --clay replaces all materials with grey.
"""
import bpy, sys, math
from pathlib import Path
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
model, out = Path(argv[0]).resolve(), Path(argv[1]).resolve()
clay = "--clay" in argv
project = Path(argv[argv.index("--project") + 1]).resolve() if "--project" in argv else None
out.mkdir(parents=True, exist_ok=True)

ext = model.suffix.lower()
if ext == ".blend":
    bpy.ops.wm.open_mainfile(filepath=str(model))
    for o in [o for o in bpy.data.objects if o.type in {"CAMERA", "LIGHT"}]:
        bpy.data.objects.remove(o)
else:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if ext in {".glb", ".gltf"}: bpy.ops.import_scene.gltf(filepath=str(model))
    elif ext == ".fbx": bpy.ops.import_scene.fbx(filepath=str(model))
    elif ext == ".obj": bpy.ops.wm.obj_import(filepath=str(model))
    else: raise SystemExit(f"Unknown format: {ext}")

scene = bpy.context.scene
meshes = [o for o in scene.objects if o.type == "MESH" and not o.hide_render]
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo = Vector(min(p[i] for p in pts) for i in range(3))
hi = Vector(max(p[i] for p in pts) for i in range(3))
center, size = (lo + hi) / 2, hi - lo
print(f"STATS objects={len(meshes)} faces={sum(len(o.data.polygons) for o in meshes)} size={tuple(round(s, 3) for s in size)}")

if clay:
    mat = bpy.data.materials.new("clay"); mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.6, 0.6, 0.6, 1); bsdf.inputs["Roughness"].default_value = 0.7
    for o in meshes:
        o.data.materials.clear(); o.data.materials.append(mat)

if project:
    # Rough colour preview: project a front reference image (with transparency) through the mesh.
    import numpy as np
    img = bpy.data.images.load(str(project))
    w, hh = img.size
    px = np.empty(w * hh * 4, dtype=np.float32); img.pixels.foreach_get(px)
    alpha = px.reshape(hh, w, 4)[:, :, 3] > 0.5
    cols, rows = np.where(alpha.any(0))[0], np.where(alpha.any(1))[0]
    u0, u1, v0, v1 = cols[0] / w, (cols[-1] + 1) / w, rows[0] / hh, (rows[-1] + 1) / hh
    mat = bpy.data.materials.new("projected"); mat.use_nodes = True
    nt = mat.node_tree; tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img; tex.extension = "EXTEND"
    bsdf = nt.nodes["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = 0.6
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    for o in meshes:
        me = o.data
        co = np.empty(len(me.vertices) * 3, dtype=np.float32); me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3) @ np.array(o.matrix_world.to_3x3()).T + np.array(o.matrix_world.translation)
        li = np.empty(len(me.loops), dtype=np.int32); me.loops.foreach_get("vertex_index", li)
        uv = np.empty((len(li), 2), dtype=np.float32)
        uv[:, 0] = u0 + (co[li, 0] - lo.x) / size.x * (u1 - u0)
        uv[:, 1] = v0 + (co[li, 2] - lo.z) / size.z * (v1 - v0)
        layer = me.uv_layers.new(name="proj") if not me.uv_layers else me.uv_layers[0]
        layer.data.foreach_set("uv", uv.ravel())
        me.materials.clear(); me.materials.append(mat)

scene.render.engine = "CYCLES"
scene.cycles.samples = 64
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "OPTIX"; prefs.get_devices()
for d in prefs.devices: d.use = d.type == "OPTIX"
scene.cycles.device = "GPU"
scene.render.film_transparent = False
scene.view_settings.view_transform = "Standard"
world = scene.world or bpy.data.worlds.new("w"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.85, 0.85, 0.85, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.35

def look_at(obj, target):
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()

h = max(size)
for name, az, energy in (("key", 35, 4), ("fill", -50, 1.5), ("rim", 160, 3)):
    light = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
    light.data.size = h; light.data.energy = energy * 60 * h * h
    a = math.radians(az)
    light.location = center + Vector((math.sin(a), -math.cos(a), 0.5)) * h * 2.5
    look_at(light, center); scene.collection.objects.link(light)

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "ORTHO"; scene.collection.objects.link(cam); scene.camera = cam

def shot(name, az, target, span, res=(1024, 1536)):
    a = math.radians(az)
    cam.location = target + Vector((math.sin(a), -math.cos(a), 0)) * h * 4
    look_at(cam, target)
    cam.data.ortho_scale = span; cam.data.clip_end = h * 20
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.filepath = str(out / f"{name}.png")
    import time; t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"RENDERTIME {name} {time.time() - t:.1f}s")

# The model must have +Z up and must look along -Y (Blender front view).
for name, az in (("front", 0), ("three_quarter", 35), ("side", 90), ("back", 180)):
    shot(name, az, center, size.z * 1.08)
head = Vector((center.x, center.y, hi.z - size.z * 0.11))
for name, az in (("head_front", 0), ("head_three_quarter", 35), ("head_side", 90)):
    shot(name, az, head, size.z * 0.3, res=(1024, 1024))
