"""Parametric prototype. Units mm; run with CadQuery 2.7."""
from pathlib import Path
import math, json
import cadquery as cq
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'parts'; OUT.mkdir(exist_ok=True)
parts={}; Z=300; assembly=cq.Assembly(name='Sharpener_20deg')
def box(x,y,z,c): return cq.Workplane('XY').box(x,y,z).translate(c)
def cyl(r,h,p,axis='z'):
 s=cq.Workplane('XY').circle(r).extrude(h)
 if axis=='y': s=s.rotate((0,0,0),(1,0,0),-90)
 if axis=='x': s=s.rotate((0,0,0),(0,1,0),90)
 return s.translate(p)
def hole(s,r,h,p,axis='z'): return s.cut(cyl(r,h,p,axis))
def add(name,s,color=(.3,.55,.7),printed=True):
 if not s.val().isValid(): raise ValueError(name+' invalid')
 cq.exporters.export(s,str(OUT/(name+'.step')))
 parts[name]={'printed':printed,'solids':len(s.solids().vals()),'volume_mm3':round(s.val().Volume(),1),'bounds_mm':[round(v,2) for v in (s.val().BoundingBox().xlen,s.val().BoundingBox().ylen,s.val().BoundingBox().zlen)]}
 assembly.add(s,name=name,color=cq.Color(*color))
 return s
# Main base: sealed bottom, open ballast reservoir, removable structural lid.
base=box(300,310,32,(0,40,16)).cut(box(260,270,32,(0,40,20)))
for x in (-140,140):
 for y in (-105,185):
  base=hole(base,2.8,40,(x,y,-1))
  pocket=cq.Workplane('XY').polygon(6,9.6).extrude(4.3).translate((x,y,0))
  base=base.cut(pocket)
add('01_ballast_base',base)
lid=box(300,310,6,(0,40,35))
for x in (-140,140):
 for y in (-105,185): lid=hole(lid,2.8,8,(x,y,31))
for y in (20,60):
 for x in (-24,24): lid=hole(lid,2.8,8,(x,y,31))
for y in (155,185):
 for x in (-110,110): lid=hole(lid,3.3,8,(x,y,31))
add('02_structural_lid',lid)
# Two axle pedestals; long vertical bolts fasten each through lid.
for i,y in enumerate((20,60)):
 s=box(64,20,280,(0,y,178))
 s=hole(s,10.3,24,(0,y-12,Z),'y')
 for x in (-24,24): s=hole(s,2.8,284,(x,y,36))
 add(f'03_pedestal_{i+1}',s)
# Rotor lower jaw, round shaft and keyed hex tail, one printed component.
rotor=box(96,50,8,(0,-20,88)).union(cyl(10,74,(0,0,100),'y'))
key=cq.Workplane('XY').polygon(6,19.63).extrude(12).rotate((0,0,0),(1,0,0),-90).translate((0,74,100))
rotor=rotor.union(key)
rotor=hole(rotor,5.3,124,(0,-14,100),'y')
rotor=hole(rotor,10,14,(0,-14,100),'y') # Standard M10 tie rod stiffens axle.
for x in (-35,35): rotor=hole(rotor,3.3,20,(x,-16,82))
# Rear fulcrum supports upper jaw without relying on blade thickness.
# Rear jack screws bear against the solid lower jaw.
add('04_rotor_lower_jaw',rotor.translate((0,0,Z-100)))
upper=cq.Workplane('YZ').polyline([(-44,201.5),(-24,201.5),(-10,208),(5,208),(5,216),(0,214),(-24,206),(-44,204.5)]).close().extrude(96).translate((-48,0,0))
for x in (-35,35):
 upper=hole(upper,3.5,30,(x,-16,198))
 upper=hole(upper,2.1,30,(x,0,198))
