"""Build and check the wall-mounted sensor jig with a printed screw, in millimetres."""
from itertools import combinations
from math import cos, pi, sin, sqrt
from pathlib import Path
import json
import struct

import cadquery as cq

ROOT = Path(__file__).resolve().parent
WALL_LEFT = -248  # Bare face of the fixed flange.
WALL_GAPS = (490, 500, 510)
RAIL_LEFT = -234
RAIL_RIGHT = 210
PAD_RADIUS = 34
PAD_DEPTH = 16
SCREW_LENGTH = 72
RECEIVER_LENGTH = 65
THREAD_PITCH = 7
THREAD_ROOT = 11.6
THREAD_CREST = 14
THREAD_FLANK = 2.6 / (THREAD_CREST - THREAD_ROOT)
THREAD_HALF_CREST = 0.35
X_LIMITS = (-209, 159)
Z_STROKE = 80
SENSOR_Y = 78
RUNNING_GAP = 0.125
PRINT_SHRINK_XYZ = (0.015, 0.015, 0.015)
THREAD_ENTRY_START = -0.4
THREAD_ENTRY_OUTER = THREAD_CREST + RUNNING_GAP + 1.2
THREAD_ENTRY_INNER = THREAD_ROOT + RUNNING_GAP - 0.05
THREAD_ENTRY_END = THREAD_ENTRY_START + 1.10 * (THREAD_ENTRY_OUTER - THREAD_ENTRY_INNER)
H2D = (300, 320, 325)
EDGE_CHAMFER = 1


def box(x, y, z, dx, dy, dz):
    return cq.Solid.makeBox(dx, dy, dz, cq.Vector(x, y, z))


def cyl(x, y, z, diameter, length, axis):
    return cq.Solid.makeCylinder(diameter / 2, length, cq.Vector(x, y, z), cq.Vector(*axis))


X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
NEG_X = (-1, 0, 0)


def prism(points, length, axis):
    wire = cq.Wire.makePolygon([cq.Vector(*point) for point in points], close=True)
    return cq.Solid.extrudeLinear(wire, [], cq.Vector(*axis) * length)


def beveled(shape):
    # Chamfer convex edges only. Beveling a reentrant edge would add material
    # in front of a stop or into the slider's travel.
    edges = []
    for edge in shape.Edges():
        point = edge.Center()
        first, second = edge.ancestors(shape, "Face").Faces()
        tangent = first.normalAt(point) - second.normalAt(point)
        if not any(shape.isInside(point + tangent * sign * 0.1) for sign in (-1, 1)):
            edges.append(edge)
    return cq.Workplane(obj=shape).newObject(edges).chamfer(EDGE_CHAMFER).val()


def bevel_openings(shape, mouths):
    edges = []
    for edge in shape.Edges():
        bounds = edge.BoundingBox()
        for axis, coordinate, cross_section in mouths:
            if (abs(getattr(bounds, axis + "min") - coordinate) < 1e-6
                    and abs(getattr(bounds, axis + "max") - coordinate) < 1e-6
                    and cross_section(edge.Center())):
                edges.append(edge)
                break
    return cq.Workplane(obj=shape).newObject(edges).chamfer(EDGE_CHAMFER).val()


def roofed_hole(origin, diameter, length, axis, up):
    """Keep the full screw clearance and replace the unsupported arc with a 45° roof."""
    center = cq.Vector(*origin)
    rise = cq.Vector(*up) * (diameter / (2 * sqrt(2)))
    half_width = cq.Vector(*axis).cross(rise)
    roof = [center + rise - half_width, center + rise + half_width, center + rise * 2]
    return fused(cyl(*origin, diameter, length, axis),
                 prism([point.toTuple() for point in roof], length, axis))


def hex_prism(origin, across_flats, length, axis):
    radius = across_flats / sqrt(3)
    ox, oy, oz = origin
    points = []
    for i in range(6):
        u, v = radius * cos(i * pi / 3), radius * sin(i * pi / 3)
        if axis == X:
            points.append(cq.Vector(ox, oy + u, oz + v))
        elif axis == Y:
            points.append(cq.Vector(ox + u, oy, oz + v))
        else:
            points.append(cq.Vector(ox + u, oy + v, oz))
    return cq.Solid.extrudeLinear(
        cq.Wire.makePolygon(points, close=True), [], cq.Vector(*axis) * length
    )


