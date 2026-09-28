"""Fixed-budget magnetic shortlist audit; original workbook is read-only.

Run with bundled Python and installed openpyxl, NumPy and SciPy.
Outputs are written only beside this script, in shortlist_audit/.
"""
from __future__ import annotations

import csv
import argparse
import hashlib
import itertools
import json
import platform
from pathlib import Path

import numpy as np
import openpyxl
import scipy
from scipy.optimize import Bounds, LinearConstraint, milp


SOURCE = Path(__file__).resolve().parents[2] / "source/Iron Factory.xlsx"
OUT = Path(__file__).resolve().parent
ELEMENTS = ["Cd", "Co", "Cr", "Cu", "Fe", "Mn", "Ni", "Pb", "Zn"]
FRACTIONS = ["F1", "F2", "F3", "F4"]
RNG_SEED = 20260927
MILP_OPTIONS = {"time_limit": 30.0, "mip_rel_gap": 1e-9, "presolve": True}


def write_csv(name: str, rows: list[dict]) -> None:
    with (OUT / name).open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def magnetic_order(ids: np.ndarray, xlf: np.ndarray) -> np.ndarray:
    return np.array(sorted(range(len(ids)), key=lambda i: (-xlf[i], ids[i])))


def score_shortlist(c: np.ndarray, selected: np.ndarray, k: int) -> dict:
    total = c.sum(axis=0)
    oracle = np.sort(c, axis=0)[-k:, :].sum(axis=0)
    assert np.all(np.isfinite(c)) and np.all(c >= 0)
    assert np.all(total > 0) and np.all(oracle > 0), "Zero-score columns require separate handling; no ratios computed"
    picked = c[selected, :].sum(axis=0)
    capture = picked / total
    retention = picked / oracle
    worst = float(retention.min())
    return {
        "selected_fraction_sums": picked.tolist(),
        "all_site_fraction_sums": total.tolist(),
        "per_fraction_oracle_top_k_sums": oracle.tolist(),
        "per_fraction_capture": capture.tolist(),
        "per_fraction_oracle_retention": retention.tolist(),
        "worst_case_capture": float(capture.min()),
        "worst_case_retention": worst,
        "worst_case_regret": 1.0 - worst,
        "active_fractions": [FRACTIONS[i] for i in np.flatnonzero(np.isclose(retention, worst, rtol=0, atol=1e-8))],
    }


def cutoff_tie(ids: np.ndarray, xlf: np.ndarray, order: np.ndarray, k: int) -> dict:
    tied = bool(xlf[order[k-1]] == xlf[order[k]]) if k < len(ids) else False
    value = float(xlf[order[k-1]])
    group = ids[xlf == value].tolist() if tied else []
    return {"cutoff_tie": tied, "cutoff_xlf": value,
            "cutoff_tied_sample_ids": group,
            "selected_cutoff_tied_ids": [int(ids[i]) for i in order[:k] if tied and xlf[i] == value]}


