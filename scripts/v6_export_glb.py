"""Export the animated character to GLB: meshes, textures, armature, skin weights, shape keys and the animation.

The GLB exporter cannot apply modifiers on meshes with shape keys. So this script applies the subdivision,
solidify and bevel modifiers by hand on the meshes without shape keys, and then exports without 'apply modifiers'.
The stage (backdrop, lights and camera) is not exported.

Usage: scripts/blender.sh <animated.blend> --python scripts/v6_export_glb.py -- <out.glb>
"""
import bpy, sys
from pathlib import Path
out = str(Path(sys.argv[sys.argv.index("--") + 1]).resolve())
objs = [o for o in bpy.data.collections["Professor_Torque"].objects]
bpy.context.scene.frame_set(1)
rig = bpy.data.objects["Rig"]; rig.data.pose_position = "REST"; bpy.context.view_layer.update()
for o in objs:
    if o.type != "MESH" or o.data.shape_keys: continue
    bpy.ops.object.select_all(action="DESELECT"); o.hide_set(False); o.select_set(True); bpy.context.view_layer.objects.active = o
    for m in [m for m in o.modifiers if m.type in ("SUBSURF", "SOLIDIFY", "BEVEL")]:
        if m.type == "SUBSURF": m.levels = max(m.levels, 1)
        try: bpy.ops.object.modifier_apply(modifier=m.name)
        except RuntimeError as e: print("could not apply", o.name, m.name, e)
rig.data.pose_position = "POSE"
bpy.ops.object.select_all(action="DESELECT")
for o in objs: o.hide_set(False); o.select_set(True)
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", use_selection=True, export_apply=False, export_yup=True, export_skins=True,
                          export_morph=True, export_animations=True, export_animation_mode="ACTIONS", export_frame_range=True,
                          export_force_sampling=True, export_optimize_animation_size=True)
print("EXPORTED", out)
