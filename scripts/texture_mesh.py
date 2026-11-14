"""Paint a texture on an AI mesh with the Hunyuan3D-2 paint model.

The model makes views of the mesh in the style of the reference images and bakes them into one texture.
The output is one mesh with a UV map and a 2048-pixel texture.

Usage: scripts/texture_mesh.sh <mesh.glb> <out.glb> --images front.png [side.png ...] [--faces 150000] [--turbo]
"""
import argparse, time
import torch, trimesh
from PIL import Image
from hy3dgen.rembg import BackgroundRemover
import numpy as np, fast_simplification
from hy3dgen.texgen import Hunyuan3DPaintPipeline

ap = argparse.ArgumentParser()
ap.add_argument("mesh"); ap.add_argument("out")
ap.add_argument("--images", nargs="+", required=True)
ap.add_argument("--faces", type=int, default=150000)
ap.add_argument("--turbo", action="store_true")
ap.add_argument("--offload", action="store_true")
args = ap.parse_args()

imgs = []; remover = None
for p in args.images:
    im = Image.open(p)
    if not (im.mode == "RGBA" and im.getextrema()[3][0] < 255):
        remover = remover or BackgroundRemover(); im = remover(im.convert("RGB"))
    imgs.append(im.convert("RGBA"))
mesh = trimesh.load(args.mesh, force="mesh")
t = time.time()
parts = mesh.split(only_watertight=False)                       # keep the large pieces only
big = max(len(p.faces) for p in parts)
mesh = trimesh.util.concatenate([p for p in parts if len(p.faces) > 0.02 * big])
if len(mesh.faces) > args.faces:
    v, f = fast_simplification.simplify(np.asarray(mesh.vertices), np.asarray(mesh.faces), target_count=args.faces)
    mesh = trimesh.Trimesh(v, f, process=True)
print(f"mesh ready: faces={len(mesh.faces)} seconds={time.time() - t:.0f}")
pipe = Hunyuan3DPaintPipeline.from_pretrained("tencent/Hunyuan3D-2", subfolder="hunyuan3d-paint-v2-0-turbo" if args.turbo else "hunyuan3d-paint-v2-0")
if args.offload: pipe.enable_model_cpu_offload()
t = time.time()
mesh = pipe(mesh, image=imgs)
mesh.export(args.out)
print(f"WROTE {args.out} seconds={time.time() - t:.0f} peak VRAM={torch.cuda.max_memory_allocated() / 2**30:.1f} GB")
