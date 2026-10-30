# CAD_TEST2 — freestanding guided knife sharpener

**Prototype CAD, revision A.** Mostly printed construction; standard metric fasteners and one off-the-shelf Ø8 × 500 mm precision shaft. No custom machined parts. Designed for your **60 × 180 × 30 mm double-sided 600/1500 stone**, blades up to **300 mm cutting length**, and **1–6 mm thickness at the clamp**. The printed angle scale covers **15–25° per side**. This is a mechanically checked CAD prototype, **not a physically printed or load-tested product**.

![Assembly at the 20 degree reference position](assembly_preview.png)

## Files

- [`sharpener_assembly.step`](sharpener_assembly.step): named, assembled components at the 20° reference setting, including printed bodies, stone, representative blade, guide rod and standard hardware envelopes.
- [`parts/`](parts/): separate STEP files for each printed component and `REF_` purchased/reference components. Each component keeps its assembly coordinates. Use your slicer's lay-flat and arrange tools before printing.
- `parts/OPTION_shim_for_1mm_blade.step` through `...6mm...`: alternative **lower** jaw spacers. Print one matching your blade, not all six. The assembly contains the 3 mm option.
- [`hardware/`](hardware/): individual standard fastener envelope STEP files; quantities in [`cad/hardware_manifest.json`](cad/hardware_manifest.json). Threads, exact head details and commercial pin-retention details are simplified.
- [`cad/generate.py`](cad/generate.py): editable CadQuery geometry source, in millimetres.
- [`cad/validate.py`](cad/validate.py), [`cad/validation.json`](cad/validation.json): exported-STEP checks and their results. No finite element analysis or physical testing is implied.

## How it works

The knife stays clamped with its edge facing the front. The stone rides on an 8 mm steel guide rod. A printed sliding bushing pivots on two trunnions, while the supporting fork swivels about a vertical M8 bolt. The rod can slide, pitch and yaw. Moving the rear carriage vertically changes the sharpening angle.

The knife rotates about a fore-and-aft axle **300 mm above the bottom of the base**. This height leaves nominal clearance for a centered 300 mm blade during a flip. The half-turn disc has a semicircular stop slot and a fixed M5 stop screw. A **separate removable 5 mm locking pin** engages one of two opposite holes. Withdraw only the locking pin to turn the knife; leave the stop screw installed. The stops give nominal 180° travel; printed tolerances cause some play. The locking pin, rather than friction alone, retains either working position.

The base is **300 × 310 mm**, with a 32 mm-deep ballast body and 6 mm lid. The assembled tower reaches **510 mm**. The tower splits into two lower legs and an upper portal, connected with rear splice plates. Fill the approximately **1.97 litre** reservoir with bagged dry sand or standard steel washers; aim for **at least 3 kg of ballast**. Use a rubber mat or stick-on rubber feet. Keep grit and slurry out of the bearings and ballast.

## Purchased parts and supplies

Use corrosion-resistant hardware where practical. Ordinary stainless fasteners are fine; choose a straight, smooth, ground steel or stainless guide shaft. Cutting threaded stock to length is not required: the axle is a standard bolt, and the pedestal tie rods can be purchased as 300 mm lengths.

