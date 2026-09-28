"""Plot current main figures from existing numerical CSVs.

Plot routines are extracted from table_generation.py and revise_sources.py.
This entry point does not mutate manuscript sources or rerun data analyses.
"""
from __future__ import annotations
import argparse
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch

ELEMENTS = ["Cd", "Co", "Cr", "Cu", "Fe", "Mn", "Ni", "Pb", "Zn"]
ORDINARY_TARGETS = ["total", "F1", "F1_plus_F2_plus_F3"]
CLASSES = ["magnetic_all_ties_better", "nearest_all_ties_better", "overlap_or_equal"]

def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))

def make_classification_figure(index,destination,wide=False):
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,
        "svg.fonttype":"none"})
    colors=["#276A98","#D88737","#DCE1E6"]
    cmap=ListedColormap(colors)
    norm=BoundaryNorm([-.5,.5,1.5,2.5],cmap.N)
    class_code={label:i for i,label in enumerate(CLASSES)}
    if wide:
        fig,axes=plt.subplots(1,3,figsize=(16.8,5.4),sharey=True)
        fig.subplots_adjust(left=.043,right=.989,bottom=.245,top=.735,wspace=.12)
    else:
        fig,axes=plt.subplots(3,1,figsize=(7.4,8.8),sharex=True)
        fig.subplots_adjust(left=.087,right=.976,bottom=.139,top=.785,hspace=.35)
    titles=["(a) Total concentration","(b) F1 concentration","(c) F1 + F2 + F3 concentration"]
    for ax,target,title in zip(axes,ORDINARY_TARGETS,titles):
        matrix=[[class_code[index[(e,target,k)]["classification"]] for k in range(1,32)] for e in ELEMENTS]
        ax.imshow(matrix,cmap=cmap,norm=norm,interpolation="nearest",aspect="auto",origin="upper")
        ax.set_title(title,fontsize=11.4 if wide else 10.4,pad=12 if wide else 8)
        ticks=[1,5,8,10,15,20,25,31]
        ax.set_xticks([k-1 for k in ticks],labels=[str(k) for k in ticks],fontsize=9.4 if wide else 8.5)
        ax.set_yticks(range(9),labels=ELEMENTS,fontsize=10 if wide else 8.5)
        ax.tick_params(axis="both",length=0,pad=6)
        if wide or target==ORDINARY_TARGETS[-1]:
            ax.set_xlabel("Selected records, k",labelpad=9,fontsize=10 if wide else 9)
        ax.set_xticks([i-.5 for i in range(32)],minor=True)
        ax.set_yticks([i-.5 for i in range(10)],minor=True)
        ax.grid(which="minor",color="white",linewidth=.48)
        ax.tick_params(which="minor",bottom=False,left=False)
        for spine in ax.spines.values():
            spine.set_visible(False)
        for tick,k in zip(ax.get_xticklabels(),ticks):
            if k==8:
                tick.set_weight("bold")
    if wide:
        fig.text(.043,.947,"Selection-rule comparisons across targets and budgets",fontsize=17,weight="bold",color="#1E2D38")
        fig.text(.043,.896,"Categorical decisions for all nine metals: colors identify the rule with separated cutoff-tie ranges, not retention magnitude.",
                 fontsize=10.2,color="#4A5661")
        legend=[Patch(facecolor=colors[0],label="Highest XLF better for all tie choices"),
                Patch(facecolor=colors[1],label="Nearest distance better for all tie choices"),
                Patch(facecolor=colors[2],label="Tie ranges overlap or are equal")]
        fig.legend(handles=legend,loc="upper left",bbox_to_anchor=(.039,.864),ncol=3,frameon=False,
                   fontsize=10,handlelength=1.7,columnspacing=2.2)
        fig.text(.043,.112,"A rule is marked better only when its lowest retention exceeds the other rule's highest retention by more than 10⁻¹².",
                 fontsize=9.7,color="#48545F")
        fig.text(.043,.065,"Each target uses its own same-budget chemical oracle. Tie ranges are not confidence intervals; budgets are dependent descriptive comparisons.",
                 fontsize=9.7,color="#48545F")
    else:
        fig.text(.087,.954,"Target and budget change the rule comparison",fontsize=13.4,weight="bold",color="#1E2D38")
        fig.text(.087,.917,"All nine metals and 31 budgets; each target uses its own chemical oracle.",fontsize=9,color="#4A5661")
        legend=[Patch(facecolor=colors[0],label="Highest XLF better\nfor all tie choices"),
                Patch(facecolor=colors[1],label="Nearest distance better\nfor all tie choices"),
                Patch(facecolor=colors[2],label="Tie ranges overlap\nor are equal")]
        fig.legend(handles=legend,loc="upper left",bbox_to_anchor=(.076,.888),ncol=3,frameon=False,
                   fontsize=8.5,handlelength=1.6,columnspacing=1.6)
        fig.text(.087,.066,"Colors classify the comparison, not retention magnitude. All cutoff-tie choices are included.",fontsize=8,color="#48545F")
        fig.text(.087,.043,"Better means the rule's minimum exceeds the other rule's maximum by more than 10⁻¹².",fontsize=8,color="#48545F")
        fig.text(.087,.020,"Ranges are not confidence intervals. Budgets are dependent descriptive comparisons.",fontsize=8,color="#48545F")
    stem="ordinary_target_budget_classification"+("_wide" if wide else "")
    fig.savefig(destination/(stem+".png"),dpi=300,facecolor="white")
    fig.savefig(destination/(stem+".svg"),facecolor="white")
    plt.close(fig)

def make_cu_figure(grid, output):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    fig,axes=plt.subplots(1,3,figsize=(10.5,3.1),sharey=True)
    for ax,target,label in zip(axes,['total','F1','F123'],['Four-fraction total','F1','F1 + F2 + F3']):
        rr=[r for r in grid if r['element']=='Cu' and r['target']==target]
        k=np.array([int(r['k']) for r in rr])
        for prefix,color,name in [('m','#245b89','Highest XLF'),('p','#bc5b24','Recorded distance')]:
            lo=np.array([float(r[prefix+'_lo'])*100 for r in rr]);hi=np.array([float(r[prefix+'_hi'])*100 for r in rr])
            ax.plot(k,lo,color=color,label=name,lw=1.8);ax.plot(k,hi,color=color,lw=.8);ax.fill_between(k,lo,hi,color=color,alpha=.18)
        ax.axvline(8,color='#888888',ls=':',lw=1);ax.set(xlim=(1,31),ylim=(0,103),title=label,xlabel='Selected records k',xticks=[1,8,16,24,31]);ax.grid(axis='y',alpha=.18)
    axes[0].set_ylabel('Same-size oracle retention (%)')
    axes[-1].legend(loc='lower right',fontsize=8,frameon=False)
    fig.tight_layout();fig.savefig(output/'Cu_ordinary_profiles.png',dpi=220);fig.savefig(output/'Cu_ordinary_profiles.svg');plt.close(fig)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", type=Path, required=True)
    parser.add_argument("--target-profiles", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    grid = read_csv(args.grid)
    profiles = read_csv(args.target_profiles)
    assert len(grid) == 837
    index = {(r["element"], r["target"], int(r["k"])): r for r in profiles}
    assert len(index) == len(profiles) == 1116
    for element in ELEMENTS:
        for target in ORDINARY_TARGETS:
            for k in range(1, 32):
                assert index[(element, target, k)]["classification"] in CLASSES
    args.output.mkdir(parents=True, exist_ok=True)
    make_cu_figure(grid, args.output)
    make_classification_figure(index, args.output)

if __name__ == "__main__":
    main()
