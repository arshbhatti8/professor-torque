"""Print the Blender version, the Cycles GPU devices, and the add-ons that the pipeline needs."""
import bpy, addon_utils
print("BLENDER", bpy.app.version_string)
prefs = bpy.context.preferences.addons["cycles"].preferences
for t in ("OPTIX", "CUDA"):
    try:
        prefs.compute_device_type = t
        prefs.get_devices()
        print(t, [(d.name, d.type) for d in prefs.devices])
    except Exception as e:
        print(t, "ERR", e)
mods = {m.__name__ for m in addon_utils.modules()}
for a in ("rigify", "io_scene_gltf2", "io_scene_fbx"):
    print("ADDON", a, any(a in m for m in mods))