| Item | Quantity | Purpose |
|---|---:|---|
| Ø8 × 500 mm precision shaft, smooth | 1 | Sliding stone guide; do not use threaded rod here |
| M10 × 100 hex bolt, preferably fully threaded | 1 | Knife-holder axle reinforcement and disc retention |
| M10 nut + flat washer | 1 each | Front axle retention |
| M5 × 300 threaded stud/rod | 4 | Tie the tall axle pedestals to the lid |
| M5 × 40 hex/socket bolts | 4 | Lid to ballast base |
| M5 × 25 bolts | 2 | Stop bridge to lid |
| M5 × 50 bolts | 4 | Pitch cheeks to yaw plate |
| M5 × 35 bolts | 2 | Stone-carrier split rod clamps |
| M5 × 20 bolts | 2 | Stone end-pad adjusters |
| M5 × 30 bolts | 2 | Upper-jaw rear jack screws |
| M5 × 40 partially threaded bolt + jam nut | 1 each | Permanent half-turn stop; smooth shank through disc slot |
| Ø5 removable clevis/quick-release pin, ≥28 mm usable engagement | 1 | Locks the flip disc; fit a tether and suitable retaining clip |
| M6 × 30 bolts | 4 | Tower feet |
| M6 × 35 bolts | 2 | Knife-clamp screws |
| M6 × 45 bolts | 10 | Eight tower splice screws, two height locks |
| M8 × 30 bolt + M8 nut | 1 each | Vertical yaw pivot |
| M4 × 12 bolts, preferably nylon-tip | 4 | Lateral stone retention; lightly tightened |
| M4 × 40 bolts + M4 nuts | 4 each | Removable stone corner keepers |
| M4 × 10 set screws | 2 | Guide-rod stop collars |
| M5 nuts | 25 total | 24 main-assembly nuts plus stop-screw jam nut |
| M6 nuts | 16 | Feet, splice plates, carriage and knife clamp |
| M5 washers | 4 minimum | Pedestal tie-rod top nuts |
| M6 washers | 4 minimum | Two height locks, two knife-clamp nuts |
| M8 washers | 2 | Yaw pivot adjustment |
| Thin resilient sheet / tape | As needed | Stone backing, end pads and non-marring knife protection |
| Rubber mat or stick-on feet, ≥5 mm high | As needed | Grip and clearance below base fasteners |
| Bagged dry sand or standard steel washers | ≥3 kg | Freestanding ballast |

Additional ordinary washers and locknuts are useful for adjustment. Washer stacks may require the next standard bolt length; verify engagement during dry assembly. The STEP hardware catalog omits threads and some small washers/retainers. The M5 stop screw and removable pin have simplified reference envelopes in the main assembly.

## Printing

Use **PETG** for the wet stone carrier, jaw spacers, bushing and collars. PETG or **ASA** is suitable for the structure. PLA is suitable for a fit-check prototype, but avoid relying on it for permanently stressed clamp parts. Do not anneal or shrink parts without rechecking all fits.

Start with 0.2 mm layers, 5–6 walls, 6 top/bottom layers and 40–50% infill. Use locally solid regions around fastener holes and journals; 60–80% infill is appropriate for the jaws, carriage and gimbal cheeks. These are starting settings, not a certified strength specification. Use broad washers and hand tightening to avoid crushing printed material.

Use the **325 × 320 × 325 mm printer** for the base, lid, upper tower, lower tower legs, carriage, pedestals and stone carrier. The **300 × 310 mm** base and lid require enough usable bed area after skirt/brim settings. Disable a large brim or orient appropriately; do not scale the model. Smaller clamp, disc, gimbal, splice and collar parts fit the 180 mm printer after reorientation.

Lay the base open side up and the lid flat. Lay tower pieces with their broad faces down. Lay the upper jaw on a side so its thin nose is supported. Orient the rotor so its axle and jaw junction have continuous layers where possible; support the journal and hex tail as needed. Print the sliding bushing with its rod bore vertical, and inspect/clean it before running the steel shaft through it. Reorient the carrier onto its flat roof face with suitable supports for the end and side rails. Slicer-generated supports may be needed; the STEP exports are solids, not pre-supported print files.

Nominal fits: 20 mm printed axle in 20.6 mm pedestal bores; 10 mm trunnions in 10.4 mm holes; 8 mm rod in 8.4 mm sliding bushing and 8.3 mm carrier clamps; 5 mm locking pin in 5.2 mm holes. Printer calibration matters. Deburr and hand-ream only enough to obtain smooth motion. Print and check a bushing/collar first. Do not force-fit the steel rod or use abrasive slurry as a lubricant.

The **4.2 mm pilot holes** in the upper jaw and permanent-stop bridge must be **tapped M5**. Tap the **3.3 mm pilots** in the carrier side rails and rod collars **M4**. Tapping printed parts is an assembly operation; use light torque and replace worn parts. Other fastener holes are clearance holes. The base and stone-end-wall hex pockets accept ordinary M5 nuts, with nominal clearance.