upper=upper.cut(box(24,10,14,(0,2,204)))
add('05_upper_jaw',upper.translate((0,0,100)))
for t in range(1,7):
 h=8-t/2
 shim=box(90,16,h,(0,-34,292+h/2))
 if t==3: add('16_blade_shim_3mm',shim,(.6,.7,.4))
 cq.exporters.export(shim,str(OUT/f'OPTION_shim_for_{t}mm_blade.step'))
# Nominal 180-degree stop disc; separate pin locks either indexed position.
disc=cyl(34,8,(0,76,100),'y')
hexhole=cq.Workplane('XY').polygon(6,20.1).extrude(12).rotate((0,0,0),(1,0,0),-90).translate((0,74,100))
disc=disc.cut(hexhole)
# Slot swept semicircle, endpoint centers at (+/-26,0) in XZ.
slot=cq.Workplane('XZ').moveTo(26,0).threePointArc((0,26),(-26,0)).wire().toPending()
# Endpoint offset compensates nominal 5 mm pin in a 5.6 mm slot.
outer=cyl(28.8,12,(0,74,100),'y'); inner=cyl(23.2,14,(0,73,100),'y')
arc=outer.cut(inner).intersect(box(80,20,40,(0,80,120.3)))
for x in (-math.sqrt(26**2-.3**2),math.sqrt(26**2-.3**2)): arc=arc.union(cyl(2.8,12,(x,74,100.3),'y'))
disc=disc.cut(arc)
for x in (-15,15): disc=hole(disc,2.6,12,(x,74,100),'y')
add('06_half_turn_disc',disc.translate((0,0,Z-100)),(.9,.6,.2))
# Stop bridge behind disc, pins are inserted from back. Clear axle/nut.
bridge=box(80,12,8,(0,92,42))
for x in (-34,34): bridge=bridge.union(box(12,12,262,(x,92,169)))
bridge=bridge.union(box(80,12,12,(0,92,Z)))
bridge=hole(bridge,10,16,(0,84,Z),'y')
bridge=hole(bridge,2.1,16,(26,84,Z),'y')
bridge=hole(bridge,2.6,16,(15,84,Z),'y')
for x in (-34,34):
 bridge=hole(bridge,2.8,14,(x,92,36)); lid=hole(lid,2.8,8,(x,92,31))
add('07_stop_bridge',bridge)
# Rewrite lid now that rear bridge holes are known.
parts.pop('02_structural_lid'); assembly.remove('02_structural_lid'); add('02_structural_lid',lid)
# Tower with dual vertical adjustment slots. Feet are built in.
tower=box(40,24,472,(-110,170,274)).union(box(40,24,472,(110,170,274))).union(box(260,24,16,(0,170,502)))
for x in (-110,110):
 tower=tower.union(box(40,54,12,(x,170,44)))
 slot=box(6.6,30,110,(x,170,426)).union(cyl(3.3,30,(x,155,371),'y')).union(cyl(3.3,30,(x,155,481),'y'))
 tower=tower.cut(slot)
 for y in (155,185): tower=hole(tower,3.3,16,(x,y,36))
 for z in (204,224,264,284): tower=hole(tower,3.3,30,(x,155,z),'y')
for a in range(15,26):
 h=Z+170*math.tan(math.radians(a))+44/math.cos(math.radians(a)); z=h-20
 tower=tower.cut(box(8 if a%5 else 12,1.4,.6,(94 if a%5 else 96,157.9,z)))
 if a%5==0:
  text=cq.Workplane('XZ').text(str(a),5,.8,combine=True).translate((122,158.3,z))
  tower=tower.cut(text)
for i,x in enumerate((-110,110)):
 add(f'08a_tower_lower_{i+1}',tower.intersect(box(40,100,202,(x,170,139))))
add('08b_tower_upper',tower.intersect(box(300,100,270,(0,170,375))))
for i,x in enumerate((-110,110)):
 splice=box(40,12,120,(x,188,244))
 for z in (204,224,264,284): splice=hole(splice,3.3,16,(x,180,z),'y')
 add(f'08c_tower_splice_{i+1}',splice)
