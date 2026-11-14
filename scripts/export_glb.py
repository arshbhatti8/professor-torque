"""Export the character collection to GLB. Large parts get a Decimate modifier for a smaller file.

Usage: scripts/blender.sh <file.blend> --python scripts/export_glb.py -- <out.glb> [ratio]
"""
import bpy, sys
from pathlib import Path
argv = sys.argv[sys.argv.index("--") + 1:]
out = str(Path(argv[0]).resolve()); ratio = float(argv[1]) if len(argv) > 1 else 0.3
bpy.ops.object.select_all(action="DESELECT")
total = 0
for o in bpy.data.collections["Professor_Torque"].objects:
    if len(o.data.polygons) > 20000:
        m = o.modifiers.new("Decimate", "DECIMATE"); m.ratio = ratio
    o.select_set(True)
    total += len(o.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.polygons)
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", use_selection=True, export_apply=True,
                          export_vertex_color="ACTIVE", export_all_vertex_colors=True, export_yup=True)
print("EXPORTED", out, "faces", total)
