"""Enumerate magnetic/proximity boundary choices for four targets and every budget.

Reads the original workbook and existing pilot outputs without modifying them.
Uses existing target definitions; no statistical or predictive model is fitted.
Run with the bundled Python, optionally --workbook PATH and --output-dir PATH.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import itertools
import json
import math
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import openpyxl

EXPECTED_SHA256 = "1f403f49d399643455cffaad47d4445dee8acfba40ca14b6452283bd9e7e6b8b"
ELEMENTS = ("Cd", "Co", "Cr", "Cu", "Fe", "Mn", "Ni", "Pb", "Zn")
TARGETS = ("total", "F1", "F1_plus_F2_plus_F3", "minimum_four_fraction")
TOLERANCE = 1e-12
BASE = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def boundary_choices(values: np.ndarray, k: int) -> list[tuple[int, ...]]:
    """All k-sets minimizing the ordered score; larger XLF uses values=-XLF."""
    order = sorted(range(len(values)), key=lambda i: (float(values[i]), i))
    cutoff = float(values[order[k - 1]])
    fixed = tuple(i for i, value in enumerate(values) if value < cutoff)
    tied = tuple(i for i, value in enumerate(values) if value == cutoff)
    needed = k - len(fixed)
    choices = [
        tuple(sorted(fixed + extra))
        for extra in itertools.combinations(tied, needed)
    ]
    assert len(choices) == math.comb(len(tied), needed)
    assert len(set(choices)) == len(choices)
    assert all(len(choice) == k and len(set(choice)) == k for choice in choices)
    return choices


def classify(magnetic: np.ndarray, nearest: np.ndarray) -> str:
    if float(nearest.min()) > float(magnetic.max()) + TOLERANCE:
        return "nearest_all_ties_better"
    if float(magnetic.min()) > float(nearest.max()) + TOLERANCE:
        return "magnetic_all_ties_better"
    return "overlap_or_equal"


def plot_cu(rows: list[dict], output: Path) -> None:
    titles = {
        "total": "Total concentration",
        "F1": "F1 concentration",
        "F1_plus_F2_plus_F3": "Nonresidual concentration: F1 + F2 + F3",
        "minimum_four_fraction": "Minimum retention across fraction priorities",
    }
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.5), sharex=True, sharey=True)
    colors = {"magnetic": "#157e98", "nearest": "#b2671b"}
    for ax, target in zip(axes.flat, TARGETS):
        selected = sorted(
            [r for r in rows if r["element"] == "Cu" and r["target"] == target],
            key=lambda r: r["k"],
        )
        budget = np.asarray([r["k"] for r in selected])
        for rule in ("magnetic", "nearest"):
            lo = 100 * np.asarray([r[rule + "_min"] for r in selected])
            hi = 100 * np.asarray([r[rule + "_max"] for r in selected])
            ax.fill_between(budget, lo, hi, color=colors[rule], alpha=0.20)
            ax.plot(budget, lo, color=colors[rule], linewidth=1.5)
            ax.plot(budget, hi, color=colors[rule], linewidth=1.0)
        ax.axvline(8, color="#707070", linestyle=":", linewidth=0.9)
        ax.set_title(titles[target], fontsize=11, pad=9)
        ax.set_xlim(1, 31)
        ax.set_ylim(0, 102)
        ax.set_xticks([1, 5, 8, 10, 15, 20, 25, 31])
        ax.grid(alpha=0.17)
    for ax in axes[:, 0]:
        ax.set_ylabel("Retention (%)")
    for ax in axes[1, :]:
        ax.set_xlabel("Number of selected records, k")
    fig.suptitle("Cu: the preferred rule depends on the chemical target", fontsize=15, y=0.98)
    fig.legend(
        handles=[
            Line2D([0], [0], color=colors["magnetic"], label="Highest stored XLF"),
            Line2D([0], [0], color=colors["nearest"], label="Nearest recorded distance"),
        ],
        loc="upper center", bbox_to_anchor=(0.5, 0.948), ncol=2, frameon=False,
    )
    fig.text(
        0.08, 0.023,
        "Bands span all cutoff-tie choices; they are not confidence intervals. "
        "The dotted line marks k = 8. Chemical oracles use the same budget.",
        fontsize=8.5,
    )
    fig.tight_layout(rect=[0.03, 0.05, 0.99, 0.90])
    fig.savefig(output / "Cu_target_budget_profiles.png", dpi=200)
    fig.savefig(output / "Cu_target_budget_profiles.svg")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workbook", "--source", dest="workbook", type=Path,
        default=Path(__file__).resolve().parents[1] / "source/Iron Factory.xlsx",
    )
    parser.add_argument("--output-dir", type=Path, default=BASE)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)

    prior_profiles = BASE / "proximity_vs_magnetic_all_budgets.csv"
    prior_k8 = BASE / "magnetic_vs_nearest_k8.csv"
    protected = (args.workbook, prior_profiles, prior_k8)
    hashes_before = {str(p.resolve()): sha256(p) for p in protected}
    assert sha256(args.workbook) == EXPECTED_SHA256, "Unexpected source workbook checksum"

    book = openpyxl.load_workbook(args.workbook, data_only=True, read_only=True)
    sheet = book["All rsults"]
    source_rows = list(sheet.iter_rows(min_row=4, max_row=35, values_only=True))
    book.close()
    fractions = np.asarray(
        [[[r[start + j] for start in (1, 11, 21, 31)] for j in range(9)]
         for r in source_rows],
        dtype=float,
    )
    xlf = np.asarray([r[58] for r in source_rows], dtype=float)
    distance = np.asarray([r[52] for r in source_rows], dtype=float)
    assert fractions.shape == (32, 9, 4)
    assert np.isfinite(fractions).all() and (fractions > 0).all()
    assert np.isfinite(xlf).all() and np.isfinite(distance).all()
    assert (distance >= 0).all()

    rows = []
    choice_counts = []
    denominator_min = math.inf
    for k in range(1, 32):
        magnetic = boundary_choices(-xlf, k)
        nearest = boundary_choices(distance, k)
        choice_counts.append({
            "k": k, "magnetic_choices": len(magnetic), "nearest_choices": len(nearest)
        })
        for j, element in enumerate(ELEMENTS):
            part = fractions[:, j, :]
            endpoint_oracles = np.asarray(
                [sum(heapq.nlargest(k, map(float, part[:, f]))) for f in range(4)]
            )
            denominator_min = min(denominator_min, float(endpoint_oracles.min()))
            fixed_targets = {
                "total": part.sum(axis=1),
                "F1": part[:, 0],
                "F1_plus_F2_plus_F3": part[:, :3].sum(axis=1),
            }
            for target in TARGETS:
                if target == "minimum_four_fraction":
                    def scores(choices):
                        return np.asarray([
                            min(
                                sum(float(part[i, f]) for i in selected)
                                / endpoint_oracles[f]
                                for f in range(4)
                            )
                            for selected in choices
                        ])
                else:
                    chemical = fixed_targets[target]
                    oracle = sum(heapq.nlargest(k, map(float, chemical)))
                    denominator_min = min(denominator_min, float(oracle))

                    def scores(choices):
                        return np.asarray([
                            sum(float(chemical[i]) for i in selected) / oracle
                            for selected in choices
                        ])

                mr = scores(magnetic)
                nr = scores(nearest)
                assert np.isfinite(mr).all() and np.isfinite(nr).all()
                assert mr.min() > 0 and nr.min() > 0
                assert mr.max() <= 1 + TOLERANCE and nr.max() <= 1 + TOLERANCE
                rows.append({
                    "element": element, "target": target, "k": k,
                    "magnetic_choices": len(magnetic), "nearest_choices": len(nearest),
                    "magnetic_min": float(mr.min()), "magnetic_max": float(mr.max()),
                    "nearest_min": float(nr.min()), "nearest_max": float(nr.max()),
                    "nearest_worst_minus_magnetic_best": float(nr.min() - mr.max()),
                    "magnetic_worst_minus_nearest_best": float(mr.min() - nr.max()),
                    "classification": classify(mr, nr),
                })
    assert len(rows) == 1116
    keys = {(r["element"], r["target"], r["k"]) for r in rows}
    assert len(keys) == 1116

    # Compare all 279 min-four rows with the original all-budget pilot.
    new_index = {(r["element"], r["target"], r["k"]): r for r in rows}
    prior = read_csv(prior_profiles)
    min4_errors = []
    assert len(prior) == 279
    for old in prior:
        new = new_index[(old["element"], "minimum_four_fraction", int(old["k"]))]
        for column in ("magnetic_min", "magnetic_max", "nearest_min", "nearest_max"):
            min4_errors.append(abs(new[column] - float(old[column])))
        assert new["classification"] == old["classification"]
        assert new["magnetic_choices"] == int(old["magnetic_choices"])
        assert new["nearest_choices"] == int(old["nearest_choices"])
    assert max(min4_errors) < TOLERANCE

    # Compare all 36 k=8 target rows with the independently audited first-pass output.
    first_pass = read_csv(prior_k8)
    k8_errors = []
    assert len(first_pass) == 36
    for old in first_pass:
        new = new_index[(old["element"], old["target"], 8)]
        assert new["magnetic_choices"] == 1
        for new_col, old_col in [
            ("magnetic_min", "magnetic_retention"),
            ("magnetic_max", "magnetic_retention"),
            ("nearest_min", "nearest_min_retention"),
            ("nearest_max", "nearest_max_retention"),
        ]:
            k8_errors.append(abs(new[new_col] - float(old[old_col])))
    assert max(k8_errors) < TOLERANCE

    summaries = []
    for element in ELEMENTS:
        for target in TARGETS:
            chosen = [r for r in rows if r["element"] == element and r["target"] == target]
            counts = Counter(r["classification"] for r in chosen)
            assert len(chosen) == 31 and sum(counts.values()) == 31
            summary = {"element": element, "target": target}
            for classification in (
                "magnetic_all_ties_better", "nearest_all_ties_better", "overlap_or_equal"
            ):
                summary[classification] = counts[classification]
                summary[classification + "_budgets"] = ",".join(
                    str(r["k"]) for r in chosen if r["classification"] == classification
                )
            summaries.append(summary)

    write_csv(output / "target_budget_profiles.csv", rows)
    write_csv(output / "target_budget_summary.csv", summaries)
    plot_cu(rows, output)

    hashes_after = {str(p.resolve()): sha256(p) for p in protected}
    assert hashes_after == hashes_before, "Source or prior output was changed"
    validation = {
        "source_sha256": EXPECTED_SHA256,
        "definition": "Same-budget oracle retention; all boundary choices for both rules",
        "elements": list(ELEMENTS), "targets": list(TARGETS),
        "budgets": list(range(1, 32)), "rows": len(rows), "summary_rows": len(summaries),
        "ratio_comparison_tolerance": TOLERANCE,
        "all_source_concentrations_finite_and_positive": True,
        "all_oracle_denominators_positive": denominator_min > 0,
        "minimum_oracle_denominator": denominator_min,
        "all_ratios_in_unit_interval_with_tolerance": True,
        "boundary_choices_checked_by_combinatorial_count": True,
        "boundary_choice_counts": choice_counts,
        "prior_min4_rows_checked": len(prior),
        "prior_min4_ratio_comparisons": len(min4_errors),
        "maximum_prior_min4_ratio_difference": max(min4_errors),
        "all_prior_min4_classifications_and_choice_counts_match": True,
        "prior_k8_rows_checked": len(first_pass),
        "prior_k8_ratio_comparisons": len(k8_errors),
        "maximum_prior_k8_ratio_difference": max(k8_errors),
        "protected_files_unchanged": hashes_before == hashes_after,
        "protected_file_hashes": hashes_after,
        "cu_summary": [r for r in summaries if r["element"] == "Cu"],
        "no_predictive_model_or_population_inference": True,
    }
    (output / "target_budget_validation.json").write_text(
        json.dumps(validation, indent=2), encoding="utf-8"
    )
    print(json.dumps({
        "rows": len(rows), "summary_rows": len(summaries),
        "max_min4_difference": max(min4_errors), "max_k8_difference": max(k8_errors),
        "protected_files_unchanged": True,
        "cu_summary": validation["cu_summary"],
    }, indent=2))


if __name__ == "__main__":
    main()
