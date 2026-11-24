"""Generate the printed butterfly locks and their carriage for the side-thread jig."""
from importlib.util import module_from_spec, spec_from_file_location
from math import sqrt
from pathlib import Path
import json
import shutil

import cadquery as cq

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "SENSOR JIG - SIDE THREAD"
spec = spec_from_file_location("side_thread", SOURCE / "generate.py")
base = module_from_spec(spec)
spec.loader.exec_module(base)

PITCH = 3.5
ROOT_RADIUS = 4.9
CREST_RADIUS = 6
FLANK_RUN = 1.25
HALF_CREST = 0.225
SCREW_LENGTH = 24
D_FLAT = -3
CLEARANCE = base.RUNNING_GAP
CONTACT_DEPTH = 19
RELEASE_DEPTH = 18
TOP_Y = -9
LOCK_PORTS = {
    "rail_top_lock": cq.Plane((0, TOP_Y, 39), (0, -1, 0), (0, 0, -1)),
    "slide_front_lock": cq.Plane((0, 76, 0), (0, 0, 1), (0, -1, 0)),
}
UNCHANGED_PARTS = ("rail_left", "rail_right", "rail_splice", "z_sensor_slide", "z_top_stop",
                   "printed_pad_screw", "printed_pad_screw_long")


def lock_thread(length, allowance=0):
    """A single-start trapezoidal thread on the local Z axis."""
    root, crest = ROOT_RADIUS + allowance, CREST_RADIUS + allowance
    inner = root - 0.15
    start = -PITCH
    slope = FLANK_RUN / (CREST_RADIUS - ROOT_RADIUS)
    flank_offset = allowance * sqrt(1 + slope ** 2)

    def width(radius):
        return HALF_CREST + slope * (CREST_RADIUS - radius) + flank_offset

    profile = cq.Wire.makePolygon(
        [cq.Vector(inner, 0, start - width(inner)),
         cq.Vector(crest, 0, start - width(crest)),
         cq.Vector(crest, 0, start + width(crest)),
         cq.Vector(inner, 0, start + width(inner))],
        close=True,
    )
    helix = cq.Wire.makeHelix(PITCH, length + 2 * PITCH, (inner + crest) / 2,
                             center=(0, 0, start))
    rib = cq.Solid.sweep(profile, [], helix, isFrenet=True)
    core = base.cyl(0, 0, -2 * PITCH, 2 * root, length + 4 * PITCH, base.Z)
    trimmed = base.fused(core, rib).intersect(base.cyl(0, 0, 0, 2 * crest + 0.2, length, base.Z))
    return trimmed.clean()


def lock_cutters():
    length = CONTACT_DEPTH + 2
    crest = CREST_RADIUS + CLEARANCE
    shoulder = (crest + 0.06) / sqrt(2)
    start = PITCH
    roof = base.prism(
        [(-shoulder, 3.4, start), (shoulder, 3.4, start), (shoulder, shoulder, start),
         (0, 2 * shoulder, start), (-shoulder, shoulder, start)],
        length - start + 0.2, base.Z,
    )
    thread = lock_thread(length, CLEARANCE).intersect(
        base.box(-8, -8, start, 16, 16, length - start + 1))
    # A faceted lead-in clears the helical surfaces at the outside plane
    # and prints with vertical walls and a 45-degree roof.
    web = 6.3
    entry = base.prism(
        [(-web, -web, -1), (web, -web, -1), (web, 2.7, -1),
         (0, 2.7 + web, -1), (-web, 2.7, -1)],
        start + 1.2, base.Z,
    )
    return thread, roof, entry


