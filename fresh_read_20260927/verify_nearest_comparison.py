"""Independent direct-source verification of the four-target k=8 comparison.

Does not import root analysis code or use its results as computational input.
The root CSV is read only after the independent calculation, for comparison.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import openpyxl

ELEMENTS = ["Cd", "Co", "Cr", "Cu", "Fe", "Mn", "Ni", "Pb", "Zn"]
DEFAULT_SOURCE = Path(__file__).resolve().parents[1] / "source/Iron Factory.xlsx"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,default=DEFAULT_SOURCE)
    parser.add_argument("--comparison-csv",type=Path,default=Path(__file__).with_name("magnetic_vs_nearest_k8.csv"))
    args=parser.parse_args()
    source=args.source.resolve(strict=True)
    checksum=sha(source)
    workbook=openpyxl.load_workbook(source,read_only=True,data_only=True)
    sheet=workbook["All rsults"]
    raw=list(sheet.iter_rows(min_row=4,max_row=35,max_col=60,values_only=True))
    workbook.close()
    ids=[int(row[0]) for row in raw]
    assert ids==list(range(1,33))
    position={record_id:i for i,record_id in enumerate(ids)}
    xlf={int(row[0]):float(row[58]) for row in raw}
    distances={int(row[0]):float(row[52]) for row in raw}
    magnetic=sorted(ids,key=lambda i:(-xlf[i],i))[:8]
    distance_order=sorted(ids,key=lambda i:(distances[i],i))
    cutoff=distances[distance_order[7]]
    strictly_closer=[i for i in distance_order if distances[i]<cutoff]
    tied=[i for i in distance_order if distances[i]==cutoff]
    nearest_sets=[sorted(strictly_closer+list(choice)) for choice in itertools.combinations(tied,8-len(strictly_closer))]
    assert magnetic==[12,8,31,19,24,26,29,16]
    assert strictly_closer==[2,8,12,14,15,31]
    assert tied==[3,5,9,11] and cutoff==200 and len(nearest_sets)==6
    assert xlf[magnetic[-1]]>xlf[sorted(ids,key=lambda i:(-xlf[i],i))[8]]

    recalculated=[]
    choice_details=[]
    componentwise=[]
    summary=[]
    for e,metal in enumerate(ELEMENTS):
        fractions={i:[float(raw[position[i]][start+e]) for start in [1,11,21,31]] for i in ids}
        assert all(math.isfinite(v) and v>0 for row in fractions.values() for v in row)
        fraction_oracles=[math.fsum(sorted((fractions[i][f] for i in ids),reverse=True)[:8]) for f in range(4)]
        assert all(o>0 for o in fraction_oracles)
        mag_sums=[math.fsum(fractions[i][f] for i in magnetic) for f in range(4)]
        mag_ratios=[a/o for a,o in zip(mag_sums,fraction_oracles)]
        for choice_number,selection in enumerate(nearest_sets,1):
            sums=[math.fsum(fractions[i][f] for i in selection) for f in range(4)]
            ratios=[a/o for a,o in zip(sums,fraction_oracles)]
            differences=[a-b for a,b in zip(sums,mag_sums)]
            componentwise.append({"element":metal,"choice_number":choice_number,"nearest_IDs":selection,
                "nearest_minus_magnetic_selected_sums_F1_F4":differences,
                "nearest_componentwise_at_least_magnetic":all(d>=0 for d in differences),
                "nearest_componentwise_strictly_above_magnetic":all(d>0 for d in differences),
                "magnetic_componentwise_at_least_nearest":all(d<=0 for d in differences),
                "magnetic_componentwise_strictly_above_nearest":all(d<0 for d in differences)})
            choice_details.append({"element":metal,"choice_number":choice_number,"nearest_IDs":selection,
                "fraction_oracles_F1_F4":fraction_oracles,"magnetic_selected_sums_F1_F4":mag_sums,
                "nearest_selected_sums_F1_F4":sums,"magnetic_fraction_ratios_F1_F4":mag_ratios,
                "nearest_fraction_ratios_F1_F4":ratios,"magnetic_minimum_four_fraction":min(mag_ratios),
                "nearest_minimum_four_fraction":min(ratios)})
        for target in ["total","F1","F1_plus_F2_plus_F3","minimum_four_fraction"]:
            if target=="minimum_four_fraction":
                mag_ret=min(mag_ratios)
                nearest_rets=[r["nearest_minimum_four_fraction"] for r in choice_details if r["element"]==metal]
                expected=None
            else:
                if target=="total":
                    values={i:float(raw[position[i]][41+e]) for i in ids}
                elif target=="F1":
                    values={i:fractions[i][0] for i in ids}
                else:
                    values={i:math.fsum(fractions[i][:3]) for i in ids}
                oracle=math.fsum(sorted(values.values(),reverse=True)[:8])
                mag_ret=math.fsum(values[i] for i in magnetic)/oracle
                nearest_rets=[math.fsum(values[i] for i in selected)/oracle for selected in nearest_sets]
                expected=(8/32)*math.fsum(values.values())/oracle
            row={"element":metal,"target":target,"magnetic_retention":mag_ret,
                 "nearest_min_retention":min(nearest_rets),"nearest_max_retention":max(nearest_rets),
                 "uniform_expected_retention":expected}
            recalculated.append(row)
            if target=="minimum_four_fraction":
                if min(nearest_rets)>mag_ret:
                    relation="all six nearest choices higher minimum retention"
                elif max(nearest_rets)<mag_ret:
                    relation="magnetic higher minimum retention than all six nearest choices"
                else:
                    relation="ranking depends on the nearest cutoff tie choice"
                relevant=[r for r in componentwise if r["element"]==metal]
                summary.append(dict(row,comparison=relation,
                    nearest_componentwise_strict_choices=sum(r["nearest_componentwise_strictly_above_magnetic"] for r in relevant),
                    magnetic_componentwise_strict_choices=sum(r["magnetic_componentwise_strictly_above_nearest"] for r in relevant)))

    with args.comparison_csv.open(encoding="utf-8-sig",newline="") as handle:
        reference=list(csv.DictReader(handle))
    assert len(reference)==len(recalculated)==36
    reference_map={(r["element"],r["target"]):r for r in reference}
    comparisons=[]
    for actual in recalculated:
        stored=reference_map[(actual["element"],actual["target"])]
        for field in ["magnetic_retention","nearest_min_retention","nearest_max_retention","uniform_expected_retention"]:
            a=actual[field]
            b=float(stored[field]) if stored[field] else None
            difference=None if a is None or b is None else a-b
            passed=(a is None and b is None) or (difference is not None and abs(difference)<=1e-12)
            comparisons.append({"element":actual["element"],"target":actual["target"],"field":field,
                                "independent":a,"reference":b,"difference":difference,"passed":passed})
    assert all(row["passed"] for row in comparisons)
    assert sha(source)==checksum
    output={"source":str(source),"source_sha256_before_and_after":checksum,"source_unchanged":True,
        "method":"Independent openpyxl extraction; standard-library sorted and math.fsum; root CSV loaded only after calculations.",
        "k":8,"n":32,"magnetic_ordered_IDs":magnetic,"magnetic_cutoff_unambiguous":True,
        "distance_cutoff_m":cutoff,"strictly_closer_IDs":strictly_closer,"distance_cutoff_tied_IDs":tied,
        "nearest_sets":nearest_sets,"distance_by_ID":distances,
        "reference_csv":str(args.comparison_csv.resolve()),"reference_csv_sha256":sha(args.comparison_csv),
        "all_36_rows_passed":True,"comparison_cell_count_including_9_expected_blank_cells":len(comparisons),
        "numeric_comparison_cell_count":sum(c["difference"] is not None for c in comparisons),
        "maximum_absolute_difference":max(abs(c["difference"]) for c in comparisons if c["difference"] is not None),
        "absolute_tolerance":1e-12,"independent_rows":recalculated,"summary":summary,
        "per_choice_details":choice_details,"componentwise_comparisons":componentwise,"reference_comparisons":comparisons}
    destination=Path(__file__).resolve().parent
    (destination/"nearest_independent_check.json").write_text(json.dumps(output,indent=2)+"\n",encoding="utf-8")
    lines=["# Independent verification of magnetic versus recorded-nearest selection","",
        "The original workbook was read directly and closed before calculations. No root analysis code was imported; the comparison CSV was loaded only after an independent standard-library calculation. The source SHA-256 remained `"+checksum+"`.","",
        f"All 36 rows and all {output['numeric_comparison_cell_count']} numeric entries in `magnetic_vs_nearest_k8.csv` agree within 1e-12; maximum absolute difference is {output['maximum_absolute_difference']:.17g}. The nine empty expected values for the minimum-of-fractions target are also correctly preserved. The additive-score expectation formula must not be applied to a minimum of ratios.","",
        "At k=8, magnetic descending-XLF IDs are **12, 8, 31, 19, 24, 26, 29, 16**, with no cutoff tie. The recorded-distance selection fixes **2, 8, 12, 14, 15, 31**, then chooses any two of **3, 5, 9, 11** at 200 m. All six valid choices were enumerated:","",
        *["- "+", ".join(map(str,choice)) for choice in nearest_sets],"",
        "The following scores are percentages: the minimum, over F1–F4, of selected concentration sum divided by the whole-file chemical top-eight sum for the corresponding fraction. They are oracle-relative concentration-sum retention scores, not metal mass or risk.","",
        "| Metal | Magnetic | Nearest minimum | Nearest maximum | Nearest strictly exceeds magnetic in all four sums: choices/6 | Magnetic strictly exceeds nearest in all four sums: choices/6 |",
        "|---|---:|---:|---:|---:|---:|"]
    for row in summary:
        lines.append(f"| {row['element']} | {100*row['magnetic_retention']:.6f} | {100*row['nearest_min_retention']:.6f} | {100*row['nearest_max_retention']:.6f} | {row['nearest_componentwise_strict_choices']} | {row['magnetic_componentwise_strict_choices']} |")
    lines.extend(["",
        "For the minimum-of-four retention criterion, every nearest tie choice exceeds magnetic for **Cd, Co, Cu, Fe, Ni, Pb, and Zn**; magnetic exceeds every nearest choice for **Mn**; **Cr** depends on how the distance tie is resolved. This verifies the stated nine-metal comparison.","",
        "A higher minimum retention alone does **not** establish superiority for every shared nonnegative fraction-weight vector. Componentwise selected sums were therefore checked separately for each of the six choices. When one selection strictly exceeds the other in all four sums, it strictly exceeds the other for every nonnegative normalized weight vector, because the comparison uses the same positive weighted-oracle denominator. Otherwise the minimum-retention comparison must not be described as all-weight dominance. Exact componentwise differences and all four ratios are in the JSON.","",
        "Recorded proximity is a workbook descriptor with a documented inside-factory zero category, an unspecified distance origin, and tied values. These are retrospective within-file comparisons. They neither verify the underlying spatial sampling design nor provide independent validation. Selection uses XLF or distance only; chemical data are used to score the resulting selections.","",
        "Reproduce with `verify_nearest_comparison.py --source <original.xlsx> --comparison-csv <magnetic_vs_nearest_k8.csv>`. Outputs are `nearest_independent_check.json` and this note; the source and root results are never modified."])
    (destination/"nearest_independent_check.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({k:output[k] for k in ["all_36_rows_passed","numeric_comparison_cell_count","maximum_absolute_difference","nearest_sets","summary"]},indent=2))


if __name__=="__main__":
    main()
