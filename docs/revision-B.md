# Revision B changes and prototype acceptance

Revision B is a compact, bench-mounted redesign. It replaces revision A rather than providing drop-in parts. Use the matching generated BOM, assembly, print files and validation report for the selected stone profile.

| Review finding | Revision B response |
|---|---|
| Hex joint could rotate despite the indexing pin | Removed rotating hex joint; round/relieved metal-pin registration with planar face preload |
| M10 head did not positively retain the disc | Removed axle/disc stack; two draw screws positively retain the cartridge |
| Rotor axial spacing was uncontrolled | Removed rotary bearing/thrust stack; cartridge seats against a broad fixed face |
| Narrow lower-jaw/journal root | Broad jaw body and registration flange; widened clamping ears keep hardware outside the cassette path |
| Large base, ballast and tall structure | Ribbed 200 × 240 bench base, open 300 mm frame and 150 mm knife datum |
| Loose printed sliding bore | Separate replaceable nominal 8.1 ID / 12 OD / 40 mm sleeve, captive-nut split clamp and fit coupon |
| Difficult stone changes | Fixed corner supports and a two-screw removable end gate |
| Repeated adjustment used printed threads | Captive metal nuts and split shaft/stop clamps |
| Height adjustment was awkward | Offset fine-height screw plus independent side clamps |
| Incomplete purchase list | Generated purchase BOM and matching hardware instance manifest |
| Sparse validation and unrepeatable report fields | Actual export/provenance report and packaging that rejects changed inputs |
| Long-edge angle variation and wider-yaw interference | Positive M4 yaw lock at 0°, protrusion gauge and short-section repositioning procedure; no continuous constant-angle claim |

The design deliberately selects a bench-mounted architecture. Thin-wall ballast-box changes are unnecessary because that box is removed. A smaller abrasive profile is optional; the original 60 × 180 × 30 mm stone remains supported. A long transverse guide has not been added because it conflicts with the chosen compact envelope. Source parameters allow further work, but their existence does not validate an arbitrary new configuration.

## What CAD validation means

Use the `status`, actual completed counts, source hashes and limitations in the generated report. A successful report only covers the listed nominal geometry and sampled cases. Smooth fastener envelopes do not simulate threads, tightening, preload or friction. Dimensional clearances do not predict the assembled jig's loaded accuracy. The supplied STL orientations do not constitute tested slicing profiles.

The configuration reports 15–25° per-side reference settings and collar-limited stroke. **Supported working yaw is 0° only**, fixed by the positive M4 bolt through the shelf and plate. Removing that bolt does not enable a validated free-yaw mode. Follow long or curved edges by removing the stone head, repositioning/reclamping short sections to the 28 mm protrusion datum, and checking actual contact/angle in both cartridge orientations. This is not a continuous constant-angle traverse.

## Physical acceptance record

None of the following physical checks has been completed by the CAD generation process. Record the actual printer, filament, print orientation, layer profile, finishing operations, purchased component dimensions, measurement method and results. Select acceptance limits and intended working force before testing; this document does not invent a certified load rating.

1. **Small fit coupons.** Check actual dowels, shaft and sleeve fits before the large prints. Record the measured bore and pin diameters, free sliding, rocking and any finishing. Verify that the cartridge is removable without force and seats on its full mating face.
2. **Unloaded assembly and access.** Assemble with a blunt dummy blade and empty cassette. Confirm each nut can be inserted and held with ordinary tools, all screw heads seat flat, and mounting screw heads permit the base to sit flat. Exercise the height screw and lock the side clamps. Lock the height-screw jam-nut pairs with spanners before sliding the keyed knob over the upper pair. Confirm the pairs stay fixed to the screw, the positive yaw-lock bolt prevents rotation and the lightly tightened dowel-retaining screws prevent either locating pin pulling out. Verify no fastener end enters the guide sleeve or rod path.
3. **Bench mounting.** Mount to a rigid surface using two appropriate clamps or a securely bolted board. Apply the intended working forces using a blunt specimen, checking base movement, frame deflection, bench flex and clamp slippage. Repeat with a wet assembly. Do not use the jig freestanding.
4. **Cartridge retention and repeatability.** Fit a blunt blade and draw both faces fully together. Measure the blade plane and end heights. Remove, invert away from the fixture, reseat and remeasure over repeated cycles. Apply alternating forces at the blade ends and check rocking, permanent movement and loss of clamp tension. Record side-to-side angular differences rather than assuming exact 180° registration from the CAD.
5. **Blade grip and centering.** Test representative 1–6 mm blunt coupons with the universal upper jaw, corresponding centering shim and protection. Verify no slip under the intended forces and that both inverted orientations remain centered. Check the thin nose and the lowest intended sharpening angle. Real knives with tapers, bolsters or a different protrusion require their own fit check.
6. **Wet-stone retention.** Over a padded surface, fit the wet stone, all pads and the secured gate. Confirm the ledges carry its weight, the side screws do not point-load it, and controlled handling cannot slide or drop it. For a grit change, back off all four padded side adjusters before removing the gate or sliding the stone; preserve and refit the pads. Repeat the retention check after a grit change and after pad compression. Test away from a knife.
7. **Stroke and clearances.** With a blunt blade and yaw positively locked at 0°, slowly check all intended angles and collar-limited stroke. Confirm continuous rod engagement and clearance of the jaws, gate, pads, frame and hardware. Do not increase the modeled stroke or remove the yaw lock to follow an edge. Reposition/reclamp a short knife section instead; an alternative guide path requires new design and validation.
8. **Loaded sharpening-angle drift.** Establish the blade plane with a gauge. Measure abrasive inclination before and during the intended light working force, after locking the carriage, and in both cartridge orientations. Check the change along a representative edge and use a marker to inspect contact. Record the actual load and angular change.
9. **Wear and wet-service repeat check.** Inspect thin noses, sleeve, pin bores, nut traps, clamped plastic and frame after repeated cycles and wet/dry exposure. Look for creep, cracking, lost preload, grit damage and corrosion. Replace worn parts and repeat the relevant checks before continuing.

Use light, controlled handling during development. If a coupon, stone, cartridge or mounting shifts, stop and correct the fit or structure; additional tightening is not evidence of adequate strength. No maximum sharpening force, service life or certified accuracy is specified until supported by physical results.
