# Iron Factory copper screening: data and reproducibility code

**Ghassan Malkawi · Version 11.0.0**

Repository: [iron-factory-copper-screening](https://github.com/shaikhamalkawi-ux/iron-factory-copper-screening). Archive DOI: [10.5281/zenodo.23019081](https://doi.org/10.5281/zenodo.23019081). This identifier was reserved during packaging; the linked Zenodo landing page is authoritative for publication status.

This companion data/code release contains a 32-record workbook and reproducible retrospective comparisons of two prioritization rules: highest stored XLF and nearest recorded distance. The chemical targets are four-fraction total concentration, F1 concentration, and combined F1+F2+F3 concentration. The full article manuscript is not included; `baseline/table2.tex` contains only the 81 printed numerical entries used by the computational check.

At eight selected records, the Cu comparison favors highest XLF for total and F1 concentrations and nearest recorded distance for F1+F2+F3. All permitted choices at tied cutoffs are enumerated. These results describe this finite candidate table; they do not establish field performance, causal source attribution, bioavailability, or a confirmed mineral carrier. Extraction fractions are operational labels, and the workbook does not establish the underlying laboratory protocol.

## Data and files

- `source/Iron Factory.xlsx`: a metadata-sanitized public derivative, 32,194 bytes. SHA-256: `1f403f49d399643455cffaad47d4445dee8acfba40ca14b6452283bd9e7e6b8b`.
- `verification/`: direct-workbook Cu checks, coordinate checks, numerical case tables and result summaries.
- `fresh_read_20260927/`: field dictionary, cell inventory, extracted records, complete target/budget comparisons and associated calculation scripts.
- `legacy_analysis/`: supplementary ordering, optimization, influence and exhaustive subset calculations.
- `figure_code/` and `figures/`: portable plotting entry point and preserved figure assets.
- `baseline/table2.tex`: table-only expected-value fixture; no TeX installation is required.
- `reproduction_verification/`: execution results and changes made for this portable public release.

Sheet `All rsults` contains records in rows 4–35, IDs 1–32. Fraction blocks `B:J`, `L:T`, `V:AD`, and `AF:AN` use the element order Cd, Co, Cr, Cu, Fe, Mn, Ni, Pb, Zn. Recorded distance is column BA; stored XLF and XHF are BG and BH. The field dictionary retains the workbook's literal labels and units.

The original private workbook has SHA-256 `aa6681c479d8855819fc68f2ebc63271668adff925eac8aeb49d2b5af55d43ef`. The public derivative removes document-author/editor metadata, document creation/modification timestamps, a stored absolute path and printer metadata, with valid corresponding package relationships. It preserves every worksheet, cell value, formula, cached value and style; the verification record describes these checks. The original binary is not distributed here.

The file lacks sufficient documentation of sampling design, material/depth/date, extraction reagents, laboratory quality controls and magnetic calibration. Reported coordinate checks are conditional internal comparisons and do not identify a factory boundary or emission origin. Concentration sums are record-prioritization scores, not landscape inventories or health-risk estimates. The source cell values, including documented internal inconsistencies, have not been corrected.

## Reproduce the calculations

Use a writable repository copy and run commands from its root. The tested environment is Windows 11 AMD64 with Python 3.12.14 and the package versions pinned in `requirements.txt`. Other environments have not been exhaustively tested. SciPy must provide `scipy.optimize.milp`.

```text
python -m pip install -r requirements.txt
python verification/verify_new_cu.py --source "source/Iron Factory.xlsx" --baseline "baseline/table2.tex" --output "recomputed/verification"
python verification/coordinate_checks.py --source "source/Iron Factory.xlsx" --output "recomputed/verification"
python figure_code/build_current_figures.py --grid "verification/ordinary_target_grid.csv" --target-profiles "fresh_read_20260927/target_budget_profiles.csv" --output "recomputed/figures"
```

The principal verifier checks the workbook hash, all 837 ordinary target/budget cases, 960 single-omission cases, 496 pair-omission cases, candidate-scope checks, fraction attribution and the 81 printed baseline entries. Historical names `r9_table2_replay.csv` and `printed_R9_table2_values_matching` identify that same comparison fixture. The plotting command initially uses recorded outputs; substitute `recomputed/verification/ordinary_target_grid.csv` for newly generated Cu inputs.

The complete fresh-read sequence is:

```text
python fresh_read_20260927/fresh_inventory.py --source "source/Iron Factory.xlsx" --output-dir "fresh_read_20260927"
python fresh_read_20260927/fresh_diagnostics.py --source "source/Iron Factory.xlsx"
python fresh_read_20260927/proximity_budget_sensitivity.py --source "source/Iron Factory.xlsx"
python fresh_read_20260927/verify_nearest_comparison.py --source "source/Iron Factory.xlsx" --comparison-csv "fresh_read_20260927/magnetic_vs_nearest_k8.csv"
python fresh_read_20260927/target_budget_extension.py --source "source/Iron Factory.xlsx" --output-dir "fresh_read_20260927"
python fresh_read_20260927/fresh_figures.py --directory "fresh_read_20260927"
```

These commands replace generated files beside their scripts. Preserve the directory layout and execute them in order: the target extension checks earlier generated comparison tables. Additional diagnostic figures and notes are generated locally. The classification map can then be rebuilt from the regenerated target/budget profiles.

The supplementary sequence is:

```text
python legacy_analysis/run_reproduce_R7.py --source "source/Iron Factory.xlsx"
python legacy_analysis/shortlist_audit/build_r3_figures.py
python legacy_analysis/influence_audit/build_influence_figure.py
```

The wrapper runs ordering checks, fixed-budget optimization, single-record influence and exact enumeration of all 10,518,300 eight-record subsets. The enumeration uses about 0.76 GB of temporary score storage, which it deletes after use. Runtime depends on the computer. This finite-table reference is not a population p-value, estimate of field-sampling uncertainty or external validation.

The primary verifier also produces optional lambda-weighting and hypothetical perturbation outputs. These describe preference/error-bound scenarios; they are not measured analytical uncertainty or additional empirical measurements. The expected-value Table 3 JSON is separately checked rather than generated by the principal command.

## Reproducibility and provenance

Public-release changes are confined to portable default input paths and the public derivative's expected hash, a table-only baseline, documentation/licensing and removal of machine-specific or editorial metadata. All 12 documented commands passed against the public derivative on 28 September 2026, including the full 10,518,300-subset enumeration. All 81 printed baseline values matched. Of 39 CSV files, 38 reproduced byte for byte; `source_numeric_cells.csv` changes only its source-hash column to identify the public derivative, with all 1,632 cell mappings and values unchanged. All seven archived figure assets were preserved, and the four regenerated PNGs matched them byte for byte.

Execution evidence identifies precisely what was tested. Generated JSON can record the reproducing computer's own absolute paths; the distributed metadata uses repository-relative paths. Metadata sanitation and successful calculation do not repair or validate missing empirical provenance.

Some historical validation files describe the scope of their original script run. Current release evidence records the complete executed sequence separately. No missing sampling or laboratory documentation is inferred from successful computation. Code and documentation were prepared with OpenAI Codex assistance; AI assistance for this release did not create or replace the supplied workbook values.

`MANIFEST.json` records the size and SHA-256 of every distributed file except itself and `SHA256SUMS`; `SHA256SUMS` additionally covers the manifest. Git's internal `.git/` directory, local replay logs and generated `recomputed/` outputs are excluded from the release archive. Check the distributed files before running calculations, because some documented commands intentionally replace generated outputs:

```python
import hashlib, json
from pathlib import Path
manifest = json.loads(Path("MANIFEST.json").read_text(encoding="utf-8"))
for name, entry in manifest["members"].items():
    data = Path(name).read_bytes()
    assert len(data) == entry["bytes"], name
    assert hashlib.sha256(data).hexdigest() == entry["sha256"], name
print("All distributed file hashes match.")
```

## Citation and licenses

Use `CITATION.cff` to cite Ghassan Malkawi and release 11.0.0.

Python source code is licensed under the [MIT License](LICENSE-MIT). The workbook, numerical results, figures, table baseline and narrative documentation are licensed under [CC BY 4.0](LICENSE-CC-BY-4.0.md). Dependency software retains its own licenses and is not bundled. Official license sources are the [Open Source Initiative](https://opensource.org/license/mit) and [Creative Commons](https://creativecommons.org/licenses/by/4.0/).
