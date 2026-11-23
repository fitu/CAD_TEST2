"""Build and check the wall-mounted sensor jig with a rotating pad, in millimetres."""
from itertools import combinations
from math import cos, pi, sin, sqrt
from pathlib import Path
import json

import cadquery as cq

ROOT = Path(__file__).resolve().parent
WALL_LEFT = -248  # Bare face of the fixed flange.
WALL_GAPS = (490, 500, 510)
RAIL_LEFT = -234
RAIL_RIGHT = 210
PRELOAD_NUT_X = RAIL_RIGHT - 13
PRELOAD_LOCK_X = 190
PAD_RADIUS = 34
PAD_DEPTH = 16
PAD_HEAD_SEAT = 8
KEEPER_DEPTH = 4
KEEPER_SCREWS_Z = (-22, 22)
X_LIMITS = (-209, 159)
Z_STROKE = 80
SENSOR_Y = 78
FITS = {"rail": 0.25, "splice": 0.30, "vertical": 0.25}
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
    shoulder, half_width = fit, 12 + fit
    return prism(
        [(x, -12 - fit, -half_width), (x, -12 - fit, half_width),
         (x, shoulder, half_width), (x, shoulder + half_width, 0),
         (x, shoulder, -half_width)],
        length, X,
    )


def rail_parts():
    cavity = splice_profile(-56, 112, FITS["splice"])
    # The wall flange and the right stop start on the same print plane as each rail.
    left = beveled(fused(box(RAIL_LEFT, -20, -20, 234, 40, 40),
                         box(-248, -20, -36, 14, 58, 72))).cut(cavity)
    right = beveled(fused(box(0, -20, -20, RAIL_RIGHT, 40, 40),
                          box(184, -20, 20, 6, 30, 4))).cut(cavity)
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
            right = right.cut(through, head, head_transition, nut)
        splice = splice.cut(through)

    # Fit an AF19 steel nut sideways. The nut loads the internal shoulder in compression.
    right = right.cut(roofed_hole((149, 0, 0), 13, RAIL_RIGHT - 148, X, Y),
                      hex_prism((PRELOAD_NUT_X, 0, 0), 19.5, 10.5, X),
                      box(PRELOAD_NUT_X, 0, -9.75, 10.5, 21, 19.5),
                      cyl(PRELOAD_LOCK_X, 5, 0, 4.4, 16, Y),
                      cyl(PRELOAD_LOCK_X, 14, 0, 5.6, 7, Y))
    mouths = [
        ("x", 0, lambda p: abs(p.y) < 14 and abs(p.z) < 14),
        ("y", -20, lambda p: abs(p.z) < 6 and any(abs(p.x - x) < 6 for x in SPLICE_BOLTS)),
        ("y", 20, lambda p: abs(p.z) < 6 and any(abs(p.x - x) < 6 for x in SPLICE_BOLTS)),
    ]
    left = bevel_openings(left, mouths)
    right = bevel_openings(right, mouths)
    return left.clean(), right.clean(), splice.clean()


def vertical_profile(z, length, fit=0):
    return prism(
        [(13 + fit, 39 - fit, z), (13 + fit, 57 + fit, z),
         (-4 - fit, 57 + fit, z), (-13 - 2 * fit, 48, z),
         (-4 - fit, 39 - fit, z)],
        length, Z,
    )


