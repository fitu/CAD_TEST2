"""Ribbed bench-mounted base, open guide frame and offset fine-height screw.

All shapes are assembled millimetres.  The central window is deliberate: the
guide rod crosses the frame at high pitch, so neither a full top crossbar nor
a height screw belongs on the rod's X=0 centreline.
"""
from __future__ import annotations

import math
import cadquery as cq


def _box(x, y, z, center):
    return cq.Workplane("XY").box(x, y, z).translate(center)


def _cylinder(radius, length, start, axis="z"):
    shape = cq.Workplane("XY").circle(radius).extrude(length)
    if axis == "y":
        shape = shape.rotate((0, 0, 0), (1, 0, 0), -90)
    return shape.translate(start)


def _hex(af, length, start):
    return (cq.Workplane("XY").polygon(6, af / math.cos(math.pi / 6))
            .extrude(length).translate(start))


def build_frame(cfg):
    """Return printed parts, purchased hardware specifications and interfaces."""
    parts, hardware = [], []
    width, depth = float(cfg.base_width), float(cfg.base_depth)
    if width < 200 or depth < 240:
        raise ValueError("Frame interfaces require at least a200x240mm base")

    def add(name, shape, role, installed=True, print_rotation=None):
        if len(shape.solids().vals()) != 1 or not shape.val().isValid():
            raise ValueError(f"Invalid frame component: {name}")
        row = dict(name=name, shape=shape, printed=True, group="fixed",
                   role=role, installed=installed)
        if print_rotation:
            row["print_rotation"] = print_rotation
        parts.append(row)

    def hw(kind, m, length, position, direction, role, purchase_name=None):
        row = dict(kind=kind, m=m, length=length, position=list(position),
                   direction=direction, group="fixed", role=role)
        if purchase_name:
            row["purchase_name"] = purchase_name
        hardware.append(row)

    # Four-millimetre bottom skin, narrow ribs and local pads replace the
    # revision-A sand box and broad, thick lid.  The skin rests on the bench.
    base = _box(width, depth, 4, (0, 30, 2))
    for x in (-width / 2 + 4, width / 2 - 4):
        base = base.union(_box(8, depth, 6, (x, 30, 7)))
    for y in (30 - depth / 2 + 4, 30 + depth / 2 - 4):
        base = base.union(_box(width, 8, 6, (0, y, 7)))
    # Dock and mast bear on pads, rather than spanning the thin bottom skin.
    base = base.union(_box(112, 46, 6, (0, 49, 7)))
    for x in (-80, 80):
        base = base.union(_box(40, 60, 6, (x, 120, 7)))
    for x in (-60, 60):
        base = base.union(_box(8, 174, 6, (x, 17, 7)))
    base = base.union(_box(168, 8, 6, (0, -25, 7)))
    for x in (-90, 90):
        base = base.union(_box(20, 24, 6, (x, -25, 7)))

    dock_mounts = [(x, y) for x in (-44, 44) for y in (40, 60)]
    mast_mounts = [(x, y) for x in (-92, 92) for y in (110, 140)]
    for x, y in dock_mounts + mast_mounts:
        base = base.cut(_cylinder(2.75, 12, (x, y, -1)))
        base = base.cut(_cylinder(4.9, 3.3, (x, y, 0)))

    # Two clearance holes offer a bolted-board mounting alternative to C-clamps.
    for x in (-76, 76):
        base = base.cut(_cylinder(3.3, 12, (x, -60, -1)))
    add("01_ribbed_bench_base", base,
        "bench-clamped ribbed base; no ballast and no freestanding rating")

    # Portal columns are connected below the guide mechanism.  The two upper
    # arms leave a72mm-wide opening for the rising rod and its yaw envelope.
    frame = None
    for x in (-80, 80):
        column = _box(20, 24, 290, (x, 130, 155))
        foot = _box(40, 60, 8, (x, 120, 14))
        brace = (cq.Workplane("YZ")
                 .polyline([(82, 18), (118, 18), (118, 100)])
                 .close().extrude(12).translate((x - 6, 0, 0)))
        column = column.union(foot).union(brace)
        arm_x = -63 if x < 0 else 63
        column = column.union(_box(54, 24, 10, (arm_x, 130, 295)))
        frame = column if frame is None else frame.union(column)
    frame = frame.union(_box(180, 24, 10, (0, 130, 145)))

    slot_low = cfg.pivot_height(cfg.angle_min) - 22
    slot_high = cfg.pivot_height(cfg.angle_max) - 22
    for x in (-80, 80):
        slot = _box(6.6, 28, slot_high - slot_low,
                    (x, 130, (slot_low + slot_high) / 2))
        for z in (slot_low, slot_high):
            slot = slot.union(_cylinder(3.3, 28, (x, 116, z), "y"))
        frame = frame.cut(slot)

    for x, y in mast_mounts:
        frame = frame.cut(_cylinder(2.75, 30, (x, y, 8)))
        # The nut is accessible from the outboard edge; relieve the adjacent
        # column locally rather than trapping a nut inside solid material.
        frame = frame.cut(_hex(8.4, 4.4, (x, y, 18)))
        frame = frame.cut(_box(10, 10, 4.4,
                               (x + (4 if x > 0 else -4), y, 20.2)))
        hw("bolt", 5, 20, (x, y, 3.25), "z", "frame_mount_bolt")
        hw("nut", 5, 0, (x, y, 18), "z", "frame_mount_nut")

    lead_x, lead_y = 50.0, 130.0
    # Keep both bridge passages explicit, although the nominal screw starts
    # above the lower one.  The lower passage remains open for assembly/tools.
    for z in (138, 288):
        frame = frame.cut(_cylinder(3.3, 16, (lead_x, lead_y, z)))

    # Reference scale is adjacent to the right carriage slot.  It is valid
    # for this stone profile only, with edgeY=-70 and the selected rod offset.
    for angle in range(int(cfg.angle_min), int(cfg.angle_max) + 1):
        z = cfg.pivot_height(angle) - 22
        frame = frame.cut(_box(7 if angle % 5 else 10, 1.0, 0.5,
                               (84, 118.2, z)))
    add("02_open_portal_frame", frame,
        "braced guide frame with central rod window and profile-specific scale",
        print_rotation={"axis": [1, 0, 0], "angle": 90})

    # Metal fine-height screw: an ordinary threaded rod cut to160mm, held by
    # jam nuts.  The carriage has its own captive M6 travelling nut.
    hw("shaft", 6, 160, (lead_x, lead_y, 155), "z", "fine_height_lead_screw",
       "threaded_rod_M6x160_cut_from_stock")
    hw("nut", 6, 0, (lead_x, lead_y, 284), "z", "lead_screw_lower_nut")
    hw("nut", 6, 0, (lead_x, lead_y, 279.2), "z", "lead_screw_lower_jam_nut")
    hw("washer", 6, 0, (lead_x, lead_y, 288.8), "z", "lead_screw_lower_washer")
    hw("washer", 6, 0, (lead_x, lead_y, 300), "z", "lead_screw_upper_washer")
    hw("nut", 6, 0, (lead_x, lead_y, 301.2), "z", "lead_screw_knob_nut")
    hw("nut", 6, 0, (lead_x, lead_y, 306), "z", "lead_screw_knob_jam_nut")
    knob = _cylinder(16, 12, (lead_x, lead_y, 301.2))
    knob = knob.cut(_cylinder(3.3, 16, (lead_x, lead_y, 300)))
    knob = knob.cut(_hex(10.4, 9.8, (lead_x, lead_y, 301.2)))
    for i in range(12):
        a = 2 * math.pi * i / 12
        knob = knob.cut(_cylinder(2.2, 14,
            (lead_x + 16.2 * math.cos(a), lead_y + 16.2 * math.sin(a), 300)))
    add("18_fine_height_knob", knob,
        "fine-height knob with captive metal jam nuts; do not carry fixture by knob")

    # Small, separately printed coupons support fit calibration before the
    # main frame.  They are not assembled components or build-volume totals.
    coupon = _box(72, 24, 10, (0, 0, 5))
    for x, bore in ((-24, 8.0), (-12, 8.1), (0, 8.2), (14, 12.05), (30, 6.1)):
        coupon = coupon.cut(_cylinder(bore / 2, 12, (x, 0, -1)))
    add("COUPON_bearing_and_dowel_fits", coupon,
        "8.0/8.1/8.2mm shaft,12.05mm sleeve and6.1mm dowel fit coupon", installed=False)

    metadata = {
        "base_bounds": {"x": [-width / 2, width / 2],
                        "y": [30 - depth / 2, 30 + depth / 2], "z": [0, 10]},
        "dock_mount_holes": [[x, y, 10] for x, y in dock_mounts],
        "frame_mount_holes": [[x, y, 10] for x, y in mast_mounts],
        "mount_head_counterbore": {"radius": 4.9, "depth": 3.3},
        "carriage_slots": {"x": [-80, 80], "y_span": [118, 142],
                           "z_span": [slot_low, slot_high], "diameter": 6.6},
        "lead_screw": {"x": lead_x, "y": lead_y,
                       "z_start": 155, "z_end": 315,
                       "diameter": 6, "pitch_mm": 1,
                       "travelling_nut_z_offset": -35.8},
        "rod_window": {"x": [-36, 36], "y": [118, 142], "z": [290, 300]},
        "frame_top_z": 300,
        "highest_hardware_z": 315,
        "bench_mount": {
            "required": True,
            "method": "two commercial C-clamps or through-bolt to a rigid board",
            "clamps": {"quantity": 2, "minimum_opening_mm": 100,
                       "clamp_regions": [[-90, -25, 10], [90, -25, 10]]},
            "alternative_bolt_holes": [[-76, -60, 0], [76, -60, 0]],
        },
        "accepted_contact_pairs": [],
    }
    return parts, hardware, metadata
