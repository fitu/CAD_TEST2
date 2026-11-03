"""Compact height carriage, yaw/pitch gimbal and serviceable guide sleeve."""
import math
from geometry import box, cyl, hex_prism, stone_pose


def build_guide(cfg):
    h = cfg.pivot_height()
    parts, hardware = [], []

    def add(name, shape, group, role, **extra):
        parts.append(dict(name=name, shape=shape, printed=True, group=group, role=role, **extra))

    def hw(kind, m, length, position, direction, group, role):
        hardware.append(dict(kind=kind, m=m, length=length, position=position,
                             direction=direction, group=group, role=role))

    carriage = box(180, 10, 12, (0, 113, h - 40))
    for x in (-80, 80):
        carriage = carriage.union(box(24, 10, 32, (x, 113, h - 30)))
    carriage = carriage.union(box(30, 52, 8, (0, 95, h - 34)))
    # Rear nut arm receives the rotating M6 lead screw. The side clamps carry
    # working loads; the lead screw is an adjustment, not a brake.
    carriage = carriage.union(box(24, 28, 12, (50, 125, h - 30)))
    carriage = carriage.cut(cyl(3.3, 20, (50, 130, h - 40)))
    carriage = carriage.cut(hex_prism(10.4, 5.2, (50, 130, h - 36)))
    # Side-entry nut access.
    carriage = carriage.cut(box(24, 14, 5.2, (62, 130, h - 33.4)))
    for x in (-80, 80):
        carriage = carriage.cut(cyl(3.3, 14, (x, 106, h - 22), "y"))
        hw("bolt", 6, 45, (x, 106.8, h - 22), "y", "height", "height locking bolt")
        hw("washer", 6, 0, (x, 106.8, h - 22), "y", "height", "front height washer")
        hw("washer", 6, 0, (x, 142, h - 22), "y", "height", "rear height washer")
        hw("nut", 6, 0, (x, 143.2, h - 22), "y", "height", "height locking nut")
    carriage = carriage.cut(cyl(4.3, 12, (0, 100, h - 40)))
    carriage = carriage.union(cyl(6, 8, (0, 118, h - 38)))
    carriage = carriage.cut(cyl(2.2, 12, (0, 118, h - 40)))
    carriage = carriage.cut(cyl(4.5, 10, (0, 118, h - 48)))
    for x in (-23, 23):
        carriage = carriage.cut(cyl(3, 4, (x, 110, h - 37)))
    add("05_height_carriage", carriage, "height", "fine-adjustable shelf with independent side clamps")
    hw("nut", 6, 0, (50, 130, h - 35.8), "z", "height", "captive fine-height nut")

    yaw = box(64, 44, 6, (0, 100, h - 27))
    yaw = yaw.cut(cyl(4.3, 10, (0, 100, h - 32)))
    yaw = yaw.union(cyl(6, 6, (0, 118, h - 30)))
    yaw = yaw.cut(cyl(2.2, 10, (0, 118, h - 32)))
    for x in (-23, 23):
        for y in (90, 110):
            yaw = yaw.cut(cyl(2.75, 10, (x, y, h - 32)))
    add("06_yaw_plate", yaw, "yaw", "yaw plate on narrow shelf, leaving cheek nuts accessible")
    hw("bolt", 8, 25, (0, 100, h - 39.2), "z", "height", "short yaw pivot bolt")
    hw("washer", 8, 0, (0, 100, h - 39.2), "z", "height", "lower yaw thrust washer")
    hw("washer", 8, 0, (0, 100, h - 24), "z", "yaw", "upper yaw thrust washer")
    hw("nut", 8, 0, (0, 100, h - 22.8), "z", "yaw", "yaw prevailing-torque nut")
    hw("bolt", 4, 25, (0, 118, h - 39.2), "z", "height", "positive yaw lock bolt")
    hw("washer", 4, 0, (0, 118, h - 39.2), "z", "height", "yaw lock lower washer")
    hw("washer", 4, 0, (0, 118, h - 24), "z", "yaw", "yaw lock upper washer")
    hw("nut", 4, 0, (0, 118, h - 22.8), "z", "yaw", "positive yaw lock nut")

    for i, x in enumerate((-23, 23), 1):
        cheek = box(10, 30, 38, (x, 100, h - 5))
        cheek = cheek.cut(cyl(5.1, 14, (x - 7, 100, h), "x"))
        for y in (90, 110):
            cheek = cheek.cut(cyl(2.75, 42, (x, y, h - 26)))
            hw("bolt", 5, 50, (x, y, h + 15.2), "-z", "yaw", "pitch cheek bolt")
            # Along -Z the washer starts at its upper face.
            hw("washer", 5, 0, (x, y, h + 15.2), "-z", "yaw", "cheek head washer")
            hw("nut", 5, 0, (x, y, h - 34), "z", "yaw", "cheek retaining nut")
        add(f"07_pitch_cheek_{i}", cheek, "yaw", "8 mm trunnion engagement")

    housing = box(24, 40, 24, (0, 0, 0)).union(cyl(5, 52, (-26, 0, 0), "x"))
    housing = housing.cut(cyl(6.025, 44, (0, -22, 0), "y"))
    housing = housing.union(box(24, 14, 8, (0, 0, 12)))
    # Relief for the M8 pivot tip through the complete 15–25° pitch range.
    # Keep four millimetres of material between this relief and the sleeve.
    housing = housing.cut(box(10, 24, 6, (0, 0, -13)))
    housing = housing.cut(box(.8, 44, 14, (0, 0, 12)))
    housing = housing.cut(cyl(2.2, 28, (-14, 0, 10), "x"))
    housing = housing.cut(hex_prism(7.4, 4, (8, 0, 10), "x"))
    for kind, length, x in (("bolt", 25, -12), ("nut", 0, 8.4)):
        hardware.append(dict(kind=kind, m=4, length=length, position=[x, 0, 10],
            direction="x", group="pitch", role="replaceable sleeve clamp", local_pitch=True))
    sleeve = cyl(6, 40, (0, -20, 0), "y").cut(cyl(4.05, 44, (0, -22, 0), "y"))
    for name, shape, role in (("08_pitch_housing", housing, "replaceable sleeve housing"),
                              ("09_calibrated_guide_sleeve", sleeve, "replaceable 8.1 ID / 12 OD / 40 mm sleeve")):
        posed = shape.rotate((0, 0, 0), (1, 0, 0), cfg.angle).translate((0, cfg.pivot_y, h))
        add(name, posed, "pitch", role,
            print_rotation={"axis": [1, 0, 0], "angle": 90 - cfg.angle})

    # Split collars with captive metal nuts replace tapped radial set screws.
    u = cfg.guide_u()
    for i, yy in enumerate((u - 57, u + 45), 1):
        collar = cyl(10, 12, (0, yy, cfg.rod_offset), "y")
        collar = collar.union(box(20, 12, 8, (0, yy + 6, cfg.rod_offset + 8)))
        collar = collar.cut(cyl(4.15, 16, (0, yy - 2, cfg.rod_offset), "y"))
        collar = collar.cut(box(1, 16, 12, (0, yy + 6, cfg.rod_offset + 7)))
        collar = collar.cut(cyl(2.2, 24, (-12, yy + 6, cfg.rod_offset + 8), "x"))
        collar = collar.cut(hex_prism(7.4, 3.8, (6.2, yy + 6, cfg.rod_offset + 8), "x"))
        add(f"15_split_rod_stop_{i}", stone_pose(collar, cfg), "rod_stops", "captive-nut split travel collar",
            print_rotation={"axis": [1, 0, 0], "angle": 90 - cfg.angle})
        for kind, m, length, position, direction, role in (
                ("bolt", 4, 20, (-10, yy + 6, cfg.rod_offset + 8), "x", "split stop screw"),
                ("nut", 4, 0, (6.5, yy + 6, cfg.rod_offset + 8), "x", "captive stop nut")):
            hardware.append(dict(kind=kind, m=m, length=length, position=position,
                                 direction=direction, group="rod_stops", role=role, local_stone=True))

    return parts, hardware, {
        "bushing_length_mm": 40, "bushing_bore_mm": 8.1, "sleeve_od_mm": 12,
        "bushing_center": [0, cfg.pivot_y, h], "rod_start_local_y": cfg.rod_start,
        "rod_end_local_y": cfg.rod_start + cfg.rod_length,
        "stop_spans_local_y": [[u - 57, u - 45], [u + 45, u + 57]],
        "stop_free_travel_mm": cfg.stroke, "accepted_contact_pairs": [],
        "working_yaw_locked": True, "yaw_lock_axis": [0, 118, h],
        "yaw_lock": {"axis_point": [0, 118, h], "diameter_mm": 4,
                     "bolt_role": "positive yaw lock bolt", "nut_role": "positive yaw lock nut",
                     "shelf_z_span": [h - 38, h - 30], "plate_z_span": [h - 30, h - 24]},
        "lead_screw_nut_z": h - 35.8,
    }