## Assembly instructions

### 1. Base and supporting structure

1. Dry-fit every component before filling the base. Remove supports, burrs and strings; confirm the rod and all pivots move freely.
2. Insert four M5 nuts into the underside hex pockets of `01_ballast_base`. Add rubber feet or a mat with enough clearance for screw ends. Keep the base sitting on rubber, not protruding screws.
3. With the lid still separate, install the two `03_pedestal` blocks at Y=20 and Y=60. Use four M5 × 300 tie rods through the long vertical holes and the lid, with nuts below the lid and nuts/washers above the blocks. The two 20.6 mm bores must be coaxial and turn freely around the rotor journal. Snug the tie rods evenly; do not bow the lid.
4. Bolt both `08a_tower_lower` legs to the rear lid holes with four M6 × 30 bolts and nuts under the lid. Attach `08b_tower_upper` using the two `08c_tower_splice` plates behind the tower and eight M6 × 45 bolts. The split is at Z=240 mm. Tighten the splices square, keeping the angle scale facing forward.
5. Bolt `07_stop_bridge` behind the axle pedestals using two M5 × 25 bolts and nuts below the lid. Its horizontal pin holes are at Z=300 mm. Leave it loose for alignment until the rotor is installed.
6. Confirm all underside nuts are accessible and tight before closing the base. Put the ballast into sealed bags, keep the rim and screw holes clear, and install the lid with four M5 × 40 bolts. Do not fill with loose water or cement. Recheck stability after the complete device is assembled.

### 2. Knife rotor and 180° indexing

1. Slide the round journal of `04_rotor_lower_jaw` through both pedestals, with the jaws facing forward and the hex tail behind the rear pedestal. If needed, loosen the pedestal mounting hardware for alignment, then retighten.
2. Fit `06_half_turn_disc` over the hex tail. With the jaw horizontal, the two small locking holes should be at 3 and 9 o'clock and the semicircular slot above the axle. The hex key transmits rotation; the axle bolt retains the stack.
3. Insert the M10 × 100 bolt from the back through the disc and rotor. Fit the M10 washer and nut in the front central recess. Tighten enough to retain the disc without deforming it. Do **not** clamp the stationary pedestals between rotating nuts; the printed rotor journal turns in their bores. Confirm it cannot withdraw and has minimal axial play.
4. Tap the bridge's rightmost small hole M5. Fit the partially threaded M5 × 40 stop screw through the disc's arc and into that hole. Leave its head clear of the moving disc; lock its depth with a jam nut behind the bridge. Its smooth shank must span the disc slot. The screw must not clamp the disc against the bridge.
5. Fit the removable 5 mm locking pin through the bridge hole at X=15 and the aligned disc hole. Tether the pin. Fully withdraw it from the disc before flipping. The permanent stop screw stays installed and restricts rotation to the half-turn slot. Reinsert the locking pin after every flip.
6. With no blade or stone installed, cycle the rotor by hand. Confirm two horizontal locked positions, no binding, and positive contact at both stop ends. Exact 180° indexing depends on print/reaming tolerances; measure the two jaw planes and correct fit before sharpening.

### 3. Knife jaws and blade centering

