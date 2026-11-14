"""Export the clean character to GLB.

The shirt mask of the jacket goes into the vertex colours, because GLB cannot hold the mask nodes.
Large AI parts get a Decimate modifier for a smaller file.

Usage: scripts/blender.sh <file.blend> --python scripts/v2_export_glb.py -- <out.glb> [ratio]
"""
import bpy, sys, numpy as np
from pathlib import Path
argv = sys.argv[sys.argv.index("--") + 1:]
out = str(Path(argv[0]).resolve()); ratio = float(argv[1]) if len(argv) > 1 else 0.3
j = bpy.data.objects["Jacket"]; me = j.data; n = len(me.vertices)
mask = np.empty(n, dtype=np.float32); me.attributes["shirt"].data.foreach_get("value", mask)
col = np.empty(n * 4, dtype=np.float32); me.color_attributes["albedo"].data.foreach_get("color", col); col = col.reshape(-1, 4)
t = np.clip((mask - 0.47) / 0.06, 0, 1)[:, None]
white = np.array([0.871, 0.855, 0.823, 1.0], dtype=np.float32)          # linear value of the shirt colour #F1EFEA
me.color_attributes["albedo"].data.foreach_set("color", (col * (1 - t) + white * t).ravel())
nt = j.material_slots[0].material.node_tree; bs = nt.nodes["Principled BSDF"]
vc = next(nd for nd in nt.nodes if nd.type == "VERTEX_COLOR")
nt.links.new(vc.outputs["Color"], bs.inputs["Base Color"])
bpy.data.materials["Hair"].node_tree.nodes["Principled BSDF"].inputs["Sheen Weight"].default_value = 0.0
bpy.ops.object.select_all(action="DESELECT")
total = 0; dg = bpy.context.evaluated_depsgraph_get()
for o in bpy.data.collections["Professor_Torque"].objects:
    if o.type != "MESH": continue
    if len(o.data.polygons) > 20000 and o.name != "Jacket" and not any(m.type == "SUBSURF" for m in o.modifiers):   # the jacket keeps all vertices for a clean shirt edge
        m = o.modifiers.new("Decimate", "DECIMATE"); m.ratio = ratio
    o.select_set(True)
dg = bpy.context.evaluated_depsgraph_get()
for o in bpy.context.selected_objects: total += len(o.evaluated_get(dg).data.polygons)
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", use_selection=True, export_apply=True,
                          export_vertex_color="ACTIVE", export_all_vertex_colors=True, export_yup=True)
print("EXPORTED", out, "faces", total)
