# Blender Technical Environment Specification

## System Information
- OS: Microsoft Windows 11 Home Single Language (64-bit, Build 26100)
- Local 3D Engine: Blender 4.2.3 LTS (Official Release, 64-bit)
- Embedded Python: Python 3.11.7 (inside Blender runtime)
- Executable Location: C:\TinyTorque-Staging\tools\blender\blender.exe

## Execution Context & Headless Limitations
1. In background mode (`blender -b`), Blender's 3D Viewport context (`bpy.context.area`, `bpy.context.region`, `bpy.context.space_data`) is `None`.
2. Interactive Sculpt Mode operators (`bpy.ops.sculpt.mesh_filter`, `bpy.ops.sculpt.brush_stroke`) crash with `EXCEPTION_ACCESS_VIOLATION` in `ED_undosys_stack_memfile_id_changed_tag` when executed headless without an OpenGL/Vulkan display window manager.
3. Modeling and retopology must be performed using BMesh API, mesh modifier stacks, geometric transformation scripts, or by generating assets that can be inspected directly in the Blender 4.2.3 GUI.