def fused(*parts):
    return parts[0].fuse(*parts[1:]).clean()


SPLICE_BOLTS = (-42, -17, 17, 42)


def splice_profile(x, length, fit=0):
    shoulder, half_width = (sqrt(2) - 1) * fit, 12 + fit
    return prism(
        [(x, -12 - fit, -half_width), (x, -12 - fit, half_width),
         (x, shoulder, half_width), (x, shoulder + half_width, 0),
         (x, shoulder, -half_width)],
        length, X,
    )


def rail_parts():
    cavity = splice_profile(-56, 112, RUNNING_GAP)
    left = beveled(fused(box(RAIL_LEFT, -20, -20, 234, 40, 40),
                         box(-248, -20, -36, 14, 58, 72))).cut(cavity)
    stop_ramp = prism([(190, -20, 20), (194, -20, 20), (190, -20, 24)], 30, Y)
    right = beveled(fused(box(0, -20, -20, RAIL_RIGHT, 40, 40),
                          box(184, -20, 20, 6, 30, 4), stop_ramp)).cut(cavity)
    splice = beveled(splice_profile(-55, 110))

    for x in SPLICE_BOLTS:
        through = cyl(x, -21, 0, 5.5, 42, Y)
        head = cyl(x, -21, 0, 9.5, 8, Y)
        # A 45° bevel meets the clearance bore above the screw head. Keep
        # the remaining 1 mm radial seat flat for the socket-head screw.
        head_transition = cq.Solid.makeCone(3.75, 2.75, 1, cq.Vector(x, -13, 0), cq.Vector(*Y))
        nut = hex_prism((x, 12.5, 0), 8.4, 8, Y)
        if x < 0:
            left = left.cut(through, head, head_transition, nut)
        else:
            half_flat = 8.4 / 2
            shoulder = x - 8.4 / (2 * sqrt(3))
            nut_roof = prism([(shoulder, 12.5, -half_flat), (shoulder, 12.5, half_flat),
                              (shoulder - half_flat, 12.5, 0)], 8, Y)
            right = right.cut(
                roofed_hole((x, -21, 0), 5.5, 42, Y, NEG_X),
                roofed_hole((x, -21, 0), 9.5, 8, Y, NEG_X),
                fused(nut, nut_roof),
            )
        splice = splice.cut(through)

    mouths = [
        ("x", 0, lambda p: abs(p.y) < 14 and abs(p.z) < 14),
        ("y", -20, lambda p: abs(p.z) < 6 and any(abs(p.x - x) < 6 for x in SPLICE_BOLTS)),
        ("y", 20, lambda p: abs(p.z) < 6 and any(abs(p.x - x) < 6 for x in SPLICE_BOLTS)),
    ]
    left = bevel_openings(left, mouths)
    # The right rail is printed upright. Teardrop head and nut pockets supply
    # the side-entry relief without adding chamfer overhangs at their mouths.
    right = bevel_openings(right, mouths[:1])
    return left.clean(), right.clean(), splice.clean()


def vertical_profile(z, length, fit=0):
    shoulder = -4 - (sqrt(2) - 1) * fit
    return prism(
        [(13 + fit, 39 - fit, z), (13 + fit, 57 + fit, z),
         (shoulder, 57 + fit, z), (-13 - sqrt(2) * fit, 48, z),
         (shoulder, 39 - fit, z)],
        length, Z,
    )


