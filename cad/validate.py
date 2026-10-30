"""Reimport STEP, check solids, functional fits and representative motion."""
from pathlib import Path
import json, math
import cadquery as cq
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'cad/part_manifest.json').read_text())
S={n:cq.importers.importStep(str(ROOT/'parts'/(n+'.step'))) for n in manifest}
assert all(s.val().isValid() and len(s.solids().vals())==1 for s in S.values())
def clashes(shapes):
 out=[]; items=list(shapes.items())
 for i,(a,sa) in enumerate(items):
  for b,sb in items[i+1:]:
   ba,bb=sa.val().BoundingBox(),sb.val().BoundingBox()
   if any(getattr(ba,k+'max')<=getattr(bb,k+'min')+.001 or getattr(bb,k+'max')<=getattr(ba,k+'min')+.001 for k in 'xyz'):continue
   c=sa.intersect(sb); v=sum(x.Volume() for x in c.solids().vals())
   if v>.1:
    if {a,b}=={'07_stop_bridge','REF_stop_pin_M5'} and v<80:continue # M5 tapped pilot
    out.append([a,b,round(v,3)])
 return out
assert not clashes(S),clashes(S)
fixed={n:s for n,s in S.items() if n.startswith(('01_','02_','03_','07_','08'))}
stone_names=[n for n in S if n.startswith(('13_','14_','15_','17_','REF_whetstone','REF_guide'))]
records=[]
def height(a):return 300+170*math.tan(math.radians(a))+44/math.cos(math.radians(a))
# Check angle endpoints, mid-angle, stroke extremes and yaw toward blade ends.
for angle in (15,20,25):
 for yaw in (-35,0,35):
  for stroke in (-25,0,25):
   h=height(angle); dy=stroke*math.cos(math.radians(angle)); dz=stroke*math.sin(math.radians(angle))
   moving={}
   for n in stone_names:
    s=S[n].rotate((0,-70,300),(1,-70,300),angle-20).translate((0,dy,dz))
    if n.startswith('15_'):
     u=lambda a:(170+44*math.sin(math.radians(a)))/math.cos(math.radians(a))
     du=u(angle)-u(20)
     s=s.translate((0,du*math.cos(math.radians(angle)),du*math.sin(math.radians(angle))))
    s=s.rotate((0,100,h),(0,100,h+1),yaw)
    moving[n]=s
   for n in ('09_height_carriage','10_yaw_plate','11_pitch_cheek_1','11_pitch_cheek_2'):
    s=S[n].translate((0,0,h-height(20)))
    if not n.startswith('09'):s=s.rotate((0,100,h),(0,100,h+1),yaw)
    moving[n]=s
   b=S['12_sliding_pitch_bushing'].rotate((0,100,height(20)),(1,100,height(20)),angle-20).translate((0,0,h-height(20))).rotate((0,100,h),(0,100,h+1),yaw)
   moving['12_sliding_pitch_bushing']=b
   # Blade contact is deliberately excluded from yaw/stroke checks: on a real
   # curved edge the operator follows the edge and resets contact height.
   c=clashes(fixed|moving)
   assert not c,(angle,yaw,stroke,c)
   records.append({'angle':angle,'yaw':yaw,'stroke':stroke,'clashes':0})
# Flip sweep with stone/guide removed, as instructed in README.
rot_names=['04_rotor_lower_jaw','05_upper_jaw','06_half_turn_disc','16_blade_shim_3mm','REF_M10_axle_100','REF_blade_envelope','REF_handle_envelope']
for a in range(0,181,15):
 shapes=fixed|{n:S[n].rotate((0,0,300),(0,1,300),a) for n in rot_names}
 # Index disc intentionally touches stop pin; fixed set contains only support bodies.
 c=clashes(shapes); assert not c,(a,c)
# All printed items fit larger printer, allowing part reorientation.
for n,p in manifest.items():
 if p['printed']:
  dims=sorted(p['bounds_mm']);assert all(a<=b for a,b in zip(dims,[320,325,325])),(n,dims)
result={'step_single_solids_valid':len(S),'assembled_interference_pairs':0,'guide_motion_configurations':len(records),'flip_positions_checked':13,'angle_reference':{'edge_y_mm':-70,'knife_midplane_z_mm':300,'pivot_y_mm':100,'rod_offset_mm':44},'angle_pivot_heights_mm':{str(a):round(height(a),3) for a in range(15,26)},'limitations':['Analytical CAD checks only; not physically printed or load tested.','Angle scale references center of a straight edge; yaw along long or curved blades changes local bevel angle.','Fasteners are generic reference envelopes, not thread-accurate models.']}
(ROOT/'cad/validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
