"""Give an AI mesh clean colours and part labels from the reference views.

The script projects the reference images on the mesh, sorts each vertex into a part
(turban, skin, beard, jacket, ...), and writes a GLB. The vertex colour holds the clean
part colour with soft detail from the reference. The alpha channel holds the part label.

Usage: label_mesh.py head|body <mesh.glb> <front.png> [<side.png>] <out.glb>
Run it in the Hunyuan3D-2 environment (it needs trimesh, scipy and OpenCV).
"""
import sys
import numpy as np, trimesh, cv2
from PIL import Image
from scipy import ndimage, sparse
from scipy.sparse.csgraph import connected_components

kind, mesh_path = sys.argv[1], sys.argv[2]
front_path = sys.argv[3]
side_path = sys.argv[4] if kind == "head" else None
out_path = sys.argv[-1]

# Part labels. DROP parts are deleted in Blender.
LABELS = ["DROP", "TURBAN", "PATKA", "SKIN", "BROW", "FRAME", "LENS", "HAIR",
          "JACKET", "TROUSERS", "SHIRT", "TIE", "POCKET", "HAND", "SHOE", "BELT"]
L = {n: i for i, n in enumerate(LABELS)}
hexc = lambda h: np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float32) / 255
ALBEDO = {"DROP": "#FF00FF", "TURBAN": "#8E1238", "PATKA": "#151517", "SKIN": "#E2A17A", "BROW": "#221815",
          "FRAME": "#1B1B1D", "LENS": "#101012", "HAIR": "#1F1715", "JACKET": "#5A6645", "TROUSERS": "#5A6645",
          "SHIRT": "#F1EFEA", "TIE": "#1E2A4A", "POCKET": "#1E2A4A", "HAND": "#E2A17A", "SHOE": "#6A3A1E", "BELT": "#3A2416"}
TIE_RED, TIE_CREAM = hexc("#B9523C"), hexc("#E2DBCB")

mesh = trimesh.load(mesh_path, force="mesh", process=False)
V = np.asarray(mesh.vertices, dtype=np.float64)
N = np.asarray(mesh.vertex_normals, dtype=np.float64)
# glTF axes: +Y is up, +Z is the front of the character, +X is the left of the character.
lo, hi = V.min(0), V.max(0); size = hi - lo
x = (V[:, 0] - lo[0]) / size[0]          # 0..1 across the front image, left to right
t = (hi[1] - V[:, 1]) / size[1]          # 0 at the top, 1 at the bottom
d = (V[:, 2] - lo[2]) / size[2]          # 0 at the back, 1 at the front
nf = N[:, 2]                             # > 0: the vertex looks to the front
cx = np.abs(x - 0.5)


def load_view(path):
    """Return the image colours (extended past the silhouette) and the bbox of the silhouette."""
    im = np.asarray(Image.open(path).convert("RGBA"), dtype=np.float32) / 255
    mask = im[:, :, 3] > 0.5
    ys, xs = np.where(mask.any(1))[0], np.where(mask.any(0))[0]
    box = (xs[0], ys[0], xs[-1] + 1, ys[-1] + 1)
    inner = ndimage.binary_erosion(mask, iterations=5)
    idx = ndimage.distance_transform_edt(~inner, return_distances=False, return_indices=True)
    rgb = im[:, :, :3][idx[0], idx[1]]
    return rgb, box


def sample(view, u, v):
    """Sample a view. u and v are 0..1 inside the silhouette bbox (v from the top)."""
    rgb, (x0, y0, x1, y1) = view
    px = np.clip(x0 + u * (x1 - x0), 0, rgb.shape[1] - 1).astype(int)
    py = np.clip(y0 + v * (y1 - y0), 0, rgb.shape[0] - 1).astype(int)
    return rgb[py, px]


front = load_view(front_path)
col = sample(front, x, t)
if side_path:
    side = load_view(side_path)                      # the face points to the right of this image
    w = np.clip((nf - 0.2) / 0.35, 0, 1)[:, None]    # 1: use the front view, 0: use the side view
    w = w * w * (3 - 2 * w)
    col = col * w + sample(side, d, t) * (1 - w)