def carriage():
    structure = beveled(fused(box(-25, -26, -26, 50, 52, 52),
                              box(-25, 22, -23, 50, 13, 46),
                              box(-25, 33, -30, 50, 30, 60)))
    h = RUNNING_GAP
    structure = structure.cut(
        box(-26, -20 - h, -20 - h, 52, 40 + 2 * h, 40 + 2 * h),
        vertical_profile(-31, 62, RUNNING_GAP),
        roofed_hole((0, -27, 0), 5.4, 8, Y, NEG_X),
        roofed_hole((0, -27, 0), 7.1, 6, Y, NEG_X),
        roofed_hole((0, 56, 0), 5.4, 8, Y, NEG_X),
        roofed_hole((0, 58, 0), 7.1, 6, Y, NEG_X),
    )
    rail_mouths = [("x", x, lambda p: abs(p.y) < 21 and abs(p.z) < 21)
                   for x in (-25, 25)]
    slide_mouths = [("z", z, lambda p: abs(p.x) < 14 and 38 < p.y < 58)
                    for z in (-30, 30)]
    return bevel_openings(structure, rail_mouths + slide_mouths).clean()


def sensor_slide():
    stem = vertical_profile(-30, 140)
    nose = box(-16, 39, -43, 29, 55, 13)
    nut_half_flat = 17.4 / 2
    nut_shoulder = -17.4 / (2 * sqrt(3))
    nut_roof = prism(
        [(nut_shoulder, SENSOR_Y - nut_half_flat, -33),
         (nut_shoulder, SENSOR_Y + nut_half_flat, -33),
         (nut_shoulder - nut_half_flat, SENSOR_Y, -33)],
        4, Z,
    )
    return beveled(fused(stem, nose)).cut(
        roofed_hole((0, SENSOR_Y, -44), 10.4, 16, Z, NEG_X),
        fused(hex_prism((0, SENSOR_Y, -33), 17.4, 4, Z), nut_roof),
        roofed_hole((0, 82.5, -37), 4.4, 12.5, Y, NEG_X),
        roofed_hole((0, 88, -37), 5.6, 7, Y, NEG_X),
        roofed_hole((0, 48, 99), 3.6, 12, Z, NEG_X),
        roofed_hole((0, 48, 102), 5.6, 9, Z, NEG_X),
    ).clean()


def top_stop():
    return beveled(box(-16, 34, 110, 32, 28, 6)).cut(cyl(0, 48, 109, 4.5, 8, Z)).clean()


def threaded_body(length, clearance=0):
    """Create the male screw or the female cutting solid on local +Z."""
    root = THREAD_ROOT + clearance
    crest = THREAD_CREST + clearance
    inner = root - 0.3  # Overlap the core to fuse the helical rib to the shaft.
    start = -THREAD_PITCH
    allowance = clearance * sqrt(1 + THREAD_FLANK ** 2)

    def half_width(radius):
        return THREAD_HALF_CREST + THREAD_FLANK * (THREAD_CREST - radius) + allowance

    profile = cq.Wire.makePolygon(
        [cq.Vector(inner, 0, start - half_width(inner)),
         cq.Vector(crest, 0, start - half_width(crest)),
         cq.Vector(crest, 0, start + half_width(crest)),
         cq.Vector(inner, 0, start + half_width(inner))],
        close=True,
    )
    helix = cq.Wire.makeHelix(
        THREAD_PITCH, length + 2 * THREAD_PITCH, (inner + crest) / 2,
        center=(0, 0, start),
    )
    rib = cq.Solid.sweep(profile, [], helix, isFrenet=True)
    core = cyl(0, 0, -2 * THREAD_PITCH, 2 * root, length + 4 * THREAD_PITCH, Z)
    body = fused(core, rib).intersect(cyl(0, 0, 0, 2 * crest + 0.2, length, Z)).clean()
    if not body.isValid() or len(body.Solids()) != 1:
        raise ValueError("Failed to build a valid helical thread")
    return body


def female_receiver():
    # Oversize the entry to catch the lead and reduce first-layer interference.
    crest = THREAD_CREST + RUNNING_GAP
    entry = cq.Solid.makeCone(THREAD_ENTRY_OUTER, THREAD_ENTRY_INNER,
                              THREAD_ENTRY_END - THREAD_ENTRY_START,
                              cq.Vector(0, 0, THREAD_ENTRY_START))
    # Close the blind bore with a 45° cone to avoid an internal bridge.
    roof_radius = crest + 0.42
    roof = cq.Solid.makeCone(roof_radius, 0, roof_radius * 1.04,
                             cq.Vector(0, 0, RECEIVER_LENGTH - 0.4))
    cutter = fused(threaded_body(RECEIVER_LENGTH, RUNNING_GAP), entry, roof)
    return cutter.rotate((0, 0, 0), Y, -90).translate((RAIL_RIGHT, 0, 0))


