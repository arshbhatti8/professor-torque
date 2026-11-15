# Known Limitations & Previous Failure Analysis

To ensure Claude does not repeat the mistakes of previous 3D generation attempts, this document explicitly details why every previous character model was rejected.

## 1. Turban (Dastar) Construction Failures
- **The "Bucket / Chef-Hat" Defect:** In early procedural attempts and base-mesh lathed splines, the dastar was generated as a series of stacked parametric cylinders or smooth lathed curves.
- **The Missing Anatomy:** An authentic Sikh dastar is created by hand-wrapping long cloth strips (*larhs*) diagonally across the forehead, building up layered overlapping tension folds that crest at a forward-leaning crown angle with a visible lower black under-cap (*patka*).
- **Previous Mistake:** Assuming a smooth symmetrical dome or cylinder resembles a turban. It does not. It looks like a plastic novelty hat.
- **AI Improvement:** Hunyuan3D-2 successfully captured the organic volumetric drape and crest angle from the 2D artwork.

## 2. Facial Anatomy & Uncanny Expression
- **The "Frozen Orbital Stare" Defect:** In previous models, eyes were placed as protruding spheres with extreme specular highlights, causing a wide-eyed, artificial mannequin stare.
- **Missing Warmth:** Professor Torque is a genial, intelligent workshop mentor and teacher. His canonical face features crinkling smile lines around the eyes, gentle cheek fullness, and friendly crow's feet.
- **Moustache Floating Geometry:** Previous models created the curled handlebar moustache as a floating mathematical bezier spline hovering in empty space 2cm in front of the upper lip. It was not rooted in the philtrum and had no connection to the beard.
- **Beard Volume:** The beard was previously modeled as a razor-thin surface shell hugging the jaw without volumetric tufting or organic chin mass.

## 3. Tailored Clothing & Suit Drape
- **The "Cardboard Cylinder Clipping" Defect:** Initial models lofted stiff cylinders around the legs and torso. When posed, the thighs and crotch clipped severely through the trouser geometry, creating giant gaping black holes.
- **The "Scuba Wetsuit" Defect:** In Mission 9, surface offsetting was used to eliminate clipping. While this stopped intersections, it produced skin-tight fabric that completely traced the underlying anatomy—looking like a painted-on green neoprene diving suit rather than a tailored 100% British wool blazer.
- **What is Required:** A real suit jacket has structured shoulder pads, separate folded notch lapels with depth, breast pocket with a cream handkerchief, natural gravity folds around the button closure, and tailored straight-leg trousers breaking over leather shoes.

## 4. Animation & Topology Readiness
- **Procedural Models:** Contained non-manifold disconnected shells, un-welded vertices, and zero deformation edge loops.
- **AI Reconstruction (Hunyuan3D-2):** Although capturing superior surface relief, it is 100% triangulated octree geometry (108,276 triangles, 0 quads). Attempting to skin-weight or bone-deform this raw scan causes catastrophic vertex pinching and volume tearing.
- **The Verified Solution:** The CC0 Base Mesh (`GEO-body_male_stylized`) in folder `02_CC0_BASE_MESH/Extracted_Base_Mesh` possesses clean quad edge loops and articulated 5-finger hands. Clothing and accessories must either be modeled cleanly on top of this base mesh or retopologized to match its quad topology.
