"""Reproduce illustrative Israeli procurement and PETG material allowances.

This is a budget model, not a supplier quote or a slicer/toolpath estimate.
"""
import argparse
import csv
import json
from pathlib import Path
import cadquery as cq

UNIT_ILS = {
    "bench_clamp_100mm": (25, 55),
    "ground_dowel_6x30": (3, 10), "ground_shaft_8x400": (30, 70),
    "threaded_rod_M6x160_cut_from_stock": (8, 20),
    "firm_backing_and_protective_pads_set": (10, 25),
    "thin_nonmarring_blade_tape": (5, 12),
    "nylon_tip_screw_M4x8": (2, 6),
    "stone_60x180x30": (60, 180), "stone_25x150x6": (30, 100),
}


def unit_price(name):
    if name in UNIT_ILS:
        return UNIT_ILS[name]
    if name.startswith("bolt_M4"):
        return .5, 1.5
    if name.startswith("set_screw_M4"):
        return .6, 2
    if name.startswith("bolt_M5"):
        return .6, 2
    if name.startswith("bolt_M6"):
        return .8, 2.5
    if name.startswith("bolt_M8"):
        return 1.5, 4
    if name.startswith("nut_"):
        return .2, .8
    if name.startswith("washer_"):
        return .1, .5
    raise ValueError(f"No price allowance for BOM item {name}")


def estimate(root):
    bom = json.loads((root / "cad/hardware_manifest.json").read_text())
    manifest = json.loads((root / "cad/part_manifest.json").read_text())
    rows = []
    for item, quantity in sorted(bom.items()):
        lo, hi = unit_price(item)
        rows.append([item, quantity, lo, hi, round(lo * quantity, 2), round(hi * quantity, 2),
                     "optional if already owned" if item.startswith("stone_") else ""])
    # Retain a procurement allowance for package sizes and spare fasteners.
    rows.append(["spare_fasteners_and_pack_size_allowance", 1, 10, 25, 10, 25, "budget allowance"])
    polymer_low = polymer_high = solid = 0.0
    for name, entry in manifest.items():
        if not entry["printed"] or entry.get("optional", False):
            continue
        s = cq.importers.importStep(str(root / entry["file"])).val()
        volume, area = s.Volume(), s.Area()
        solid += volume
        # Uniform shell equivalents bracket the orientation-dependent walls
        # and skins. First-order area*t overcounts overlaps; cap at solid V.
        for shell, infill, key in ((1.2, .4, "lo"), (2.4, .6, "hi")):
            skin = min(volume, area * shell)
            amount = skin + (volume - skin) * infill
            if key == "lo":
                polymer_low += amount
            else:
                polymer_high += amount
    # 1.27g/cm³ PETG and 15% support/brim/waste planning allowance.
    masses = [round(v / 1e6 * 1.27 * 1.15, 3) for v in (polymer_low, polymer_high)]
    rows.append(["PETG_1kg_spool", 2, 70, 120, 140, 240, "whole spools; includes unused filament"])
    with (root / "cad/cost_estimate.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["item", "quantity", "unit_low_ILS", "unit_high_ILS",
                         "total_low_ILS", "total_high_ILS", "note"])
        writer.writerows(rows)
    total = [round(sum(row[i] for row in rows), 2) for i in (4, 5)]
    stone = next(row for row in rows if row[0].startswith("stone_"))
    summary = {
        "currency": "ILS", "pricing_basis": "Illustrative Israeli retail allowances, VAT-inclusive where locally purchased; not live supplier quotations. Shipping, tools, labor and printer ownership excluded.",
        "total_with_stone_and_two_spools_ILS": total,
        "total_if_stone_owned_ILS": [round(total[0] - stone[4], 2), round(total[1] - stone[5], 2)],
        "printed_solid_cm3_including_setup_tools": round(solid / 1000, 3),
        "PETG_consumed_kg_estimate_including_15percent_waste": masses,
        "method": "Actual STEP volume/area; capped area*1.2/2.4mm uniform-shell equivalents and 40/60% infill. Engineering approximation, not sliced toolpaths; excludes failed full reprints.",
        "PETG_purchase": "Two 1kg spools at70–120ILS each. Recheck actual slicer material including supports before printing.",
    }
    (root / "cad/cost_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    estimate(parser.parse_args().root.resolve())