def printed_pad_screw():
    profile = []
    for i in range(32):
        angle = i * pi / 16
        radius = PAD_RADIUS - (2 if i % 2 else 0)
        profile.append((0, radius * cos(angle), radius * sin(angle)))
    pad = beveled(prism(profile, PAD_DEPTH, X))
    # The tapered nose opens the first turn without needing supports.
    start = SCREW_LENGTH - 4
    taper = cq.Solid.makeCone(THREAD_CREST + 0.1, THREAD_ROOT - 0.8, 4,
                             cq.Vector(0, 0, start))
    envelope = fused(cyl(0, 0, 0, 2 * THREAD_CREST + 0.2, start, Z), taper)
    shaft = threaded_body(SCREW_LENGTH).intersect(envelope)
    return fused(pad, shaft.rotate((0, 0, 0), Y, -90))


def fitted_pad(pad, gap, left_overlay=0, right_overlay=0):
    pad_front = WALL_LEFT - left_overlay + gap - right_overlay - PAD_DEPTH
    extension = pad_front - RAIL_RIGHT
    angle = -360 * extension / THREAD_PITCH
    fitted = pad.rotate((0, 0, 0), NEG_X, angle).translate((pad_front, 0, 0))
    return fitted, extension


def joint_hardware():
    parts = {}
    for index, x in enumerate(SPLICE_BOLTS, 1):
        parts[f"M5_splice_bolt_{index}"] = fused(cyl(x, -18, 0, 8.5, 5, Y),
                                                cyl(x, -13, 0, 5, 30, Y))
        parts[f"M5_splice_nut_{index}"] = hex_prism((x, 12.5, 0), 8, 4, Y).cut(
            cyl(x, 12, 0, 5, 5, Y)
        )
    return parts


def moving_parts(parts, x, drop):
    on_x = parts["x_carriage"].translate((x, 0, 0))
    shifted = (x, 0, -drop)
    # Reference sensor with a 3 mm projection. Set-screw tips shown at their contact positions.
    sensor = cyl(0, SENSOR_Y, -46, 10, 30, Z)
    sensor_nut = hex_prism((0, SENSOR_Y, -33), 17, 8, Z).cut(
        cyl(0, SENSOR_Y, -34, 10, 10, Z)
    )
    set_screw = cyl(0, SENSOR_Y + 5, -37, 4, 14, Y)
    cap_bolt = fused(cyl(0, 48, 104, 4, 12, Z), cyl(0, 48, 116, 7, 4, Z))
    return {
        "x_carriage": on_x,
        "z_sensor_slide": parts["z_sensor_slide"].translate(shifted),
        "z_top_stop": parts["z_top_stop"].translate(shifted),
        "M4_top_stop_bolt": cap_bolt.translate(shifted),
        "sensor_reference": sensor.translate(shifted),
        "M10_sensor_nut": sensor_nut.translate(shifted),
        "M4_sensor_set_screw": set_screw.translate(shifted),
        "M5_x_lock": cyl(x, -30, 0, 5, 10, Y),
        "M5_z_lock": cyl(x, 57, 0, 5, 10, Y),
    }


def make_parts():
    left, rail_blank, splice = rail_parts()
    receiver = female_receiver()
    parts = {
        "rail_left": left, "rail_right": rail_blank.cut(receiver).clean(), "rail_splice": splice,
        "x_carriage": carriage(), "z_sensor_slide": sensor_slide(), "z_top_stop": top_stop(),
        "printed_pad_screw": printed_pad_screw(),
    }
    return parts, rail_blank


def volume_intersection(one, two):
    return one.intersect(two).Volume()


