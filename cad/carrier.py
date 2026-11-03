"""Ribbed, axially loaded stone cassette for revision B (local millimetres).

The stone's working face is Z=0; the parent generator applies the sharpening
pose to every part and hardware item returned here.  The two end-gate screws
retain the stone positively: side pressure is not the vertical load path.
"""
from __future__ import annotations

import math
import cadquery as cq


def _box(x, y, z, center):
    return cq.Workplane("XY").box(x, y, z).translate(center)


def _cylinder(radius, length, position, direction="z"):
    shape = cq.Workplane("XY").circle(radius).extrude(length)
    if direction == "x":
        shape = shape.rotate((0, 0, 0), (0, 1, 0), 90)
    elif direction == "y":
        shape = shape.rotate((0, 0, 0), (1, 0, 0), -90)
    return shape.translate(position)


def _hex_pocket(af, length, position, direction):
    shape = cq.Workplane("XY").polygon(6, af / math.cos(math.pi / 6)).extrude(length)
    if direction == "x":
        shape = shape.rotate((0, 0, 0), (0, 1, 0), 90)
    elif direction == "y":
        shape = shape.rotate((0, 0, 0), (1, 0, 0), -90)
    return shape.translate(position)


def build_carrier(cfg):
    """Return ``(parts, hardware, metadata)`` in the unposed stone frame.

    Both the original 60 x180 x30 stone and a 25 x150 x6 slim stone use
    exactly the same retention architecture.  Pads are purchased reference
    components and are deliberately excluded from printed-volume totals.
    """
    width = float(cfg.stone_width)
    length = float(cfg.stone_length)
    thick = float(cfg.stone_thickness)
    backing = float(getattr(cfg, "stone_backing", 2))
    rod_z = float(cfg.rod_offset)
    roof_bottom = thick + backing
    roof_top = roof_bottom + 4
    clamp_bottom = roof_bottom + 2
    clamp_top = rod_z + 12
    if rod_z - 4.15 <= clamp_bottom:
        raise ValueError("rod_offset must leave at least4.15mm above the clamp foot")
    side_x = width / 2 + 6
    rail_y = -3
    rail_length = length + 10
    end_lo, end_hi = -length / 2 - 8, length / 2 + 2
    clamp_ys = (-length / 2 + 20, length / 2 - 20)
    screw_ys = (-length / 3, length / 3)
    # The much lighter slim stone permits shallower corner ledges, needed to
    # clear the inverted clamp at the15degree/negative-stroke extreme.
    ledge_thickness = 2.0 if thick <= 10 else 3.0
    keeper_inset = 8.0 if thick <= 10 else 12.0
    keeper_ys = (-length / 2 + keeper_inset, length / 2 - keeper_inset)
    parts, hardware = [], []

    def add(name, shape, printed=True, role=""):
        if len(shape.solids().vals()) != 1 or not shape.val().isValid():
            raise ValueError(f"invalid carrier component: {name}")
        parts.append({"name": name, "shape": shape, "printed": printed,
                      "group": "stone", "role": role,
                      "print_rotation": {"axis": [1, 0, 0], "angle": 180}})

    def hw(kind, m, size, position, direction, role, purchase_name=None):
        item = {"kind": kind, "m": m, "length": size,
                "position": position, "direction": direction,
                "group": "stone", "role": role}
        if purchase_name:
            item["purchase_name"] = purchase_name
        hardware.append(item)

    # The lower structural rail is ABOVE the working face.  Only fixed corner
    # ledges project below that face, well outside the central contact stroke;
    # a full-length ledge would hit a wide knife before the abrasive touches it.
    # Three roof ribs and discrete side posts replace a solid roof/sidewalls.
    body = None
    for sign in (-1, 1):
        x = sign * side_x
        ledge = _box(8, rail_length, 5, (x, rail_y, 8.5))
        rail = _box(8, rail_length, 5, (x, rail_y, roof_top - 2.5))
        side = ledge.union(rail)
        for y in keeper_ys:
            keeper = _box(8, 10, 8 + ledge_thickness,
                          (x, y, (8 - ledge_thickness) / 2))
            keeper = keeper.union(_box(12, 10, ledge_thickness,
                (sign * (width / 2 + 4), y, -ledge_thickness / 2)))
            side = side.union(keeper)
        for y in (-length / 2 - 2, *screw_ys, length / 2 - 4):
            # Gate nuts need side walls alongside the8.6mm insertion slot.
            post_width = 10 if y == length / 2 - 4 else 8
            side = side.union(_box(post_width, 12, roof_top,
                                   (x, y, roof_top / 2)))
        body = side if body is None else body.union(side)
    body = body.union(_box(width + 20, 6, roof_top - 6,
                           (0, -length / 2 - 5, (roof_top + 6) / 2)))
    for y in (*clamp_ys, 0):
        body = body.union(_box(width + 20, 10, 4, (0, y, roof_bottom + 2)))

    # Split shaft clamps with captive M5 nuts.  No tapped plastic is used.
    for y in clamp_ys:
        clamp = _box(24, 18, clamp_top - clamp_bottom,
                     (0, y, (clamp_top + clamp_bottom) / 2))
        clamp = clamp.cut(_cylinder(4.15, 22, (0, y - 11, rod_z), "y"))
        clamp = clamp.cut(_box(1, 22, 14, (0, y, rod_z + 7)))
        clamp = clamp.cut(_cylinder(2.75, 28, (-14, y, rod_z + 7), "x"))
        clamp = clamp.cut(_hex_pocket(8.4, 4.5, (7.5, y, rod_z + 7), "x"))
        body = body.union(clamp)
        hw("bolt", 5, 25, (-12, y, rod_z + 7), "x", "split rod clamp")
        hw("nut", 5, 0, (8, y, rod_z + 7), "x", "captive rod-clamp nut")

    # Four protected side adjusters.  The nominal screw tip touches the outer
    # face of a2mm soft pad; do not tighten enough to deform the brittle stone.
    # A slim stone still needs theM4 nut's lower corner above the working
    # plane.  The protective pad extends slightly above the6mm stone.
    pad_z = max(thick / 2, 5.5)
    side_pad_height = max(thick, 8)
    for sign in (-1, 1):
        for y in screw_ys:
            x = sign * side_x
            body = body.cut(_cylinder(2.2, 12, (x - 6, y, pad_z), "x"))
            if sign > 0:
                pocket_x = width / 2 + 4.6
            else:
                pocket_x = -width / 2 - 8.4
            body = body.cut(_hex_pocket(7.4, 3.8, (pocket_x, y, pad_z), "x"))
            # Top-entry slot makes the nut replaceable after printing.
            body = body.cut(_box(3.8, 7.4, roof_top - pad_z + 1,
                                 (pocket_x + 1.9, y,
                                  (roof_top + pad_z + 1) / 2)))
            direction = "-x" if sign > 0 else "x"
            outer_x = sign * (width / 2 + 10)
            nut_x = width / 2 + 8.2 if sign > 0 else -width / 2 - 8.2
            hw("bolt", 4, 8, (outer_x, y, pad_z), direction,
               "padded side adjuster", "nylon_tip_screw_M4x8")
            hw("nut", 4, 0, (nut_x, y, pad_z), direction, "captive side-adjuster nut")

    # The gate bears on a2mm end cushion.  Its two screws engage captive metal
    # nuts in the rail posts, leaving the abrasive face completely unobstructed
    # between the2mm edge ledges.  Slide the stone in/out along+Y with gate off.
    gate = _box(width + 20, 6, roof_top,
                (0, length / 2 + 5, roof_top / 2))
    gate_nut_y = length / 2 - 4
    for sign in (-1, 1):
        x = sign * side_x
        body = body.cut(_cylinder(2.2, 18, (x, length / 2 - 12, pad_z), "y"))
        body = body.cut(_hex_pocket(7.4, 3.8, (x, gate_nut_y, pad_z), "y"))
        body = body.cut(_box(8.6, 3.8, roof_top - pad_z + 1,
                             (x, gate_nut_y + 1.9,
                              (roof_top + pad_z + 1) / 2)))
        gate = gate.cut(_cylinder(2.2, 10, (x, length / 2, pad_z), "y"))
        hw("bolt", 4, 16, (x, length / 2 + 8, pad_z), "-y", "removable end-gate screw")
        hw("nut", 4, 0, (x, gate_nut_y, pad_z), "y", "captive gate nut")
    add("13_ribbed_stone_cassette", body, role="fixed corner ledges and split shaft clamps")
    add("14_removable_end_gate", gate, role="two-screw axial stone gate")
    add("REF_whetstone", _box(width, length, thick, (0, 0, thick / 2)), False,
        "purchased double-sided stone; working face at localZ0")
    for i, y in enumerate((*clamp_ys, 0), 1):
        add(f"REF_stone_backing_{i}", _box(width, 10, backing,
            (0, y, thick + backing / 2)), False, "firm resilient roof backing")
    add("REF_end_pad_fixed", _box(width, 2, thick,
        (0, -length / 2 - 1, thick / 2)), False, "soft end cushion")
    add("REF_end_pad_gate", _box(width, 2, thick,
        (0, length / 2 + 1, thick / 2)), False, "soft end cushion")
    for i, (sign, y) in enumerate(((sign, y) for sign in (-1, 1) for y in screw_ys), 1):
        add(f"REF_side_pad_{i}", _box(2, 8, side_pad_height,
            (sign * (width / 2 + 1), y, side_pad_height / 2)), False,
            "firm padded contact for side screw")

    metadata = {
        "local_stone_bounds": {"x": [-width / 2, width / 2],
                               "y": [-length / 2, length / 2], "z": [0, thick]},
        "abrasive_face_z": 0, "rod_axis_z": rod_z,
        "roof_bottom_z": roof_bottom, "backing_mm": backing,
        "rod_clamp_spans_y": [[y - 9, y + 9] for y in clamp_ys],
        "gate_inner_y": length / 2 + 2, "gate_outer_y": length / 2 + 8,
        "gate_screw_length": 16, "gate_nut_y_span": [gate_nut_y, gate_nut_y + 3.2],
        "side_adjuster_axis_z": pad_z,
        "side_adjuster_positions_y": list(screw_ys),
        "side_pad_height_mm": side_pad_height,
        "ledge_overlap_mm": 2,
        "ledge_thickness_mm": ledge_thickness,
        "keeper_spans_y": [[y - 5, y + 5] for y in keeper_ys],
        "clear_working_length_mm": length - 2 * (keeper_inset + 5),
        "stone_insertion_direction": [0, 1, 0],
        "usable_abrasive_width_mm": width - 4,
        "accepted_contact_pairs": [],
        "retention": "fixed corner ledges plus two captive-nut M4 end-gate screws",
        "local_bounds_y": [end_lo, length / 2 + 8],
    }
    return parts, hardware, metadata
