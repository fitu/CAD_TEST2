"""Create a deterministic revision B source/CAD bundle after validation.

Usage: python cad/package.py [--root PATH] [--output PATH]
Every hashed validation input must still match. Packaging does not establish
physical fit, strength or printed-part accuracy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def resolve_file(root: Path, name: str) -> Path:
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"File escapes output directory: {name}")
    if not path.is_file():
        raise ValueError(f"Required bundle file is missing: {name}")
    return path


def verified_inputs(root: Path) -> dict[str, str]:
    report = json.loads(resolve_file(root, "cad/validation.json").read_text())
    if report.get("revision") != "B" or report.get("status") != "passed":
        raise ValueError("A passing revision B validation report is required; run cad/validate.py first")
    hashes = report.get("source_hashes")
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError("Validation report has no source_hashes; regenerate validation before packaging")
    required = {
        "cad/generate.py", "cad/validate.py", "cad/design.json", "cad/part_manifest.json",
        "cad/assembly_manifest.json", "sharpener_assembly.step",
    }
    missing = required.difference(hashes)
    if missing:
        raise ValueError(f"Validation did not hash required inputs: {', '.join(sorted(missing))}")
    for name, expected in hashes.items():
        actual = hashlib.sha256(resolve_file(root, name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Validation is stale: {name} changed; rerun cad/validate.py")
    return hashes


def collect_files(root: Path, hashes: dict[str, str]) -> list[Path]:
    names = set(hashes)
    names.update({"README.md", "requirements.txt", "cad/validation.json", "assembly_preview.png", "exploded_preview.png"})
    if (root / ".gitignore").is_file():
        names.add(".gitignore")
    manifest = json.loads(resolve_file(root, "cad/assembly_manifest.json").read_text())
    entries = manifest if isinstance(manifest, list) else manifest.values()
    for entry in entries:
        name = entry["file"]
        if name not in hashes:
            raise ValueError(f"Assembly instance was not included in validation hashes: {name}")
        names.add(name)
    catalog_path = root / "cad/hardware_catalog.json"
    if catalog_path.exists():
        catalog = json.loads(catalog_path.read_text())
        for entry in catalog.values():
            name = entry["file"] if isinstance(entry, dict) else entry
            if name not in hashes:
                raise ValueError(f"Hardware catalog file was not included in validation hashes: {name}")
            names.add(name)
    # Never include caches, previous archives, .git or unrelated workspace data.
    for folder in ("cad", "docs", "print", "prints", "hardware"):
        directory = root / folder
        if directory.exists():
            for file in directory.rglob("*"):
                if not file.is_file() or "__pycache__" in file.parts:
                    continue
                if file.suffix.lower() in {".py", ".md", ".json", ".csv", ".stl", ".3mf", ".svg", ".png"}:
                    names.add(file.relative_to(root).as_posix())
    for pattern in ("*.csv", "LICENSE*", "COST*.md"):
        names.update(file.relative_to(root).as_posix() for file in root.glob(pattern) if file.is_file())
    files = [resolve_file(root, name) for name in sorted(names)]
    assembly_mtime = resolve_file(root, "sharpener_assembly.step").stat().st_mtime
    for name in ("assembly_preview.png", "exploded_preview.png"):
        if resolve_file(root, name).stat().st_mtime < assembly_mtime:
            raise ValueError(f"Stale preview: {name}; run cad/render.py after generation")
    return files


def write_bundle(root: Path, output: Path, files: list[Path]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for file in files:
                info = zipfile.ZipInfo(file.relative_to(root).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, file.read_bytes())
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    hashes = verified_inputs(root)
    files = collect_files(root, hashes)
    output = args.output.resolve() if args.output else root / "knife_sharpener_rev_B.zip"
    if output in files:
        raise ValueError("Bundle output must not overwrite an input file")
    write_bundle(root, output, files)
    print(json.dumps({"bundle": str(output), "files": len(files), "bytes": output.stat().st_size,
                      "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}, indent=2))


if __name__ == "__main__":
    main()