hsv = cv2.cvtColor(col.reshape(-1, 1, 3).astype(np.float32), cv2.COLOR_RGB2HSV).reshape(-1, 3)
h, s, v = hsv[:, 0], hsv[:, 1], hsv[:, 2]
navy = (h > 190) & (h < 265) & (s > 0.25) & (v < 0.75)
dark = (v < 0.24) & ~navy
white = (s < 0.16) & (v > 0.62)
crimson = ((h > 315) | (h < 8)) & (s > 0.5) & ~dark
olive = (h > 55) & (h < 130) & (s > 0.12) & ~dark & ~white
warm = (h >= 8) & (h <= 45) & (s > 0.18) & ~dark
isfront = nf > 0.3

lab = np.zeros(len(V), dtype=np.int32)
tie_col = None
if kind == "head":
    lab[:] = L["SKIN"]
    lab[crimson] = L["TURBAN"]
    lab[(olive | navy) & (t > 0.6)] = L["DROP"]
    upper = dark & (t < 0.285)
    lab[upper] = L["TURBAN"]
    lab[upper & (cx < 0.085) & (t > 0.15) & (t < 0.235) & isfront] = L["PATKA"]
    hairy = dark | ((v < 0.42) & (s < 0.55) & ~navy & ~olive)        # the beard has lighter strands
    lab[dark & (t >= 0.285) & (t < 0.47)] = L["HAIR"]
    lab[hairy & (t >= 0.47) & (t < 0.74)] = L["HAIR"]
    lab[dark & (t >= 0.285) & (t < 0.345) & (cx < 0.27) & isfront] = L["BROW"]
    # Skin that the turban hides: all points at the back of the head above the neck are turban.
    lab[(lab == L["SKIN"]) & (t < 0.3) & ~((cx < 0.2) & isfront)] = L["TURBAN"]
    # Glasses: two lens areas, and the dark ring and bridge around them.
    in_l = lambda g: (t > 0.362 - g) & (t < 0.448 + g) & (((x > 0.272 - g) & (x < 0.458 + g)) | ((x > 0.542 - g) & (x < 0.732 + g)))
    front_face = isfront & (d > 0.55)
    ring = front_face & in_l(0.02) & ~in_l(0.0) & ((v < 0.55) | (t < 0.362))
    bridge = front_face & (cx < 0.05) & (t > 0.355) & (t < 0.395) & (v < 0.45)
    lab[ring | bridge] = L["FRAME"]
    lab[front_face & in_l(0.0)] = L["LENS"]
    # Shirt collar and the top of the shirt front come from the head mesh.
    collar = white & (t > 0.6) & (((t < 0.74) & (cx < 0.19)) | ((t < 0.8) & (cx < 0.1)))
    lab[collar] = L["SHIRT"]
    lab[(white & (t > 0.6) & ~collar) | (t > 0.8) | ((lab == L["SKIN"]) & (t > 0.74))] = L["DROP"]