angle=20; pz=Z+170*math.tan(math.radians(angle))+44/math.cos(math.radians(angle))
# Carriage attachment plate and projecting yaw shelf.
car=box(260,10,40,(0,152,pz-32)).union(box(64,72,10,(0,121,pz-39)))
for x in (-110,110): car=hole(car,3.3,14,(x,146,pz-20),'y')
car=hole(car,4.3,14,(0,100,pz-46))
# index pointer follows engraved fixing-bolt scale
car=car.union(box(10,3,1,(94,146,pz-20)))
add('09_height_carriage',car,(.9,.6,.2))
# Yaw plate and removable cheeks. Pitch trunnions are integral with sliding bushing.
yaw=box(64,40,8,(0,96,pz-30))
yaw=hole(yaw,4.3,12,(0,100,pz-36))
for x in (-23,23):
 for y in (86,108): yaw=hole(yaw,2.8,12,(x,y,pz-36))
add('10_yaw_plate',yaw)
for i,x in enumerate((-23,23)):
 cheek=box(10,34,38,(x,97,pz-7))
 cheek=hole(cheek,5.2,14,(x-7,100,pz),'x')
 for y in (86,108): cheek=hole(cheek,2.8,42,(x,y,pz-28))
 add(f'11_pitch_cheek_{i+1}',cheek)
bush=box(24,40,24,(0,0,0)).union(cyl(5,44,(-22,0,0),'x'))
bush=hole(bush,4.2,44,(0,-22,0),'y')
bush=bush.rotate((0,0,0),(1,0,0),angle).translate((0,100,pz))
add('12_sliding_pitch_bushing',bush,(.9,.6,.2))
# Stone carrier in local coordinates: abrasive face z=0; stone z0..30;
# roof underside z32 allows 2 mm resilient backing. Guide rod center z44.
carrier=box(80,212,6,(0,0,35))
for y in (-70,70):
 collar=box(24,22,22,(0,y,45))
 collar=hole(collar,4.15,26,(0,y-13,44),'y')
 collar=collar.cut(box(1,26,14,(0,y,54)))
 collar=hole(collar,2.8,28,(-14,y,51),'x')
 carrier=carrier.union(collar)
# Fixed end jaw at -94; adjustable opposing jaw is carried by two M5 jacking screws.
carrier=carrier.union(box(80,10,28,(0,-95,20)))
carrier=carrier.union(box(80,10,28,(0,107,20)))
for x in (-23,23):
 carrier=hole(carrier,2.8,16,(x,100,19),'y')
 # hex nuts inserted from the exterior into endwall pockets
 nut=cq.Workplane('XY').polygon(6,9.6).extrude(4.5).rotate((0,0,0),(1,0,0),-90).translate((x,107.5,19))
 carrier=carrier.cut(nut)
# Keeper lip below top edges: lateral screws/pads restrain stone, end pads take thrust.
for x in (-37,37):
 rail=box(6,180,20,(x,0,22))
 for y in (-60,60): rail=hole(rail,1.65,10,(x-5,y,20),'x')
 carrier=carrier.union(rail)
for x in (-37,37):
 for y in (-78,78): carrier=hole(carrier,2.2,40,(x,y,-4))
# Assemble stone centered at edge y=-60; transform carrier around X by20deg.
# rod line from pitch to knife edge shifted along stone normal44.
def stone_pose(s): return s.rotate((0,0,0),(1,0,0),angle).translate((0,-70,Z))
add('13_stone_carrier',stone_pose(carrier))
for i,(x,y) in enumerate([(x,y) for x in (-37,37) for y in (-78,78)]):
 keeper=box(6,10,15,(x,y,4.5)).union(box(12,10,3,(34 if x>0 else -34,y,-1.5)))
 keeper=hole(keeper,2.2,20,(x,y,-4))
 add(f'17_stone_keeper_{i+1}',stone_pose(keeper),(.9,.6,.2))