1. Place the appropriate `OPTION_shim_for_Nmm_blade` on the lower jaw's front clamping shelf. The 3 mm version is already shown in the assembly. The spacer thickness is **8 − N/2 mm**. It locates the blade midplane at Z=300 mm for equal angles after flipping.
2. Use thin non-marring tape on the knife or jaws. Account for its thickness in the spacer height; thick rubber causes angle drift. For an in-between thickness, use accurately measured thin packing under the lower spacer or adjust a copy of the parametric spacer. Match the **actual thickness at the clamp**, not a thicker bolster.
3. Place the blade with its spine behind the nose of the jaws, its cutting edge facing forward. The reference blade edge is at **Y=−70 mm**, 170 mm from the guide pivot. The CAD shows a 45 mm-wide blade, with approximately 17 mm engaged by the jaw. Center a 300 mm blade along X; do not place its whole length to one side of the clamp.
4. Install `05_upper_jaw`, the two M6 × 35 clamp bolts at Y=−16, and washers/nuts underneath. Tap and install the two rear M5 jack screws at Y=0. Their tips bear on the solid lower jaw. Adjust their height so tightening the clamp bolts loads the front noses onto the blade instead of bending the whole upper jaw. Use the jack-screw nuts as jam nuts.
5. Tighten alternately by hand and test grip using a blunt dummy blade first. The thin front jaws must stay clear of the stone at the selected angle. A narrow blade, thick blade or different protrusion may need a different setting or jaw geometry; do not assume every 1–6 mm knife can use 15° with arbitrary protrusion. Keep at least **26 mm of edge-to-jaw-nose distance** for the nominal low-angle layout, then check actual clearance.
6. Cover the edge while checking rotation. Remove the stone/guide assembly before flipping. Check the entire blade **and handle** sweep by hand. The CAD flip sweep includes a centered 300 mm blade plus a 100 mm handle extending from one end, with about 12 mm minimum nominal clearance over the lid. Larger handles and offset clamping can reduce clearance. Blade-length capacity does not guarantee clearance for every handle.

### 4. Adjustable guide pivot

1. Fit `09_height_carriage` in front of the tower, shelf toward the knife and index mark beside the right-hand scale. Use two M6 × 45 bolts through the carriage and tower slots, with wide washers/nuts behind the tower. Loosen only enough to slide; support the stone before adjusting.
2. Attach `10_yaw_plate` on top of the projecting shelf with the M8 × 30 bolt, washers and nut. Add a washer below the shelf to set the bolt tip below the sliding bushing. Adjust to allow yaw without wobble. Use a locknut or jam arrangement; this pivot must move freely and must not unscrew in use.
3. Set `12_sliding_pitch_bushing` between the two `11_pitch_cheek` parts. Its printed trunnions seat in their 10.4 mm bores. Bolt the cheeks to the yaw plate using four M5 × 50 bolts and nuts underneath. Install the cheeks around the bushing; do not spread a finished rigid fork to snap it in.
4. Confirm independent pitch and yaw motion. The bushing should rotate freely but should not rock markedly. Its bore must remain clear of the M8 bolt tip. Do not add a long bolt that projects into the rod path.

### 5. Stone carrier and sliding rod

1. Put approximately **2 mm of firm resilient backing** between the top face of the 30 mm-thick stone and the underside of the carrier roof. This puts the abrasive working face 44 mm below the rod axis. The roof covers the unused face. Four removable corner keepers overlap the outermost 2 mm of the lower face at the stone corners; the central sharpening area stays clear.
2. Add thin protective pads against the fixed end and `14_floating_end_pad`. Fit the floating pad at the adjustable end with its blind screw sockets facing outward. Insert two M5 nuts into the end-wall hex pockets, then fit the M5 × 20 adjuster bolts. Their ends push the floating pad. Tighten evenly and only enough to retain the stone; brittle stones can crack under screw pressure.
3. Install the four `17_stone_keeper` parts under the side rails using M4 × 40 bolts upward from below and nuts on top. Their small ledges positively support the stone at its lower corners; the side screws alone must not support the stone's weight. The keepers are removable to let the stone load from below. Then tap the side rails M4 and install four M4 × 12 screws with protective tips/pads. These center the 60 mm stone in the 68 mm channel and restrain sideways movement. They should just contact the pads, not visibly indent the stone. Shake-test the carrier **over a padded surface**, away from any knife. It must retain the wet stone without relying on adhesive alone.
4. Slide the Ø8 × 500 shaft through both carrier collars, with most excess length extending toward the rear pivot. Tighten the two M5 × 35 cross-clamp bolts and nuts. The shaft is fixed to the stone carrier and slides through the pivot bushing.
5. Pass the rod through the sliding bushing and install the two `15_rod_stop` collars immediately before and after the sliding bushing. Tap their radial holes M4 and fit the M4 set screws. Use only enough torque to secure them. At the calibrated central contact position, leave **25 mm of free travel** between each collar's nearest face and its corresponding bushing face, then tighten the set screws. Reset these gaps whenever the sharpening angle or blade position changes. Check that the rod cannot pull out and the stone holder cannot hit the guide structure. The modeled guide-motion checks use **±25 mm** carrier travel; do not increase it without checking clearances. The collars are travel stops, not handles.
6. To change from 600 to 1500 grit, remove the stone/rod assembly, remove the four corner keepers, loosen the side and end adjusters, turn the stone over, reinstall all four keepers, reseat the backing and pads, and retighten. The knife remains locked in its holder. Check retention and recalibrate after changing faces, flattening or replacing the stone.

