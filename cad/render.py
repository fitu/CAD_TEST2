"""Render the generated assembly and an illustrative exploded view headlessly.

Usage: python cad/render.py [--root PATH]
Exploded offsets illustrate removable subassemblies, not motion clearances.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cadquery as cq
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

COLORS = {
    "fixed": "#3e8490", "cartridge": "#8d729e", "height": "#d2a24d",
    "yaw": "#d2a24d", "pitch": "#d2a24d", "stone": "#598f9a",
    "rod_stops": "#cf9b45",
}
EXPLODED_OFFSETS = {
    "cartridge": (0, -85, 45), "height": (0, 10, 0),
    "yaw": (0, 20, 25), "pitch": (0, 20, 65),
    "stone": (50, -15, 115), "rod_stops": (50, -15, 115),
}


def relative_file(root: Path, filename: str) -> Path:
    path = (root / filename).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Manifest path escapes output directory: {filename}")
    return path


def load_components(root: Path) -> list[dict]:
    """Prefer full assembly instances, including heads, washers and pins."""
    manifest_file = root / "cad/assembly_manifest.json"
    if manifest_file.exists():
        manifest = json.loads(manifest_file.read_text())
        entries = [(entry["name"], entry) for entry in manifest] if isinstance(manifest, list) else list(manifest.items())
    else:
        manifest = json.loads((root / "cad/part_manifest.json").read_text())
        entries = list(manifest.items())
    components = []
    for name, entry in entries:
        shape = cq.importers.importStep(str(relative_file(root, entry.get("file", f"parts/{name}.step")))).val()
        vertices, triangles = shape.tessellate(0.8, 0.4)
        components.append({
            "name": name, "group": entry.get("group", "fixed"),
            "role": entry.get("role", ""),
            "printed": entry.get("printed", not name.startswith(("REF_", "HW_"))),
            "vertices": [vertex.toTuple() for vertex in vertices], "triangles": triangles,
        })
    if not components:
        raise ValueError("Cannot render an empty assembly")
    return components


def component_color(component: dict) -> str:
    name, role = component["name"].lower(), component["role"].lower()
    if "blade" in name or "handle" in name:
        return "#60666d"
    if "whetstone" in name or "abrasive" in role or "reference_stone" in name:
        return "#b7ad91"
    if not component["printed"]:
        return "#a4a9af"
    return COLORS.get(component["group"], "#3e8490")


def draw(root: Path, components: list[dict], profile: str, exploded: bool) -> Path:
    fig = plt.figure(figsize=(13, 10))
    ax = fig.add_subplot(111, projection="3d")
    low, high = [float("inf")] * 3, [float("-inf")] * 3
    for component in components:
        shift = EXPLODED_OFFSETS.get(component["group"], (0, 0, 0)) if exploded else (0, 0, 0)
        vertices = [tuple(v[i] + shift[i] for i in range(3)) for v in component["vertices"]]
        for vertex in vertices:
            for i in range(3):
                low[i], high[i] = min(low[i], vertex[i]), max(high[i], vertex[i])
        faces = [[vertices[index] for index in triangle] for triangle in component["triangles"]]
        ax.add_collection3d(Poly3DCollection(
            faces, facecolors=component_color(component), edgecolors="none", linewidths=0, rasterized=True,
        ))
    spans = [max(40, high[i] - low[i]) for i in range(3)]
    margins = [span * 0.08 for span in spans]
    ax.set(
        xlim=(low[0] - margins[0], high[0] + margins[0]),
        ylim=(low[1] - margins[1], high[1] + margins[1]),
        zlim=(min(0, low[2] - margins[2]), high[2] + margins[2]),
        xlabel="X / mm", ylabel="Y / mm", zlabel="Z / mm",
    )
    ax.set_box_aspect(spans)
    ax.view_init(elev=23, azim=-58)
    title = "Knife sharpener — revision B"
    title += " — exploded subassemblies" if exploded else " — reference assembly"
    ax.set_title(title + f"\n{profile} stone profile", fontsize=14, pad=14)
    ax.legend(handles=[
        Patch(facecolor=COLORS["fixed"], label="Bench-mounted frame / dock"),
        Patch(facecolor=COLORS["cartridge"], label="Removable indexed knife cartridge"),
        Patch(facecolor=COLORS["height"], label="Height / pitch adjustment and yaw lock"),
        Patch(facecolor="#b7ad91", label="Purchased stone"),
        Patch(facecolor="#a4a9af", label="Purchased hardware"),
    ], loc="upper left", fontsize=8, framealpha=0.95)
    if exploded:
        fig.text(0.5, 0.025,
                 "Illustrative separation only. Withdraw the stone head and release the cartridge before flipping it away from the frame.",
                 ha="center", fontsize=9, color="#34383d")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    path = root / ("exploded_preview.png" if exploded else "assembly_preview.png")
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    root = parser.parse_args().root.resolve()
    design_path = root / "cad/design.json"
    design = json.loads(design_path.read_text()) if design_path.exists() else {}
    profile = design.get("config", design).get("profile", "large")
    components = load_components(root)
    paths = [draw(root, components, profile, exploded) for exploded in (False, True)]
    print(json.dumps({"rendered_instances": len(components), "images": [str(path) for path in paths]}, indent=2))


if __name__ == "__main__":
    main()