end=box(65,6,24,(0,95,18))
for x in (-23,23):
 # Blind sockets accept jacking bolt ends without piercing stone-facing face.
 end=hole(end,2.8,3.5,(x,94.5,19),'y')
add('14_floating_end_pad',stone_pose(end),(.9,.6,.2))
# Printed end-stop collars on sliding rod keep it captive.
guide_u=(170+44*math.sin(math.radians(angle)))/math.cos(math.radians(angle))
for idx,yy in enumerate((guide_u-57,guide_u+45)):
 collar=cyl(10,12,(0,yy,44),'y'); collar=hole(collar,4.15,14,(0,yy-1,44),'y')
 collar=hole(collar,1.65,12,(0,yy+6,44),'x')
 add(f'15_rod_stop_{idx+1}',stone_pose(collar),(.9,.6,.2))
# Reference hardware and stone exported individually; generic smooth envelope models.
stone=box(60,180,30,(0,1,15)); add('REF_whetstone_60x180x30',stone_pose(stone),(.55,.55,.5),False)
rod=cyl(4,500,(0,-145,44),'y'); add('REF_guide_rod_8x500',stone_pose(rod),(.7,.7,.75),False)
axle=cyl(5,100,(0,-14,Z),'y'); add('REF_M10_axle_100',axle,(.7,.7,.75),False)
for name,r,h,p,axis in [('stop_pin_M5',2.5,40,(26,70,Z),'y'),('locking_pin_5',2.5,30,(15,70,Z),'y'),('yaw_pivot_M8',4,30,(0,100,pz-46),'z')]:
 add('REF_'+name,cyl(r,h,p,axis),(.7,.7,.75),False)
# Reference blade plus 100 mm handle; handle is an envelope, not a printed part.
add('REF_blade_envelope',cq.Workplane('YZ').polyline([(-70,Z),(-60,Z+1.5),(-25,Z+1.5),(-25,Z-1.5),(-60,Z-1.5)]).close().extrude(300).translate((-150,0,0)),(.75,.77,.8),False)
add('REF_handle_envelope',box(100,30,20,(200,-40,Z)),(.35,.3,.25),False)
# Off-the-shelf hardware, smooth ISO-style envelopes (threads omitted).
HW=ROOT/'hardware';HW.mkdir(exist_ok=True)
hardware_counts={}
def orient(shape,p,direction):
 if direction=='-z':shape=shape.rotate((0,0,0),(1,0,0),180)
 if direction=='y':shape=shape.rotate((0,0,0),(1,0,0),-90)
 if direction=='-y':shape=shape.rotate((0,0,0),(1,0,0),90)
 if direction=='x':shape=shape.rotate((0,0,0),(0,1,0),90)
 if direction=='-x':shape=shape.rotate((0,0,0),(0,1,0),-90)
 return shape.translate(p)
def hardware(kind,m,length,p,direction='z'):
 name=f'{kind}_M{m}'+(f'x{length}' if length else '')
 if kind=='bolt':
  af={4:7,5:8,6:10,8:13,10:17}[m]
  sh=cyl(m/2,length,(0,0,0)).union(cq.Workplane('XY').polygon(6,af/math.cos(math.pi/6)).extrude(-.65*m))
 elif kind=='nut':
  af={4:7,5:8,6:10,8:13,10:17}[m]
  sh=cq.Workplane('XY').polygon(6,af/math.cos(math.pi/6)).extrude(.8*m).cut(cyl(m/2,.8*m+2,(0,0,-1)))
 elif kind=='washer':
  sh=cyl(m,1.2,(0,0,0)).cut(cyl(m/2+.2,3,(0,0,-1)))
 else:sh=cyl(m/2,length,(0,0,0))
 if name not in hardware_counts:cq.exporters.export(sh,str(HW/(name+'.step')))
 hardware_counts[name]=hardware_counts.get(name,0)+1
 assembly.add(orient(sh,p,direction),name=f'HW_{name}_{hardware_counts[name]}',color=cq.Color(.65,.67,.7))