def butterfly_screw():
    taper_length = 2.6
    taper_start = SCREW_LENGTH - taper_length
    tip = cq.Solid.makeCone(CREST_RADIUS + 0.1, 4.15, taper_length, cq.Vector(0, 0, taper_start))
    envelope = base.fused(base.cyl(0, 0, 0, 2 * CREST_RADIUS + 0.2, taper_start, base.Z), tip)
    thread = lock_thread(SCREW_LENGTH).intersect(envelope)
    shaft = thread.intersect(base.box(-7, D_FLAT, 0, 14, 10, SCREW_LENGTH))
    # Both wings and the shaft share the same flat face on the print bed.
    outline = [
        (-5.5, 0), (-9, -3), (-15, -3), (-18, -6), (-18, -11),
        (-15.5, -13), (-8, -13), (-6, -10), (6, -10), (8, -13),
        (15.5, -13), (18, -11), (18, -6), (15, -3), (9, -3), (5.5, 0),
    ]
    handle = base.beveled(base.prism([(x, D_FLAT, z) for x, z in outline], 9, base.Y))
    return base.fused(handle, shaft)


def carriage():
    # Both bosses start at the carriage's X-side bed face. They need no
    # cantilever between the mounting face and the threaded opening.
    top_boss = base.box(-25, -20, 23, 50, 22, 16)
    front_boss = base.box(-25, 61, -11, 50, 15, 22)
    structure = base.beveled(base.fused(
        base.box(-25, -26, -26, 50, 52, 52),
        base.box(-25, 22, -23, 50, 13, 46),
        base.box(-25, 33, -30, 50, 30, 60),
        top_boss, front_boss,
    ))
    h = CLEARANCE
    cutters = lock_cutters()
    result = structure.cut(
        base.box(-26, -20 - h, -20 - h, 52, 40 + 2 * h, 40 + 2 * h),
        base.vertical_profile(-31, 62, CLEARANCE),
        *[cutter.moved(plane.location) for plane in LOCK_PORTS.values() for cutter in cutters],
    )
    square_openings = [("x", x, lambda p: abs(p.y) < 21 and abs(p.z) < 21)
                       for x in (-25, 25)]
    slide_openings = [("z", z, lambda p: abs(p.x) < 14 and 38 < p.y < 58)
                      for z in (-30, 30)]
    return base.bevel_openings(result, square_openings + slide_openings).clean()


def installed_screw(model, port, depth):
    extension = SCREW_LENGTH - depth
    threaded = model.rotate((0, 0, 0), base.Z, -360 * extension / PITCH)
    return threaded.translate((0, 0, -extension)).moved(LOCK_PORTS[port].location)


def moving_parts(parts, x, drop, depth):
    moving = base.moving_parts(parts, x, drop)
    for name in ("M5_x_lock", "M5_z_lock"):
        del moving[name]
    for port in LOCK_PORTS:
        moving[port] = installed_screw(parts["butterfly_screw"], port, depth).translate((x, 0, 0))
    return moving


def load_parts():
    parts = {name: cq.importers.importStep(str(SOURCE / "step" / f"{name}.step")).val()
             for name in UNCHANGED_PARTS}
    parts["x_carriage"] = carriage()
    parts["butterfly_screw"] = butterfly_screw()
    for name in ("x_carriage", "butterfly_screw"):
        if not parts[name].isValid() or len(parts[name].Solids()) != 1:
            raise ValueError(f"{name} is not one valid solid")
    return parts


def check_locks(parts):
    rail = base.box(-25, -20, -20, 50, 40, 40)
    guide = parts["z_sensor_slide"]
    stops = {"rail_top_lock": rail, "slide_front_lock": guide}
    samples = [CONTACT_DEPTH - PITCH * fraction / 4 for fraction in range(5)]
    screw = parts["butterfly_screw"]
    checked = 0
    for port, target in stops.items():
        for depth in [*samples, RELEASE_DEPTH, CONTACT_DEPTH + 0.25]:
            posed = installed_screw(screw, port, depth)
            if base.volume_intersection(posed, parts["x_carriage"]) > 0.01:
                raise ValueError(f"{port} thread binds at depth {depth}")
            overlap = base.volume_intersection(posed, target)
            if depth <= CONTACT_DEPTH and overlap > 0.01:
                raise ValueError(f"{port} hits the guide before reaching the clamping depth")
            if depth > CONTACT_DEPTH and overlap < 0.1:
                raise ValueError(f"{port} has no load-bearing contact at the tip")
            checked += 1
        seated = installed_screw(screw, port, CONTACT_DEPTH)
        released = installed_screw(screw, port, RELEASE_DEPTH)
        if seated.distance(target) > 0.001 or abs(released.distance(target) - 1) > 0.001:
            raise ValueError(f"{port} does not have the expected contact and release gap")
    for depth in samples:
        first, second = (installed_screw(screw, port, depth) for port in LOCK_PORTS)
        if base.volume_intersection(first, second) > 0.001:
            raise ValueError("The lock handles interfere")
    return checked


