"""Exact uniform eight-of-32 reference distribution for nine chemical scores.

The workbook is read-only. No optimization or inferential p-value is computed.
Temporary float64 subset scores are deleted after summary calculation.
"""
from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import platform
import tempfile
import time

import numpy as np
import openpyxl


DEFAULT_SOURCE = Path(__file__).resolve().parents[2] / "source/Iron Factory.xlsx"
OUT = Path(__file__).resolve().parent
ELEMENTS = ["Cd", "Co", "Cr", "Cu", "Fe", "Mn", "Ni", "Pb", "Zn"]
K = 8
CHUNK = 16384
TIE_ATOL = 1e-12


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,default=DEFAULT_SOURCE)
    args = parser.parse_args()
    args.source = args.source.expanduser().resolve()
    if not args.source.is_file():
        parser.error(f"Source workbook not found: {args.source}")
    return args


def batch_sums(c_flat,indices):
    # Every subset is accumulated in ascending original sample-ID order.
    sums = np.zeros((len(indices),c_flat.shape[1]),dtype=np.float64)
    for position in range(indices.shape[1]):
        sums += c_flat[indices[:,position]]
    return sums


def summarize_scores(values,magnetic_score):
    count = len(values)
    average = float(np.mean(values,dtype=np.float64))
    standard_deviation = float(np.std(values,ddof=0,dtype=np.float64))
    minimum,maximum = float(values.min()),float(values.max())
    below = int(np.count_nonzero(values<magnetic_score))
    equal = int(np.count_nonzero(values==magnetic_score))
    above = int(np.count_nonzero(values>magnetic_score))
    below_tol = int(np.count_nonzero(values<magnetic_score-TIE_ATOL))
    above_tol = int(np.count_nonzero(values>magnetic_score+TIE_ATOL))
    tied_tol = count-below_tol-above_tol
    assert below+equal+above==count and below_tol+tied_tol+above_tol==count
    # Values is an explicit copy, so partitioning cannot modify stored scores.
    q05,q50,q95 = np.quantile(values,[.05,.5,.95],method="linear",overwrite_input=True)
    return {"subset_count":count,"mean":average,"SD_population":standard_deviation,
            "minimum":minimum,"quantile_05":float(q05),"median":float(q50),
            "quantile_95":float(q95),"maximum":maximum,"magnetic_score":float(magnetic_score),
            "count_below_magnetic":below,"count_equal_magnetic":equal,
            "count_above_magnetic":above,"count_at_or_below_magnetic":below+equal,
            "fraction_below_magnetic":below/count,"fraction_equal_magnetic":equal/count,
            "fraction_above_magnetic":above/count,"fraction_at_or_below_magnetic":(below+equal)/count,
            "tie_absolute_tolerance":TIE_ATOL,
            "count_below_magnetic_outside_tolerance":below_tol,"count_tied_within_tolerance":tied_tol,
            "count_above_magnetic_outside_tolerance":above_tol,
            "fraction_at_or_below_magnetic_plus_tolerance":(below_tol+tied_tol)/count}