def collision_check(parts, label):
    for (first_name, first), (second_name, second) in combinations(parts.items(), 2):
        a, b = first.BoundingBox(), second.BoundingBox()
        if (min(a.xmax, b.xmax) <= max(a.xmin, b.xmin) + 1e-6
                or min(a.ymax, b.ymax) <= max(a.ymin, b.ymin) + 1e-6
                or min(a.zmax, b.zmax) <= max(a.zmin, b.zmin) + 1e-6):
            continue
        overlap = volume_intersection(first, second)
        if overlap > 0.001:
            raise ValueError(f"{label}: {first_name} collides with {second_name} ({overlap:.3f} mm³)")


def validate_thread(parts):
    pad, rail = parts["printed_pad_screw"], parts["rail_right"]
    minimum_engagement = float("inf")
    minimum_extension = float("inf")
    checked = 0
    for gap in WALL_GAPS:
        for overlays in (0, 2):
            fitted, extension = fitted_pad(pad, gap, overlays, overlays)
            if volume_intersection(rail, fitted) > 0.01:
                raise ValueError(f"Thread interference at {gap} mm with {overlays} mm wall pads")
            # Exclude the tapered male nose and female entry.
            engagement = SCREW_LENGTH - extension - 4 - THREAD_ENTRY_END
            if engagement < 4 * THREAD_PITCH or SCREW_LENGTH - extension >= RECEIVER_LENGTH:
                raise ValueError(f"Inadequate thread engagement or tip clearance at {gap} mm")
            minimum_engagement = min(engagement, minimum_engagement)
            minimum_extension = min(extension, minimum_extension)
            checked += 1
    return {
        "thread_configurations_checked": checked,
        "thread_pitch_mm": THREAD_PITCH,
        "thread_major_diameter_mm": 2 * THREAD_CREST,
        "minimum_full_profile_engagement_mm": round(minimum_engagement, 3),
        "minimum_pad_to_rail_gap_mm": minimum_extension,
        "optional_wall_overlay_mm_per_side": [0, 2],
    }


def validated_poses(parts, rail_blank):
    static = {name: parts[name] for name in ("rail_left", "rail_right", "rail_splice")}
    static.update(joint_hardware())
    stationary_envelope = static | {"rail_right": rail_blank}
    results = validate_thread(parts)
    tested_poses = 0
    for x in (X_LIMITS[0], -25, 0, 25, X_LIMITS[1]):
        for drop in (0, 40, Z_STROKE):
            moving = moving_parts(parts, x, drop)
            pose = stationary_envelope | moving
            collision_check(pose, f"x={x}, drop={drop}")
            keepout = cyl(x, SENSOR_Y, -146 - drop, 20, 100, Z)
            if any(volume_intersection(keepout, part) > 0.001 for part in pose.values()):
                raise ValueError(f"Sensor keep-out obstruction at x={x}, drop={drop}")
            tested_poses += 1

    left_overrun = parts["x_carriage"].translate((X_LIMITS[0] - 0.5, 0, 0))
    right_overrun = parts["x_carriage"].translate((X_LIMITS[1] + 0.5, 0, 0))
    up_overrun = parts["z_sensor_slide"].translate((0, 0, 0.5))
    down_overrun = parts["z_top_stop"].translate((0, 0, -Z_STROKE - 0.5))
    stops = (
        (left_overrun, parts["rail_left"]),
        (right_overrun, rail_blank),
        (up_overrun, parts["x_carriage"]),
        (down_overrun, parts["x_carriage"]),
    )
    if any(volume_intersection(moving, fixed) < 0.001 for moving, fixed in stops):
        raise ValueError("An axis limit lacks a physical stop")
    results.update(poses_checked=tested_poses, physical_stop_geometries_checked=len(stops),
                   wall_spans_mm=list(WALL_GAPS), sensor_keepout_diameter_mm=20,
                   sensor_keepout_depth_mm=100)
    pad, _ = fitted_pad(parts["printed_pad_screw"], 500)
    return static | {"printed_pad_screw": pad} | moving_parts(parts, 0, 40), results


