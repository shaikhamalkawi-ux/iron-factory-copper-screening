"""Render checked CSV results without rerunning or altering scientific calculations."""
from pathlib import Path
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parent
def read(name):
    with (OUT / name).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'svg.fonttype': 'none', 'savefig.facecolor': 'white'})
rows = read('retrospective_maximin_k8.csv')
assert len(rows) == 9 and all(r['solver_status'] == '0' for r in rows)
elements = [r['element'] for r in rows]
xlf = np.array([float(r['XLF_worst_case_retention']) for r in rows]) * 100
best = np.array([float(r['retrospective_maximin_retention']) for r in rows]) * 100
y = np.arange(len(rows))
fig, ax = plt.subplots(figsize=(9, 6.1))
fig.subplots_adjust(left=.11, right=.96, top=.78, bottom=.25)
ax.barh(y-.18, xlf, height=.32, color='#245b78', label='Highest XLF')
ax.barh(y+.18, best, height=.32, color='#c87935', label='Retrospective maximin (requires chemistry)')
for yi, v1, v2 in zip(y, xlf, best):
    ax.text(v1+1, yi-.18, f'{v1:.1f}', va='center', fontsize=9)
    ax.text(v2+1, yi+.18, f'{v2:.1f}', va='center', fontsize=9)
ax.set_yticks(y, elements)
ax.invert_yaxis()
ax.set_xlim(0, 103)
ax.set_xticks(np.arange(0, 101, 20))
ax.set_xlabel('Worst-case retention of the same-budget chemical oracle (%)', labelpad=10)
ax.grid(axis='x', alpha=.17)
ax.set_axisbelow(True)
ax.legend(loc='lower left', bbox_to_anchor=(-.01,1.02), frameon=False, fontsize=10)
fig.text(.11,.95,'Eight-record shortlists retain very different chemical scores', fontsize=15, weight='bold')
fig.text(.11,.91,'32 records · each metal analyzed separately · all shared nonnegative fraction weights', fontsize=10, color='#4a4a4a')
fig.text(.11,.04,'Scores sum concentrations over records; they do not represent total environmental mass or risk.\nThe retrospective benchmark uses all chemical measurements. No prospective validation is implied.', fontsize=9, linespacing=1.5, color='#4a4a4a')
for ext in ('png','svg'):
    fig.savefig(OUT / f'Figure_1_k8_retention.{ext}', dpi=220)
plt.close(fig)

profiles = read('magnetic_budget_summary.csv')
fig, axes = plt.subplots(3,3,figsize=(10,8.2),sharex=True,sharey=True)
fig.subplots_adjust(left=.09,right=.97,top=.88,bottom=.18,wspace=.17,hspace=.34)
for ax, element in zip(axes.flat,elements):
    rr = [r for r in profiles if r['element']==element]
    assert [int(r['k']) for r in rr] == list(range(1,32))
    k = np.array([int(r['k']) for r in rr])
    val = np.array([float(r['worst_case_retention']) for r in rr])*100
    ax.plot(k,val,color='#245b78',lw=1.7)
    ax.scatter([8],[val[7]],s=26,color='#c87935',zorder=3)
    ties = [i for i,r in enumerate(rr) if r['cutoff_tie']=='True']
    ax.scatter(k[ties],val[ties],s=18,facecolors='white',edgecolors='#245b78',zorder=3)
    ax.set_title(element,loc='left',fontweight='bold')
    ax.set_ylim(0,103); ax.set_xlim(1,31)
    ax.set_xticks([1,8,16,24,31]); ax.set_yticks([0,25,50,75,100])
    ax.grid(alpha=.18)
fig.suptitle('Magnetic shortlist performance across every nontrivial budget', fontsize=15, x=.09, ha='left', y=.965, weight='bold')
fig.text(.09,.915,'Full weight-simplex minimum; ascending record ID resolves exact XLF cutoff ties', fontsize=10, color='#4a4a4a')
fig.text(.5,.115,'Number of records selected by descending stored XLF (k)', ha='center', fontsize=11)
fig.text(.025,.54,'Worst-case oracle-relative score retention (%)', va='center', rotation=90, fontsize=11)
fig.text(.09,.04,'Orange point: k = 8. Open points: cutoff ties (k = 13, 21, 23, 27).\nThe oracle and its denominator change with k; the ratio need not increase at every step.',fontsize=9,linespacing=1.5,color='#4a4a4a')
for ext in ('png','svg'):
    fig.savefig(OUT / f'Figure_2_budget_profiles.{ext}',dpi=220)
plt.close(fig)
print('Rendered two figures in PNG and editable SVG from verified CSVs.')
