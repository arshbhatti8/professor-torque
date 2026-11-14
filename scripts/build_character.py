"""Assemble Professor Torque from the labelled head mesh and the labelled body mesh.

Usage: scripts/blender.sh --python scripts/build_character.py -- <head.glb> <body.glb> <out.blend>
"""
import bpy, bmesh, sys, numpy as np
from pathlib import Path
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
head_path, body_path, out_path = (str(Path(a).resolve()) for a in argv[:3])
LABELS = ["DROP", "TURBAN", "PATKA", "SKIN", "BROW", "FRAME", "LENS", "HAIR",
          "JACKET", "TROUSERS", "SHIRT", "TIE", "POCKET", "HAND", "SHOE", "BELT"]
# Final objects, and the labels that each object contains.
PARTS = {"Collar": ["SHIRT"], "Turban": ["TURBAN"], "Patka": ["PATKA"], "Head": ["SKIN", "BROW"], "Glasses": ["FRAME"], "Lenses": ["LENS"],
         "Beard_Moustache": ["HAIR"], "Jacket": ["JACKET", "POCKET"], "Trousers": ["TROUSERS", "BELT"],
         "Shirt": ["SHIRT"], "Tie": ["TIE"], "Hands": ["HAND"], "Shoes": ["SHOE"]}

bpy.ops.wm.read_factory_settings(use_empty=True)


def import_labelled(path, name):
    bpy.ops.import_scene.gltf(filepath=path)
    obj = next(o for o in bpy.context.selected_objects if o.type == "MESH")
    bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True); bpy.context.view_layer.objects.active = obj
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in [o for o in bpy.data.objects if o.type != "MESH"]:
        bpy.data.objects.remove(o)
    obj.name = name
    me = obj.data
    attr = me.color_attributes[0]
    n = len(attr.data)
    raw = np.empty(n * 4, dtype=np.float32)
    attr.data.foreach_get("color", raw)   # the importer keeps the file values as linear values
    raw = raw.reshape(-1, 4)
    print("ATTR", name, attr.name, attr.data_type, attr.domain, "alpha range", raw[:, 3].min(), raw[:, 3].max())
    if attr.domain == "CORNER":
        li = np.empty(len(me.loops), dtype=np.int32); me.loops.foreach_get("vertex_index", li)
        per_vert = np.zeros((len(me.vertices), 4), dtype=np.float32); per_vert[li] = raw; raw = per_vert
    label = np.clip(np.rint((raw[:, 3] * 255 - 15) / 15), 0, len(LABELS) - 1).astype(np.int32)
    srgb = raw[:, :3]
    lin = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
    me.color_attributes.remove(attr)
    alb = me.color_attributes.new("albedo", "FLOAT_COLOR", "POINT")
    alb.data.foreach_set("color", np.concatenate([lin, np.ones((len(lin), 1))], axis=1).astype(np.float32).ravel())
    me.color_attributes.active_color = alb; me.color_attributes.render_color_index = 0
    la = me.attributes.new("part", "INT", "POINT"); la.data.foreach_set("value", label)
    return obj, label


def coords(obj):
    co = np.empty(len(obj.data.vertices) * 3, dtype=np.float32); obj.data.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


head, hl = import_labelled(head_path, "HeadSource")
body, bl = import_labelled(body_path, "BodySource")
hc, bc = coords(head), coords(body)

# Scale the body to the character height. The top of the turban is the top of the body mesh.
HEIGHT = 1.88
s = HEIGHT / (bc[:, 2].max() - bc[:, 2].min())
body.matrix_world = Matrix.Translation((0, 0, -bc[:, 2].min() * s)) @ Matrix.Scale(s, 4)
bpy.context.view_layer.objects.active = body; bpy.ops.object.select_all(action="DESELECT"); body.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bc = coords(body)