for x in (-140,140):
 for y in (-105,185):
  hardware('bolt',5,40,(x,y,38),'-z');hardware('nut',5,0,(x,y,0))
for x in (-24,24):
 for y in (20,60):
  hardware('threaded_rod',5,300,(x,y,24));hardware('nut',5,0,(x,y,28));hardware('nut',5,0,(x,y,319.2));hardware('washer',5,0,(x,y,318))
for x in (-34,34):
 hardware('bolt',5,25,(x,92,46),'-z');hardware('nut',5,0,(x,92,28))
for x in (-110,110):
 for y in (155,185):
  hardware('bolt',6,30,(x,y,50),'-z');hardware('nut',6,0,(x,y,27.2))
 for z in (204,224,264,284):
  hardware('bolt',6,45,(x,158,z),'y');hardware('nut',6,0,(x,194,z),'y')
 hardware('bolt',6,45,(x,147,pz-20),'y');hardware('washer',6,0,(x,182,pz-20),'y');hardware('nut',6,0,(x,183.2,pz-20),'y')
for x in (-35,35):
 hardware('bolt',6,35,(x,-16,309),'-z');hardware('washer',6,0,(x,-16,282.8));hardware('nut',6,0,(x,-16,278))
 hardware('bolt',5,30,(x,0,322),'-z');hardware('nut',5,0,(x,0,314))
# Axle head and front nut; shank is already in REF_M10_axle_100.
hardware('nut',10,0,(0,-1.2,Z),'-y');hardware('washer',10,0,(0,0,Z),'-y')
head=cq.Workplane('XY').polygon(6,19.63).extrude(6.5)
assembly.add(orient(head,(0,86,Z),'y'),name='HW_M10_axle_bolt_head',color=cq.Color(.65,.67,.7))
# Existing REF yaw pin supplies the shank; washer and nut retain without pinching yaw.
hardware('washer',8,0,(0,100,pz-26));hardware('nut',8,0,(0,100,pz-24.8))
for x in (-23,23):
 for y in (86,108):
  hardware('bolt',5,50,(x,y,pz+12),'-z');hardware('nut',5,0,(x,y,pz-38))
# Stone-carrier fasteners move with its local frame.
def stone_hw(kind,m,l,p,d='z'):
 # hardware() places directly; temporarily capture and transform the new child.
 hardware(kind,m,l,p,d)
 child=assembly.children[-1]
 child.loc=cq.Location(cq.Vector(0,-70,Z))*cq.Location(cq.Vector(0,0,0),cq.Vector(1,0,0),20)*child.loc
for y in (-70,70):
 stone_hw('bolt',5,35,(-12,y,51),'x');stone_hw('nut',5,0,(12,y,51),'x')
for x in (-23,23):
 stone_hw('bolt',5,20,(x,116,19),'-y');stone_hw('nut',5,0,(x,107.5,19),'y')
for y in (-60,60):
 stone_hw('bolt',4,12,(-42,y,20),'x');stone_hw('bolt',4,12,(42,y,20),'-x')
for x in (-37,37):
 for y in (-78,78):
  stone_hw('bolt',4,40,(x,y,-3));stone_hw('nut',4,0,(x,y,32))
for y in (guide_u-51,guide_u+51):stone_hw('set_screw',4,10,(14,y,44),'-x')
(ROOT/'cad'/'hardware_manifest.json').write_text(json.dumps(hardware_counts,indent=2)+'\n')
assembly.save(str(ROOT/'sharpener_assembly.step'))
(ROOT/'cad'/'part_manifest.json').write_text(json.dumps(parts,indent=2)+'\n')
print(json.dumps({'parts':len(parts),'invalid':[n for n,p in parts.items() if not p['solids']],'pivot_z_20deg':pz},indent=2))
