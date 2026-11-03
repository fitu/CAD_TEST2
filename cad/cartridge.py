"""Revision B removable knife cartridge and stationary bench dock.

The cartridge is withdrawn from the two metal dowels and inverted away from the
fixture.  It deliberately has no rotating journal, loose hex coupling or axle
bolt.  Coordinates are assembled millimetres; no files are written on import.
"""
import math

import cadquery as cq


def _box(x, y, z, center):
    return cq.Workplane("XY").box(x, y, z).translate(center)


def _cylinder(radius, length, start, axis="z"):
    shape = cq.Workplane("XY").circle(radius).extrude(length)
    if axis == "y":
        shape = shape.rotate((0, 0, 0), (1, 0, 0), -90)
    return shape.translate(start)


def _through(shape, radius, length, start, axis="z"):
    return shape.cut(_cylinder(radius, length, start, axis))


def _hex_prism(af, length, start, axis="z"):
    shape = cq.Workplane("XY").polygon(6, af / math.cos(math.pi / 6)).extrude(length)
    if axis == "y":
        shape = shape.rotate((0, 0, 0), (1, 0, 0), -90)
    return shape.translate(start)


def shim_shape(cfg, thickness):
    """One selected spacer centers a measured 1–6 mm blade about the datum."""
    if not 1 <= thickness <= 6:
        raise ValueError("Blade thickness must be between 1 and 6 mm")
    height = 3.5 - thickness / 2
    return _box(122, 16, height, (0, -34, cfg.knife_z - 3.5 + height / 2))