# Align the head mesh to the head of the body mesh: use the turban width and the head height.
bt = bc[bc[:, 2] > HEIGHT * (1 - 0.10)]                     # turban of the body mesh
ht = hc[hl == LABELS.index("TURBAN")]
hz0, hz1 = hc[:, 2].min(), hc[:, 2].max()
s_w = (bt[:, 0].max() - bt[:, 0].min()) / (ht[:, 0].max() - ht[:, 0].min())
s_h = (0.172 * HEIGHT) / (0.71 * (hz1 - hz0))               # turban top to beard tip, from the references
s = s_h
print(f"HEAD SCALE width={s_w:.4f} height={s_h:.4f} used={s:.4f}")
src = Vector(((ht[:, 0].max() + ht[:, 0].min()) / 2, (ht[:, 1].max() + ht[:, 1].min()) / 2, hz1))
dst = Vector(((bt[:, 0].max() + bt[:, 0].min()) / 2, (bt[:, 1].max() + bt[:, 1].min()) / 2, HEIGHT))
head.matrix_world = Matrix.Translation(dst) @ Matrix.Scale(s, 4) @ Matrix.Translation(-src)
bpy.context.view_layer.objects.active = head; bpy.ops.object.select_all(action="DESELECT"); head.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def material(name):
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    nt = mat.node_tree; bsdf = nt.nodes["Principled BSDF"]
    att = nt.nodes.new("ShaderNodeVertexColor"); att.layer_name = "albedo"
    nt.links.new(att.outputs["Color"], bsdf.inputs["Base Color"])
    def setv(key, val):
        if key in bsdf.inputs: bsdf.inputs[key].default_value = val
    rough = {"Turban": 0.85, "Patka": 0.85, "Head": 0.5, "Hands": 0.5, "Glasses": 0.35, "Lenses": 0.45, "Beard_Moustache": 0.6,
             "Jacket": 0.9, "Trousers": 0.9, "Shirt": 0.75, "Collar": 0.75, "Tie": 0.5, "Shoes": 0.3}[name]
    setv("Roughness", rough)
    if name in ("Head", "Hands"):
        setv("Subsurface Weight", 0.25); setv("Subsurface Radius", (0.9, 0.4, 0.25)); setv("Subsurface Scale", 0.012)
    if name in ("Turban", "Jacket", "Trousers", "Patka"):
        setv("Sheen Weight", 0.12); setv("Sheen Roughness", 0.5)
        # Fine cloth weave as a bump.
        tex = nt.nodes.new("ShaderNodeTexNoise"); tex.inputs["Scale"].default_value = 900 if name != "Turban" else 500
        tex.inputs["Detail"].default_value = 2
        bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.12; bump.inputs["Distance"].default_value = 0.001
        nt.links.new(tex.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    if name == "Lenses":
        setv("Specular IOR Level", 0.2)
    if name == "Glasses":
        setv("Coat Weight", 0.25); setv("Coat Roughness", 0.15); setv("Specular IOR Level", 0.35)
    if name == "Shoes":
        setv("Coat Weight", 0.4); setv("Coat Roughness", 0.15)
    return mat


def split(src, labels_per_vert, keep_parts):
    """Make one object for each part from the faces with the labels of that part."""
    made = []
    me = src.data
    lv = np.empty(len(me.loops), dtype=np.int32); me.loops.foreach_get("vertex_index", lv)
    tri = lv.reshape(-1, 3)                                  # the AI meshes contain triangles only
    fl = labels_per_vert[tri]
    face_label = np.where(fl[:, 1] == fl[:, 2], fl[:, 1], fl[:, 0])   # majority label of the 3 vertices
    face_label[(fl == 0).any(1)] = 0                                  # a face that touches a deleted area goes too
    for part in keep_parts:
        ids = [LABELS.index(n) for n in PARTS[part]]
        sel = np.isin(face_label, ids)
        if not sel.any():
            print("PART", part, "EMPTY"); continue
        obj = src.copy(); obj.data = src.data.copy(); obj.name = part; obj.data.name = part
        bpy.context.scene.collection.objects.link(obj)
        bm = bmesh.new(); bm.from_mesh(obj.data)
        bmesh.ops.delete(bm, geom=[f for f, k in zip(bm.faces, sel) if not k], context="FACES")
        bm.to_mesh(obj.data); bm.free()
        obj.data.materials.clear(); obj.data.materials.append(material(part))
        obj.data.polygons.foreach_set("use_smooth", np.ones(len(obj.data.polygons), dtype=bool))
        print("PART", part, "faces", len(obj.data.polygons))
        made.append(obj)
    bpy.data.objects.remove(src)
    return made


for o in bpy.data.objects: o.select_set(False)
parts = split(head, hl, ["Turban", "Patka", "Head", "Glasses", "Lenses", "Beard_Moustache", "Collar"])
parts += split(body, bl, ["Jacket", "Trousers", "Shirt", "Tie", "Hands", "Shoes"])
col = bpy.data.collections.new("Professor_Torque"); bpy.context.scene.collection.children.link(col)
for o in parts:
    for c in o.users_collection: c.objects.unlink(o)
    col.objects.link(o)
bpy.ops.wm.save_as_mainfile(filepath=out_path)
print("SAVED", out_path)
