"""Descriptive leave-one-record-out influence at fixed shortlist budget eight.

Read-only source extraction; no optimization, inference, or deletion of records.
Run: python influence_audit.py --source "path/to/Iron Factory.xlsx"
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import openpyxl


DEFAULT_SOURCE = Path(__file__).resolve().parents[2] / "source/Iron Factory.xlsx"
OUT = Path(__file__).resolve().parent
ELEMENTS = ["Cd", "Co", "Cr", "Cu", "Fe", "Mn", "Ni", "Pb", "Zn"]
K = 8
RATIO_ATOL = 1e-12
SUM_ATOL = 1e-9
EXTREME_PP_ATOL = 1e-9


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                        help="Original Excel workbook, opened read-only")
    args = parser.parse_args()
    args.source = args.source.expanduser().resolve()
    if not args.source.is_file():
        parser.error(f"Source workbook does not exist: {args.source}")
    return args


def write_csv(name: str, rows: list[dict]) -> None:
    with (OUT/name).open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def active_fractions(ratios: np.ndarray) -> list[str]:
    return [f"F{i+1}" for i in np.flatnonzero(np.isclose(ratios,ratios.min(),rtol=0,atol=RATIO_ATOL))]


def magnetic_order(ids: np.ndarray, xlf: np.ndarray) -> np.ndarray:
    return np.array(sorted(range(len(ids)),key=lambda i:(-xlf[i],ids[i])))


def evaluate(c: np.ndarray, selected: np.ndarray) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
    picked = c[selected,:].sum(axis=0)
    oracle = np.sort(c,axis=0)[-K:,:].sum(axis=0)
    assert np.all(np.isfinite(picked)) and np.all(oracle>0)
    ratios = picked/oracle
    assert np.all(ratios>=0) and np.all(ratios<=1+RATIO_ATOL)
    return picked,oracle,ratios


def main(source: Path) -> None:
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    workbook = openpyxl.load_workbook(source,data_only=True,read_only=True)
    rows = list(workbook["All rsults"].iter_rows(min_row=4,max_row=35,max_col=60,values_only=True))
    workbook.close()
    ids = np.array([int(row[0]) for row in rows])
    assert ids.tolist()==list(range(1,33))
    xlf = np.array([float(row[58]) for row in rows])
    c_all = np.array([[[float(row[start+j-1]) for start in (2,12,22,32)] for j in range(9)] for row in rows])
    assert np.all(np.isfinite(c_all)) and np.all(c_all>=0)
    full_order = magnetic_order(ids,xlf)
    full_selected = full_order[:K]
    full_selected_ids = ids[full_selected].tolist()
    original_rank = {int(ids[index]):position+1 for position,index in enumerate(full_order)}
    original_rank9_id = int(ids[full_order[K]])
    full_file_totals = c_all.sum(axis=0)
    assert np.all(full_file_totals>0)
    baselines = {}
    details, summaries = [], []
    invariant_counts = {"all_cases_checked":0,"originally_unselected_cases":0,
                        "unselected_selection_and_numerator_unchanged":0,
                        "unselected_oracles_nonincreasing":0,
                        "unselected_each_fraction_retention_nondecreasing":0,
                        "unselected_minimum_retention_nondecreasing":0,
                        "originally_selected_cases":0,"selected_exact_rank9_replacement":0,
                        "exactly_8_of_31_unique_eligible_selected":0,
                        "positive_oracles_and_ratios_in_unit_interval":0,
                        "oracle_analytical_deletion_identity":0,
                        "selected_sum_analytical_deletion_identity":0}
    deletion_identity_max_errors = {"oracle_absolute":0.0,"selected_sum_absolute":0.0}
    for j,element in enumerate(ELEMENTS):
        c = c_all[:,j,:]
        base_sum,base_oracle,base_ratios = evaluate(c,full_selected)
        chemical_rank9_values = np.sort(c,axis=0)[-(K+1),:]
        base_retention = float(base_ratios.min())
        baselines[element] = {"selected_ids":full_selected_ids,"selected_sums":base_sum.tolist(),
                              "oracle_sums":base_oracle.tolist(),"fraction_ratios":base_ratios.tolist(),
                              "retention":base_retention,"active_fractions":active_fractions(base_ratios)}
        metal_rows = []
        for omitted_index,omitted_id_np in enumerate(ids):
            omitted_id = int(omitted_id_np)
            mask = ids!=omitted_id
            eligible_ids,eligible_xlf,eligible_c = ids[mask],xlf[mask],c[mask,:]
            order = magnetic_order(eligible_ids,eligible_xlf)
            selected = order[:K]
            selected_ids = eligible_ids[selected].tolist()
            selected_sum,oracle,ratios = evaluate(eligible_c,selected)
            retention = float(ratios.min())
            was_selected = omitted_id in full_selected_ids
            predicted_oracle = base_oracle-np.maximum(c[omitted_index,:]-chemical_rank9_values,0)
            predicted_selected_sum = base_sum-c[omitted_index,:]+c[full_order[K],:] if was_selected else base_sum
            assert np.allclose(oracle,predicted_oracle,rtol=1e-12,atol=SUM_ATOL)
            assert np.allclose(selected_sum,predicted_selected_sum,rtol=1e-12,atol=SUM_ATOL)
            invariant_counts["oracle_analytical_deletion_identity"] += 1
            invariant_counts["selected_sum_analytical_deletion_identity"] += 1
            deletion_identity_max_errors["oracle_absolute"] = max(deletion_identity_max_errors["oracle_absolute"],float(np.max(np.abs(oracle-predicted_oracle))))
            deletion_identity_max_errors["selected_sum_absolute"] = max(deletion_identity_max_errors["selected_sum_absolute"],float(np.max(np.abs(selected_sum-predicted_selected_sum))))
            entering = sorted(set(selected_ids)-set(full_selected_ids))
            leaving = sorted(set(full_selected_ids)-set(selected_ids))
            cutoff = float(eligible_xlf[order[K-1]])
            cutoff_tie = bool(eligible_xlf[order[K-1]]==eligible_xlf[order[K]])
            cutoff_group = eligible_ids[eligible_xlf==cutoff].tolist() if cutoff_tie else []
            assert len(eligible_ids)==31 and len(selected_ids)==K and len(set(selected_ids))==K
            assert omitted_id not in selected_ids
            invariant_counts["all_cases_checked"] += 1
            invariant_counts["exactly_8_of_31_unique_eligible_selected"] += 1
            invariant_counts["positive_oracles_and_ratios_in_unit_interval"] += 1
            if not was_selected:
                invariant_counts["originally_unselected_cases"] += 1
                assert selected_ids==full_selected_ids and np.array_equal(selected_sum,base_sum)
                assert not entering and not leaving
                invariant_counts["unselected_selection_and_numerator_unchanged"] += 1
                assert np.all(oracle<=base_oracle+SUM_ATOL)
                invariant_counts["unselected_oracles_nonincreasing"] += 1
                assert np.all(ratios>=base_ratios-RATIO_ATOL)
                invariant_counts["unselected_each_fraction_retention_nondecreasing"] += 1
                assert retention>=base_retention-RATIO_ATOL
                invariant_counts["unselected_minimum_retention_nondecreasing"] += 1
            else:
                invariant_counts["originally_selected_cases"] += 1
                assert entering==[original_rank9_id] and leaving==[omitted_id]
                assert set(selected_ids)==(set(full_selected_ids)-{omitted_id})|{original_rank9_id}
                invariant_counts["selected_exact_rank9_replacement"] += 1
            row = {"element":element,"omitted_id":omitted_id,"omitted_excel_row":omitted_id+3,
                   "baseline_n":32,"eligible_n":31,"k":K,
                   "baseline_retention":base_retention,"loo_retention":retention,
                   "delta_percentage_points":100*(retention-base_retention),
                   "active_fractions":";".join(active_fractions(ratios)),
                   "omitted_in_magnetic8":was_selected,"original_XLF_rank":original_rank[omitted_id],
                   "entering_id":entering[0] if entering else None,
                   "replacement_for_id":omitted_id if was_selected else None,
                   "selected_ids":";".join(map(str,selected_ids)),
                   "baseline_selected_ids":";".join(map(str,full_selected_ids)),
                   "cutoff_XLF":cutoff,"cutoff_tie":cutoff_tie,
                   "cutoff_tied_ids":";".join(map(str,cutoff_group)),
                   "all_case_invariants_passed":True}
            for f in range(4):
                row[f"F{f+1}_selected_sum"] = float(selected_sum[f])
                row[f"F{f+1}_oracle_sum"] = float(oracle[f])
                row[f"F{f+1}_ratio"] = float(ratios[f])
                row[f"F{f+1}_removed_concentration"] = float(c[omitted_index,f])
                row[f"F{f+1}_removed_fullfile_share"] = float(c[omitted_index,f]/full_file_totals[j,f])
            details.append(row)
            metal_rows.append(row)
        retentions = np.array([row["loo_retention"] for row in metal_rows])
        deltas = np.array([row["delta_percentage_points"] for row in metal_rows])
        extreme_ids = lambda values,target,tol: ";".join(str(metal_rows[i]["omitted_id"]) for i in np.flatnonzero(np.isclose(values,target,rtol=0,atol=tol)))
        min_ret,max_ret = float(retentions.min()),float(retentions.max())
        max_abs = float(np.abs(deltas).max())
        positive = float(deltas.max()) if deltas.max()>EXTREME_PP_ATOL else None
        negative = float(deltas.min()) if deltas.min() < -EXTREME_PP_ATOL else None
        summaries.append({"element":element,"baseline_retention":base_retention,"n_omissions":32,
                          "min_loo_retention":min_ret,"min_omitted_ids":extreme_ids(retentions,min_ret,RATIO_ATOL),
                          "max_loo_retention":max_ret,"max_omitted_ids":extreme_ids(retentions,max_ret,RATIO_ATOL),
                          "median_loo_retention":float(np.median(retentions)),
                          "max_absolute_delta_pp":max_abs,"max_absolute_delta_omitted_ids":extreme_ids(np.abs(deltas),max_abs,EXTREME_PP_ATOL),
                          "largest_positive_delta_pp":positive,"largest_positive_omitted_ids":extreme_ids(deltas,positive,EXTREME_PP_ATOL) if positive is not None else "",
                          "largest_negative_delta_pp":negative,"largest_negative_omitted_ids":extreme_ids(deltas,negative,EXTREME_PP_ATOL) if negative is not None else "",
                          "positive_delta_cases":int(np.sum(deltas>EXTREME_PP_ATOL)),
                          "negative_delta_cases":int(np.sum(deltas < -EXTREME_PP_ATOL)),
                          "zero_within_tolerance_delta_cases":int(np.sum(np.abs(deltas)<=EXTREME_PP_ATOL))})

    # Independent selected-case calculation uses Python lists/sorting/sums and
    # original Excel column positions, rather than the NumPy analysis helpers.
    independent_cases = []
    for omitted_id in (1,12):
        eligible_rows = [row for row in rows if int(row[0])!=omitted_id]
        chosen_rows = sorted(eligible_rows,key=lambda row:(-float(row[58]),int(row[0])))[:8]
        selected_ids = [int(row[0]) for row in chosen_rows]
        pb_columns_zero_based = [8,18,28,38]
        picked = [sum(float(row[column]) for row in chosen_rows) for column in pb_columns_zero_based]
        oracle = [sum(sorted((float(row[column]) for row in eligible_rows),reverse=True)[:8]) for column in pb_columns_zero_based]
        ratios = [a/b for a,b in zip(picked,oracle)]
        primary = next(row for row in details if row["element"]=="Pb" and row["omitted_id"]==omitted_id)
        primary_ids = [int(value) for value in primary["selected_ids"].split(";")]
        checks = {"selected_ids_match":selected_ids==primary_ids,
                  "selected_sums_match":bool(np.allclose(picked,[primary[f"F{f+1}_selected_sum"] for f in range(4)],rtol=1e-12,atol=SUM_ATOL)),
                  "oracle_sums_match":bool(np.allclose(oracle,[primary[f"F{f+1}_oracle_sum"] for f in range(4)],rtol=1e-12,atol=SUM_ATOL)),
                  "retention_matches":bool(np.isclose(min(ratios),primary["loo_retention"],rtol=0,atol=RATIO_ATOL))}
        assert all(checks.values())
        independent_cases.append({"element":"Pb","omitted_id":omitted_id,"selected_ids":selected_ids,
                                  "selected_sums":picked,"oracle_sums":oracle,"fraction_ratios":ratios,
                                  "retention":min(ratios),"checks":checks})

    reference_path = OUT.parent/"shortlist_audit"/"shortlist_summary.json"
    r3_check = {"reference_path":str(reference_path),"available":reference_path.is_file()}
    if reference_path.is_file():
        reference = json.loads(reference_path.read_text(encoding="utf-8"))
        r3_check["source_sha_matches"] = reference["source_sha256"]==source_sha
        if r3_check["source_sha_matches"]:
            prior = next(row for row in reference["Pb_sensitivity"] if row["subset"]=="omit_sample_1")
            current = next(row for row in details if row["element"]=="Pb" and row["omitted_id"]==1)
            r3_check["Pb_omit1_R3_retention"] = prior["worst_case_retention"]
            r3_check["Pb_omit1_current_retention"] = current["loo_retention"]
            r3_check["Pb_omit1_matches"] = bool(np.isclose(prior["worst_case_retention"],current["loo_retention"],rtol=0,atol=RATIO_ATOL))
            r3_check["all_baseline_retentions_match"] = all(np.isclose(baselines[element]["retention"],reference["magnetic_k8"][element]["worst_case_retention"],rtol=0,atol=RATIO_ATOL) for element in ELEMENTS)
            assert r3_check["Pb_omit1_matches"] and r3_check["all_baseline_retentions_match"]
        else:
            r3_check["comparison_not_performed_reason"] = "R3 records a different source checksum"
    assert len(details)==288 and len(summaries)==9
    assert hashlib.sha256(source.read_bytes()).hexdigest()==source_sha
    validation = {"source_path":str(source),"source_sha256":source_sha,"source_unchanged_at_finish":True,
                  "sheet":"All rsults","sample_range":"A4:A35","XLF_range":"BG4:BG35",
                  "fraction_mapping":{"F1":"B:J","F2":"L:T","F3":"V:AD","F4":"AF:AN"},
                  "software":{"python":platform.python_version(),"numpy":np.__version__,"openpyxl":openpyxl.__version__},
                  "all_concentrations_finite_nonnegative":True,"positive_denominators_checked":True,
                  "number_of_records":32,"number_of_metals":9,"number_of_omission_cases":288,
                  "fixed_budget":8,"baseline_selected_fraction":8/32,"omission_selected_fraction":8/31,
                  "selection_rule":"Descending stored XLF; exact ties resolved by ascending sample ID",
                  "baseline_selected_ids":full_selected_ids,"original_XLF_rank9_id":original_rank9_id,
                  "baseline_results":baselines,"per_metal_summaries":summaries,
                  "invariant_counts":invariant_counts,"independent_Pb_cases":independent_cases,"R3_read_only_comparison":r3_check,
                  "analytical_deletion_checks":{"chemical_oracle_identity":"O'_f=O_f-max(c_removed,f-h_f,0), where h_f is the original ninth-largest chemical concentration in fraction f",
                                                "selected_sum_identity":"If originally selected, A'_f=A_f-c_removed,f+c_original_XLF_rank9,f; otherwise A'_f=A_f",
                                                "all_288_cases_passed":True,"maximum_absolute_discrepancies":deletion_identity_max_errors,
                                                "comparison_relative_tolerance":1e-12,"comparison_absolute_tolerance":SUM_ATOL},
                  "cutoff_tie_case_count":sum(row["cutoff_tie"] for row in details),
                  "cutoff_tie_omitted_ids":sorted({row["omitted_id"] for row in details if row["cutoff_tie"]}),
                  "tolerances":{"ratio_absolute":RATIO_ATOL,"sum_absolute":SUM_ATOL,"extreme_delta_pp_absolute":EXTREME_PP_ATOL},
                  "definitions":{"loo_retention":"Minimum over four fractions of selected concentration sum divided by same-population top-eight oracle sum",
                                 "delta_percentage_points":"100*(LOO retention - full32 retention)",
                                 "removed_fullfile_share":"Omitted record concentration divided by all32 records' sum for that metal/fraction",
                                 "largest_negative_delta":"Most negative delta strictly below tolerance; null if there is no negative case",
                                 "extreme_omitted_ids":"All omissions tied at an extreme within the documented numerical tolerance"},
                  "interpretation":"Descriptive sensitivity of the observed fixed-budget concentration-sum decision score. Not jackknife inference, an independent validation cohort, a population confidence interval, or a reason to delete an influential record.",
                  "limitations":["Budget remains8 while eligible population changes from32 to31; sampling fraction increases from25% to25.80645%.",
                                 "Each oracle is recomputed from the same31 eligible records as its magnetic selection.",
                                 "Removing an originally unselected record leaves magnetic numerators unchanged and can only reduce the oracles, so fraction-wise and minimum retention cannot decrease.",
                                 "Removing a selected record changes numerators through replacement by original XLF rank9, as well as potentially changing the oracles.",
                                 "Concentration sums are decision scores, not represented mass, landscape inventory, exposure, or biological risk.",
                                 "Original laboratory/provenance limitations remain unresolved; influence does not identify a data error.",
                                 "No optimization, resampling confidence interval, or new-theory claim is performed."]}
    OUT.mkdir(parents=True,exist_ok=True)
    write_csv("influence_details.csv",details)
    write_csv("influence_summary.csv",summaries)
    (OUT/"influence_validation.json").write_text(json.dumps(validation,indent=2,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    note = ["# Fixed-budget leave-one-record-out influence", "",
            f"Source SHA-256: `{source_sha}`. The original workbook and earlier R3/R4 outputs remain unchanged.","",
            "For each of nine metals, all32 possible single-record omissions were evaluated. Each case reselects eight records by descending stored XLF, breaks ties by ascending sample ID, and recomputes each fraction's best-eight oracle from the same31 eligible records. The reported retention is the minimum of the four selected-sum/oracle-sum ratios. Deltas are percentage points relative to the full32-record result.","",
            "The budget stays at eight records. Thus the selected fraction changes from8/32=25% to8/31=25.80645%; it is not held at25%.","",
            "| Metal | Full32 retention | Minimum LOO retention (omitted IDs) | Median LOO retention | Maximum LOO retention (omitted IDs) | Largest absolute delta (pp; IDs) |",
            "|---|---:|---|---:|---|---|"]
    for row in summaries:
        note.append(f"| {row['element']} | {row['baseline_retention']:.4%} | {row['min_loo_retention']:.4%} ({row['min_omitted_ids']}) | {row['median_loo_retention']:.4%} | {row['max_loo_retention']:.4%} ({row['max_omitted_ids']}) | {row['max_absolute_delta_pp']:.4f}; {row['max_absolute_delta_omitted_ids']} |")
    pb1 = next(row for row in details if row["element"]=="Pb" and row["omitted_id"]==1)
    pb12 = next(row for row in details if row["element"]=="Pb" and row["omitted_id"]==12)
    note += ["", "## Interpretation and checks", "",
             "For the216 cases omitting an originally unselected record, selected IDs and concentration-sum numerators are unchanged. Every chemical oracle is nonincreasing, and every fraction ratio and minimum retention is nondecreasing. An improvement can therefore arise solely from removing a comparator from the eligible population.","",
             f"For the72 cases omitting an originally selected record, original XLF rank9 (sample{original_rank9_id}) enters. This changes the selected numerator as well as potentially changing the oracle. Both mechanisms are recorded separately. All288 cases contain exactly8 distinct selections from31 eligible records, with positive denominators. There are {validation['cutoff_tie_case_count']} cutoff-tie cases.","",
             "All288 recalculated oracle sums also match the independent deletion identity O'_f=O_f-max(c_removed,f-h_f,0), where h_f is the original ninth-largest chemical value. Recalculated selected sums match A'_f=A_f-c_removed,f+c_XLF-rank9,f for selected omissions and A'_f=A_f otherwise, within the documented floating-point tolerances.","",
             f"For Pb, omitting sample1 retains {pb1['loo_retention']:.8%} ({pb1['delta_percentage_points']:+.8f} percentage points); the magnetic selection is unchanged and the value agrees with the earlier R3 calculation. Omitting selected sample12 introduces sample{pb12['entering_id']} and gives {pb12['loo_retention']:.8%} ({pb12['delta_percentage_points']:+.8f} percentage points). These two cases were independently recomputed using plain Python sorting and sums on the original Excel values.","",
             "This is descriptive influence analysis. It is not a jackknife confidence interval, independent cohort validation, or evidence that an influential record should be removed. Concentration sums are decision scores rather than measured mass, landscape burden, exposure or biological risk. Source provenance and laboratory uncertainties remain unresolved.","",
             "Files: influence_details.csv contains all288 cases, selected IDs, replacement information, cutoff ties, fraction sums/oracles/ratios, and each removed record's concentration and full-file concentration share. influence_summary.csv identifies extrema and positive/negative changes. influence_validation.json records baselines, source identity, invariants and independent checks.","",
             "Reproduce with `python influence_audit.py --source \"path/to/Iron Factory.xlsx\"`. Omitting --source retains the original Windows source path. The run uses Python, NumPy and openpyxl versions recorded in the JSON. No R3 code is imported and no optimization is run."]
    (OUT/"influence_note.md").write_text("\n".join(note)+"\n",encoding="utf-8")
    print(json.dumps({"source_sha256":source_sha,"case_count":len(details),"summary":summaries,
                      "invariant_counts":invariant_counts,"independent_Pb_cases":independent_cases,
                      "R3_comparison":r3_check,"cutoff_tie_cases":validation["cutoff_tie_case_count"]},indent=2),flush=True)


if __name__=="__main__":
    main(arguments().source)