def orient_for_print(name, shape):
    if name in {"rail_left", "rail_splice"}:
        shape = shape.rotate((0, 0, 0), X, 90)
    elif name in {"x_carriage", "rail_right", "printed_pad_screw", "z_sensor_slide"}:
        shape = shape.rotate((0, 0, 0), Y, 90)
    bounds = shape.BoundingBox()
    return shape.translate((-bounds.xmin, -bounds.ymin, -bounds.zmin))


def audit_print_overhangs(name, printable):
    """Find downward surfaces shallower than 45°, excluding the build plane."""
    import numpy as np

    vertices, faces = printable.tessellate(0.04, 0.10)
    triangles = np.asarray([v.toTuple() for v in vertices])[faces]
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    doubled_areas = np.linalg.norm(normals, axis=1)
    heights = triangles[:, :, 2]
    # Tessellated cones can vary slightly from their exact 45° CAD slope.
    angular_tolerance = cos(44 * pi / 180)
    steep = ((heights.max(axis=1) > 0.01)
             & (normals[:, 2] < -angular_tolerance * doubled_areas))
    if name == "rail_left":
        # The flat-printed left rail has two annular M5 head seats at Z=7.
        allowed = np.all(np.abs(heights - 7) < 0.01, axis=1)
        if np.any(steep & ~allowed) or not np.any(steep & allowed):
            raise ValueError(f"{name} has an unexpected overhang or missing screw head seat")
    # Ignore isolated mesh facets below 0.02 mm² at curved intersections.
    elif doubled_areas[steep].sum() / 2 > 0.02:
        raise ValueError(f"{name} has an overhang shallower than 45° away from the bed")
    return round(float(doubled_areas[steep].sum()) / 2, 2)


