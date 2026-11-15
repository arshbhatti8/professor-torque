# TinyTorque: Professor Torque 3D Character Handoff

Welcome, Claude. This archive contains the complete technical foundation, canonical artwork, anatomical base meshes, previous failed attempts, and forensic audits for creating the authoritative 3D character model of **Professor Torque** for TinyTorque.

---

## 1. What is TinyTorque?
TinyTorque is a high-production-value automotive engineering storytelling studio. The channel produces hyper-realistic educational videos focusing on miniature automotive mechanics, luxury die-cast engineering (e.g., Rolls-Royce Cullinan 1:8 scale models), tactile ASMR soundscapes, and mechanical explainer animations.

## 2. Who is Professor Torque?
Professor Torque is the human soul of TinyTorque: a Sikh master mechanic and engineering mentor. He explains complex internal combustion mechanics, planetary gearsets, and bespoke coachbuilding with warmth, contagious enthusiasm, and flawless technical authority.

## 3. What Did Previous Modeling Attempts Achieve?
Over multiple production missions, previous automated agents attempted to generate Professor Torque:
1. **Procedural Lofting (Missions 2–6):** Attempted to assemble the character using mathematical cylinders, spheres, and bezier curves. **Result: REJECTED.** Produced distorted cardboard-like figures with severe mesh tearing and a floating moustache.
2. **Blender Studio CC0 Base Mesh (Mission 8–9):** Successfully adopted the official Blender Studio CC0 stylized male base mesh (`GEO-body_male_stylized`). This provided clean quad topology, realistic human proportions, and an articulated skeleton rig. However, clothing was offset into a tight "scuba wetsuit" and the turban was a smooth cylindrical bucket. **Result: REJECTED.**
3. **Headless Sculpting Attempt (Mission 10):** Attempted to run Blender's internal sculpting operators programmatically in background mode (`blender -b`). Blender crashed with `EXCEPTION_ACCESS_VIOLATION` in its C++ undo stack, confirming that headless code cannot substitute for interactive viewport brush strokes.
4. **Cloud AI Reconstruction (Mission 11):** Tested free cloud AI image-to-3D (Tencent Hunyuan3D-2). This captured genuine 3D dastar volume, beard contours, and blazer lapels from `canonical_hero.jpg`. However, the raw output is 108,276 triangles without quad topology, depth-flattened, and unrigged. **Result: PROMISING (Visual breakthrough, but needs retopology).**

## 4. What Claude Must Create
Claude is invited to inspect this package and produce the final, definitive Professor Torque 3D character:
- **Format:** Native Blender (`.blend`) compatible with Blender 4.2+ and an exported standard `.glb` file.
- **Likeness:** Faithfully matches `01_CANONICAL_REFERENCES/Canonical_Hero/canonical_hero.jpg` (SHA-256: `7AC72FBAB620A5ECA7195A4D7B6E277C9D13E8F807B8F6844F2ECB8A730C6F3A`).
- **Turban (Dastar):** Authentic Sikh dastar with realistic diagonal wraps (*larhs*), front tension crest, and black under-cap (*patka*).
- **Face:** Expressive, warm, intelligent adult Sikh male; curled handlebar moustache rooted in facial hair; trimmed beard with volume; thin-framed glasses with visible eyes.
- **Attire:** Tailored olive wool suit blazer with distinct notch lapels and pocket square; cream collared shirt; navy tie; tailored trousers; brown dress shoes.
- **Topology:** Clean, manifold quad-dominant edge loops suitable for facial blendshapes and body deformation (using the CC0 base mesh in folder `02` as the anatomical foundation).
- **Rigging:** Animation-ready armature rig with 5-finger hand controls.

## 5. Recommended Architecture for Claude
Rather than trying to generate a character from scratch procedurally:
1. Start with the clean quad base mesh (`02_CC0_BASE_MESH/Extracted_Base_Mesh/human_base_meshes_bundle.blend`).
2. Use the Hunyuan3D-2 3D geometry (`03_PREVIOUS_3D_MODELS/Final_Model_Attempts/professor_torque_hunyuan3d2_mesh.blend`) as a reference mold / sculpt volume for the turban, beard, and jacket lapels.
3. Generate clean Python scripts that perform vertex displacement, shrinkwrap snapping, or procedural mesh modeling with verified quad topology.

---

### Folder Navigation Guide
- `00_START_HERE/`: Project overview, character specification, asset manifest, and checksums.
- `01_CANONICAL_REFERENCES/`: Mandatory visual authority images, pose sheets, and landmarks.
- `02_CC0_BASE_MESH/`: Blender Studio CC0 anatomical base meshes and experimental staging files.
- `03_PREVIOUS_3D_MODELS/`: All previous `.blend` and `.glb` models across all project phases.
- `04_VISUAL_EVIDENCE/`: Render comparisons, failed attempts, and turnaround sheets.
- `05_TECHNICAL_REPORTS/`: Full technical audits and failure investigation reports.
- `06_LICENSING_AND_TECHNICAL_NOTES/`: CC0 licensing terms, Blender 4.2 specifications, and known limitations.