def carriage():
    structure = beveled(fused(box(-25, -26, -26, 50, 52, 52),
                              box(-25, 22, -23, 50, 13, 46),
                              box(-25, 33, -30, 50, 30, 60)))
    h = FITS["rail"]
    structure = structure.cut(
        box(-26, -20 - h, -20 - h, 52, 40 + 2 * h, 40 + 2 * h),
        vertical_profile(-31, 62, FITS["vertical"]),
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


def rotating_pad():
    # The wall face at X=PAD_DEPTH lies on the bed and carries the pressure.
    profile = []
    for i in range(32):
        angle = i * pi / 16
        radius = PAD_RADIUS - (2 if i % 2 else 0)
        profile.append((0, radius * cos(angle), radius * sin(angle)))
    blank = beveled(prism(profile, PAD_DEPTH, X))
    access = box(-1, 0, -9.8, PAD_HEAD_SEAT + 1, PAD_RADIUS + 1, 19.6)
    seat = hex_prism((-1, 0, 0), 19.6, PAD_HEAD_SEAT + 1, X)
    inserts = [cyl(-1, 0, z, 4.6, 7, X) for z in KEEPER_SCREWS_Z]
    return blank.cut(access, seat, *inserts).clean()


def bolt_head_keeper():
    plate = beveled(box(-KEEPER_DEPTH, -11, -29, KEEPER_DEPTH, 22, 58))
    bolt_clearance = cyl(-KEEPER_DEPTH - 1, 0, 0, 13, KEEPER_DEPTH + 2, X)
    screws = [cyl(-KEEPER_DEPTH - 1, 0, z, 3.4, KEEPER_DEPTH + 2, X)
              for z in KEEPER_SCREWS_Z]
    return plate.cut(bolt_clearance, *screws).clean()


def preload_bolt():
    shank_end = PAD_HEAD_SEAT - 7.5
    return fused(cyl(shank_end - 65, 0, 0, 12, 65, X),
                 hex_prism((shank_end, 0, 0), 19, 7.5, X))


def rotating_end(parts):
    end = {
        "rotating_pad": parts["rotating_pad"],
        "bolt_head_keeper": parts["bolt_head_keeper"],
        "M12_preload_bolt": preload_bolt(),
    }
    for i, z in enumerate(KEEPER_SCREWS_Z, 1):
        end[f"M3_keeper_screw_{i}"] = fused(cyl(-4, 0, z, 3, 10, X),
                                           cyl(-7, 0, z, 5.5, 3, X))
    return end


def wall_hardware(parts, gap, left_overlay=0, right_overlay=0):
    wall_face = WALL_LEFT - left_overlay + gap
    offset = (wall_face - right_overlay - PAD_DEPTH, 0, 0)
    end = {name: shape.translate(offset) for name, shape in rotating_end(parts).items()}
    nut = hex_prism((PRELOAD_NUT_X, 0, 0), 19, 10, X).cut(
        cyl(PRELOAD_NUT_X - 1, 0, 0, 12, 12, X)
    )
    end["M12_captive_nut"] = nut
    return end


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
    left, right, splice = rail_parts()
    return {
        "rail_left": left, "rail_right": right, "rail_splice": splice,
        "x_carriage": carriage(), "z_sensor_slide": sensor_slide(),
        "z_top_stop": top_stop(), "rotating_pad": rotating_pad(),
        "bolt_head_keeper": bolt_head_keeper(),
    }


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


def validate_rotating_end(parts):
    pad, keeper = parts["rotating_pad"], parts["bolt_head_keeper"]
    bolt = preload_bolt()
    for offset in (0, 4, 12, 24, 34, 46):
        if volume_intersection(pad, bolt.translate((0, offset, 0))) > 0.001:
            raise ValueError(f"Bolt head binds on side entry at {offset} mm")
    for angle in (-15, 15):
        turned = bolt.rotate((0, 0, 0), X, angle)
        if volume_intersection(pad, turned) < 0.1:
            raise ValueError("The pad does not key to the bolt head in both directions")
    if volume_intersection(keeper, bolt.translate((0, 3, 0))) < 0.1:
        raise ValueError("Installed keeper does not retain the head")
    if volume_intersection(pad, bolt.translate((0.5, 0, 0))) < 0.1:
        raise ValueError("A thrust face is missing from the head pocket")

    checked_settings, clearance, engagement = 0, float("inf"), {}
    lock = cyl(PRELOAD_LOCK_X, 6, 0, 4, 20, Y)
    for gap in WALL_GAPS:
        for left in (0, 2):
            for right in (0, 2):
                end = wall_hardware(parts, gap, left, right)
                shank = end["M12_preload_bolt"].BoundingBox()
                if not 149 < shank.xmin <= PRELOAD_NUT_X or shank.xmax <= PRELOAD_NUT_X + 10:
                    raise ValueError(f"Insufficient thread engagement at {gap} mm")
                if shank.xmin >= PRELOAD_LOCK_X - 2:
                    raise ValueError("The optional lock cannot reach the shank")
                for angle in (0, 45, 90, 180):
                    turned_end = {name: shape.rotate((0, 0, 0), X, angle)
                                  for name, shape in end.items() if name != "M12_captive_nut"}
                    nearest = min(shape.BoundingBox().xmin for name, shape in turned_end.items()
                                  if name != "M12_preload_bolt")
                    clearance = min(clearance, nearest - RAIL_RIGHT)
                    collision_check(turned_end | {
                        "rail_right": parts["rail_right"],
                        "M12_captive_nut": end["M12_captive_nut"],
                        "optional_M4_preload_lock": lock,
                    }, f"rotating end at {gap} mm, overlays {left}/{right} mm, angle {angle}")
                    checked_settings += 1
        engagement[str(gap)] = 10
    if clearance < 4:
        raise ValueError("Inadequate space between the turning pad and the rail")
    return {
        "preload_nut_thread_engagement_mm": engagement,
        "rotating_end_configurations_checked": checked_settings,
        "minimum_rotating_end_to_rail_mm": round(clearance, 3),
        "optional_wall_overlay_mm_per_side": [0, 2],
        "bolt_head_side_entry_positions_checked": 6,
        "keeper_retention_and_bidirectional_drive_checked": True,
    }


def validated_poses(parts):
    static = {name: parts[name] for name in ("rail_left", "rail_right", "rail_splice")}
    static.update(joint_hardware())
    results = validate_rotating_end(parts)
    tested_poses = 0
    for gap in WALL_GAPS:
        ends = wall_hardware(parts, gap)
        for x in (X_LIMITS[0], -25, 0, 25, X_LIMITS[1]):
            for drop in (0, 40, Z_STROKE):
                moving = moving_parts(parts, x, drop)
                pose = static | ends | moving
                collision_check(pose, f"gap={gap}, x={x}, drop={drop}")
                keepout = cyl(x, SENSOR_Y, -146 - drop, 20, 100, Z)
                if any(volume_intersection(keepout, part) > 0.001 for part in pose.values()):
                    raise ValueError(f"Sensor keep-out obstruction at x={x}, drop={drop}")
                tested_poses += 1

    # Deliberate overtravel must hit each physical stop.
    left_overrun = parts["x_carriage"].translate((X_LIMITS[0] - 0.5, 0, 0))
    right_overrun = parts["x_carriage"].translate((X_LIMITS[1] + 0.5, 0, 0))
    up_overrun = parts["z_sensor_slide"].translate((0, 0, 0.5))
    down_overrun = parts["z_top_stop"].translate((0, 0, -Z_STROKE - 0.5))
    stops = (
        (left_overrun, parts["rail_left"]),
        (right_overrun, parts["rail_right"]),
        (up_overrun, parts["x_carriage"]),
        (down_overrun, parts["x_carriage"]),
    )
    if any(volume_intersection(moving, fixed) < 0.001 for moving, fixed in stops):
        raise ValueError("An axis limit lacks a physical stop")
    results.update(poses_checked=tested_poses, physical_stop_geometries_checked=len(stops),
                   wall_spans_mm=list(WALL_GAPS), sensor_keepout_diameter_mm=20,
                   sensor_keepout_depth_mm=100)
    return static | wall_hardware(parts, 500) | moving_parts(parts, 0, 40), results


def orient_for_print(name, shape):
    if name in {"rail_left", "rail_right", "rail_splice"}:
        shape = shape.rotate((0, 0, 0), X, 90)
    elif name in {"x_carriage", "rotating_pad", "bolt_head_keeper", "z_sensor_slide"}:
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
    if name in {"rail_left", "rail_right"}:
        # Each rail has two flat annular M5 head seats, 1 mm wide at Z=7.
        allowed = np.all(np.abs(heights - 7) < 0.01, axis=1)
        if np.any(steep & ~allowed) or not np.any(steep & allowed):
            raise ValueError(f"{name} has an unexpected overhang or missing screw head seat")
    elif np.any(steep):
        raise ValueError(f"{name} has an overhang shallower than 45° away from the bed")
    return round(float(doubled_areas[steep].sum()) / 2, 2)


COLORS = {
    "rail_left": (0.21, 0.35, 0.48), "rail_right": (0.21, 0.35, 0.48),
    "x_carriage": (0.94, 0.49, 0.19), "z_sensor_slide": (0.12, 0.61, 0.60),
    "z_top_stop": (0.12, 0.61, 0.60), "rotating_pad": (0.21, 0.35, 0.48),
    "bolt_head_keeper": (0.94, 0.49, 0.19),
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
    fig.text(0.05, 0.06, "Blue / rail and rotating pad    Orange / X carriage    Teal / Z slide",
             color="#334b61", fontsize=11)
    fig.subplots_adjust(left=0.02, right=0.98, bottom=0.12, top=0.86, wspace=0.04)
    fig.savefig(ROOT / "assembly_preview.png", dpi=160)
    plt.close(fig)


def render_pad_preview(parts):
    from matplotlib import pyplot as plt

    captured = rotating_end(parts)
    loading = {
        "rotating_pad": parts["rotating_pad"],
        "M12_preload_bolt": captured["M12_preload_bolt"].translate((0, 37, 0)),
    }
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), facecolor="#f5f7fa")
    views = (("1. Slide the hex head in from the rim", loading),
             ("2. Install the keeper over the shank", captured))
    for ax, (title, solids) in zip(axes, views):
        ax.imshow(render_view(solids, 22, azimuth=140))
        ax.set_title(title, color="#334b61", fontsize=12)
        ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(ROOT / "pad_detail.png", dpi=160)
    plt.close(fig)


