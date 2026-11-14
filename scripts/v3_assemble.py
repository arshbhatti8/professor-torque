"""Version 3: join the textured AI head (bust) to the textured AI body.

The body keeps all parts below the shirt collar. The bust keeps the head, the neck and the shirt collar.
The two meshes overlap at the collar, where the shirt is white on both.

Usage: scripts/blender.sh --python scripts/v3_assemble.py -- <head.glb> <body.glb> <out.blend>
"""
import bpy, bmesh, sys, numpy as np
from pathlib import Path
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
head_path, body_path, out_path = (str(Path(a).resolve()) for a in argv[:3])
opt = {a.split("=")[0]: float(a.split("=")[1]) for a in argv[3:] if "=" in a}
HEIGHT = 1.88
bpy.ops.wm.read_factory_settings(use_empty=True)


def load(path, name):
    bpy.ops.import_scene.gltf(filepath=path)
    obj = next(o for o in bpy.context.selected_objects if o.type == "MESH")
    bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True); bpy.context.view_layer.objects.active = obj
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM"); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in [o for o in bpy.data.objects if o.type != "MESH"]: bpy.data.objects.remove(o)
    obj.name = name; obj.data.name = name
    return obj


def co(o):
    a = np.empty(len(o.data.vertices) * 3, dtype=np.float32); o.data.vertices.foreach_get("co", a); return a.reshape(-1, 3).astype(np.float64)


def apply(o, M):
    o.matrix_world = M; bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def delete(o, drop):
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[v for v, k in zip(bm.verts, drop) if k], context="VERTS"); bm.to_mesh(o.data); bm.free()


head, body = load(head_path, "Head"), load(body_path, "Body")
bc = co(body); s = HEIGHT / (bc[:, 2].max() - bc[:, 2].min())
apply(body, Matrix.Translation((-(bc[:, 0].min() + bc[:, 0].max()) / 2 * s, 0, -bc[:, 2].min() * s)) @ Matrix.Scale(s, 4)); bc = co(body)
hc = co(head); hz0, hz1 = hc[:, 2].min(), hc[:, 2].max()
s = (0.172 * HEIGHT) / (0.71 * (hz1 - hz0)) * opt.get("--head_scale", 1.0)
bt = bc[bc[:, 2] > HEIGHT * 0.93]; ht = hc[hc[:, 2] > hz1 - 0.2 * (hz1 - hz0)]
src = Vector(((ht[:, 0].max() + ht[:, 0].min()) / 2, (ht[:, 1].max() + ht[:, 1].min()) / 2, hz1))
dst = Vector(((bt[:, 0].max() + bt[:, 0].min()) / 2, (bt[:, 1].max() + bt[:, 1].min()) / 2 + opt.get("--head_dy", 0.0), HEIGHT + opt.get("--head_dz", 0.0)))
apply(head, Matrix.Translation(dst) @ Matrix.Scale(s, 4) @ Matrix.Translation(-src)); hc = co(head)
print("turban width: body", round(bt[:, 0].max() - bt[:, 0].min(), 3), "head", round(float(np.ptp(hc[hc[:, 2] > 1.75][:, 0])), 3))
for z0 in (1.50, 1.53, 1.56, 1.59, 1.62):
    for nm, c in (("head", hc), ("body", bc)):
        sl = c[np.abs(c[:, 2] - z0) < 0.004]
        if len(sl): print(f"slice {nm} z={z0}: x {sl[:,0].min():.3f}..{sl[:,0].max():.3f} y {sl[:,1].min():.3f}..{sl[:,1].max():.3f}")

# Cut surfaces. The plane is low at the front (under the beard) and high at the back (shirt collar).
Z0, SLOPE = opt.get("--cut_z", 1.552), opt.get("--cut_slope", 0.17)
plane = lambda c: Z0 + (c[:, 1] + 0.13) * SLOPE
neck = hc[np.abs(hc[:, 2] - (Z0 + 0.06)) < 0.006]
NX, NY = (neck[:, 0].min() + neck[:, 0].max()) / 2, neck[:, 1].max() - opt.get("--neck_back", 0.066)     # the back of the neck is clear; the beard hides the front
R = opt.get("--collar_r", 0.074)
print("neck centre", round(NX, 3), round(NY, 3))
def bisect(o, z_at_front, keep_above):
    """Cut the mesh with the tilted plane. This gives a clean, straight edge."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, -0.13, z_at_front), plane_no=Vector((0, -SLOPE, 1)).normalized(),
                           clear_outer=not keep_above, clear_inner=keep_above)
    bm.to_mesh(o.data); bm.free()


BODY_DROP, OVERLAP = opt.get("--body_drop", 0.012), opt.get("--overlap", 0.035)
bisect(body, Z0 - BODY_DROP, keep_above=False)
# Close the open top of the body with a flat olive cap, so that no dark hole shows beside the collar.
cap_mat = bpy.data.materials.new("Jacket_Inner"); cap_mat.use_nodes = True
cb = cap_mat.node_tree.nodes["Principled BSDF"]; cb.inputs["Base Color"].default_value = (0.075, 0.105, 0.045, 1); cb.inputs["Roughness"].default_value = 0.85
body.data.materials.append(cap_mat)
bm = bmesh.new(); bm.from_mesh(body.data)
# Use only the edges on the cut plane. The mesh has other open edges at its texture seams, and these must stay.
pn = Vector((0, -SLOPE, 1)).normalized(); pc = Vector((0, -0.13, Z0 - BODY_DROP))
on_cut = lambda v: abs((v.co - pc).dot(pn)) < 1e-4
rim_v = [v for v in bm.verts if on_cut(v)]
bmesh.ops.remove_doubles(bm, verts=rim_v, dist=1e-5)             # join the double seam vertices on the rim to one loop
rim_e = [e for e in bm.edges if e.is_boundary and on_cut(e.verts[0]) and on_cut(e.verts[1])]
res = bmesh.ops.triangle_fill(bm, edges=rim_e, use_beauty=True)
new_faces = [g for g in res["geom"] if isinstance(g, bmesh.types.BMFace)]
for f in new_faces: f.material_index = len(body.data.materials) - 1
print("body top closed with", len(new_faces), "cap faces")
bm.to_mesh(body.data); bm.free()
bisect(head, Z0 - OVERLAP, keep_above=True); hc = co(head)
# Near the cut, keep only the neck column: round at the back, open to the front for the beard.
dyb = np.clip((hc[:, 1] - NY) / (R * opt.get("--back", 0.82)), 0, None)
inside = ((hc[:, 0] - NX) / R) ** 2 + dyb ** 2 < 1
keep = (hc[:, 2] > plane(hc) + opt.get("--free", 0.06)) | inside
delete(head, ~keep)

# Set the full height to the character height again (the head moved up for the neck).
top = max(co(head)[:, 2].max(), co(body)[:, 2].max())
for o in (head, body): apply(o, Matrix.Scale(HEIGHT / top, 4))
col = bpy.data.collections.new("Professor_Torque"); bpy.context.scene.collection.children.link(col)
for o in (head, body):
    for c in o.users_collection: c.objects.unlink(o)
    col.objects.link(o)
    o.data.polygons.foreach_set("use_smooth", np.ones(len(o.data.polygons), dtype=bool))
    for sl in o.material_slots:
        b = sl.material.node_tree.nodes.get("Principled BSDF")
        if b: b.inputs["Roughness"].default_value = 0.7; b.inputs["Metallic"].default_value = 0.0
    print("PART", o.name, "faces", len(o.data.polygons), "uv", len(o.data.uv_layers))
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=out_path)
print("SAVED", out_path)
