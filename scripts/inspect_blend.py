"""Print the objects of a .blend file: type, vertices, faces, modifiers, size, armature bones."""
import bpy, sys
print("FILE", bpy.data.filepath.split("\\")[-1], "saved with", bpy.data.version)
for o in sorted(bpy.data.objects, key=lambda o: o.name):
    d = o.dimensions
    line = f"  {o.type:9} {o.name[:44]:44} dim=({d.x:.2f},{d.y:.2f},{d.z:.2f})"
    if o.type == "MESH":
        m = o.data
        quads = sum(1 for p in m.polygons if len(p.vertices) == 4)
        line += f" v={len(m.vertices)} f={len(m.polygons)} quads={quads} uv={len(m.uv_layers)} sk={len(m.shape_keys.key_blocks) if m.shape_keys else 0} vg={len(o.vertex_groups)} mods={[x.type for x in o.modifiers]}"
    if o.type == "ARMATURE": line += f" bones={len(o.data.bones)}"
    print(line)
print("  collections:", [c.name for c in bpy.data.collections][:40])