def check_motion(parts):
    left, right_blank, splice = base.rail_parts()
    blank_frame = {"rail_left": left, "rail_right": right_blank, "rail_splice": splice}
    blank_frame.update(base.joint_hardware())
    limits = base.X_LIMITS
    states = 0
    # Screws in the released positions are free of the moving targets. The
    # pressure screw is outside the carriage's travel, as in the parent frame.
    for x in (limits[0], base.RAIL_SEAM - 25, base.RAIL_SEAM, base.RAIL_SEAM + 25, limits[1]):
        for drop in (0, 40, base.Z_STROKE):
            moving = moving_parts(parts, x, drop, RELEASE_DEPTH)
            pair = {name: moving.pop(name) for name in LOCK_PORTS}
            base.collision_check(blank_frame | moving, f"x={x}, drop={drop}")
            for name, installed in pair.items():
                guides = dict(blank_frame | moving)
                del guides["x_carriage"]  # The relative thread fit is checked in check_locks().
                for neighbor, part in guides.items():
                    a, b = installed.BoundingBox(), part.BoundingBox()
                    if (min(a.xmax, b.xmax) <= max(a.xmin, b.xmin)
                            or min(a.ymax, b.ymax) <= max(a.ymin, b.ymin)
                            or min(a.zmax, b.zmax) <= max(a.zmin, b.zmin)):
                        continue
                    if base.volume_intersection(installed, part) > 0.01:
                        raise ValueError(f"{name} collides with {neighbor} at x={x}, drop={drop}")
            keepout = base.cyl(x, base.SENSOR_Y, -146 - drop, 20, 100, base.Z)
            if any(base.volume_intersection(keepout, part) > 0.001
                   for part in (blank_frame | moving | pair).values()):
                raise ValueError(f"Obstruction below the sensor at x={x}, drop={drop}")
            states += 1

    stop_trials = (
        (parts["x_carriage"].translate((limits[0] - 0.5, 0, 0)), left),
        (parts["x_carriage"].translate((limits[1] + 0.5, 0, 0)), right_blank),
        (parts["z_sensor_slide"].translate((0, 0, 0.5)), parts["x_carriage"]),
        (parts["z_top_stop"].translate((0, 0, -base.Z_STROKE - 0.5)), parts["x_carriage"]),
    )
    if any(base.volume_intersection(moving, fixed) < 0.001 for moving, fixed in stop_trials):
        raise ValueError("An axis limit lacks a physical stop")

    screw = parts["butterfly_screw"]
    for x in (limits[0], base.RAIL_SEAM, limits[1]):
        loaded = installed_screw(screw, "rail_top_lock", CONTACT_DEPTH + 0.25).translate((x, 0, 0))
        if sum(base.volume_intersection(loaded, rail) for rail in (left, right_blank)) < 0.1:
            raise ValueError(f"Rail lock lacks contact at x={x}")
    return states, len(stop_trials)


def copy_reference_assets():
    for folder in ("step", "print", "d-option", "fit-test"):
        (ROOT / folder).mkdir(exist_ok=True)
    for name in UNCHANGED_PARTS:
        for folder, suffix in (("step", ".step"), ("print", ".stl")):
            path = Path(folder) / (name + suffix)
            shutil.copyfile(SOURCE / path, ROOT / path)
    for folder in ("d-option", "fit-test"):
        for path in (SOURCE / folder).iterdir():
            if path.is_file():
                shutil.copyfile(path, ROOT / folder / path.name)
    shutil.copyfile(SOURCE / "pad_detail.png", ROOT / "pad_detail.png")