def write_compensated_stl(printable, path):
    """Apply the shrink inverse in machine XYZ, to the already oriented mesh."""
    import numpy as np

    shrink = np.asarray(PRINT_SHRINK_XYZ)
    if not np.all((0 <= shrink) & (shrink < 1)):
        raise ValueError("Expected linear shrink fractions between 0 and 1")
    nominal, faces = printable.tessellate(0.025, angularTolerance=0.06)
    positions = np.asarray([vertex.toTuple() for vertex in nominal])
    positions -= positions.min(axis=0)
    expanded = positions / (1 - shrink)
    size = expanded.max(axis=0)
    if np.any(size > H2D):
        raise ValueError(f"{path.name} exceeds the H2D envelope after compensation")
    # Weld coincident tessellation vertices on a 0.1 μm grid before writing STL.
    vertices = np.round(expanded, 4).astype("<f4")
    if not np.allclose(vertices * (1 - shrink), positions, atol=0.0001, rtol=0):
        raise ValueError("STL coordinates failed the shrink compensation round-trip")
    triangles = vertices[faces]
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    norm = np.linalg.norm(cross, axis=1)
    nondegenerate = norm > 0
    triangles = triangles[nondegenerate]
    if not len(triangles):
        raise ValueError(f"{path.name} has no nondegenerate triangles")
    records = np.empty(len(triangles), dtype=[("normal", "<f4", 3),
                                            ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
    records["normal"] = cross[nondegenerate] / norm[nondegenerate, None]
    records["vertices"] = triangles
    records["attribute"] = 0
    with path.open("wb") as output:
        output.write(b"Sensor jig: shrink-compensated in printer XYZ".ljust(80, b" "))
        output.write(struct.pack("<I", len(triangles)))
        output.write(records.tobytes())
    return [round(float(dimension), 3) for dimension in size]


def export_thread_fit_samples(parts):
    # Use sections of the production solids so the trial has the same pitch,
    # lead-in, wall thickness near the opening and orientation as the real parts.
    directory = ROOT / "fit-test"
    directory.mkdir(exist_ok=True)
    pad = parts["printed_pad_screw"]
    tip = pad.intersect(box(-SCREW_LENGTH - 1, -15, -15, 23, 30, 30))
    tip = fused(tip, cyl(-SCREW_LENGTH + 22, 0, 0, 36, 4, X))
    receiver = parts["rail_right"].intersect(box(RAIL_RIGHT - 22, -21, -21, 22, 42, 46))
    for name, shape, orientation in (("male", tip, "printed_pad_screw"),
                                      ("female", receiver, "rail_right")):
        if not shape.isValid() or len(shape.Solids()) != 1:
            raise ValueError(f"Invalid thread fit sample: {name}")
        printable = orient_for_print(orientation, shape)
        write_compensated_stl(printable, directory / f"{name}.stl")


COLORS = {
    "rail_left": (0.21, 0.35, 0.48), "rail_right": (0.21, 0.35, 0.48),
    "x_carriage": (0.94, 0.49, 0.19), "z_sensor_slide": (0.12, 0.61, 0.60),
    "z_top_stop": (0.12, 0.61, 0.60), "printed_pad_screw": (0.94, 0.49, 0.19),
    "sensor_reference": (0.78, 0.65, 0.31), "rail_splice": (0.37, 0.48, 0.62),
}


def render_view(parts, elevation, azimuth=69):
    """Orthographic triangle render with a depth buffer for hidden surfaces."""
    import numpy as np

    azimuth *= pi / 180
    angle = elevation * pi / 180
    toward_camera = np.asarray((cos(angle) * cos(azimuth),
                                cos(angle) * sin(azimuth), sin(angle)))
    right = np.asarray((-sin(azimuth), cos(azimuth), 0))
    up = np.cross(toward_camera, right)
    camera = np.stack((right, -up, toward_camera), axis=1)
    light = np.asarray((0.16, 0.55, 0.82))
    meshes = []
    for name, part in parts.items():
        if not part.Solids():
            continue
        vertices, faces = part.tessellate(0.3)
        points = np.asarray([vertex.toTuple() for vertex in vertices])
        triangles = points[faces]
        normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
        lengths = np.linalg.norm(normals, axis=1)
        facing = (lengths > 0) & (normals @ toward_camera > 0)
        brightness = 0.61 + 0.39 * np.maximum(0, normals[facing] @ light / lengths[facing])
        color = np.asarray(COLORS.get(name, (0.58, 0.6, 0.63)))
        meshes.append((triangles[facing] @ camera, brightness[:, None] * color))

    width, height = 1100, 850
    screen = np.concatenate([mesh[:, :, :2].reshape(-1, 2) for mesh, _ in meshes])
    lower, upper = screen.min(axis=0), screen.max(axis=0)
    scale = min(((width - 70) / (upper - lower)[0]), ((height - 60) / (upper - lower)[1]))
    offset = np.asarray((width, height)) / 2 - (lower + upper) * scale / 2
    pixels = np.full((height, width, 3), (245, 247, 250), dtype=np.uint8)
    depth = np.full((height, width), -np.inf)

    for mesh, shades in meshes:
        mesh[:, :, :2] = mesh[:, :, :2] * scale + offset
        for triangle, shade in zip(mesh, shades):
            a, b, c = triangle
            x0, y0 = np.floor(triangle[:, :2].min(axis=0)).astype(int)
            x1, y1 = np.ceil(triangle[:, :2].max(axis=0)).astype(int) + 1
            u, v = b - a, c - a
            determinant = u[0] * v[1] - u[1] * v[0]
            if abs(determinant) < 1e-8:
                continue
            y, x = np.ogrid[y0:y1, x0:x1]
            first = ((x - a[0]) * v[1] - (y - a[1]) * v[0]) / determinant
            second = (u[0] * (y - a[1]) - u[1] * (x - a[0])) / determinant
            z = a[2] + first * u[2] + second * v[2]
            region = depth[y0:y1, x0:x1]
            visible = (first >= 0) & (second >= 0) & (first + second <= 1) & (z > region)
            region[visible] = z[visible]
            pixels[y0:y1, x0:x1][visible] = np.round(shade * 255).astype(np.uint8)
    return pixels


def render_preview(parts):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    fig = plt.figure(figsize=(12, 6), facecolor="#f5f7fa")
    fig.suptitle("Sensor jig", x=0.05, y=0.95, ha="left", fontsize=23, weight="bold",
                 color="#1d3348")
    detail = box(-63, -40, -95, 126, 140, 180)
    views = (
        ("Assembly · 500 mm wall opening", parts, 24),
        ("Carriage and downward-facing M10 sensor",
         {name: part.intersect(detail) for name, part in parts.items()}, -12),
    )
    for index, (title, visible, elevation) in enumerate(views, 1):
        ax = fig.add_subplot(1, 2, index)
        ax.imshow(render_view(visible, elevation))
        ax.set_axis_off()
        ax.set_title(title, fontsize=12, color="#334b61")
    fig.text(0.05, 0.06, "Blue / rails    Orange / carriage and pressure pad    Teal / Z slide",
             color="#334b61", fontsize=11)
    fig.subplots_adjust(left=0.02, right=0.98, bottom=0.12, top=0.86, wspace=0.04)
    fig.savefig(ROOT / "assembly_preview.png", dpi=160)
    plt.close(fig)


def render_pad_preview(parts):
    from matplotlib import pyplot as plt

    rail_end = parts["rail_right"].intersect(box(136, -21, -21, 74, 42, 46))
    pad, _ = fitted_pad(parts["printed_pad_screw"], 500)
    section = box(132, 0, -34, 120, 35, 68)
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), facecolor="#f5f7fa")
    views = (("Single printed pad and screw", {"printed_pad_screw": parts["printed_pad_screw"]}),
             ("Section through the threaded rail and pad",
              {"rail_right": rail_end.intersect(section), "printed_pad_screw": pad.intersect(section)}))
    for ax, (title, solids) in zip(axes, views):
        ax.imshow(render_view(solids, 23, azimuth=235))
        ax.set_title(title, color="#334b61", fontsize=12)
        ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(ROOT / "pad_detail.png", dpi=160)
    plt.close(fig)