def tiny_exhaustive_check(c_all):
    # Six original sites, Pb F1/F3, budget two: plain nested loops independently
    # check the vectorized scorer, moments, quantiles, and comparator counts.
    tiny = c_all[:6,ELEMENTS.index("Pb"),:][:,[0,2]]
    oracle = np.sort(tiny,axis=0)[-2:,:].sum(axis=0)
    combinations = np.array(list(itertools.combinations(range(6),2)),dtype=np.int8)
    vector_scores = np.min(batch_sums(tiny,combinations)/oracle,axis=1)
    direct = []
    for first in range(5):
        for second in range(first+1,6):
            direct.append(min((float(tiny[first,f])+float(tiny[second,f]))/float(oracle[f]) for f in range(2)))
    assert np.allclose(vector_scores,direct,rtol=0,atol=1e-14)
    direct_sorted = sorted(direct)
    mean = sum(direct)/len(direct)
    sd = math.sqrt(sum((value-mean)**2 for value in direct)/len(direct))
    quantiles = []
    for probability in [.05,.5,.95]:
        position = (len(direct)-1)*probability
        lower,upper = math.floor(position),math.ceil(position)
        quantiles.append(direct_sorted[lower]+(position-lower)*(direct_sorted[upper]-direct_sorted[lower]))
    threshold = direct[3]
    reported = summarize_scores(vector_scores.copy(),threshold)
    checks = {"score_vectors_match":bool(np.allclose(vector_scores,direct,rtol=0,atol=1e-14)),
              "mean_matches":bool(np.isclose(mean,reported["mean"],rtol=0,atol=1e-14)),
              "population_SD_matches":bool(np.isclose(sd,reported["SD_population"],rtol=0,atol=1e-14)),
              "linear_quantiles_match":bool(np.allclose(quantiles,[reported["quantile_05"],reported["median"],reported["quantile_95"]],rtol=0,atol=1e-14)),
              "at_or_below_count_matches":sum(value<=threshold for value in direct)==reported["count_at_or_below_magnetic"]}
    assert all(checks.values())
    return {"data":"Original samples1–6, Pb F1/F3, k=2","subset_count":15,"checks":checks,
            "mean":mean,"SD_population":sd,"quantiles_05_50_95":quantiles}