else:
    lab[:] = np.where((t < 0.55) | (cx > 0.25), L["JACKET"], L["TROUSERS"])
    nb = nf > -0.15                                   # not a back-facing vertex
    lab[white & (t < 0.5) & nb & (cx < 0.25)] = L["SHIRT"]
    lab[white & (cx > 0.3) & (t > 0.42) & (t < 0.5)] = L["SHIRT"]      # cuffs
    lab[(s < 0.2) & (v > 0.3) & (cx < 0.1) & (t > 0.17) & (t < 0.36) & nb] = L["SHIRT"]   # shirt front in the shadow of the beard
    # Tie: the navy region at the centre of the chest in the front image, with the stripes filled.
    rgb, (x0, y0, x1, y1) = front
    hsv_i = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    navy_i = ((hsv_i[..., 0] > 190) & (hsv_i[..., 0] < 265) & (hsv_i[..., 1] > 0.25) & (hsv_i[..., 2] < 0.75)).astype(np.uint8)
    roi = np.zeros_like(navy_i)
    ra, rb = int(y0 + 0.185 * (y1 - y0)), int(y0 + 0.35 * (y1 - y0))
    ca, cb = int(x0 + 0.45 * (x1 - x0)), int(x0 + 0.55 * (x1 - x0))
    roi[ra:rb, ca:cb] = navy_i[ra:rb, ca:cb]
    roi = cv2.morphologyEx(roi, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    px = np.clip(x0 + x * (x1 - x0), 0, rgb.shape[1] - 1).astype(int)
    py = np.clip(y0 + t * (y1 - y0), 0, rgb.shape[0] - 1).astype(int)
    tie = (roi[py, px] > 0) & (nf > 0.0)
    lab[tie] = L["TIE"]
    tie_col = np.tile(hexc(ALBEDO["TIE"]), (len(V), 1))
    tie_col[warm | crimson] = TIE_RED
    tie_col[white] = TIE_CREAM
    lab[~white & ~olive & (cx > 0.33) & (t > 0.44) & (t < 0.6)] = L["HAND"]
    lab[warm & (cx > 0.3) & (t > 0.4) & (t < 0.6)] = L["HAND"]
    lab[(t > 0.928) & ~olive] = L["SHOE"]
    lab[t > 0.955] = L["SHOE"]
    # The head of the body mesh is replaced by the head mesh.
    lab[(t < 0.15) | ((t < 0.18) & (cx < 0.065))] = L["DROP"]

# Remove small islands: a vertex group smaller than the limit takes the label of its neighbours.
E = mesh.edges_unique
A = sparse.coo_matrix((np.ones(len(E)), (E[:, 0], E[:, 1])), shape=(len(V), len(V))).tocsr()
A = A + A.T
limit = 400 if kind == "head" else 150
for _ in range(3):
    same = lab[E[:, 0]] == lab[E[:, 1]]
    G = sparse.coo_matrix((np.ones(same.sum()), (E[same, 0], E[same, 1])), shape=(len(V), len(V)))
    ncomp, comp = connected_components(G, directed=False)
    small = np.bincount(comp)[comp] < limit
    if not small.any():
        break
    onehot = sparse.csr_matrix((np.where(small, 0.0, 1.0), (np.arange(len(V)), lab)), shape=(len(V), len(LABELS)))
    votes = onehot
    for _ in range(12):                                # spread the labels of the large groups
        votes = votes + A @ votes
        votes.data = np.minimum(votes.data, 1e6)
    best = np.asarray(votes.argmax(1)).ravel()
    has = np.asarray(votes.sum(1)).ravel() > 0
    lab = np.where(small & has, best, lab)

if kind == "body":      # small parts: set them after the island clean-up
    lab[navy & isfront & (x > 0.57) & (x < 0.69) & (t > 0.235) & (t < 0.305)] = L["POCKET"]
    lab[(dark | warm) & ~olive & (cx < 0.07) & (t > 0.43) & (t < 0.465) & isfront] = L["BELT"]

# Clean colour: part colour, with soft light and dark detail from the reference.
lin = np.where(col <= 0.04045, col / 12.92, ((col + 0.055) / 1.055) ** 2.4)
lum = lin @ np.array([0.2126, 0.7152, 0.0722])
out = np.zeros((len(V), 3), dtype=np.float32)
facing = np.clip((nf - 0.25) / 0.4, 0, 1) if kind == "body" else np.ones(len(V))
for name, i in L.items():
    m = lab == i
    if not m.any():
        continue
    base = np.tile(hexc(ALBEDO[name]), (m.sum(), 1))
    if name == "TIE":
        base = tie_col[m]
        out[m] = base
        continue
    if name == "LENS":
        out[m] = base
        continue
    if name == "FRAME":
        out[m] = base
        continue
    if name in ("HAIR", "BROW", "PATKA"):
        out[m] = base * np.clip((lum[m] / (np.median(lum[m]) + 1e-4)) ** 0.35, 0.85, 1.25)[:, None]
        continue
    med = np.median(lum[m]) + 1e-4
    mod = np.clip((lum[m] / med) ** 0.5, 0.6, 1.22)
    mod = 1 + (mod - 1) * facing[m]
    out[m] = np.clip(base * mod[:, None], 0, 1)

if kind == "head":
    # Make each lens a smooth, flat surface a small distance behind the front of the frame.
    for side_sel in (x < 0.5, x >= 0.5):
        m = (lab == L["LENS"]) & side_sel
        if m.sum() < 10:
            continue
        P = V[m]
        A3 = np.c_[P[:, 0], P[:, 1], np.ones(len(P))]
        coef, *_ = np.linalg.lstsq(A3, P[:, 2], rcond=None)
        plane = A3 @ coef
        V[m, 2] = plane + np.percentile(P[:, 2] - plane, 80)
    mesh.vertices = V

rgba = np.concatenate([np.clip(out * 255, 0, 255), (15 + 15 * lab)[:, None]], axis=1).astype(np.uint8)
mesh.visual = trimesh.visual.ColorVisuals(mesh, vertex_colors=rgba)
mesh.export(out_path)
print("WROTE", out_path, {n: int((lab == i).sum()) for n, i in L.items() if (lab == i).any()})