## Setting the sharpening angle

All angles are **per side**, relative to the blade midplane. A nominal 20° setting gives approximately 40° included bevel angle when both sides are sharpened equally.

The scale is marked every 1°, with numerals at 15°, 20° and 25°. Align the carriage index line with a tick, and secure both height-lock bolts. It is a **reference scale**, not a universal angle measurement: it assumes a horizontal blade midplane at Z=300 mm, edge at Y=−70 mm, pivot at Y=100 mm, and stone-face-to-rod-axis offset of 44 mm. The stone thickness, backing, blade protrusion and blade centering all matter.

The reference pitch-axis height is:

```text
H = 300 + 170 × tan(angle) + 44 / cos(angle)   [mm from base bottom]
```

The carriage index/locking-bolt centers are 20 mm below H. The full reference-height table is in `cad/validation.json`.

**Calibrate before sharpening:** lock a blunt flat test blade, establish its midplane as the zero reference with an external digital angle gauge or bevel gauge, and rest the stone lightly at the center of the intended edge. Measure the inclination of the stone's broad face, or the straight guide rod parallel to that face. Adjust carriage height to the desired angle, lock it, and remeasure. Flip the blade and verify the same angle on the other side. Adjust lower-jaw packing to correct blade centering rather than compensating each side with a different scale reading. A marker on the existing bevel is useful for confirming where the abrasive actually contacts.

A fixed rear pivot introduces angle variation when following a long or curved edge. Yawing the rod changes the effective angle relative to a straight blade even if the carriage stays fixed. The CAD checks allow ±35° yaw for reach, **not a claim of constant bevel angle along a 300 mm knife**. Work in sections, check contact with a marker, and reposition the knife/recalibrate as needed for consistent bevels. A true constant-angle linear-traverse system would be a separate mechanism.

## First-use checks and limitations

- Start with a blunt dummy blade and a dry, empty carrier. Verify both locked positions and full handle clearance before installing the stone.
- Add the ballast and rubber footing before using the heavy stone. Use light hand pressure; check that the base cannot slide or lift. No maximum sharpening load has been certified.
- Retract/remove the stone assembly, support the knife, withdraw the locking pin, rotate gently to the other stop, then reinsert the locking pin completely. Never rotate the knife under the stone or force a stop.
- Check the entire abrasive stroke for jaw/end-pad contact. Stop before a stone end or printed rail can hit the edge. Do not run the bushing into a collar at speed.
- Rinse slurry from the wet parts, dry the steel hardware, inspect the clamp noses and pivots, and replace cracked or creeping prints. Hand-tighten; printed threads and journals are wear items.

## Regenerating and checking CAD

The files were generated with **Python 3.12 and CadQuery 2.7.0**. From this directory, in an environment with CadQuery installed:

```sh
python cad/generate.py
python cad/validate.py
python cad/render.py  # optional preview; requires matplotlib
```

The validation reimports the STEP files, checks body validity, checks nominal assembly interferences, sweeps representative guide settings, checks flip positions with the stone removed, and verifies printed bounding boxes against the larger printer. Tapped pilot/fastener overlap is intentionally excluded. Standard fastener threads, structural strength, printed fits, water sealing, dynamic stability and all possible knives are not validated by these checks. Read `cad/validation.json` for the actual completed results.