def save_assembly(parts, filename):
    assembly = cq.Assembly(name=filename.stem)
    colors = base.COLORS | {"rail_top_lock": (0.52, 0.31, 0.72),
                            "slide_front_lock": (0.52, 0.31, 0.72)}
    for name, part in parts.items():
        assembly.add(part, name=name, color=cq.Color(*colors.get(name, (0.58, 0.60, 0.63))))
    assembly.export(str(filename))


def render_previews(assembly, parts):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    base.ROOT = ROOT
    base.COLORS.update(rail_top_lock=(0.52, 0.31, 0.72), slide_front_lock=(0.52, 0.31, 0.72),
                       butterfly_screw=(0.52, 0.31, 0.72))
    base.render_preview(assembly)
    view = {name: assembly[name] for name in ("x_carriage", "z_sensor_slide", *LOCK_PORTS)}
    view["rail_right"] = assembly["rail_right"].intersect(base.box(-65, -24, -24, 130, 50, 48))
    view["rail_left"] = assembly["rail_left"].intersect(base.box(-65, -24, -24, 130, 50, 48))
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), facecolor="#f5f7fa")
    for axis, (title, image) in zip(axes, (
            ("Upper rail lock and front slider lock", base.render_view(view, 37, 143)),
            ("Butterfly screw with D-flat for side printing",
             base.render_view({"butterfly_screw": parts["butterfly_screw"]}, 24, 253)),
    )):
        axis.imshow(image)
        axis.set_title(title, color="#334b61", fontsize=12)
        axis.set_axis_off()
    fig.tight_layout()
    fig.savefig(ROOT / "lock_detail.png", dpi=160)
    plt.close(fig)


def main():
    parts = load_parts()
    lock_checks = check_locks(parts)
    states, stops = check_motion(parts)
    copy_reference_assets()
    report = json.loads((SOURCE / "validation.json").read_text())
    sizes = report["compensated_stl_sizes_mm"]
    slopes = report["print_overhang_audit"]["shallower_downward_surface_area_excluding_bed_mm2"]
    for name in ("x_carriage", "butterfly_screw"):
        shape = parts[name]
        if name == "butterfly_screw":
            shape = shape.rotate((0, 0, 0), base.X, 90)
        printable = base.orient_for_print(name, shape)
        sizes[name], slopes[name] = base.write_compensated_stl(printable, ROOT / "print" / f"{name}.stl")
        cq.exporters.export(parts[name], str(ROOT / "step" / f"{name}.step"))

    coupon = parts["x_carriage"].intersect(base.box(-13, -20, 27, 38, 22, 12))
    coupon = base.orient_for_print("x_carriage", coupon)
    base.write_compensated_stl(coupon, ROOT / "fit-test" / "butterfly_female.stl")

    stationary = {name: parts[name] for name in ("rail_left", "rail_right", "rail_splice")}
    pressure_pad, _ = base.fitted_pad(parts["printed_pad_screw"], 500)
    stationary["printed_pad_screw"] = pressure_pad
    stationary.update(base.joint_hardware())
    assembly = stationary | moving_parts(parts, 0, 40, CONTACT_DEPTH)
    save_assembly(assembly, ROOT / "sensor_jig.step")
    render_previews(assembly, parts)
    report.update(
        poses_checked=states,
        physical_stop_geometries_checked=stops,
        lock_variant={
            "locations": ["top of horizontal rail", "front of vertical slide"],
            "interchangeable_printed_screws": 2,
            "thread_major_diameter_mm": 2 * CREST_RADIUS,
            "thread_root_diameter_mm": 2 * ROOT_RADIUS,
            "thread_pitch_mm": PITCH,
            "shaft_length_mm": SCREW_LENGTH,
            "wing_span_mm": 36,
            "tip_retraction_mm": CONTACT_DEPTH - RELEASE_DEPTH,
            "thread_rotation_and_contact_positions_checked": lock_checks,
        },
    )
    (ROOT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
