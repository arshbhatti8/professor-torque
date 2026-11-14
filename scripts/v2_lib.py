"""Shared helpers for the clean head build (stage 2)."""
import bpy, bmesh, math, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

D = bpy.data.objects


def collection():
    return bpy.data.collections["Professor_Torque"]


def new_object(name, verts, faces, smooth=True):
    old = D.get(name)
    if old: bpy.data.objects.remove(old)
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces]); me.update()
    if smooth: me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), dtype=bool))
    o = bpy.data.objects.new(name, me); collection().objects.link(o)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    return o


def eval_arrays(obj):
    """Vertex positions, normals and faces of an object with its modifiers applied."""
    dg = bpy.context.evaluated_depsgraph_get(); ev = obj.evaluated_get(dg); me = ev.to_mesh()
    n = len(me.vertices)
    P = np.empty(n * 3, dtype=np.float32); me.vertices.foreach_get("co", P)
    N = np.empty(n * 3, dtype=np.float32); me.vertices.foreach_get("normal", N)
    F = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    return P.reshape(-1, 3).astype(np.float64), N.reshape(-1, 3).astype(np.float64), F


def surface(obj):
    P, N, F = eval_arrays(obj)
    return BVHTree.FromPolygons([Vector(p) for p in P], F)


def front_hit(tree, x, z, y0=-0.5):
    """First surface point that a ray from the front meets at (x, z)."""
    hit = tree.ray_cast(Vector((x, y0, z)), Vector((0, 1, 0)))
    return (np.array(hit[0]), np.array(hit[1])) if hit[0] is not None else (None, None)


def tube(path, ra, rb, up=(0, -1, 0), seg=14, cap=True):
    """A tube along a 3D path with an elliptical section. ra: radius across, rb: radius along 'up'."""
    path = np.asarray(path, dtype=np.float64); n = len(path)
    verts, faces = [], []
    upv = np.asarray(up, dtype=np.float64)
    for i in range(n):
        t = path[min(i + 1, n - 1)] - path[max(i - 1, 0)]; t /= np.linalg.norm(t)
        b = upv - t * upv.dot(t); b /= np.linalg.norm(b)          # 'up' direction, square to the path
        a = np.cross(t, b)
        for k in range(seg):
            th = 2 * math.pi * k / seg
            verts.append(path[i] + a * ra[i] * math.cos(th) + b * rb[i] * math.sin(th))
    for i in range(n - 1):
        for k in range(seg):
            k2 = (k + 1) % seg
            faces.append((i * seg + k, i * seg + k2, (i + 1) * seg + k2, (i + 1) * seg + k))
    if cap:
        for i0 in (0, n - 1):
            c = len(verts); verts.append(path[i0])
            for k in range(seg): faces.append((c, i0 * seg + k, i0 * seg + (k + 1) % seg))
    return verts, faces


def spline(points, count):
    """Catmull-Rom curve through the points."""
    P = np.asarray(points, dtype=np.float64); P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    segs = len(P) - 3
    for j in range(count):
        u = j / (count - 1) * segs; i = min(int(u), segs - 1); t = u - i
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return np.array(out)


def principled(name, colour, rough=0.5, **extra):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True; nt = mat.node_tree
    for nd in list(nt.nodes):
        if nd.type not in ("BSDF_PRINCIPLED", "OUTPUT_MATERIAL"): nt.nodes.remove(nd)
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*colour, 1); b.inputs["Roughness"].default_value = rough
    for k, v in extra.items():
        key = k.replace("_", " ")
        if key in b.inputs: b.inputs[key].default_value = v
    return mat


def srgb(hexcode):
    c = [int(hexcode[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