def optimize_maximin(c: np.ndarray, ids: np.ndarray, k: int) -> dict:
    n, number_fractions = c.shape
    oracle = np.sort(c, axis=0)[-k:, :].sum(axis=0)
    assert np.all(np.isfinite(c)) and np.all(c >= 0)
    assert np.all(oracle > 0), "Zero-oracle columns require separate handling; optimization not run"
    objective = np.zeros(n+1)
    objective[-1] = -1.0
    # -sum(z_i*c_if)/O_f + t <= 0 gives well-scaled ratio constraints.
    matrix = np.zeros((number_fractions+1, n+1))
    matrix[0, :n] = 1.0
    matrix[1:, :n] = -c.T / oracle[:, None]
    matrix[1:, -1] = 1.0
    lower = np.r_[k, np.full(number_fractions, -np.inf)]
    upper = np.r_[k, np.zeros(number_fractions)]
    result = milp(objective, integrality=np.r_[np.ones(n), 0],
                  bounds=Bounds(np.zeros(n+1), np.ones(n+1)),
                  constraints=LinearConstraint(matrix, lower, upper), options=MILP_OPTIONS)
    base = {"status": int(result.status), "message": str(result.message),
            "solver_success": bool(result.success), "solver_options": MILP_OPTIONS,
            "mip_relative_gap": float(result.mip_gap) if getattr(result, "mip_gap", None) is not None else None,
            "retention_upper_bound_from_dual": -float(result.mip_dual_bound) if getattr(result, "mip_dual_bound", None) is not None else None,
            "mip_node_count": int(result.mip_node_count) if getattr(result, "mip_node_count", None) is not None else None}
    if result.x is None:
        return {**base, "selected_ids": [], "validation_passed": False, "failure": "No feasible incumbent returned"}
    z = result.x[:n]
    selected = np.flatnonzero(z > 0.5)
    sums = c[selected, :].sum(axis=0)
    ratios = sums / oracle
    direct_t = float(ratios.min())
    solver_t = float(result.x[-1])
    checks = {
        "selected_count_equals_budget": len(selected) == k,
        "maximum_binary_integrality_error": float(np.max(np.abs(z - np.round(z)))),
        "direct_minus_solver_retention": direct_t - solver_t,
        "minimum_fraction_constraint_slack": float(np.min(ratios - solver_t)),
        "objective_matches_t": bool(np.isclose(-float(result.fun), solver_t, atol=1e-9, rtol=0)),
    }
    valid = (checks["selected_count_equals_budget"] and
             checks["maximum_binary_integrality_error"] < 1e-6 and
             abs(checks["direct_minus_solver_retention"]) < 1e-7 and
             checks["minimum_fraction_constraint_slack"] >= -1e-7 and
             checks["objective_matches_t"])
    return {**base, "selected_ids": sorted(int(ids[i]) for i in selected),
            "selected_count": len(selected), "direct_fraction_sums": sums.tolist(),
            "per_fraction_oracle_top_k_sums": oracle.tolist(),
            "direct_fraction_retentions": ratios.tolist(),
            "direct_worst_case_retention": direct_t, "solver_t": solver_t,
            "optimum_retention_if_status_0": direct_t if result.status == 0 else None,
            "worst_case_regret": 1.0-direct_t,
            "active_fractions": [f"F{i+1}" for i in np.flatnonzero(np.isclose(ratios, direct_t, atol=1e-8, rtol=0))],
            "checks": checks, "validation_passed": bool(valid)}


def sampled_weight_check(c: np.ndarray, selected: np.ndarray, k: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    weights = np.vstack([np.eye(c.shape[1]), np.full((1,c.shape[1]),1/c.shape[1]),
                         rng.dirichlet(np.ones(c.shape[1]), size=1000)])
    weighted_site_scores = c @ weights.T
    selected_sum = weighted_site_scores[selected, :].sum(axis=0)
    weighted_oracle = np.sort(weighted_site_scores, axis=0)[-k:, :].sum(axis=0)
    observed = selected_sum / weighted_oracle
    exact = float((c[selected, :].sum(axis=0) / np.sort(c, axis=0)[-k:, :].sum(axis=0)).min())
    return {"weights_checked": len(weights), "seed": seed,
            "exact_vertex_minimum": exact, "smallest_checked_actual_weighted_oracle_ratio": float(observed.min()),
            "no_checked_ratio_below_bound": bool(np.all(observed >= exact-1e-10)),
            "vertices_attain_bound": bool(np.isclose(observed[:c.shape[1]].min(), exact, rtol=0, atol=1e-10)),
            "interpretation": "A numerical implementation check only; sampled weights are not a proof."}


def parse_cli_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--source", type=Path, default=SOURCE,
                        help="Path to the original Iron Factory.xlsx workbook; opened read-only")
    args = parser.parse_args(argv)
    args.source = args.source.expanduser().resolve()
    if not args.source.is_file():
        parser.error(f"Source workbook does not exist or is not a file: {args.source}")
    return args


