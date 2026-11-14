"""Make a 3D mesh from reference views with Hunyuan3D-2.

One view (--front only) uses the single-view model.
Two or more views use the multi-view model (front, left, back).
The output is a dense, fused mesh. Use it as a shape source only.
"""
import argparse, time
from pathlib import Path

import torch
from PIL import Image
from hy3dgen.rembg import BackgroundRemover
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline

ap = argparse.ArgumentParser()
ap.add_argument("--front", required=True)
ap.add_argument("--left")
ap.add_argument("--back")
ap.add_argument("--out", required=True, help="Output folder")
ap.add_argument("--name", default="candidate")
ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4])
ap.add_argument("--steps", type=int, default=50)
ap.add_argument("--octree", type=int, default=380)
args = ap.parse_args()

remover = None
def load(path):
    """Load an image. Remove the background if the image has no transparency."""
    global remover
    img = Image.open(path)
    has_alpha = img.mode == "RGBA" and img.getextrema()[3][0] < 255
    if not has_alpha:
        remover = remover or BackgroundRemover()
        img = remover(img.convert("RGB"))
    return img.convert("RGBA")

views = {k: load(v) for k, v in (("front", args.front), ("left", args.left), ("back", args.back)) if v}
out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
for k, img in views.items():
    img.save(out / f"{args.name}_input_{k}.png")

if len(views) > 1:
    repo, sub, image = "tencent/Hunyuan3D-2mv", "hunyuan3d-dit-v2-mv", views
else:
    repo, sub, image = "tencent/Hunyuan3D-2", "hunyuan3d-dit-v2-0", views["front"]
pipe = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(repo, subfolder=sub, variant="fp16")

for seed in args.seeds:
    t = time.time()
    mesh = pipe(image=image, num_inference_steps=args.steps, octree_resolution=args.octree,
                num_chunks=20000, generator=torch.manual_seed(seed), output_type="trimesh")[0]
    path = out / f"{args.name}_seed{seed}.glb"
    mesh.export(path)
    print(f"WROTE {path} faces={len(mesh.faces)} seconds={time.time() - t:.0f}")
