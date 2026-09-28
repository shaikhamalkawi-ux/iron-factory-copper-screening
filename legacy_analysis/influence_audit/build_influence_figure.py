"""Plot the complete finite set of omission cases; no inference or model fitting."""
from pathlib import Path
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

BASE=Path(__file__).resolve().parent
with (BASE/'influence_details.csv').open(encoding='utf-8-sig',newline='') as stream:
    rows=list(csv.DictReader(stream))
elements=['Cd','Co','Cr','Cu','Fe','Mn','Ni','Pb','Zn']
assert len(rows)==288
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,
                     'axes.spines.top':False,'axes.spines.right':False,
                     'svg.fonttype':'none','savefig.facecolor':'white'})
fig,ax=plt.subplots(figsize=(10.8,6.4))
fig.subplots_adjust(left=.10,right=.83,top=.77,bottom=.26)
for y,element in enumerate(elements):
    rr=[r for r in rows if r['element']==element]
    assert sorted(int(r['omitted_id']) for r in rr)==list(range(1,33))
    values=np.array([float(r['loo_retention'])*100 for r in rr])
    inside=np.array([r['omitted_in_magnetic8'].lower()=='true' for r in rr])
    baseline=float(rr[0]['baseline_retention'])*100
    assert inside.sum()==8
    ax.plot([values.min(),values.max()],[y,y],color='#a5a5a5',lw=2,zorder=1)
    ax.scatter(values[~inside],np.full((~inside).sum(),y-.085),s=23,
               facecolors='white',edgecolors='#318c86',linewidths=1,
               label='Omit an unselected record' if y==0 else None,zorder=3)
    ax.scatter(values[inside],np.full(inside.sum(),y+.085),s=23,
               color='#c87935',edgecolors='white',linewidths=.3,
               label='Omit a selected record' if y==0 else None,zorder=4)
    ax.scatter([baseline],[y],marker='D',s=38,color='#183b50',edgecolors='white',linewidths=.5,
               label='Full-data baseline' if y==0 else None,zorder=5)
    ax.text(1.025,y,f'{values.min():.2f}–{values.max():.2f}',transform=ax.get_yaxis_transform(),
            va='center',fontsize=10,color='#333333')
ax.set_yticks(range(9),elements)
ax.invert_yaxis()
ax.set_xlim(0,100);ax.set_xticks([0,20,40,60,80,100])
ax.set_xlabel('Worst-case retention of the same-budget chemical oracle (%)',labelpad=12)
ax.grid(axis='x',alpha=.17);ax.set_axisbelow(True)
handles,labels=ax.get_legend_handles_labels()
ax.legend([handles[2],handles[1],handles[0]],[labels[2],labels[1],labels[0]],
          loc='lower left',bbox_to_anchor=(-.01,1.015),ncol=3,frameon=False,fontsize=9,
          columnspacing=1.3,handletextpad=.5)
fig.text(.10,.95,'Single-record influence on an eight-record magnetic shortlist',fontsize=15,weight='bold')
fig.text(.10,.907,'Each element: all 32 omissions · shortlist and oracle recomputed within 31 eligible records',fontsize=10,color='#4a4a4a')
fig.text(.85,.827,'Omission range (%)',fontsize=9,color='#444444')
fig.text(.10,.08,'Horizontal spans are finite sensitivity ranges, not confidence intervals. Coincident cases overlap.\nDeleting an unselected record keeps the magnetic shortlist unchanged; any increase then comes from a smaller oracle.\nScores sum concentrations over records. Eight selections represent 25% of the full file and 25.81% after an omission.',
         fontsize=9,color='#4a4a4a',linespacing=1.6)
for ext in ('png','svg'):
    fig.savefig(BASE/f'Figure_3_single_record_influence.{ext}',dpi=220)
plt.close(fig)
print('Figure 3 PNG/SVG rendered from all 288 omission cases.')
