"""Independent, read-only verification of magnetic/Pareto claims.

Run with the bundled Python runtime. Dependencies: openpyxl, numpy, scipy.
The original workbook is opened read-only and never modified.
"""
from __future__ import annotations

import csv
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import openpyxl
import scipy
from scipy.stats import spearmanr


SOURCE = Path(__file__).resolve().parents[2] / "source/Iron Factory.xlsx"
OUT = Path(__file__).resolve().parent
EXPECTED = {
    "Pb": (67, 168), "Cr": (89, 251), "Co": (93, 266),
    "Fe": (71, 218), "Cd": (93, 298), "Ni": (70, 232),
    "Mn": (75, 252), "Cu": (12, 60), "Zn": (43, 244),
}
ELEMENTS = ["Cd", "Co", "Cr", "Cu", "Fe", "Mn", "Ni", "Pb", "Zn"]


def dump_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def correlation(x: np.ndarray, y: np.ndarray) -> dict:
    result = spearmanr(x, y)
    return {"n": len(x), "rho": float(result.statistic),
            "p_two_sided_scipy_asymptotic": float(result.pvalue)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    workbook = openpyxl.load_workbook(SOURCE, data_only=True, read_only=True)
    sheet = workbook["All rsults"]
    # Materialize once; indexing below remains in the original Excel coordinates.
    rows = list(sheet.iter_rows(min_row=4, max_row=35, max_col=60, values_only=True))
    ids = np.array([int(row[0]) for row in rows])
    assert ids.tolist() == list(range(1, 33))
    xlf = np.array([float(row[58]) for row in rows])  # BG, stored XLF
    # shape: sites x elements x extraction fractions
    fractions = np.array([
        [[float(row[start + j - 1]) for start in (2, 12, 22, 32)]
         for j in range(9)] for row in rows
    ])
    totals = np.array([[float(row[41 + j]) for j in range(9)] for row in rows])
    summary_rows, pair_rows = [], []

    for element in EXPECTED:
        j = ELEMENTS.index(element)
        records = []
        # Ordered dominating->dominated pairs; each comparable unordered pair
        # contributes exactly once (strictness excludes identical fraction vectors).
        for a in range(len(ids)):
            for b in range(len(ids)):
                if a == b:
                    continue
                delta = fractions[a, j, :] - fractions[b, j, :]
                if np.all(delta >= 0) and np.any(delta > 0):
                    relation = ("reversal" if xlf[a] < xlf[b]
                                else "magnetic_tie" if xlf[a] == xlf[b]
                                else "concordant")
                    row = {
                        "element": element,
                        "dominating_sample": int(ids[a]),
                        "dominated_sample": int(ids[b]),
                        "dominating_excel_row": int(ids[a] + 3),
                        "dominated_excel_row": int(ids[b] + 3),
                        "xlf_dominating": float(xlf[a]),
                        "xlf_dominated": float(xlf[b]),
                        "magnetic_relation": relation,
                        "componentwise_strict": bool(np.all(delta > 0)),
                        "equal_fraction_coordinates": ";".join(
                            f"F{k+1}" for k in range(4) if delta[k] == 0),
                    }
                    for k in range(4):
                        row[f"F{k+1}_dominating"] = float(fractions[a, j, k])
                        row[f"F{k+1}_dominated"] = float(fractions[b, j, k])
                        row[f"F{k+1}_difference"] = float(delta[k])
                    records.append(row)
        reversals = sum(row["magnetic_relation"] == "reversal" for row in records)
        ties = sum(row["magnetic_relation"] == "magnetic_tie" for row in records)
        componentwise_strict = sum(row["componentwise_strict"] for row in records)
        expected_reversals, expected_denominator = EXPECTED[element]
        strict_reversals = sum(
            row["componentwise_strict"] and row["magnetic_relation"] == "reversal"
            for row in records)
        weak_only = len(records) - componentwise_strict
        weak_only_reversals = reversals - strict_reversals
        summary_rows.append({
            "element": element,
            "dominance_pairs": len(records),
            "xlf_strict_reversals": reversals,
            "xlf_ties": ties,
            "xlf_strict_concordances": len(records) - reversals - ties,
            "reversal_fraction": reversals / len(records),
            "componentwise_strict_pairs": componentwise_strict,
            "weak_only_pairs_with_equal_coordinates": len(records) - componentwise_strict,
            "componentwise_strict_reversals": strict_reversals,
            "componentwise_strict_reversal_fraction": strict_reversals / componentwise_strict if componentwise_strict else None,
            "weak_only_reversals": weak_only_reversals,
            "weak_only_reversal_fraction": weak_only_reversals / weak_only if weak_only else None,
            "expected_reversals": expected_reversals,
            "expected_denominator": expected_denominator,
            "matches_expected": reversals == expected_reversals and len(records) == expected_denominator,
        })
        pair_rows.extend(records)

    pb_index = ELEMENTS.index("Pb")
    zn_index = ELEMENTS.index("Zn")
    pb_f1 = fractions[:, pb_index, 0]
    pb_total = totals[:, pb_index]
    # Sort by descending value, then ascending sample ID. Boundaries are reported
    # explicitly so any top-eight ambiguity can be checked.
    top_xlf = sorted(range(32), key=lambda i: (-xlf[i], ids[i]))[:8]
    top_pb_f1 = sorted(range(32), key=lambda i: (-pb_f1[i], ids[i]))[:8]
    intersection = sorted(set(ids[top_xlf]) & set(ids[top_pb_f1]))
    sample1 = {
        "sample": 1, "excel_row": 4,
        "Pb_F1_I4": float(pb_f1[0]), "Pb_total_AW4": float(pb_total[0]),
        "XLF_BG4": float(xlf[0]),
        "XLF_descending_competition_rank": int(1 + np.sum(xlf > xlf[0])),
        "XLF_other_equal_sites": ids[(xlf == xlf[0]) & (ids != 1)].tolist(),
        "Pb_fraction_values": fractions[0, pb_index, :].tolist(),
        "Pb_fraction_maxima": np.max(fractions[:, pb_index, :], axis=0).tolist(),
        "Pb_strictly_exceeds_all_other_samples_in_all_four": bool(
            np.all(fractions[0, pb_index, :] > fractions[1:, pb_index, :])),
    }
    tolerance_sensitivity = []
    for tolerance in (0, 1e-12, 1e-9):
        for element in EXPECTED:
            j = ELEMENTS.index(element)
            count, reversals, ties = 0, 0, 0
            for a in range(32):
                for b in range(32):
                    delta = fractions[a, j, :] - fractions[b, j, :]
                    if a != b and np.all(delta >= -tolerance) and np.any(delta > tolerance):
                        count += 1
                        reversals += bool(xlf[a] - xlf[b] < -tolerance)
                        ties += bool(abs(xlf[a] - xlf[b]) <= tolerance)
            tolerance_sensitivity.append({"absolute_tolerance": tolerance,
                                          "element": element, "dominance_pairs": count,
                                          "xlf_strict_reversals": reversals, "xlf_ties": ties})
    details = {
        "source": str(SOURCE),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "sheet": "All rsults", "sample_range": "A4:A35", "n_samples": 32,
        "fraction_units_from_workbook": "micrograms per gram",
        "magnetic_score": "stored XLF, cells BG4:BG35",
        "software": {"python": platform.python_version(), "openpyxl": openpyxl.__version__,
                     "numpy": np.__version__, "scipy": scipy.__version__},
        "definitions": {
            "dominance": "i >= j in all four fraction concentrations, and i > j in at least one",
            "reversal": "XLF_i < XLF_j for a dominating i and dominated j",
            "magnetic_tie": "XLF_i == XLF_j; recorded separately, not a reversal",
            "componentwise_strict": "i > j in all four fraction concentrations",
            "numerical_comparison": "Direct comparisons of the stored floating-point values; no tolerance or rounding",
            "MDR_denominator": "All dominance pairs, including magnetic ties",
        },
        "dominance_results": summary_rows,
        "floating_point_tolerance_sensitivity": tolerance_sensitivity,
        "inferential_limitation": "Dominance pairs share sites and are statistically dependent; the pair-level reversal fractions are descriptive, not independent Bernoulli trials. No binomial confidence interval is justified.",
        "all_nine_reported_counts_match": all(row["matches_expected"] for row in summary_rows),
        "sample1": sample1,
        "XLF_median": float(np.median(xlf)),
        "top_eight": {
            "XLF_ids_descending": ids[top_xlf].tolist(),
            "Pb_F1_ids_descending": ids[top_pb_f1].tolist(),
            "intersection_ids": [int(i) for i in intersection],
            "overlap_count": len(intersection),
            "Pb_F1_top_eight_missed_by_XLF": sorted(set(ids[top_pb_f1]).difference(ids[top_xlf])),
            "XLF_eighth": float(sorted(xlf, reverse=True)[7]),
            "XLF_ninth": float(sorted(xlf, reverse=True)[8]),
            "Pb_F1_eighth": float(sorted(pb_f1, reverse=True)[7]),
            "Pb_F1_ninth": float(sorted(pb_f1, reverse=True)[8]),
            "interpretation": "Illustrative ranking budget of 8/32; not a health, regulatory, or risk threshold",
        },
        "spearman_XLF_vs_total_Pb_all": correlation(xlf, pb_total),
        "spearman_XLF_vs_total_Pb_omit_sample1": correlation(xlf[1:], pb_total[1:]),
        "Zn_comparison": {
            "sample11_total_AX14": float(totals[10, zn_index]),
            "sample11_F1_J14": float(fractions[10, zn_index, 0]),
            "sample12_total_AX15": float(totals[11, zn_index]),
            "sample12_F1_J15": float(fractions[11, zn_index, 0]),
            "sample12_to11_F1_ratio": float(fractions[11, zn_index, 0] / fractions[10, zn_index, 0]),
        },
        "theorem_audit": {
            "weak_dominance_simplex": "If delta >= 0 componentwise with some delta > 0, then w.dot(delta) >= 0 for every w >= 0 with sum(w)=1. Equality occurs iff the support of w is entirely among zero-delta coordinates.",
            "strict_all_simplex": "w.dot(delta) > 0 for every closed-simplex weight vector iff every delta coordinate > 0.",
            "strict_interior_weights": "Weak dominance with at least one strict coordinate gives w.dot(delta) > 0 for every strictly positive weight vector summing to one.",
            "counterexample": {"delta": [1, 0, 0, 0], "w": [0, 1, 0, 0], "weighted_difference": 0},
            "MDR_effect": "A strictly reversed magnetic score remains a violation of weak Pareto order. Under weak-only dominance it need not reverse a strictly ordered weighted score for every closed-simplex weight vector, since some weights produce a true weighted tie. Ties in magnetic score must be separated from strict reversals.",
            "provenance": "The workbook does not establish physical perturbation weights, measured release responses, provenance of transformations, or external validation.",
        },
    }
    # Convert NumPy integer sets retained above to plain Python integers for JSON.
    details["top_eight"]["Pb_F1_top_eight_missed_by_XLF"] = [
        int(i) for i in details["top_eight"]["Pb_F1_top_eight_missed_by_XLF"]]
    workbook.close()
    (OUT / "audit_summary.json").write_text(json.dumps(details, indent=2, ensure_ascii=False), encoding="utf-8")
    dump_csv(OUT / "dominance_summary.csv", summary_rows)
    dump_csv(OUT / "dominance_pairs.csv", pair_rows)
    dump_csv(OUT / "tolerance_sensitivity.csv", tolerance_sensitivity)
    print(json.dumps(details, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
