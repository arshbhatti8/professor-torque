"""Export the character with its rig to GLB (meshes, textures, armature and skin weights).

Usage: scripts/blender.sh <file.blend> --python scripts/v4_export_glb.py -- <out.glb>
"""
import bpy, sys
from pathlib import Path
out = str(Path(sys.argv[sys.argv.index("--") + 1]).resolve())
bpy.ops.object.select_all(action="DESELECT")
for o in bpy.data.collections["Professor_Torque"].objects:
    o.hide_set(False); o.select_set(True)
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", use_selection=True, export_apply=True, export_yup=True, export_skins=True, export_animations=False)
print("EXPORTED", out)
