# Professor Torque — Canonical Master Character Specification (Version 2.0)

**Character Identifier:** `PROFESSOR_TORQUE`  
**Art Direction Lock:** `TINYTORQUE_STYLIZED_3D_CARTOON_V1`  
**Document Revision:** `2.0.0-PRODUCTION-READY`  
**Target Blender Project:** `assets/character/professor_torque.blend`  
**Approved Canonical Source:** [`media_1794390580256_f9a4cd8f.jpg`](file:///C:/Users/snavr/.gemini/antigravity/brain/7dd716eb-4eef-4cd2-b9af-277379063e40/.user_uploaded/media_1794390580256_f9a4cd8f.jpg)  
**Approved Facial Reference Sheet:** [`professor_torque_facial_reference_sheet_1794391395937.jpg`](file:///C:/TinyTorque-Staging/tinytorque_mvp_01/output/TT-PROFESSOR-TORQUE-REFERENCE-COMPLETION-02/references/professor_torque_facial_reference_sheet_1794391395937.jpg) (`1D70ACDF...`)  
**Approved Rigging Pose Sheet:** [`professor_torque_rigging_pose_sheet_1794391392969.jpg`](file:///C:/TinyTorque-Staging/tinytorque_mvp_01/output/TT-PROFESSOR-TORQUE-REFERENCE-COMPLETION-02/references/professor_torque_rigging_pose_sheet_1794391392969.jpg) (`6704F508...`)  

---

## 1. Character Persona & Core Identity

Professor Torque is TinyTorque's permanent presenter, guide, and master workshop mentor.
- **Personality Core:** Workshop Mentor + Automotive Enthusiast. Curious, intelligent, warm, conversational, articulate, highly animated when explaining complex mechanisms.
- **Demographic & Heritage:** Adult Sikh male engineer and master craftsman.
- **Visual Stature:** Tall, lean, distinguished adult male silhouette. Never made childlike, exaggeratedly bulky, comic-book muscular, or photorealistically gritty.
- **Stylization Principle:** Feature-film stylized 3D cartoon character (Pixar/DreamWorks clarity). Simplified anatomical planes, rounded beveled edges, expressive eyes, crisp silhouette.

---

## 2. Anatomical Scale & Proportion Specifications

| Measurement Landmark | Metric Dimension | Proportional Ratio | Notes |
|:---|:---:|:---:|:---|
| **Total Crowned Stature (Z)** | **1.92 m (192 cm)** | $6.15 : 1$ (crowned stature / head height) | Top apex of Dastar turban fold to floor contact |
| **Bare-Head Stature** | **1.85 m (185 cm)** | $7.40 : 1$ (stature / bare-head height) | Estimated cranial skull top to floor contact |
| **Head Height (Chin to Crown Apex)** | **0.312 m (31.2 cm)** | Base module | Includes Dastar crest wrap |
| **Head Height (Chin to Bare Skull)** | **0.250 m (25.0 cm)** | Base anatomical unit ($H$) | Forehead undercap to jaw bottom |
| **Shoulder Width (Acromion-to-Acromion)** | **0.415 m (41.5 cm)** | $1.66 \times H$ | Natural tailored suit shoulder line |
| **Chest Depth (A-P)** | **0.260 m (26.0 cm)** | $1.04 \times H$ | Slender athletic posture, upright thoracic spine |
| **Waist Width (Trouser Belt Line)** | **0.310 m (31.0 cm)** | $1.24 \times H$ | Slim flat-front trouser waist |
| **Crotch / Inseam Height** | **0.950 m (95.0 cm)** | **51.4%** of stature | Gives distinguished tall presenter leg silhouette |
| **Arm Span (Finger tip to tip in T-Pose)** | **1.86 m (186 cm)** | $1.005 \times$ bare stature | Balanced reach, relaxed wrists |
| **Foot Length (Shoe Soles)** | **0.285 m (28.5 cm)** | $1.14 \times H$ | Sleek Oxford/Derby shoe proportions |

---

## 3. Detailed Wardrobe & Material Specifications

All materials use Blender Principled BSDF PBR shaders:

| Element | Color Description | Hex Color | Roughness | Metallic | Subsurface | Notes |
|:---|:---|:---:|:---:|:---:|:---:|:---|
| **Skin (Face & Hands)** | Warm tan stylized cartoon | `#FBBB8F` | 0.45 | 0.00 | 0.08 | Soft SSS radius (1.0, 0.5, 0.3) for warm skin scatter |
| **Turban (Dastar)** | Deep crimson / magenta wool | `#780E2B` | 0.65 | 0.00 | 0.02 | Clean folded layered geometry, center V crest |
| **Undercap (Patka)** | Matte charcoal-black cotton | `#151515` | 0.70 | 0.00 | 0.00 | Symmetrical forehead triangle apex |
| **Beard & Moustache** | Jet black sculpted hair | `#1A1817` | 0.55 | 0.00 | 0.00 | Trimmed jawline edge, curled handlebar moustache |
| **Eyebrows** | Jet black arched hair | `#1A1817` | 0.55 | 0.00 | 0.00 | Thick stylized cartoon eyebrows |
| **Suit Jacket** | Olive green tailored wool | `#5C6348` | 0.75 | 0.00 | 0.02 | Two-button front, notched lapels, flap pockets |
| **Suit Trousers** | Matching olive green wool | `#5C6348` | 0.75 | 0.00 | 0.02 | Slim flat-front, crisp pressed creases |
| **Dress Shirt** | Crisp white woven cotton | `#F4F4F6` | 0.50 | 0.00 | 0.00 | Stiff spread collar, exposed cuffs at wrist |
| **Necktie** | Dark navy patterned silk | `#1C2541` | 0.40 | 0.00 | 0.00 | Diagonal stripes (`#D0533C` & `#EFE8D8`) sloping `\` |
| **Pocket Square** | Navy blue folded silk | `#1C2541` | 0.40 | 0.00 | 0.00 | Triangular peak seated in left breast pocket |
| **Leather Shoes** | Cognac / espresso brown | `#4A2E1B` | 0.35 | 0.00 | 0.00 | Derby lace-up, stitched welt, stacked heel |
| **Leather Belt** | Dark espresso brown | `#352013` | 0.35 | 0.00 | 0.00 | Stitched leather with brushed brass buckle |
| **Glasses Frame** | Dark charcoal acetate | `#222222` | 0.30 | 0.15 | 0.00 | Rectangular rims with straight horizontal top bar |
| **Glasses Lenses** | Clear optical glass (Alt B) | Transparent | 0.05 | 0.00 | 0.00 | Transmission 0.95, IOR 1.52, anti-reflective |
| **Wristwatch** | Brown strap + gold bezel | `#C5A059` | 0.25 | 0.85 | 0.00 | Left wrist, gold bezel, clean round dial face |
| **Eyes (Iris)** | Warm dark brown cartoon | `#3D2314` | 0.10 | 0.00 | 0.00 | Sharp pupil `#050505`, glossy corneal reflection |

---

## 4. 10-State Emotional Expression Matrix

| # | Expression State | Primary Facial Deformation | Mouth / Viseme State | Eyebrows & Eyes | Emotional Delivery |
|:---:|:---|:---|:---|:---|:---|
| 1 | `NEUTRAL` | Resting anatomical state | Closed lips, resting jaw | Relaxed natural arch | Baseline resting pose |
| 2 | `FRIENDLY_SMILE` | Zygomaticus major lift + cheek fullness | Warm closed/parted smile | Gentle lower lid crinkle, soft focus | Warm workshop welcome |
| 3 | `EXCITEMENT` | Upward jaw open + wide smile | Open happy grin, visible upper teeth | High arched brows, dilated pupils | Engineering breakthrough |
| 4 | `CURIOSITY` | Asymmetric brow lift + head tilt ($8^\circ$) | Slightly parted wry lips | Left brow raised $+30\%$, focused squint | Diagnostic investigation |
| 5 | `SURPRISE` | Brow apex peak + rounded jaw drop | Open rounded 'O' mouth shape | Widened eyes showing white above iris | Unexpected mechanism reveal |
| 6 | `SERIOUS_EXPLANATION` | Level grounded gaze + firm chin | Precise consonant articulation | Straight level brows, direct camera lock | Principle of operation |
| 7 | `THINKING` | Inner brow knit (AU4) + lateral gaze | Lightly closed lips, chin tucked | Saccade diagonal glance away then back | Analytical deduction |
| 8 | `AMUSEMENT` | Single brow cocked + subtle smirk | Handlebar moustache curled higher | Knowing twinkle, relaxed eyelid crescent | Insider enthusiast humor |
| 9 | `CONCERN` | Inner brow pinch (AU1+AU4) + soft chin | Downward lip corner relaxation | Gentle empathetic focus toward defect | Cautionary failure warning |
| 10 | `CELEBRATION` | Full radiant open grin + chest lift | Radiant open smile, teeth arc visible | High triumphant arches, happy Duchenne eyes | Test passed / engine running |

---

## 5. Lip-Sync Phoneme / Viseme Morph Targets

Standard 15-viseme mapping for speech synchronization:
1. `viseme_sil`: Resting silence (closed lips).
2. `viseme_PP`: Bilabials /p/, /b/, /m/ (pressed lips).
3. `viseme_FF`: Labiodentals /f/, /v/ (lower lip tucked to upper incisors).
4. `viseme_TH`: Dental /θ/, /ð/ (tongue tip visible between teeth).
5. `viseme_DD`: Alveolars /t/, /d/, /n/, /l/ (tongue touching palate, parted teeth).
6. `viseme_kk`: Velars /k/, /g/, /ŋ/ (open jaw, neutral tongue).
7. `viseme_CH`: Postalveolars /tʃ/, /dʒ/, /ʃ/ (funneled rounded lips).
8. `viseme_SS`: Fricatives /s/, /z/ (closely approximation of teeth, slight smile).
9. `viseme_nn`: Nasals /n/, /m/ (jaw neutral).
10. `viseme_RR`: Rhotic /r/ (puckered rounded lips).
11. `viseme_aa`: Open vowels /ɑ/, /æ/ (maximum jaw vertical drop 0.70).
12. `viseme_E`: Front vowels /e/, /ɛ/ (lateral smile stretch, medium opening).
13. `viseme_I`: Close front vowels /i/, /ɪ/ (wide lateral grin, close teeth).
14. `viseme_O`: Mid back vowels /o/, /ɔ/ (circular open lips).
15. `viseme_U`: Close back vowels /u/, /ʊ/ (tight puckered circle).

---

## 6. Rigging Skeleton & Hierarchy Specifications

```
Root (0, 0, 0)
 └── Hips (0, 0, 0.95m)
      ├── Spine (0, 0, 1.05m)
      │    └── Spine1 (0, 0, 1.20m)
      │         └── Chest (0, 0, 1.35m)
      │              ├── Neck (0, 0, 1.50m)
      │              │    └── Head (0, 0, 1.58m)
      │              │         ├── Eye.L & Eye.R (Look-at IK constraints)
      │              │         ├── Jaw (0, 0.05, 1.52m)
      │              │         ├── Moustache.L & Moustache.R
      │              │         └── Turban_Bone (stabilizer)
      │              ├── Shoulder.L (0.08, 0, 1.45m)
      │              │    └── Upper_Arm.L ──► Forearm.L ──► Hand.L ──► Thumb/Fingers
      │              └── Shoulder.R (-0.08, 0, 1.45m)
      │                   └── Upper_Arm.R ──► Forearm.R ──► Hand.R ──► Thumb/Fingers
      ├── Upper_Leg.L (0.10, 0, 0.90m) ──► Lower_Leg.L ──► Foot.L ──► Toe.L
      └── Upper_Leg.R (-0.10, 0, 0.90m) ──► Lower_Leg.R ──► Foot.R ──► Toe.R
```

---

## 7. Reusable Action & Performance Libraries

1. **`Action_Idle_Breathing` (60 frames / 2.0s loop):**
   - Spine gently expands $+0.8\text{ cm}$ vertically on frame 15, smoothly relaxes on frame 45.
   - Arms sway subtly ($\pm 0.8^\circ$).
   - Spontaneous natural blink at frame 35 ($120\text{ ms}$).
2. **`Action_Talking_Explaining` (90 frames / 3.0s loop):**
   - Right forearm raises $45^\circ$, open palm frames mechanical concept.
   - Head tilts $4^\circ$ with affirmative nod at key emphasis frames (frame 25 & 65).
   - Left hand rests grounded at hip or waist.
3. **`Action_Pointing_Upward` (60 frames / 2.0s loop):**
   - Right index finger points cleanly upward-diagonal ($45^\circ$) toward UI callout.
   - Head and eyes track along pointing vector.