def main():
    parts, rail_blank = make_parts()
    sizes, shallow_surfaces = {}, {}
    oriented = {}
    for name, part in parts.items():
        if not part.isValid() or len(part.Solids()) != 1:
            raise ValueError(f"{name} is not one valid solid")
        printable = orient_for_print(name, part)
        oriented[name] = printable
        shallow_surfaces[name] = audit_print_overhangs(name, printable)
    assembly, results = validated_poses(parts, rail_blank)
    for directory in ("print", "step"):
        (ROOT / directory).mkdir(exist_ok=True)
    for name, part in parts.items():
        sizes[name] = write_compensated_stl(oriented[name], ROOT / "print" / f"{name}.stl")
        cq.exporters.export(part, str(ROOT / "step" / f"{name}.step"))
    model = cq.Assembly(name="sensor_jig")
    for name, part in assembly.items():
        model.add(part, name=name, color=cq.Color(*COLORS.get(name, (0.58, 0.6, 0.63))))
    model.export(str(ROOT / "sensor_jig.step"))
    render_preview(assembly)
    render_pad_preview(parts)
    export_thread_fit_samples(parts)
    results.update(status="passed", x_travel_mm=X_LIMITS[1] - X_LIMITS[0],
                   z_travel_mm=Z_STROKE, h2d_check_envelope_mm=H2D,
                   compensated_stl_sizes_mm=sizes, external_chamfer_mm=EDGE_CHAMFER,
                   assumed_linear_shrink_xyz=PRINT_SHRINK_XYZ,
                   stl_scale_xyz=[round(1 / (1 - axis), 8) for axis in PRINT_SHRINK_XYZ],
                   nominal_clearance_after_shrink_mm_per_side=RUNNING_GAP,
                   print_overhang_audit={
                       "target_minimum_slope_from_bed_deg": 45,
                       "mesh_angular_tolerance_deg": 1,
                       "mesh_sliver_threshold_mm2": 0.02,
                       "shallower_downward_surface_area_excluding_bed_mm2": shallow_surfaces,
                       "exceptions": "Two 1 mm radial annular M5 head seats on the left rail",
                   },
                   limitations=["Discrete CAD checks", "No slicer or physical print validation",
                                "No physical load or grip tests"])
    (ROOT / "validation.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
