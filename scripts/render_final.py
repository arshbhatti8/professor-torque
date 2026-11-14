"""Render the delivery views of the character with studio light.

Usage: scripts/blender.sh <file.blend> --python scripts/render_final.py -- <output folder> [samples]
"""
import bpy, sys, math
from pathlib import Path
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
out = Path(argv[0]).resolve(); out.mkdir(parents=True, exist_ok=True)
samples = int(argv[1]) if len(argv) > 1 else 128
only = argv[2].split(",") if len(argv) > 2 else None
scene = bpy.context.scene
H = 1.88                                  # character height; the feet are at Z = 0 and the face looks along -Y

stage = bpy.data.collections.new("Stage"); scene.collection.children.link(stage)

# Backdrop: a floor that curves up into a wall.
import bmesh
bm = bmesh.new()
prof = [(-6, 0)] + [(2.5 + 1.5 * math.sin(a), 1.5 - 1.5 * math.cos(a)) for a in [i * math.pi / 2 / 16 for i in range(17)]] + [(4, 7)]
rows = [[bm.verts.new((x, y, z)) for (y, z) in prof] for x in (-9, 9)]
for i in range(len(prof) - 1):
    bm.faces.new((rows[0][i], rows[0][i + 1], rows[1][i + 1], rows[1][i]))
me = bpy.data.meshes.new("Backdrop"); bm.to_mesh(me); bm.free()
for p in me.polygons: p.use_smooth = True
bd = bpy.data.objects.new("Backdrop", me); stage.objects.link(bd)
mat = bpy.data.materials.new("Backdrop"); mat.use_nodes = True
b = mat.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (0.23, 0.30, 0.42, 1); b.inputs["Roughness"].default_value = 0.9
me.materials.append(mat)

world = scene.world or bpy.data.worlds.new("World"); scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.55, 0.62, 0.75, 1); bg.inputs[1].default_value = 0.12


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


for name, loc, size, power, colour in (
        ("Key", (-2.4, -3.2, 3.0), 2.2, 190, (1.0, 0.95, 0.88)),
        ("Fill", (3.0, -2.6, 1.6), 3.5, 60, (0.85, 0.92, 1.0)),
        ("Rim", (1.8, 2.6, 3.0), 1.5, 130, (1.0, 0.97, 0.92)),
        ("Top", (0.0, -0.4, 4.2), 2.5, 35, (1.0, 1.0, 1.0))):
    L = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
    L.data.size = size; L.data.energy = power; L.data.color = colour; L.location = loc
    look_at(L, (0, 0, H * 0.62)); stage.objects.link(L)

scene.render.engine = "CYCLES"; scene.cycles.samples = samples; scene.cycles.use_denoising = True
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "OPTIX"; prefs.get_devices()
for d in prefs.devices: d.use = d.type == "OPTIX"
scene.cycles.device = "GPU"
scene.view_settings.view_transform = "Standard"; scene.view_settings.look = "None"
scene.render.film_transparent = False

cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera")); stage.objects.link(cam); scene.camera = cam


def shot(name, az, target, dist, lens=85, res=(1200, 1800), elev=0.0):
    if only and not any(name.startswith(k) for k in only): return
    a, e = math.radians(az), math.radians(elev)
    cam.location = Vector(target) + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * dist
    look_at(cam, target); cam.data.lens = lens
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.filepath = str(out / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", name)


if len(argv) > 3:                       # save the file with the stage, the lights and the camera
    cam.location = (0, -5, H * 0.5); look_at(cam, (0, 0, H * 0.5)); cam.data.lens = 85
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(argv[3]).resolve()))
body = (0, 0, H * 0.5); head = (0, -0.02, H * 0.91)
shot("01_front", 0, body, 5.0)
shot("02_side", 90, body, 5.0)
shot("03_three_quarter", -35, body, 5.0)
shot("04_face_closeup", -12, head, 1.3, res=(1400, 1400), elev=2)
shot("05_turban_closeup", -40, (0, 0, H * 0.93), 1.15, res=(1400, 1400), elev=18)
shot("06_full_body", -22, (0, 0, H * 0.5), 4.4, lens=70, elev=4)
# Turnaround: turn the character, not the camera, so that the light and the backdrop stay the same.
pivot = bpy.data.objects.new("Turn_Pivot", None); stage.objects.link(pivot)
chars = list(bpy.data.collections["Professor_Torque"].objects)
for o in chars: o.parent = pivot
for i in range(8):
    pivot.rotation_euler = (0, 0, -math.radians(i * 45))
    shot(f"turn_{i}", 0, body, 5.0, res=(600, 1100))
