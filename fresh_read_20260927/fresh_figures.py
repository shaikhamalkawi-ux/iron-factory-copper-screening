"""Polish two fresh-read figures from existing CSVs; no analysis is rerun.

Only the two PNGs and a figure-validation JSON are written. The original
workbook and all analytical CSV files are read-only / never modified.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator, PercentFormatter


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path):
    with path.open(encoding="utf-8-sig",newline="") as handle:
        return list(csv.DictReader(handle))


def recorded_locations(rows, path):
    fig,ax=plt.subplots(figsize=(9.4,7.2))
    fig.subplots_adjust(left=.105,right=.865,bottom=.16,top=.9)
    east=[float(r["east_relative_m"]) for r in rows]
    north=[float(r["north_relative_m"]) for r in rows]
    xlf=[float(r["stored_XLF"]) for r in rows]
    im=ax.scatter(east,north,c=xlf,cmap="viridis",s=64,edgecolors="white",linewidths=.7,zorder=3)
    inside=[r for r in rows if float(r["recorded_distance_m"])==0]
    ax.scatter([float(r["east_relative_m"]) for r in inside],
        [float(r["north_relative_m"]) for r in inside],s=130,
        facecolors="none",edgecolors="#C75B24",linewidths=1.5,
        label="Recorded distance = 0",zorder=4)
    # Point locations and numeric values remain unchanged. Manual label offsets
    # are in typographic points and address the crowded central pairs.
    offsets={
        2:(-11,-1,"right","center"), 4:(8,7,"left","bottom"),
        7:(5,12,"left","bottom"), 8:(10,4,"left","bottom"),
        12:(-7,12,"right","bottom"),14:(-8,12,"right","bottom"),
        15:(11,-4,"left","center"),26:(5,8,"left","bottom"),
        30:(-10,7,"right","bottom"),31:(-9,-5,"right","top"),
        3:(-5,-7,"right","top"),23:(7,-1,"left","center"),
    }
    annotation_objects=[]
    for row in rows:
        record=int(row["ID"])
        dx,dy,ha,va=offsets.get(record,(5,5,"left","bottom"))
        annotation_objects.append(ax.annotate(str(record),
            (float(row["east_relative_m"]),float(row["north_relative_m"])),
            xytext=(dx,dy),textcoords="offset points",fontsize=8.6,
            ha=ha,va=va,color="#20252A",zorder=5))
    ax.set(xlabel="Approximate east displacement (m)",
           ylabel="Approximate north displacement (m)",
           title="Recorded locations and stored XLF")
    ax.set_aspect("equal",adjustable="box")
    ax.margins(x=.065,y=.07)
    ax.grid(color="#E5E7EB",linewidth=.7,zorder=0)
    ax.legend(loc="upper left",fontsize=9,frameon=True,facecolor="white",edgecolor="#D5D8DB")
    cb=fig.colorbar(im,ax=ax,fraction=.039,pad=.045,shrink=.84)
    cb.set_label("Stored XLF (units unverified)",labelpad=9)
    fig.text(.105,.075,"Labels identify workbook records; orange rings mark the five distance-zero records.",fontsize=8.7,color="#444B53")
    fig.text(.105,.046,"Origin: centroid of those five records; the origin is not a verified emission source.",fontsize=8.7,color="#444B53")
    fig.canvas.draw()
    renderer=fig.canvas.get_renderer()
    label_overlaps=[]
    for i,a in enumerate(annotation_objects):
        for b in annotation_objects[i+1:]:
            if a.get_window_extent(renderer).overlaps(b.get_window_extent(renderer)):
                label_overlaps.append([a.get_text(),b.get_text()])
    assert not label_overlaps, f"Overlapping label boxes: {label_overlaps}"
    fig.savefig(path,dpi=300,facecolor="white")
    plt.close(fig)
    return {"record_count":len(rows),"orange_ring_count":len(inside),
        "all_32_record_ID_labels_present":len(annotation_objects)==32,
        "overlapping_label_bounding_boxes":label_overlaps,
        "manual_annotation_offsets_points":offsets,
        "pixel_dimensions":[2820,2160]}


def comparison(rows,path):
    elements=["Cd","Co","Cr","Cu","Fe","Mn","Ni","Pb","Zn"]
    selected={r["element"]:r for r in rows if r["target"]=="minimum_four_fraction"}
    assert set(selected)==set(elements) and len(selected)==9
    fig,ax=plt.subplots(figsize=(9.6,6.6))
    fig.subplots_adjust(left=.085,right=.965,bottom=.21,top=.79)
    blue="#275D8C"
    orange="#C56A22"
    for y,element in enumerate(elements):
        row=selected[element]
        magnetic=100*float(row["magnetic_retention"])
        lo=100*float(row["nearest_min_retention"])
        hi=100*float(row["nearest_max_retention"])
        assert 0<=lo<=hi<=100 and 0<=magnetic<=100
        if y%2==0:
            ax.axhspan(y-.5,y+.5,color="#F4F6F8",zorder=0)
        # Small vertical offsets prevent the Cr point from hiding the lower
        # distance-range endpoint; both still belong to the same metal row.
        ax.hlines(y+.11,lo,hi,color=orange,linewidth=3.1,zorder=2)
        ax.vlines([lo,hi],y+.02,y+.20,color=orange,linewidth=1.5,zorder=2)
        ax.scatter([magnetic],[y-.11],s=66,marker="o",facecolor=blue,
            edgecolor="white",linewidth=.9,zorder=4)
    ax.set_yticks(range(len(elements)),elements)
    ax.set_ylim(8.5,-.65)
    ax.set_xlim(0,100)
    ax.xaxis.set_major_locator(MultipleLocator(10))
    ax.xaxis.set_major_formatter(PercentFormatter(xmax=100,decimals=0))
    ax.set_xlabel("Minimum oracle-relative concentration-sum retention",labelpad=11)
    ax.grid(axis="x",color="#DEE2E6",linewidth=.7,zorder=1)
    ax.tick_params(axis="y",length=0,pad=10)
    ax.spines[["top","right","left"]].set_visible(False)
    ax.spines["bottom"].set_color("#B7BEC5")
    fig.text(.085,.95,"Selecting eight of the 32 records",fontsize=15,weight="bold",color="#1C2730")
    fig.text(.085,.907,"All nine metals; minimum retention across the four extraction fractions",fontsize=10.5,color="#48515A")
    handles=[Line2D([0],[0],marker="o",color="none",markerfacecolor=blue,markeredgecolor="white",markersize=8,
                    label="Highest stored XLF"),
             Line2D([0],[0],color=orange,lw=3,marker="|",markersize=8,
                    label="Nearest recorded distance: range of six tie choices")]
    fig.legend(handles=handles,loc="upper left",bbox_to_anchor=(.077,.875),frameon=False,
               ncol=2,columnspacing=1.8,handlelength=2.2,fontsize=9.6)
    fig.text(.085,.093,"The orange range covers six valid ways to resolve the distance cutoff tie; it is not a confidence interval.",
             fontsize=9.1,color="#444B53")
    fig.text(.085,.055,"Each fraction is divided by its own chemical top-eight concentration sum. Comparisons are retrospective.",
             fontsize=9.1,color="#444B53")
    fig.savefig(path,dpi=300,facecolor="white")
    plt.close(fig)
    return {"target":"minimum_four_fraction","element_order":elements,"k":8,"n":32,
            "nearest_interval_meaning":"minimum and maximum across six distance-cutoff tie choices; not a confidence interval",
            "pixel_dimensions":[2880,1980]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory",type=Path,default=Path(__file__).resolve().parent)
    args=parser.parse_args()
    base=args.directory.resolve(strict=True)
    inputs=[base/"metadata_diagnostics.csv",base/"magnetic_vs_nearest_k8.csv"]
    before={str(path.name):sha(path) for path in inputs}
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,
        "axes.titlesize":13,"axes.titlepad":13,"axes.labelsize":10.5,
        "xtick.labelsize":9,"ytick.labelsize":10.5})
    maps=recorded_locations(read_rows(inputs[0]),base/"recorded_locations.png")
    scores=comparison(read_rows(inputs[1]),base/"magnetic_vs_nearest_min_retention_k8.png")
    after={str(path.name):sha(path) for path in inputs}
    assert before==after
    report={"script":"fresh_figures.py","matplotlib_version":matplotlib.__version__,
        "analysis_recomputed":False,"input_CSV_hashes_before":before,"input_CSV_hashes_after":after,
        "input_CSVs_unchanged":True,"source_workbook_accessed":False,
        "figures":{"recorded_locations.png":maps,"magnetic_vs_nearest_min_retention_k8.png":scores}}
    (base/"fresh_figures_validation.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
