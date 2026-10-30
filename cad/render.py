from pathlib import Path
import json
import cadquery as cq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
R=Path(__file__).resolve().parents[1]; m=json.loads((R/'cad/part_manifest.json').read_text())
fig=plt.figure(figsize=(12,10));ax=fig.add_subplot(111,projection='3d')
for n,p in m.items():
 s=cq.importers.importStep(str(R/'parts'/(n+'.step')))
 v,f=s.val().tessellate(.8,.3);verts=[q.toTuple() for q in v];faces=[[verts[i] for i in face] for face in f]
 color='#edac45' if n.startswith(('06','09','12','14','15')) else ('#a7adb3' if n.startswith('REF') else '#5097a4')
 poly=Poly3DCollection(faces,facecolors=color,edgecolors='none',alpha=1)
 ax.add_collection3d(poly)
ax.set(xlim=(-210,210),ylim=(-180,310),zlim=(0,550),xlabel='X / mm',ylabel='Y / mm',zlabel='Z / mm')
ax.set_box_aspect((420,490,550));ax.view_init(25,-55);ax.set_title('Knife sharpener prototype — 20° reference assembly')
fig.tight_layout();fig.savefig(R/'assembly_preview.png',dpi=150)
