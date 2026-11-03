"""Generate revision B CAD, oriented print meshes and an authoritative BOM.

python cad/generate.py --profile large [--output /path/to/fresh/output]
The slim profile accepts a150x25x6mm stone. Units are millimetres.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import shutil
from dataclasses import replace
import cadquery as cq
from config import get_config
from geometry import cyl, hardware_shape, orient, stone_pose
from cartridge import build_cartridge
from carrier import build_carrier
from frame import build_frame
from guide import build_guide

SOURCE = Path(__file__).resolve().parents[1]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def generate(root, cfg):
    root = root.resolve()
    for folder in ("parts", "hardware", "assembly_parts", "print", "cad"):
        (root / folder).mkdir(parents=True, exist_ok=True)
    if root != SOURCE:
        for source in (SOURCE / "cad").glob("*.py"):
            shutil.copy2(source, root / "cad" / source.name)
        for name in ("README.md", "requirements.txt", ".gitignore"):
            if (SOURCE / name).exists():
                shutil.copy2(SOURCE / name, root / name)
        if (SOURCE / "docs").exists():
            shutil.copytree(SOURCE / "docs", root / "docs", dirs_exist_ok=True)
    parts, specs, module_meta = [], [], {}
    for name, builder in (("frame", build_frame), ("cartridge", build_cartridge),
                          ("guide", build_guide), ("carrier", build_carrier)):
        pp, hh, meta = builder(cfg)
        if name == "carrier":
            for part in pp:
                part["shape"] = stone_pose(part["shape"], cfg)
                rotation = part.get("print_rotation", {"axis": [1, 0, 0], "angle": 180})
                part["print_rotation"] = dict(rotation, angle=rotation["angle"] - cfg.angle)
            for hw in hh:
                hw["local_stone"] = True
        parts.extend(pp)
        specs.extend(hh)
        module_meta[name] = meta
    # Supply complete, matched jaw/shim options without making users edit CAD.
    # Only the selected pair is installed or included in the material budget.
    for thickness in range(1, 7):
        if thickness == cfg.blade_thickness:
            continue
        alternatives, _, _ = build_cartridge(replace(cfg, blade_thickness=float(thickness)))
        for p in alternatives:
            if p["name"].startswith("06_blade_shim_"):
                p = p.copy()
                component = "blade_shim"
                p.update(name=f"OPTION_{component}_for_{thickness}mm", installed=False,
                         optional=True, group="options", blade_thickness_mm=thickness)
                parts.append(p)
    parts.append(dict(name="REF_guide_rod_8x400", shape=stone_pose(
        cyl(4, cfg.rod_length, (0, cfg.rod_start, cfg.rod_offset), "y"), cfg),
        printed=False, group="stone", role="purchased ground smooth shaft"))
    specs.append(dict(kind="shaft", m=8, length=cfg.rod_length,
        position=(0, cfg.rod_start, cfg.rod_offset), direction="y", group="stone",
        role="smooth guide shaft", purchase_name="ground_shaft_8x400", reference_only=True))
    manifest, assembly_manifest, bom, names = {}, {}, Counter(), set()
    assembly = cq.Assembly(name=f"Sharpener_rev_B_{cfg.profile}_20deg")
    normalization = {"fixed_dock": "fixed", "knife": "cartridge"}

    def register(name, shape, printed, group, role, installed=True, **details):
        if name in names:
            raise ValueError(f"Duplicate part/instance name: {name}")
        names.add(name)
        solids = shape.solids().vals()
        if len(solids) != 1 or not solids[0].isValid() or solids[0].Volume() <= 0:
            raise ValueError(f"Invalid single-solid component: {name}")
        group = normalization.get(group, group)
        filename = f"parts/{name}.step"
        cq.exporters.export(shape, str(root / filename))
        bb = shape.val().BoundingBox()
        entry = dict(printed=printed, installed=installed, group=group, role=role,
            solids=1, volume_mm3=round(sum(s.Volume() for s in solids), 3),
            bounds_mm=[round(bb.xlen, 3), round(bb.ylen, 3), round(bb.zlen, 3)], file=filename)
        if printed:
            printable = shape
            rot = details.pop("print_rotation", None)
            if rot:
                if isinstance(rot, (list, tuple)):
                    rot = {"axis": rot[0], "angle": rot[1]}
                printable = printable.rotate((0, 0, 0), tuple(rot["axis"]), rot["angle"])
            b = printable.val().BoundingBox()
            printable = printable.translate((-b.xmin, -b.ymin, -b.zmin))
            stl = f"print/{name}.stl"
            cq.exporters.export(printable, str(root / stl), tolerance=.12, angularTolerance=.15)
            print_step = f"print/{name}.step"
            cq.exporters.export(printable, str(root / print_step))
            b = printable.val().BoundingBox()
            entry.update(print_stl=stl, print_file=print_step,
                print_bounds_mm=[round(b.xlen, 3), round(b.ylen, 3), round(b.zlen, 3)])
        entry.update(details)
        manifest[name] = entry
        if installed:
            instance = f"assembly_parts/{name}.step"
            shutil.copy2(root / filename, root / instance)
            assembly_manifest[name] = dict(entry, file=instance)
            color = (.95, .65, .23) if group in {"cartridge", "pitch", "height"} else (
                (.30, .60, .65) if printed else (.68, .70, .73))
            assembly.add(shape, name=name, color=cq.Color(*color))
    for p in parts:
        register(**p.copy())
    catalog = {}
    for hw in specs:
        hw = hw.copy()
        kind, m, length = hw["kind"], hw["m"], hw["length"]
        default_name = f"{kind}_M{m:g}" + (f"x{length:g}" if length else "")
        buy_name = hw.get("purchase_name", default_name)
        bom[buy_name] += 1
        if hw.get("reference_only"):
            assembly_manifest["REF_guide_rod_8x400"]["bom_name"] = buy_name
            continue
        canonical = hardware_shape(kind, m, length)
        if default_name not in catalog:
            filename = f"hardware/{default_name}.step"
            cq.exporters.export(canonical, str(root / filename))
            catalog[default_name] = filename
        shape = orient(canonical, hw["position"], hw["direction"])
        if hw.get("local_stone"):
            shape = stone_pose(shape, cfg)
        if hw.get("local_pitch"):
            shape = shape.rotate((0, 0, 0), (1, 0, 0), cfg.angle).translate((0, cfg.pivot_y, cfg.pivot_height()))
        n = sum(1 for item in assembly_manifest.values() if item.get("bom_name") == buy_name) + 1
        name = f"HW_{buy_name}_{n}"
        filename = f"assembly_parts/{name}.step"
        if len(shape.solids().vals()) != 1 or not shape.val().isValid():
            raise ValueError(name)
        cq.exporters.export(shape, str(root / filename))
        group = normalization.get(hw["group"], hw["group"])
        assembly_manifest[name] = dict(file=filename, printed=False, group=group,
            role=hw["role"], kind=kind, m=m, length=length, bom_name=buy_name,
            position=list(hw["position"]), direction=hw["direction"],
            local_stone=hw.get("local_stone", False))
        assembly.add(shape, name=name, color=cq.Color(.63, .65, .68))
    supplies = dict(module_meta["frame"].get("supplies", {}))
    supplies.update(firm_backing_and_protective_pads_set=1, thin_nonmarring_blade_tape=1,
                    bench_clamp_100mm=2)
    for name, count in supplies.items():
        bom[name] += count
    for name, item in assembly_manifest.items():
        if name.startswith("REF_") and "whetstone" in name:
            item["bom_name"] = f"stone_{cfg.stone_width:g}x{cfg.stone_length:g}x{cfg.stone_thickness:g}"
            bom[item["bom_name"]] += 1
        if item.get("kind") == "dowel":
            item["group"] = "fixed"
    groups = {}
    for name, item in assembly_manifest.items():
        groups.setdefault(item["group"], []).append(name)
    design = dict(revision="B", profile=cfg.profile, config=cfg.to_dict(), groups=groups,
        **module_meta, accepted_contact_pairs=[], unmodeled_supplies=supplies,
        operating_mode="positive_yaw_lock",
        motion={"angles_deg": [15, 20, 25], "yaws_deg": [0], "strokes_mm": [-cfg.stroke, 0, cfg.stroke]},
        validation_scope="Nominal CAD and sampled functional geometry; no physical/load certification",
        operation="Remove stone head, undo two draw bolts, pull cartridge forward, lift clear, flip off-fixture and reseat")
    write_json(root / "cad/part_manifest.json", manifest)
    write_json(root / "cad/assembly_manifest.json", assembly_manifest)
    write_json(root / "cad/hardware_manifest.json", dict(sorted(bom.items())))
    write_json(root / "cad/design.json", design)
    write_json(root / "cad/hardware_catalog.json", catalog)
    with (root / "cad/purchase_bom.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["item", "quantity"])
        writer.writerows(sorted(bom.items()))
    assembly.export(str(root / "sharpener_assembly.step"))
    print(json.dumps(dict(profile=cfg.profile, instances=len(assembly_manifest),
        printed_pieces=sum(p["printed"] and p["installed"] for p in manifest.values()),
        printed_solid_cm3=round(sum(p["volume_mm3"] for p in manifest.values()
            if p["printed"] and p["installed"]) / 1000, 2)), indent=2))
    return design


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("large", "slim"), default="large")
    parser.add_argument("--output", type=Path, default=SOURCE)
    args = parser.parse_args()
    generate(args.output, get_config(args.profile))


if __name__ == "__main__":
    main()
