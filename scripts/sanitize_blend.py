"""Save a copy of a Blender file without absolute paths (they contain the user name of the computer).

Blender stores its own file path, the render path and the image paths in the file. This script sets relative
paths and saves the file in a neutral folder. Copy the result to the project after that.

Usage: blender -b <file.blend> --python scripts/sanitize_blend.py -- <neutral folder>/<name>.blend
"""
import bpy, sys
out = sys.argv[sys.argv.index("--") + 1]
for im in bpy.data.images:
    if im.packed_file or im.source == "FILE": im.filepath = "//textures/" + (im.name if "." in im.name else im.name + ".png"); im.filepath_raw = im.filepath
for lib in list(bpy.data.libraries): bpy.data.libraries.remove(lib)
for sc in bpy.data.scenes: sc.render.filepath = "//render/"
bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=out, relative_remap=False, compress=False)
print("SANITIZED", out)
