# Professor Torque 3D character

This project makes the production 3D model of Professor Torque for TinyTorque.

## Folders

| Folder | Contents |
|---|---|
| `inputs/canonical/` | The approved canonical image. This image is the visual authority. |
| `inputs/reference_sheets/` | The accepted reference sheets (front, side, back, head). |
| `inputs/base_mesh/` | The CC0 human base mesh. |
| `inputs/previous_attempts/` | The earlier `.blend` and `.glb` files and their renders. |
| `inputs/failure_reports/` | The earlier failure reports. |
| `work/references/` | Prepared references (background removed, cropped). |
| `work/ai_candidates/` | Meshes from the image-to-3D model. Git ignores this folder. |
| `work/blend/` | Blender files in work. |
| `renders/` | Renders for review and for delivery. |
| `output/` | `professor_torque_final.blend` and `professor_torque_final.glb`. |
| `scripts/` | Blender scripts and generation scripts. |
| `tools/blender/` | Blender 4.5.10 LTS (portable). Git ignores this folder. |

## Tools

- **Blender 4.5.10 LTS.** To open the interface, start `tools\blender\blender-launcher.exe` in Windows.
- **Blender without a window (WSL).** Run `scripts/blender.sh --python scripts/check_blender.py`.
- **Hunyuan3D-2 (image-to-3D).** The location is `~/tools/Hunyuan3D-2` in WSL, with its environment in `.venv`.
  Run `scripts/generate_mesh.sh` to make a mesh from reference views.

## Tool roles

- Hunyuan3D-2 makes real geometry, but the mesh is dense and fused. Use it as a shape source only.
- Blender makes the final geometry, the UV maps, the rig, the renders, and the exports.
- Image models make flat references only.

## Clean head build (version 2)

Run these commands in sequence to rebuild version 2 from the first assembled character (`output/v1_archive/`).

1. `scripts/blender.sh output/v1_archive/professor_torque_final.blend --python scripts/v2_fit_head.py -- work/v2/base_head.blend work/blend/torque_v8_s1.blend` fits the CC0 stylized head to the AI head shape.
2. `scripts/blender.sh work/blend/torque_v8_s1.blend --python scripts/v2_build_parts.py -- work/blend/torque_v8_s2.blend` builds the eyes, eyebrows, glasses, beard, moustache, collar, tie and textures.
3. `scripts/blender.sh work/blend/torque_v8_s2.blend --python scripts/render_final.py -- renders/final 160 0,turn output/professor_torque_final.blend` renders the views and saves the final file.
4. `scripts/blender.sh output/professor_torque_final.blend --python scripts/v2_export_glb.py -- output/professor_torque_final.glb` exports the GLB file.

`scripts/v2_preview_head.py` renders a quick three-view sheet of the head for checks.

## Painted AI model with rig (version 4, current)

This version uses the local Hunyuan3D-2 paint model for real textures. Run the commands in sequence.

1. `scripts/generate_mesh.sh --front work/references/head_front_tinted.png --left work/ai_candidates/gateA/head_mvR_input_left.png --out work/v4 --name head_hi --seeds 1 --octree 512` makes the head mesh.
2. `scripts/texture_mesh.sh <mesh.glb> <out.glb> --images <reference.png>` paints a mesh. Use it for the head (`--faces 300000`) and for the body.
3. `~/tools/Hunyuan3D-2/.venv/bin/python scripts/colour_match.py <in.glb> <out.glb>` corrects the colours (`--turban --gain` for the head).
   Then `~/tools/Hunyuan3D-2/.venv/bin/python scripts/clean_texture.py <body_in.glb> <body_out.glb>` removes the dots from the suit texture.
4. `scripts/blender.sh --python scripts/v3_assemble.py -- <head.glb> <body.glb> work/blend/torque_v10_a.blend --head_scale=1.12 --head_dz=0.03 --cut_z=1.535 --collar_r=0.084 --back=1.05` joins the head to the body.
5. `scripts/blender.sh work/blend/torque_v10_a.blend --python scripts/v4_parts.py -- work/v4/base_hand.blend work/blend/torque_v10_b.blend` adds the CC0 hands with nails, the shirt cuffs, the modelled collar, and the striped tie with its knot.
   Then `scripts/blender.sh <parts.blend> --python scripts/v5_face.py -- <face.blend>` adds the eyes behind the lenses and the mouth that can open. Use its output as the input of the rig step.
6. `scripts/blender.sh work/blend/torque_v10_b.blend --python scripts/v4_rig.py -- work/blend/torque_v10_c.blend --pose=1` adds the rig with IK controls for the hands and the feet, and saves a test pose.
7. `scripts/blender.sh work/blend/torque_v10_c.blend --python scripts/render_final.py -- renders/final 160 0,turn output/professor_torque_final.blend` renders the views and saves the final file.
8. `scripts/blender.sh output/professor_torque_final.blend --python scripts/v4_export_glb.py -- output/professor_torque_final.glb` exports the rigged GLB.

The paint model needs the CUDA compiler in `~/tools/cuda124` only for the first build of its extensions.

## Repository contents

- `output/` holds the final model: `professor_torque_final.blend` and `professor_torque_final.glb` (with the rig), and the textures.
- `renders/final/` holds the final pictures.
- `inputs/` holds the canonical image and the reference sheets.
- `assets/` holds the two small CC0 base meshes that the build uses: `base_head.blend` and `base_hand.blend`. The build commands read them from `work/v2/` and `work/v4/`, so copy them there first.
- `scripts/` holds all build scripts.

The folders `tools/` and `work/`, the earlier versions, and the handoff package are not in the repository, because they are large.

## Credits and licences

- The hand and head base meshes come from the Blender Studio Human Base Meshes bundle (CC0).
- The head and body meshes and their textures were generated with Tencent Hunyuan3D-2 from the reference sheets. The Hunyuan3D-2 community licence applies to the use of that model.