def main(source: Path = SOURCE) -> None:
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Source workbook does not exist or is not a file: {source}")
    OUT.mkdir(parents=True, exist_ok=True)
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    workbook = openpyxl.load_workbook(source, data_only=True, read_only=True)
    source_rows = list(workbook["All rsults"].iter_rows(min_row=4, max_row=35, max_col=60, values_only=True))
    workbook.close()
    ids = np.array([int(row[0]) for row in source_rows])
    assert ids.tolist() == list(range(1,33))
    xlf = np.array([float(row[58]) for row in source_rows])
    c_all = np.array([[[float(row[start+j-1]) for start in (2,12,22,32)] for j in range(9)] for row in source_rows])
    assert np.all(c_all > 0) and np.all(np.isfinite(c_all))
    data_checks = {"all_concentrations_finite":bool(np.all(np.isfinite(c_all))),
                   "all_concentrations_nonnegative":bool(np.all(c_all>=0)),
                   "all_concentrations_strictly_positive":bool(np.all(c_all>0)),
                   "minimum_concentration":float(c_all.min()),
                   "zero_fraction_columns":0,
                   "minimum_full_data_oracle_sum_over_k1_to31":float(np.max(c_all,axis=0).min()),
                   "all_evaluated_oracle_denominators_checked_positive":True}
    order = magnetic_order(ids, xlf)
    tie_rows = []
    for k in range(1,32):
        info = cutoff_tie(ids,xlf,order,k)
        if info["cutoff_tie"]:
            tie_rows.append({"k":k,"cutoff_xlf":info["cutoff_xlf"],
                             "tied_ids":";".join(map(str,info["cutoff_tied_sample_ids"])),
                             "selected_tied_ids":";".join(map(str,info["selected_cutoff_tied_ids"]))})
    print(json.dumps({"event":"source_loaded","n":32,"source_sha256":source_sha,"cutoff_ties":tie_rows}),flush=True)

    budget_rows, detailed_rows, k8_magnetic, optimization_rows = [], [], {}, []
    optimizations, checks = {}, {}
    for j, element in enumerate(ELEMENTS):
        c = c_all[:,j,:]
        for k in range(1,32):
            selected = order[:k]
            score = score_shortlist(c,selected,k)
            tie = cutoff_tie(ids,xlf,order,k)
            common = {"element":element,"n":32,"k":k,
                      "selected_ids_descending_XLF":";".join(str(int(ids[i])) for i in selected),
                      "cutoff_tie":tie["cutoff_tie"]}
            budget_rows.append({**common,"worst_case_retention":score["worst_case_retention"],
                                "worst_case_regret":score["worst_case_regret"],
                                "worst_case_capture":score["worst_case_capture"],
                                "active_fractions":";".join(score["active_fractions"])})
            for f in range(4):
                detailed_rows.append({**common,"fraction":FRACTIONS[f],
                                      "selected_sum":score["selected_fraction_sums"][f],
                                      "all_site_sum":score["all_site_fraction_sums"][f],
                                      "oracle_top_k_sum":score["per_fraction_oracle_top_k_sums"][f],
                                      "capture_fraction":score["per_fraction_capture"][f],
                                      "oracle_retention":score["per_fraction_oracle_retention"][f]})
            if k == 8:
                k8_magnetic[element] = {"selected_ids_descending_XLF":ids[selected].tolist(),**score,**tie}
        optimized = optimize_maximin(c,ids,8)
        optimizations[element] = optimized
        assert optimized["validation_passed"], (element,optimized)
        optimization_rows.append({"element":element,"n":32,"k":8,
                                  "XLF_worst_case_retention":k8_magnetic[element]["worst_case_retention"],
                                  "retrospective_maximin_retention":optimized["direct_worst_case_retention"],
                                  "retention_difference":optimized["direct_worst_case_retention"]-k8_magnetic[element]["worst_case_retention"],
                                  "selected_ids":";".join(map(str,optimized["selected_ids"])),
                                  "active_fractions":";".join(optimized["active_fractions"]),
                                  "solver_status":optimized["status"],"mip_relative_gap":optimized["mip_relative_gap"],
                                  "retention_upper_bound_from_dual":optimized["retention_upper_bound_from_dual"],
                                  "validation_passed":optimized["validation_passed"]})
        checks[element] = sampled_weight_check(c,order[:8],8,RNG_SEED+j)
        assert checks[element]["no_checked_ratio_below_bound"] and checks[element]["vertices_attain_bound"]
        print(json.dumps({"event":"metal_completed",**optimization_rows[-1]}),flush=True)

    sensitivities, sensitivity_csv = [], []
    for name,mask,k in [("all_32",np.ones(32,dtype=bool),8),
                        ("omit_sample_1",ids!=1,8),
                        ("IDs_1_to_16",ids<=16,4),
                        ("IDs_17_to_32",ids>=17,4)]:
        subset_ids,subset_xlf,c = ids[mask],xlf[mask],c_all[mask,ELEMENTS.index("Pb"),:]
        subset_order = magnetic_order(subset_ids,subset_xlf)
        score = score_shortlist(c,subset_order[:k],k)
        tie = cutoff_tie(subset_ids,subset_xlf,subset_order,k)
        sensitivity = {"subset":name,"element":"Pb","n":len(subset_ids),"k":k,
                       "sample_ids":subset_ids.tolist(),"selected_ids_descending_XLF":subset_ids[subset_order[:k]].tolist(),
                       **score,**tie}
        sensitivities.append(sensitivity)
        for f in range(4):
            sensitivity_csv.append({"subset":name,"element":"Pb","n":len(subset_ids),"k":k,
                                    "selected_ids":";".join(map(str,sensitivity["selected_ids_descending_XLF"])),
                                    "fraction":FRACTIONS[f],"capture_fraction":score["per_fraction_capture"][f],
                                    "oracle_retention":score["per_fraction_oracle_retention"][f],
                                    "worst_case_retention":score["worst_case_retention"],
                                    "worst_case_regret":score["worst_case_regret"],"cutoff_tie":tie["cutoff_tie"]})

    # Independent exhaustive enumeration of all C(6,2)=15 possible subsets.
    tiny_c = c_all[:6,ELEMENTS.index("Pb"),:2]
    tiny_ids = ids[:6]
    tiny_oracle = np.sort(tiny_c,axis=0)[-2:,:].sum(axis=0)
    tiny_results = [{"selected_ids":[int(tiny_ids[i]) for i in subset],
                     "retention":float(np.min(tiny_c[list(subset),:].sum(axis=0)/tiny_oracle))}
                    for subset in itertools.combinations(range(6),2)]
    brute_best = max(row["retention"] for row in tiny_results)
    tiny_milp = optimize_maximin(tiny_c,tiny_ids,2)
    brute_check = {"data":"Original Pb, samples1–6, fractionsF1/F2, k=2",
                   "enumerated_subset_count":len(tiny_results),"all_subsets":tiny_results,
                   "brute_force_optimum":brute_best,"MILP":tiny_milp,
                   "optima_agree":bool(np.isclose(brute_best,tiny_milp["direct_worst_case_retention"],rtol=0,atol=1e-9))}
    assert brute_check["optima_agree"] and tiny_milp["validation_passed"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_sha

    summary = {"source_path":str(source),"source_sha256":source_sha,"source_unchanged_at_finish":True,
               "sheet":"All rsults","sample_range":"A4:A35","stored_XLF_range":"BG4:BG35",
               "fraction_mapping":{"F1":"B:J","F2":"L:T","F3":"V:AD","F4":"AF:AN"},
               "software":{"python":platform.python_version(),"numpy":np.__version__,"scipy":scipy.__version__,"openpyxl":openpyxl.__version__},
               "selection_rule":"Descending stored XLF; ascending sample ID breaks exact XLF ties",
               "data_checks":data_checks,"k8_cutoff_unambiguous":bool(xlf[order[7]]>xlf[order[8]]),
               "fixed_budget_range":list(range(1,32)),"cutoff_ties":tie_rows,
               "definitions":{
                   "per_fraction_capture":"sum of selected-site fraction concentrations / sum across all eligible sites",
                   "per_fraction_oracle_retention":"selected-site concentration sum / largest possible concentration sum over k eligible sites in that fraction",
                   "weighted_oracle":"For a common nonnegative weight vector summing to1, choose the best k sites by their weighted concentration score",
                   "exact_worst_case_retention":"Minimum of the four per-fraction oracle-retention ratios; equivalently the infimum of selected weighted sum / optimal-k weighted sum over the closed simplex",
                   "worst_case_regret":"1 minus exact worst-case retention",
                   "hindsight_benchmark":"Binary MILP maximizes minimum per-fraction oracle retention using all chemical observations; not a deployable magnetic screen"},
               "magnetic_k8":k8_magnetic,"retrospective_maximin_k8":optimizations,
               "Pb_sensitivity":sensitivities,"tiny_exhaustive_optimizer_check":brute_check,
               "sampled_weight_checks":checks,
               "limitations":["These are sums of measured concentrations at sampled sites, not area-weighted inventories, exposure or measured biological risk.",
                              "The same nonnegative normalized weights apply to all sites within a single metal; no physical release-weight calibration is supplied.",
                              "The hindsight optimizer and oracle require all chemical data; neither is an operational magnetic-only screening strategy.",
                              "IDs1–16 and17–32 are exploratory subsets of unknown provenance, not established batches, depths or campaigns.",
                              "All calculations are descriptive for the supplied32-site dataset; no population-level or causal claim is made.",
                              "Earlier Cd constant-total and Cr proportionality provenance issues remain unresolved.",
                              "The exact guarantee is conditional on stored numerical concentrations; tolerance checks do not establish measurement accuracy.",
                              "No novelty or new-theory claim is made."]}
    write_csv("magnetic_budget_summary.csv",budget_rows)
    write_csv("magnetic_per_fraction.csv",detailed_rows)
    write_csv("retrospective_maximin_k8.csv",optimization_rows)
    write_csv("Pb_sensitivity.csv",sensitivity_csv)
    write_csv("XLF_cutoff_ties.csv",tie_rows)
    (OUT/"shortlist_summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False,allow_nan=False),encoding="utf-8")

    lines = ["# Fixed-budget shortlist audit", "",f"Source SHA-256: `{source_sha}`.", "",
             "This is a retrospective description of the supplied 32 samples. Stored XLF ranks sites in descending order, with ascending sample ID resolving exact ties. Original Excel data and earlier delivered outputs were not modified.","",
             "For each budget k=1–31, the CSVs report concentration-sum capture and retention relative to the best k-site sum separately in F1–F4. The smallest of the four retention ratios is the exact worst-case ratio over common nonnegative normalized weights; regret is one minus this ratio. The comparison uses the optimal k-site weighted score at each weight, not a fixed oracle selected for a different weight.","",
             "The k=8 maximin comparator uses the complete chemical dataset to choose eight sites. It is an informed hindsight benchmark, not a deployable magnetic screening rule. Each returned selection was independently recalculated from its site IDs.","",
             "| Metal | XLF worst-case retention | Hindsight maximin retention | Hindsight selected IDs | Solver status / gap |", "|---|---:|---:|---|---|"]
    for row in optimization_rows:
        lines.append(f"| {row['element']} | {row['XLF_worst_case_retention']:.4%} | {row['retrospective_maximin_retention']:.4%} | {row['selected_ids']} | {row['solver_status']} / {row['mip_relative_gap']} |")
    lines += ["", "## Pb sensitivity", "", "| Eligible sites | Budget | Worst-case retention | Worst-case regret | Active fraction |", "|---|---:|---:|---:|---|"]
    for row in sensitivities:
        lines.append(f"| {row['subset']} | {row['k']} | {row['worst_case_retention']:.4%} | {row['worst_case_regret']:.4%} | {';'.join(row['active_fractions'])} |")
    lines += ["", "The two ID ranges are exploratory subsets with unknown meaning. Omitting sample1 changes the eligible population and its oracle denominators; this is not evidence that the observation should be discarded.","",
              f"XLF cutoff ties affect budgets: {', '.join(str(row['k']) for row in tie_rows)}. Budget8 has {'a tie' if k8_magnetic['Pb']['cutoff_tie'] else 'no cutoff tie'}. Full tie groups are recorded in XLF_cutoff_ties.csv.","",
              f"Optimizer check: exhaustive enumeration of all15 subsets in the six-site/two-fraction test gives retention {brute_best:.12f}; the MILP agrees. Each full-data magnetic k=8 guarantee also passed a check at four simplex vertices, the equal-weight vector and1000 seeded random weights. Sampled weights check implementation and do not prove the guarantee.","",
              "All reported sums are sums of concentrations over sampled sites, not spatial inventories, measured release, exposure or biological risk. Laboratory/provenance concerns for Cd and Cr remain unresolved. The calculations establish properties of the supplied numbers and make no new-theory or novelty claim.","",
              "Reproduce by running shortlist_audit.py with the bundled Python runtime and its NumPy, openpyxl and SciPy dependencies. Solver status0 denotes optimality within the configured numerical tolerance; reported gaps and dual bounds are retained in JSON. No statistical confidence interval is inferred from these site subsets."]
    (OUT/"brief_note.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({"event":"complete","files":["shortlist_audit.py","magnetic_budget_summary.csv","magnetic_per_fraction.csv","retrospective_maximin_k8.csv","Pb_sensitivity.csv","XLF_cutoff_ties.csv","shortlist_summary.json","brief_note.md"],"all_MILP_statuses":[optimizations[e]["status"] for e in ELEMENTS],"tiny_bruteforce_agreement":brute_check["optima_agree"],"Pb_sensitivity":[{"subset":s["subset"],"retention":s["worst_case_retention"],"active":s["active_fractions"]} for s in sensitivities]}),flush=True)


if __name__ == "__main__":
    main(parse_cli_args().source)
