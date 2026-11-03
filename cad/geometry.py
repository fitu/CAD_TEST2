"""Small shared primitives and conservative metric hardware envelopes."""
import math
import cadquery as cq


def box(x, y, z, center):
    return cq.Workplane("XY").box(x, y, z).translate(center)


def orient(shape, position, direction="z"):
    axes = {"-z": ((1, 0, 0), 180), "y": ((1, 0, 0), -90),
            "-y": ((1, 0, 0), 90), "x": ((0, 1, 0), 90),
            "-x": ((0, 1, 0), -90)}
    if direction in axes:
        axis, angle = axes[direction]
        shape = shape.rotate((0, 0, 0), axis, angle)
    return shape.translate(position)


def cyl(radius, length, position, direction="z"):
    return orient(cq.Workplane("XY").circle(radius).extrude(length), position, direction)


def hex_prism(af, height, position=(0, 0, 0), direction="z"):
    shape = cq.Workplane("XY").polygon(6, af / math.cos(math.pi / 6)).extrude(height)
    return orient(shape, position, direction)


def hardware_shape(kind, m, length=0):
    af = {4: 7, 5: 8, 6: 10, 8: 13, 10: 17}
    if kind == "bolt":
        return cyl(m / 2, length, (0, 0, 0)).union(hex_prism(af[int(m)], -.65 * m))
    if kind == "nut":
        return hex_prism(af[int(m)], .8 * m).cut(cyl(m / 2, .8 * m + 2, (0, 0, -1)))
    if kind == "washer":
        return cyl(m, 1.2, (0, 0, 0)).cut(cyl(m / 2 + .2, 3, (0, 0, -1)))
    if kind in {"shaft", "dowel", "threaded_rod", "set_screw"}:
        return cyl(m / 2, length, (0, 0, 0))
    raise ValueError(f"Unsupported hardware type: {kind}")


def stone_pose(shape, cfg):
    return shape.rotate((0, 0, 0), (1, 0, 0), cfg.angle).translate((0, cfg.edge_y, cfg.knife_z))