def main(source):
    started = time.perf_counter()
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    workbook = openpyxl.load_workbook(source,read_only=True,data_only=True)
    rows = list(workbook["All rsults"].iter_rows(min_row=4,max_row=35,max_col=60,values_only=True))
    workbook.close()
    ids = np.array([int(row[0]) for row in rows])
    assert ids.tolist()==list(range(1,33))
    xlf = np.array([float(row[58]) for row in rows])
    c = np.array([[[float(row[start+j-1]) for start in (2,12,22,32)] for j in range(9)] for row in rows])
    assert np.all(np.isfinite(c)) and np.all(c>=0)
    c_flat = c.reshape(32,36)
    oracle = np.sort(c,axis=0)[-K:,:].sum(axis=0)
    assert np.all(oracle>0)
    magnetic_order = sorted(range(32),key=lambda i:(-xlf[i],ids[i]))
    magnetic_ids = ids[magnetic_order[:K]].tolist()
    canonical_magnetic = np.array([sorted(magnetic_order[:K])],dtype=np.int8)
    magnetic_sums = batch_sums(c_flat,canonical_magnetic).reshape(9,4)
    magnetic_scores = (magnetic_sums/oracle).min(axis=1)
    n_subsets = math.comb(32,K)
    assert n_subsets==10518300
    inclusion_expected = math.comb(31,K-1)
    tiny_check = tiny_exhaustive_check(c)
    OUT.mkdir(parents=True,exist_ok=True)

    descriptor,scratch_name = tempfile.mkstemp(prefix="iron_exact_random_reference_",suffix=".bin")
    os.close(descriptor)
    scratch_path = Path(scratch_name)
    scratch_size = 9*n_subsets*np.dtype(np.float64).itemsize
    score_store = None
    summaries,conditional_pb = [],{}
    inclusion_counts = np.zeros(32,dtype=np.int64)
    sum_of_selected_fraction_sums = np.zeros(36,dtype=np.float64)
    running_score_sum = np.zeros(9,dtype=np.float64)
    count = 0
    combinations = itertools.combinations(range(32),K)
    first_combination = last_combination = None
    benchmark = None
    try:
        score_store = np.memmap(scratch_path,dtype=np.float64,mode="w+",shape=(9,n_subsets))
        enumeration_started = time.perf_counter()
        last_progress = enumeration_started
        while count<n_subsets:
            batch_count = min(CHUNK,n_subsets-count)
            indices = np.fromiter(itertools.chain.from_iterable(itertools.islice(combinations,batch_count)),
                                  dtype=np.int8,count=batch_count*K).reshape(batch_count,K)
            if first_combination is None:
                first_combination = (indices[0].astype(int)+1).tolist()
            last_combination = (indices[-1].astype(int)+1).tolist()
            sums = batch_sums(c_flat,indices)
            scores = (sums.reshape(batch_count,9,4)/oracle).min(axis=2)
            assert np.all(np.isfinite(scores)) and np.all(scores>=0) and np.all(scores<=1+1e-12)
            score_store[:,count:count+batch_count] = scores.T
            sum_of_selected_fraction_sums += sums.sum(axis=0)
            running_score_sum += scores.sum(axis=0)
            inclusion_counts += np.bincount(indices.ravel(),minlength=32)
            count += batch_count
            now = time.perf_counter()
            if benchmark is None and count>=262144:
                benchmark = {"subsets":count,"seconds_including_temporary_storage":now-enumeration_started,
                             "projected_enumeration_seconds":(now-enumeration_started)*n_subsets/count}
                print(json.dumps({"event":"benchmark",**benchmark}),flush=True)
            if now-last_progress>=20:
                print(json.dumps({"event":"enumeration_progress","subsets_completed":count,"total":n_subsets,"seconds":now-enumeration_started}),flush=True)
                last_progress = now
        assert next(combinations,None) is None
        score_store.flush()
        enumeration_seconds = time.perf_counter()-enumeration_started
        assert count==n_subsets and np.all(inclusion_counts==inclusion_expected)
        assert first_combination==list(range(1,9)) and last_combination==list(range(25,33))
        print(json.dumps({"event":"enumeration_complete","subsets":count,"seconds":enumeration_seconds}),flush=True)
        for j,element in enumerate(ELEMENTS):
            column = np.array(score_store[j,:],dtype=np.float64,copy=True)
            summary = summarize_scores(column,magnetic_scores[j])
            del column
            assert np.isclose(summary["mean"],running_score_sum[j]/n_subsets,rtol=1e-11,atol=1e-12)
            assert summary["count_equal_magnetic"]>=1
            summaries.append({"element":element,**summary})
            if element=="Pb":
                # Lexicographic combinations containing original sample1 occupy
                # the first C(31,7) entries. The full32 oracles stay fixed.
                for label,left,right in [("sample1_included",0,inclusion_expected),
                                         ("sample1_excluded",inclusion_expected,n_subsets)]:
                    conditional_column = np.array(score_store[j,left:right],dtype=np.float64,copy=True)
                    conditional_pb[label] = summarize_scores(conditional_column,magnetic_scores[j])
                    del conditional_column
                assert conditional_pb["sample1_included"]["subset_count"]==inclusion_expected
                assert conditional_pb["sample1_excluded"]["subset_count"]==n_subsets-inclusion_expected
            print(json.dumps({"event":"metal_summarized","element":element,"mean":summary["mean"],
                              "median":summary["median"],"fraction_at_or_below_magnetic":summary["fraction_at_or_below_magnetic"],
                              "magnetic_score":summary["magnetic_score"]}),flush=True)
    finally:
        if score_store is not None:
            score_store.flush()
            del score_store
        gc.collect()
        # This is the single owned temporary file returned by mkstemp; no
        # recursive cleanup or deletion of another directory is performed.
        scratch_path.unlink(missing_ok=True)

    observed_means = sum_of_selected_fraction_sums.reshape(9,4)/n_subsets
    expected_means = (K/32)*c.sum(axis=0)
    assert np.allclose(observed_means,expected_means,rtol=1e-10,atol=1e-8)
    mean_checks = [{"element":element,"fraction":f"F{f+1}",
                    "enumerated_mean_selected_sum":float(observed_means[j,f]),
                    "analytical_mean_selected_sum":float(expected_means[j,f]),
                    "absolute_difference":float(abs(observed_means[j,f]-expected_means[j,f]))}
                   for j,element in enumerate(ELEMENTS) for f in range(4)]
    reference_path = OUT.parent/"shortlist_audit"/"shortlist_summary.json"
    reference_checks = {"path":str(reference_path),"available":reference_path.is_file()}
    if reference_path.is_file():
        prior = json.loads(reference_path.read_text(encoding="utf-8"))
        reference_checks["source_sha_matches"] = prior["source_sha256"]==source_sha
        if reference_checks["source_sha_matches"]:
            checks = []
            for summary in summaries:
                element = summary["element"]
                retrospective = prior["retrospective_maximin_k8"][element]
                check = {"element":element,"enumerated_maximum":summary["maximum"],
                         "prior_MILP_status":retrospective["status"],
                         "prior_retrospective_retention":retrospective["direct_worst_case_retention"],
                         "prior_dual_upper_bound":retrospective["retention_upper_bound_from_dual"],
                         "magnetic_matches":bool(np.isclose(summary["magnetic_score"],prior["magnetic_k8"][element]["worst_case_retention"],rtol=0,atol=1e-12)),
                         "maximum_matches_prior_optimum":bool(np.isclose(summary["maximum"],retrospective["direct_worst_case_retention"],rtol=0,atol=1e-10)),
                         "maximum_within_prior_dual_bound":summary["maximum"]<=retrospective["retention_upper_bound_from_dual"]+1e-10}
                assert check["magnetic_matches"] and check["maximum_matches_prior_optimum"] and check["maximum_within_prior_dual_bound"]
                checks.append(check)
            reference_checks["metals"] = checks
    assert hashlib.sha256(source.read_bytes()).hexdigest()==source_sha
    validation = {"source_path":str(source),"source_sha256":source_sha,"source_unchanged_at_finish":True,
                  "sheet":"All rsults","sample_range":"A4:A35","stored_XLF_range":"BG4:BG35",
                  "software":{"python":platform.python_version(),"numpy":np.__version__,"openpyxl":openpyxl.__version__},
                  "method":"Exact enumeration, not Monte Carlo","n_records":32,"budget":8,"n_subsets":n_subsets,
                  "denominator_for_unconditional_proportions":n_subsets,
                  "same_subsets_used_for_all_metals":True,"magnetic_selected_ids_descending_XLF":magnetic_ids,
                  "accumulation_order":"All subset sums, including the magnetic comparator, accumulated in ascending original sample-ID order",
                  "score_definition":"min over F1–F4 of selected concentration sum / full32-population top8 chemical oracle sum",
                  "oracle_scope":"Full32-population denominators are fixed for every subset and both Pb conditional references",
                  "SD_definition":"Descriptive finite-distribution population SD, denominator N, ddof0",
                  "quantile_definition":"NumPy linear/type7 quantiles: h=(N-1)*p for zero-based sorted scores; linear interpolation between floor(h) and ceil(h)",
                  "comparison_definition":"Primary below/equal/above counts compare canonical float64 scores directly. Additional counts group values within absolute1e-12 of the magnetic score as numerical ties. Both partitions sum exactly to N.",
                  "analytical_checks":{"enumerated_combination_count":count,"expected_combination_count":n_subsets,
                                       "first_combination":first_combination,"last_combination":last_combination,
                                       "each_record_expected_inclusion_count":inclusion_expected,
                                       "each_record_observed_inclusion_counts":inclusion_counts.tolist(),
                                       "fraction_specific_mean_selected_sum_formula":"E[A_f]=(8/32)*sum_all32(c_if)",
                                       "fraction_specific_mean_checks":mean_checks,
                                       "all_fraction_means_match":True,"all_scores_finite_and_between0_and1":True},
                  "tiny_direct_exhaustive_check":tiny_check,"prior_retrospective_bound_checks":reference_checks,
                  "unconditional_summaries":summaries,"conditional_Pb":conditional_pb,
                  "conditional_Pb_explanation":"Uniform subsets conditional on inclusion/exclusion of original sample1; full32 oracle denominators remain fixed. This differs from the R5 omission analysis, which recomputes oracles after deletion.",
                  "runtime":{"benchmark":benchmark,"enumeration_seconds":enumeration_seconds,
                             "total_seconds":time.perf_counter()-started,"chunk_size":CHUNK},
                  "temporary_score_storage":{"bytes":scratch_size,"dtype":"float64","temporary_file_deleted":not scratch_path.exists(),"raw_subsets_or_scores_delivered":False},
                  "interpretation":"A finite random-selection reference conditional on the supplied Excel data. Fractions at/below the magnetic score are descriptive proportions of feasible subsets, not inferential p-values, independent validation, or population error probabilities."}
    with (OUT/"random_reference_summary.csv").open("w",newline="",encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream,fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    (OUT/"random_reference_validation.json").write_text(json.dumps(validation,indent=2,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    note = ["# Exact uniform eight-record reference", "",
            f"All {n_subsets:,} subsets of eight among the32 supplied records were evaluated, using the same subsets for all nine metals. The score is the minimum over F1–F4 of the selected concentration sum divided by that fraction's full32-population top-eight oracle. The source workbook was read-only; its SHA-256 is `{source_sha}`.","",
            "| Metal | Magnetic score | Uniform mean | Population SD | 5th percentile | Median | 95th percentile | Exact count at/below magnetic | Fraction at/below magnetic |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in summaries:
        note.append(f"| {row['element']} | {row['magnetic_score']:.4%} | {row['mean']:.4%} | {row['SD_population']:.4%} | {row['quantile_05']:.4%} | {row['median']:.4%} | {row['quantile_95']:.4%} | {row['count_at_or_below_magnetic']:,} / {n_subsets:,} | {row['fraction_at_or_below_magnetic']:.6%} |")
    note += ["", "Every unconditional proportion uses the exact denominator10,518,300. The CSV separately gives strict-below, exact-equal and strict-above counts, plus a second exhaustive partition using an absolute1e-12 numerical-tie tolerance. Comparisons use canonical ascending-ID accumulation for both random subsets and the magnetic comparator.","",
             "The SD is the population SD of this finite score distribution (ddof0). Quantiles use linear/type7 interpolation at zero-based position(N-1)*p. These definitions summarize the complete reference distribution rather than simulation estimates.","",
             "## Pb conditional reference", ""]
    for label,row in conditional_pb.items():
        note.append(f"- {label}: {row['subset_count']:,} subsets; mean {row['mean']:.4%}, median {row['median']:.4%}, 5th–95th percentiles {row['quantile_05']:.4%}–{row['quantile_95']:.4%}; fraction at/below magnetic {row['fraction_at_or_below_magnetic']:.6%}.")
    note += ["", "Both conditional Pb references retain the full32 chemical oracle. They condition whether a candidate subset includes sample1; they do not remove sample1 from the underlying oracle population and should not be confused with the R5 deletion exercise.","",
             "Validation counted every combination, confirmed identical record inclusion counts C(31,7), and checked each fraction's enumerated mean selected sum against (8/32) times its full-file concentration sum. A separate six-record/two-fraction direct enumeration checked scores, moments, quantiles and comparison counts. All nine enumerated maxima agree with the previous retrospective optimum and dual bound within numerical tolerance. Temporary raw-score storage was deleted.","",
             "This is a uniform-selection reference conditional on the supplied Excel values. Its comparison proportions are not inferential p-values, independent validation, or population error probabilities. Concentration-sum scores represent neither landscape metal inventory nor measured health outcomes. No claim of external generalization is made.","",
             "Files: random_reference.py, random_reference_summary.csv and random_reference_validation.json. Reproduce with `python random_reference.py --source \"path/to/Iron Factory.xlsx\"`. The default path retains the original Windows source. Dependency versions, exact comparison counts, analytical checks, runtime and source identity are recorded in JSON."]
    (OUT/"random_reference_note.md").write_text("\n".join(note)+"\n",encoding="utf-8")
    print(json.dumps({"event":"complete","subsets":n_subsets,"total_seconds":validation["runtime"]["total_seconds"],
                      "temporary_file_deleted":validation["temporary_score_storage"]["temporary_file_deleted"],
                      "source_sha256":source_sha,"conditional_Pb":conditional_pb}),flush=True)


if __name__=="__main__":
    main(arguments().source)