def main():
    parts = make_parts()
    assembly, results = validated_poses(parts)
    sizes, shallow_surfaces = {}, {}
    for directory in ("print", "step"):
        (ROOT / directory).mkdir(exist_ok=True)
    for name, part in parts.items():
        if not part.isValid() or len(part.Solids()) != 1:
            raise ValueError(f"{name} is not one valid solid")
        printable = orient_for_print(name, part)
        bounds = printable.BoundingBox()
        size = (bounds.xlen, bounds.ylen, bounds.zlen)
        if not all(dimension <= maximum for dimension, maximum in zip(size, H2D)):
            raise ValueError(f"{name} exceeds the selected H2D envelope: {size}")
        sizes[name] = [round(dimension, 3) for dimension in size]
        shallow_surfaces[name] = audit_print_overhangs(name, printable)
        cq.exporters.export(printable, str(ROOT / "print" / f"{name}.stl"),
                            tolerance=0.04, angularTolerance=0.10)
        cq.exporters.export(part, str(ROOT / "step" / f"{name}.step"))
    model = cq.Assembly(name="sensor_jig")
    for name, part in assembly.items():
        model.add(part, name=name, color=cq.Color(*COLORS.get(name, (0.58, 0.6, 0.63))))
    model.export(str(ROOT / "sensor_jig.step"))
    render_preview(assembly)
    render_pad_preview(parts)
    results.update(status="passed", x_travel_mm=X_LIMITS[1] - X_LIMITS[0],
                   z_travel_mm=Z_STROKE, h2d_check_envelope_mm=H2D,
                   oriented_print_sizes_mm=sizes, external_chamfer_mm=EDGE_CHAMFER,
                   print_overhang_audit={
                       "target_minimum_slope_from_bed_deg": 45,
                       "mesh_angular_tolerance_deg": 1,
                       "shallower_downward_surface_area_excluding_bed_mm2": shallow_surfaces,
                       "exceptions": "Two 1 mm radial annular M5 head seats on each rail",
                   },
                   limitations=["Discrete CAD checks", "No slicer or physical print validation",
                                "No physical load or grip tests"])
    (ROOT / "validation.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
