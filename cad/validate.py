"""Reimport revision B CAD and verify assemblies, sampled motion and provenance."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
import struct
import sys
import cadquery as cq


def require(condition, message):
    if not condition:
        raise ValueError(message)


def dimensions(shape):
    b = shape.BoundingBox()
    return [b.xlen, b.ylen, b.zlen]


def single(path):
    solids = cq.importers.importStep(str(path)).solids().vals()
    require(len(solids) == 1, f'{path}: expected single solid, got {len(solids)}')
    s = solids[0]
    require(s.isValid() and s.Volume() > 0, f'{path}: invalid solid')
    return s


def stl_bounds(path):
    """Read the generated binary STL directly, independently of its manifest."""
    data = path.read_bytes()
    require(len(data) >= 84, f'Truncated print mesh: {path}')
    triangles = struct.unpack_from('<I', data, 80)[0]
    require(triangles > 0 and len(data) == 84+50*triangles, f'Invalid binary STL: {path}')
    low, high = [float('inf')]*3, [float('-inf')]*3
    for face in struct.iter_unpack('<12fH', data[84:]):
        for start in (3, 6, 9):
            for k in range(3):
                value = face[start+k]
                require(math.isfinite(value), f'Nonfinite STL vertex: {path}')
                low[k], high[k] = min(low[k], value), max(high[k], value)
    return low, high


def clashes(shapes, allowances, changed_names=None):
    boxes = {n: s.BoundingBox() for n, s in shapes.items()}
    failures, permitted = [], []
    for a, b in combinations(shapes, 2):
        if changed_names is not None and a not in changed_names and b not in changed_names:
            continue
        aa, bb = boxes[a], boxes[b]
        if any(min(getattr(aa, k+'max'), getattr(bb, k+'max')) -
               max(getattr(aa, k+'min'), getattr(bb, k+'min')) <= .001 for k in 'xyz'):
            continue
        v = shapes[a].intersect(shapes[b]).Volume()
        if v <= .1:
            continue
        record = {'parts': [a, b], 'overlap_mm3': round(v, 5)}
        allowance = allowances.get(frozenset((a, b)))
        if allowance and v <= allowance['max_overlap_mm3']:
            record['reason'] = allowance['reason']
            permitted.append(record)
        else:
            failures.append(record)
    return failures, permitted


def height(c, a):
    r = math.radians(a)
    return c['knife_z'] + (c['pivot_y']-c['edge_y'])*math.tan(r) + c['rod_offset']/math.cos(r)


def guide_u(c, a):
    r = math.radians(a)
    return (c['pivot_y']-c['edge_y']+c['rod_offset']*math.sin(r))/math.cos(r)


def pose(shapes, manifest, c, angle, yaw, stroke):
    ref = c['angle']
    h0, h = height(c, ref), height(c, angle)
    edge = (0, c['edge_y'], c['knife_z'])
    pitch0 = (0, c['pivot_y'], h0)
    pivot = (0, c['pivot_y'], h)
    r = math.radians(angle)
    result = {}
    for name, s in shapes.items():
        g = manifest[name].get('group', 'fixed')
        if g in ('stone', 'rod_stops'):
            s = s.rotate(edge, (1, edge[1], edge[2]), angle-ref)
            travel = stroke + (guide_u(c, angle)-guide_u(c, ref) if g == 'rod_stops' else 0)
            s = s.translate((0, travel*math.cos(r), travel*math.sin(r)))
            s = s.rotate(pivot, (0, pivot[1], h+1), yaw)
        elif g == 'pitch':
            s = s.rotate(pitch0, (1, pitch0[1], h0), angle-ref).translate((0, 0, h-h0))
            s = s.rotate(pivot, (0, pivot[1], h+1), yaw)
        elif g == 'yaw':
            s = s.translate((0, 0, h-h0)).rotate(pivot, (0, pivot[1], h+1), yaw)
        elif g == 'height':
            s = s.translate((0, 0, h-h0))
        result[name] = s
    return result


def rod_checks(c, design, angles, strokes, shapes):
    g = design.get('guide', {})
    start = g.get('rod_start_y', g.get('rod_start_local_y', c.get('rod_start', -110)))
    length, bearing = c['rod_length'], g.get('bushing_length_mm', 40)
    stop_width = g.get('stop_width_mm', 12)
    clearance = g.get('stop_clearance_mm', c['stroke'])
    rods = [s for n, s in shapes.items() if n.startswith('REF_guide_rod_')]
    require(len(rods) == 1, 'Expected one finite guide rod reference')
    local_rod = rods[0].translate((0, -c['edge_y'], -c['knife_z']))
    local_rod = local_rod.rotate((0, 0, 0), (1, 0, 0), -c['angle'])
    box = local_rod.BoundingBox()
    require(abs(box.ymin-start) < .01 and abs(box.ymax-(start+length)) < .01,
            'Exported rod endpoints differ from engagement metadata')
    require(abs((box.zmin+box.zmax)/2-c['rod_offset']) < .01,
            'Exported rod axis differs from working-face offset')
    min_engagement, min_margin = float('inf'), float('inf')
    for angle in angles:
        u = guide_u(c, angle)
        for stroke in strokes:
            rod_lo, rod_hi = start+stroke, start+length+stroke
            lo, hi = u-bearing/2, u+bearing/2
            engagement = min(rod_hi, hi)-max(rod_lo, lo)
            min_engagement = min(min_engagement, engagement)
            require(engagement >= bearing-.01, f'Rod leaves bearing: angle={angle}, stroke={stroke}')
            stop_lo = lo-clearance-stop_width+stroke
            stop_hi = hi+clearance+stop_width+stroke
            margin = min(stop_lo-rod_lo, rod_hi-stop_hi)
            min_margin = min(min_margin, margin)
            require(margin >= 0, f'Rod ends inside stop: angle={angle}, stroke={stroke}')
            require(min(clearance-stroke, clearance+stroke) >= -.01, 'End stop passes through bushing')
    stop_spans = g.get('stop_spans_local_y')
    if stop_spans:
        u = guide_u(c, c['angle'])
        require(abs(u-bearing/2-stop_spans[0][1]-clearance) < .01,
                'Front stop model does not have the stated free travel')
        require(abs(stop_spans[1][0]-u-bearing/2-clearance) < .01,
                'Rear stop model does not have the stated free travel')
    spans = g.get('carrier_clamp_spans_y', design.get('carrier', {}).get('rod_clamp_spans_y', []))
    for lo, hi in spans:
        require(start <= lo and start+length >= hi, f'Rod does not cover clamp {lo, hi}')
    return {'configurations': len(angles)*len(strokes),
            'minimum_bushing_engagement_mm': round(min_engagement, 3),
            'minimum_end_stop_end_margin_mm': round(min_margin, 3),
            'carrier_clamp_intervals_checked': len(spans)}


def angle_checks(c):
    d, off = c['pivot_y']-c['edge_y'], c['rod_offset']
    h = height(c, c['angle'])-c['knife_z']
    values = []
    for x in (0, 50, 100, 150):
        radius = math.hypot(d, x)
        theta = math.atan2(h, radius)-math.asin(off/math.hypot(h, radius))
        values.append({'edge_x_mm': x, 'yaw_deg': round(math.degrees(math.atan2(x, d)), 5),
                       'stone_inclination_deg': round(math.degrees(theta), 5)})
    require(abs(values[0]['stone_inclination_deg']-c['angle']) < .0001, 'Center angle formula mismatch')
    return {'pivot_heights_mm': {str(a): round(height(c, a), 5) for a in range(15, 26)},
            'conditional_centerline_contact_path': values,
            'limitation': 'Stone inclination under one centered-contact path, not an exact finished-bevel prediction.'}


def blade_variant_checks(shapes, manifest, c, design, allowances, axis, angles, strokes):
    """Exercise all supported shim/jaw settings, with the defined dummy blade.

    The code builds the corresponding cartridge geometry rather than treating
    a shim formula alone as evidence of blade/stone clearance. The upper jaw
    and its hardware move with thickness, so the module's actual hardware
    placements are rebuilt too, matched to the exported instance identities.
    """
    from dataclasses import fields, replace
    from config import Config
    from cartridge import build_cartridge
    from geometry import hardware_shape, orient
    config_names = {f.name for f in fields(Config)}
    cfg = Config(**{k: v for k, v in c.items() if k in config_names})
    cartridge_names = {n for n, e in manifest.items() if e.get('group') == 'cartridge'}
    moving_names = {n for n, e in manifest.items()
                    if e.get('group') in ('stone', 'rod_stops', 'pitch', 'yaw', 'height')}
    shim_names = [n for n in cartridge_names if n.startswith('06_blade_shim_')]
    require(len(shim_names) == 1, 'Expected one installed blade-centering shim')
    checked = 0
    for thickness in range(1, 7):
        parts, hardware, _ = build_cartridge(replace(cfg, blade_thickness=float(thickness)))
        variant = dict(shapes)
        for entry in parts:
            n = entry['name']
            if n.startswith('06_blade_shim_'):
                n = shim_names[0]
            if n in cartridge_names:
                variant[n] = entry['shape'].val()
        for spec in hardware:
            matches = [n for n, e in manifest.items()
                       if e.get('kind') == spec['kind'] and e.get('m') == spec['m']
                       and e.get('role') == spec['role']
                       and e.get('direction') == spec['direction']
                       and all(abs(a-b) < .001 for a, b in zip(e.get('position', [])[:2], spec['position'][:2]))]
            require(len(matches) == 1,
                    f'Cannot identify thickness-dependent hardware: {spec["role"]}, {spec["position"]}')
            n = matches[0]
            require(manifest[n]['length'] == spec['length'],
                    f'Blade variant unexpectedly changes purchased fastener length: {n}')
            variant[n] = orient(hardware_shape(spec['kind'], spec['m'], spec['length']),
                                spec['position'], spec['direction']).val()
        shim = variant[shim_names[0]].BoundingBox()
        blade = variant['REF_blade_envelope'].BoundingBox()
        require(abs(shim.zmax-(c['knife_z']-thickness/2)) < .01,
                f'{thickness}mm shim fails to center blade')
        require(abs((blade.zmax+blade.zmin)/2-c['knife_z']) < .01,
                f'{thickness}mm reference blade is not centered')
        for angle in angles:
            for stroke in strokes:
                posed = pose(variant, manifest, c, angle, 0, stroke)
                for seat in (0, 180):
                    seated = {n: s.rotate(axis[0], axis[1], seat) if n in cartridge_names else s
                              for n, s in posed.items()}
                    failures, _ = clashes(seated, allowances, moving_names | cartridge_names)
                    require(not failures,
                            f'{thickness}mm blade intersections angle={angle}, stroke={stroke}, cartridge={seat}: {json.dumps(failures)}')
                    checked += 1
    return {'thicknesses_mm': list(range(1, 7)), 'configurations': checked,
            'reference_blade': design.get('cartridge', {}).get('blade_profile', 'Defined tapered dummy blade'),
            'limitation': 'Other knives, bolsters, bevels, padding and protrusions require a dry fit.'}


def yaw_lock_check(shapes, manifest, design, c, yaws):
    require(design.get('operating_mode') == 'positive_yaw_lock', 'Unknown working yaw mode')
    require(c['yaw_limit'] == 0 and set(yaws) == {0}, 'Working motion must retain the positive yaw lock')
    lock = design['guide']['yaw_lock']
    diameter = lock['diameter_mm']
    x, y, _ = lock['axis_point']
    bolts = [n for n, e in manifest.items() if e.get('role') == lock['bolt_role']]
    nuts = [n for n, e in manifest.items() if e.get('role') == lock['nut_role']]
    require(len(bolts) == len(nuts) == 1, 'Positive yaw lock requires one modeled bolt and nut')
    bolt, nut = manifest[bolts[0]], manifest[nuts[0]]
    require(bolt.get('m') == nut.get('m') == diameter, 'Yaw lock fastener diameter mismatch')
    require(bolt.get('direction') == 'z', 'Yaw lock bolt must span both vertical stack interfaces')
    require(abs(bolt['position'][0]-x) < .01 and abs(bolt['position'][1]-y) < .01,
            'Yaw lock bolt is not on the stated common axis')
    start = bolt['position'][2]
    end = start + bolt['length']
    nut_bounds = shapes[nuts[0]].BoundingBox()
    require(start <= min(lock['shelf_z_span']) and end >= nut_bounds.zmax,
            'Yaw lock bolt does not engage the whole shelf/plate/nut stack')
    for name, span in (('05_height_carriage', lock['shelf_z_span']),
                       ('06_yaw_plate', lock['plate_z_span'])):
        low, high = sorted(span)
        ring = (cq.Workplane('XY').circle(diameter/2+.75).circle(diameter/2+.25)
                .extrude(high-low).translate((x, y, low)).val())
        volume = shapes[name].intersect(ring).Volume()
        require(volume >= ring.Volume()*.95,
                f'Yaw lock lacks surrounding bearing material in {name}')
    return {'positive_lock_verified': True, 'working_yaw_deg': 0,
            'bolt': bolts[0], 'nut': nuts[0],
            'procedure': 'Keep this bolt installed; reposition the knife in short sections with the protrusion gauge.'}


def validate(root):
    root = root.resolve()
    design = json.loads((root/'cad/design.json').read_text())
    c = design['config']
    require(design.get('revision', 'B') == 'B', 'Expected revision B')
    raw = json.loads((root/'cad/assembly_manifest.json').read_text())
    manifest = raw.get('instances', raw) if isinstance(raw, dict) else raw
    if isinstance(manifest, list):
        manifest = {entry['name']: entry for entry in manifest}
    require(manifest, 'No assembly instances')
    shapes = {n: single(root/e['file']) for n, e in manifest.items()}
    parts = json.loads((root/'cad/part_manifest.json').read_text())
    report = {'revision': 'B', 'status': 'running', 'profile': c.get('profile', design.get('profile', 'large')),
              'checks': {}, 'limitations': []}
    checks = report['checks']
    checks['exported_single_solids'] = len(shapes)
    count, volume, setup_count, setup_volume = 0, 0, 0, 0
    for n, e in parts.items():
        if e.get('installed', True):
            require(n in shapes, f'Part missing from assembly: {n}')
            s = shapes[n]
        else:
            s = single(root/e.get('file', f'parts/{n}.step'))
        require(abs(s.Volume()-e['volume_mm3']) <= max(.1, s.Volume()*.0001), f'Stale volume: {n}')
        if e.get('printed'):
            if e.get('installed', True):
                count += 1
                volume += s.Volume()
            else:
                setup_count += 1
                setup_volume += s.Volume()
            oriented_file = e.get('print_step_file', e.get('print_file'))
            if oriented_file:
                oriented = single(root/oriented_file)
                require(abs(oriented.Volume()-s.Volume()) <= max(.1, s.Volume()*.0001),
                        f'Print STEP differs from source component: {n}')
                dims = dimensions(oriented)
                require(all(a <= b+.01 for a, b in zip(dims, [325, 320, 325])), f'Printer fit: {n}, {dims}')
                bounds = oriented.BoundingBox()
                require(min(bounds.xmin, bounds.ymin, bounds.zmin) >= -.01,
                        f'Print STEP is not placed on the positive build plate: {n}')
                stl_file = e.get('print_stl')
                require(stl_file, f'Oriented part lacks slicer STL: {n}')
                lo, hi = stl_bounds(root/stl_file)
                require(all(abs((b-a)-expected) < .3 for a, b, expected in zip(lo, hi, dims)),
                        f'Print STL differs from oriented STEP bounds: {n}')
            else:
                dims = sorted(dimensions(s))
                require(all(a <= b+.01 for a, b in zip(dims, [320, 325, 325])), f'Printer fit: {n}, {dims}')
    checks.update(printed_parts=count, printed_solid_volume_cm3=round(volume/1000, 3),
                  setup_printed_parts=setup_count, setup_solid_volume_cm3=round(setup_volume/1000, 3),
                  printer_fit='Measured STEP bounds; axis realignment allowed unless print STEP supplied')
    allowances = {}
    for entry in design.get('allowed_contacts', []):
        pair = entry.get('parts', entry.get('pair'))
        require(isinstance(pair, list) and len(pair) == 2 and all(n in shapes for n in pair), 'Invalid allowed pair')
        require(entry.get('reason') and entry.get('max_overlap_mm3', 0) > 0, 'Contact needs reason and finite bound')
        allowances[frozenset(pair)] = entry
    failures, permitted = clashes(shapes, allowances)
    require(not failures, f'Static assembly intersections: {json.dumps(failures)}')
    checks.update(assembled_interference_pairs=0, bounded_intentional_contacts=permitted)
    assembly = cq.importers.importStep(str(root/'sharpener_assembly.step')).solids().vals()
    require(len(assembly) == len(manifest), f'Combined STEP count {len(assembly)} differs from manifest {len(manifest)}')
    require(all(s.isValid() and s.Volume() > 0 for s in assembly), 'Invalid combined assembly')
    checks.update(assembly_step_valid=True, assembly_solid_count=len(assembly))
    actual = Counter(e['bom_name'] for e in manifest.values() if e.get('bom_name'))
    supplies = design.get('unmodeled_supplies', {})
    require(all(isinstance(q, int) and q > 0 for q in supplies.values()), 'Invalid unmodeled supply declaration')
    require(not set(supplies).intersection(actual), 'Supplies must not duplicate modeled BOM instances')
    raw_hw = json.loads((root/'cad/hardware_manifest.json').read_text())
    expected = {n: e.get('quantity') if isinstance(e, dict) else e for n, e in raw_hw.items()}
    total = actual + Counter(supplies)
    require(dict(total) == expected, f'BOM mismatch: actual={dict(total)}, expected={expected}')
    checks['hardware_quantity_verified'] = sum(actual.values())
    checks['unmodeled_supplies'] = supplies
    motion = design.get('motion', {})
    angles = motion.get('angles_deg', [15, 20, 25])
    yaws = motion.get('yaws_deg', [-c['yaw_limit'], 0, c['yaw_limit']])
    strokes = motion.get('strokes_mm', [-c['stroke'], 0, c['stroke']])
    require(angles and yaws and strokes, 'Empty motion coverage')
    checks['working_yaw_lock'] = yaw_lock_check(shapes, manifest, design, c, yaws)
    groups = {e.get('group', 'fixed') for e in manifest.values()}
    require({'stone', 'pitch', 'yaw', 'height'}.issubset(groups), 'Required motion groups missing')
    blades = {n for n, e in manifest.items()
              if e.get('role') in ('blade', 'blade_envelope', 'handle', 'handle_envelope')
              or n in ('REF_blade_envelope', 'REF_handle_envelope')}
    require(blades, 'Blade and handle reference roles missing')
    cartridge = design.get('cartridge', {})
    names = {n for n, e in manifest.items() if e.get('group') == 'cartridge'}
    require(names, 'No cartridge group')
    axis = cartridge.get('flip_axis', [[0, 26, c['knife_z']], [0, 27, c['knife_z']]])
    structural_count = center_count = 0
    moving_names = {n for n, e in manifest.items()
                    if e.get('group') in ('stone', 'rod_stops', 'pitch', 'yaw', 'height')}
    for angle in angles:
        for yaw in yaws:
            for stroke in strokes:
                posed = pose(shapes, manifest, c, angle, yaw, stroke)
                if abs(yaw) > .0001:
                    # This is explicitly an envelope test, not an edge-following
                    # sharpening motion. Center contact retains blade and handle.
                    posed = {n: s for n, s in posed.items() if n not in blades}
                for seat in (0, 180):
                    seated = {n: s.rotate(axis[0], axis[1], seat) if n in names else s
                              for n, s in posed.items()}
                    failures, _ = clashes(seated, allowances,
                                          moving_names | (names if seat else set()))
                    require(not failures, f'Guide intersections angle={angle}, yaw={yaw}, stroke={stroke}, cartridge={seat}: {json.dumps(failures)}')
                    structural_count += 1
                    center_count += abs(yaw) < .0001
    checks.update(guide_motion_configurations=structural_count,
                  center_contact_configurations_with_blade_and_hardware=center_count,
                  nonzero_yaw_excluded_instances=sorted(blades) if any(yaws) else [],
                  rod_engagement=rod_checks(c, design, angles, strokes, shapes), angle_geometry=angle_checks(c))
    checks['blade_and_shim_variants'] = blade_variant_checks(
        shapes, manifest, c, design, allowances, axis, angles, strokes)
    extraction_info = cartridge.get('extraction', {})
    removed_groups = set(extraction_info.get('remove_hardware_groups', ['draw_screws']))
    stationary = {n: s for n, s in shapes.items()
                  if manifest[n].get('group') not in {'stone', 'rod_stops', 'pitch', 'yaw'} | removed_groups}
    for a in (0, 180):
        posed = {n: s.rotate(axis[0], axis[1], a) if n in names else s for n, s in stationary.items()}
        failures, _ = clashes(posed, allowances)
        require(not failures, f'Cartridge seat {a}deg intersections: {json.dumps(failures)}')
    extraction = cartridge.get('extraction_vector_mm')
    if extraction is None:
        extraction = [v*extraction_info.get('distance_mm', 30)
                      for v in extraction_info.get('vector', [0, -1, 0])]
    for fraction in (.25, .5, .75, 1):
        posed = {n: s.translate(tuple(fraction*v for v in extraction)) if n in names else s for n, s in stationary.items()}
        failures, _ = clashes(posed, allowances)
        require(not failures, f'Cartridge extraction {fraction} intersections: {json.dumps(failures)}')
    checks.update(indexed_cartridge_seats_checked=2, cartridge_extraction_positions_checked=4,
                  in_place_knife_flip='Not supported; remove cartridge and turn it outside the fixture')
    paths = set(root.glob('cad/*.py'))
    paths.update(root/e['file'] for e in manifest.values())
    paths.update(root/e.get('file', f'parts/{n}.step') for n, e in parts.items())
    paths.update(root.glob('print/**/*'))
    paths.update(root.glob('prints/**/*'))
    paths.update(root/p for p in ('cad/design.json', 'cad/part_manifest.json', 'cad/assembly_manifest.json',
                                'cad/hardware_manifest.json', 'sharpener_assembly.step'))
    paths.update(p for p in (root/'cad/hardware_catalog.json', root/'cad/purchase_bom.csv') if p.exists())
    paths.update(p for p in (root/'requirements.txt',) if p.exists())
    catalog_file = root/'cad/hardware_catalog.json'
    if catalog_file.exists():
        catalog = json.loads(catalog_file.read_text())
        paths.update(root/p for p in catalog.values())
    report['source_hashes'] = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted(paths) if p.is_file()}
    report['limitations'] = [
        'Analytical CAD checks; no physical printing, load, slip, retention or wet-use tests.',
        'Motion checks sample discrete poses and do not prove continuous swept-volume clearance.',
        'Working yaw is positively locked at zero; all supported guide samples include blade and handle. Free yaw is unsupported.',
        'Fixed-pivot geometry does not maintain a constant bevel across long or curved edges.',
        'Purchased-part models are generic envelopes without thread or commercial-tolerance details.',
        'The knife cartridge must be removed before flipping; in-place rotation is unsupported.',
    ]
    report.update(status='passed', generated_at=datetime.now(timezone.utc).isoformat())
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = p.parse_args()
    output = args.root/'cad/validation.json'
    output.write_text(json.dumps({'revision': 'B', 'status': 'running',
                                 'generated_at': datetime.now(timezone.utc).isoformat()}, indent=2)+'\n')
    try:
        result = validate(args.root)
    except Exception as error:
        result = {'revision': 'B', 'status': 'failed', 'failure': str(error),
                  'exception': type(error).__name__,
                  'generated_at': datetime.now(timezone.utc).isoformat()}
        output.write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result, indent=2), file=sys.stderr)
        return 1
    output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'source_hashes'}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