def build_cartridge(cfg):
    z = cfg.knife_z
    t = cfg.blade_thickness
    if not 1 <= t <= 6:
        raise ValueError("Blade thickness must be between 1 and 6 mm")
    parts, hardware = [], []

    def add(name, shape, group, role, printed=True, print_rotation=None):
        if len(shape.solids().vals()) != 1 or not shape.val().isValid():
            raise ValueError(f"Invalid cartridge component: {name}")
        part = dict(name=name, shape=shape, printed=printed, group=group, role=role)
        if print_rotation:
            part["print_rotation"] = {"axis": print_rotation[0], "angle": print_rotation[1]}
        parts.append(part)

    def hw(kind, m, length, position, direction, role, group="cartridge", **extra):
        hardware.append(dict(kind=kind, m=m, length=length, position=list(position),
                             direction=direction, group=group, role=role, **extra))

    # A braced stationary dock.  Its datum is the planar front face at Y=26.
    dock = _box(112, 46, 8, (0, 49, 14))
    dock = dock.union(_box(100, 24, 44, (0, 38, z)))
    dock = dock.cut(_box(40, 28, 30, (0, 38, z)))
    for x in (-42, 42):
        dock = dock.union(_box(18, 24, z - 30 - 18 + 8,
                              (x, 38, (18 + z - 22) / 2)))
        brace = (cq.Workplane("YZ")
                 .polyline([(50, 18), (72, 18), (50, z - 22)])
                 .close().extrude(18).translate((x - 9, 0, 0)))
        dock = dock.union(brace)

    mount_holes = []
    for x in (-44, 44):
        for y in (40, 60):
            dock = _through(dock, 2.75, 18, (x, y, 8))
            dock = dock.cut(_hex_prism(8.4, 4.4, (x, y, 18)))
            # Columns and rear braces rise over the feet: accessible side
            # pockets are essential, rather than hiding nuts in solid ribs.
            dock = dock.cut(_box(12, 10, 4.4, (x + (6 if x > 0 else -6), y, 20.2)))
            mount_holes.append(dict(position=[x, y, 10], m=5,
                                    bolt_head_z=3.25, head_counterbore_radius=4.9,
                                    head_counterbore_depth=3.3))
            hw("bolt", 5, 20, (x, y, 3.25), "z", "dock_mount_bolt", "fixed_dock")
            hw("nut", 5, 0, (x, y, 18), "z", "dock_mount_nut", "fixed_dock")

    # Two equal pins and one round/one relieved bore avoid four-pin binding.
    # Inverting the cartridge swaps which pin enters the relieved bore.
    pin_positions = [[-28, 14, z], [28, 14, z]]
    for x in (-28, 28):
        dock = _through(dock, 3.0, 20, (x, 24, z), "y")
        # A pin must stay in the dock when the cartridge is withdrawn.
        # Radial screws bear on the dowels through metal nuts: the printed
        # bore fit alone is not relied on for retention. The rear entry slot
        # preserves a roof over each nut to react the screw's upward load.
        dock = _through(dock, 2.2, 22, (x, 38, z + 2))
        dock = dock.cut(_hex_prism(7.4, 3.8, (x, 38, z + 13)))
        dock = dock.cut(_box(8.2, 13, 3.8, (x, 44.5, z + 14.9)))
        hw("dowel", 6, 30, (x, 14, z), "y", "registration_dowel", "fixed_dock",
           purchase_name="ground_dowel_6x30")
        hw("set_screw", 4, 16, (x, 38, z + 19), "-z",
           "registration_pin_retaining_screw", "fixed_dock")
        hw("nut", 4, 0, (x, 38, z + 13), "z",
           "registration_pin_captive_nut", "fixed_dock")

    # Nut traps open at the back for assembly. Draw screws preload the broad
    # mating face instead of asking the locating pins to provide retention.
    for x in (-43, 43):
        dock = _through(dock, 2.75, 28, (x, 24, z), "y")
        dock = dock.cut(_hex_prism(8.4, 4.3, (x, 45.8, z), "y"))
        hw("bolt", 5, 40, (x, 14.8, z), "y", "cartridge_draw_bolt", "draw_screws")
        hw("washer", 5, 0, (x, 14.8, z), "y", "cartridge_draw_washer", "draw_screws")
        hw("nut", 5, 0, (x, 46, z), "y", "cartridge_draw_nut", "fixed_dock")
    add("03_fixed_cartridge_dock", dock, "fixed_dock", "ribbed stationary registration dock")

    # Both seats must clear the stone.  The lower nose is only 3 mm thick;
    # after inversion it stays below the 15 degree abrasive plane. The body
    # deepens behind the blade to a broad, full-width root, not a round neck.
    body = _box(100, 10, 38, (0, 21, z))
    lower = (cq.Workplane("YZ")
             .polyline([(-42, z - 3.5), (-26, z - 3.5), (-16, z - 8),
                        (16, z - 8), (16, z - 19), (-16, z - 10),
                        (-26, z - 6.5), (-42, z - 6.5)])
             .close().extrude(124).translate((-62, 0, 0)))
    body = body.union(lower)
    # Outboard ears keep clamp and jack hardware outside the 80 mm cassette
    # envelope at the positively locked working yaw of zero degrees.
    for x in (-52, 52):
        body = body.union(_box(18, 20, 7, (x, -16, z - 6.5)))
        body = body.union(_cylinder(4, 1.2, (x, 0, z - 8)))
    body = _through(body, 3.05, 16, (-28, 12, z), "y")
    slot = _box(0.6, 16, 6.1, (28, 20, z))
    for x in (27.7, 28.3):
        slot = slot.union(_cylinder(3.05, 16, (x, 12, z), "y"))
    body = body.cut(slot)
    for x in (-43, 43):
        body = _through(body, 2.75, 14, (x, 14, z), "y")
    for x in (-52, 52):
        body = _through(body, 3.3, 60, (x, -16, z - 40))
        # Flat washer seats remove the local reinforcing-rib slope.
        body = body.cut(_cylinder(7, 40, (x, -16, z - 50)))
    add("04_removable_knife_cartridge", body, "cartridge",
        "full-width lower jaw and symmetric registration flange",
        print_rotation=[[1, 0, 0], 90])

    nose_bottom = z + t / 2
    upper_pad_top = nose_bottom + 7
    upper = (cq.Workplane("YZ")
             .polyline([(-42, nose_bottom), (-26, nose_bottom), (-18, nose_bottom),
                        (5, nose_bottom), (5, upper_pad_top), (-18, upper_pad_top),
                        (-26, nose_bottom + 3), (-42, nose_bottom + 3)])
             .close().extrude(124).translate((-62, 0, 0)))
    for x in (-52, 52):
        upper = _through(upper, 3.3, 40, (x, -16, z - 10))
        upper = _through(upper, 2.75, 24, (x, 0, nose_bottom - 1))
        upper = upper.cut(_hex_prism(8.4, 4.3, (x, 0, nose_bottom - 0.1)))
        # The underside opening permits nut insertion before the jaw is fitted.
        hw("bolt", 6, 30, (x, -16, upper_pad_top + 1.2), "-z", "knife_clamp_bolt")
        hw("washer", 6, 0, (x, -16, upper_pad_top), "z", "knife_clamp_top_washer")
        hw("washer", 6, 0, (x, -16, z - 11.2), "z", "knife_clamp_lower_washer")
        hw("nut", 6, 0, (x, -16, z - 16), "z", "knife_clamp_nut")
        hw("bolt", 5, 25, (x, 0, z + 18.2), "-z", "knife_jack_screw")
        hw("nut", 5, 0, (x, 0, nose_bottom), "z", "knife_jack_captive_nut")
        hw("washer", 5, 0, (x, 0, upper_pad_top), "z", "knife_jack_lock_washer")
        hw("nut", 5, 0, (x, 0, upper_pad_top + 1.2), "z", "knife_jack_lock_nut")
    add("05_upper_knife_jaw", upper, "cartridge", "thin-nose jaw with captive metal jack nuts",
        print_rotation=[[0, 1, 0], 90])
    add(f"06_blade_shim_{t:g}mm", shim_shape(cfg, t), "cartridge",
        "selected blade-centering shim")

    # Full-width taper is a defined blunt test envelope, not every real knife.
    blade = (cq.Workplane("YZ")
             .polyline([(cfg.edge_y, z), (-42, z + t / 2), (-25, z + t / 2),
                        (-25, z - t / 2), (-42, z - t / 2)])
             .close().extrude(300).translate((-150, 0, 0)))
    add("REF_blade_envelope", blade, "knife", "300 mm tapered dummy-blade envelope", False)
    add("REF_handle_envelope", _box(100, 30, 20, (200, -40, z)), "knife",
        "reference handle; cartridge is flipped away from fixture", False)

    # A separate bench setup tool, deliberately absent from the operating
    # assembly. Its two inner fences are 28 mm apart; do not press a sharp
    # edge against it. Measure/mark with a protected or blunt test blade.
    gauge = _box(52, 34, 3, (0, 14, 1.5))
    gauge = gauge.union(_box(52, 3, 6, (0, -1.5, 6)))
    gauge = gauge.union(_box(52, 3, 6, (0, 29.5, 6)))
    add("SETUP_28mm_protrusion_gauge", gauge, "setup", "28 mm edge-to-nose setup gauge")
    parts[-1]["installed"] = False

    metadata = {
        "name": "removable_indexed_cartridge",
        "datum_y": 26.0,
        "knife_midplane_z": z,
        "nose_y": -42.0,
        "edge_y": cfg.edge_y,
        "edge_to_nose_mm": -42.0 - cfg.edge_y,
        "blade_thickness_mm": t,
        "lower_shelf_z": z - 3.5,
        "shim_height_mm": 3.5 - t / 2,
        "shim_width_mm": 122.0,
        "blade_profile": "linear taper from edge Y=-70 to full thickness at Y=-42; flat grip from -42 to -25",
        "mount_holes": mount_holes,
        "locating_pins": [{"position": p, "diameter_mm": 6.0, "length_mm": 30,
                           "projection_mm": 12, "cartridge_engagement_mm": 10,
                           "dock_engagement_mm": 18} for p in pin_positions],
        "registration_bores": [
            {"center": [-28, 21, z], "shape": "round", "diameter_mm": 6.1},
            {"center": [28, 21, z], "shape": "horizontal_slot", "height_mm": 6.1, "width_mm": 6.7}],
        "pin_retention": {
            "method": "one M4x16 radial set screw and captive M4 nut per dowel",
            "screw_positions": [[-28, 38, z + 19], [28, 38, z + 19]],
            "screw_tip_z": z + 3,
            "nut_access": "rear-facing side slots; nut pocket roof remains intact",
            "scope": "friction retention; confirm dowels stay in the dock during cartridge withdrawal before use",
        },
        "draw_bolt_axes": [[-43, 14.8, z], [43, 14.8, z]],
        "draw_bolt_roles": ["cartridge_draw_bolt", "cartridge_draw_washer"],
        "jaw_names": {"lower": "04_removable_knife_cartridge", "upper": "05_upper_knife_jaw",
                      "shim": f"06_blade_shim_{t:g}mm"},
        "setup_gauge_mm": 28.0,
        "clamp_axes_x": [-52.0, 52.0],
        "upper_jaw_universal_geometry": True,
        "upper_jaw_pose_z_offset_mm": t / 2,
        "working_yaw_deg": 0.0,
        "extraction": {"vector": [0, -1, 0], "distance_mm": 18,
                       "remove_hardware_groups": ["draw_screws"],
                       "moving_groups": ["cartridge", "knife"],
                       "flip_axis": [[0, 0, z], [0, 1, z]],
                       "reseat_angles_deg": [0, 180],
                       "procedure": "Remove guide/stone, remove both draw screws, withdraw18mm, lift cartridge fully clear, invert away from the jig, reseat and tighten both draw screws."},
        "intended_contacts": [
            ["03_fixed_cartridge_dock", "04_removable_knife_cartridge"],
            ["04_removable_knife_cartridge", f"06_blade_shim_{t:g}mm"],
            [f"06_blade_shim_{t:g}mm", "REF_blade_envelope"],
            ["05_upper_knife_jaw", "REF_blade_envelope"],
            ["REF_blade_envelope", "REF_handle_envelope"]],
        "registration_note": "Dowels locate; broad face and two metal draw screws preload and retain. Calibrate the printed round bore/slot using a coupon; nominal geometry does not certify backlash or loaded repeatability.",
    }
    return parts, hardware, metadata
