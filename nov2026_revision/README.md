# Iron factory soil-metal screening — November 2026 public reproducibility update

**Manuscript:** *Chemical-Target Dependence of Low-Frequency Magnetic Susceptibility versus Factory-Center Distance in Soil-Metal Screening* (under major revision at *Environments*, manuscript `environments-4640261`; no acceptance is implied).

**Public source workbook:** [`source/Iron Factory.xlsx`](../source/Iron%20Factory.xlsx) in the repository root. The published input is a metadata-sanitized derivative of the historical 32-record workbook, SHA-256 `1f403f49d399643455cffaad47d4445dee8acfba40ca14b6452283bd9e7e6b8b`. This file was already public in the repository and is retained unchanged. Do not replace it with the original private workbook.

The November 2026 update adds **replayable numeric and four-figure source packages** corresponding to the author-review manuscript revisions through V67. Its analytical content is unchanged from the locked scientific baseline. The work compares higher recorded XLF and shorter recorded distance over the same 32 records, nine elements, three operational chemical targets and budgets 1–31. The primary test collection contains 837 element × target × budget comparisons. This is retrospective deterministic source-to-output reproducibility, not independent soil resampling, instrument calibration, source-attribution validation or field prediction.

## Available files

- `Iron_Nov2026_S2_Numerical_Replay.zip` — the exact public-safe supplementary data scripts, 32-row workbook, expected derived CSV/JSON files, MS2B dimensional audit and Figure 1/3 renderer from the manuscript's Supplementary Data S2. A redundant nested legacy archive has been omitted *without changing scientific inputs*. See this archive's own README for the preserved `Baseline_Reproduction_V39` directory names, retained for command compatibility.
- `Iron_Nov2026_Four_Figure_Source_Replay.zip` — complete executable source, frozen numeric input tables, reference PDF figures, and QA scripts for **Figures 1–3 and Supplementary Figure S1**, including 216 dpi pixel-parity verification and optional 600 dpi PNG previews.
- `reproduce_nov2026.py` — single-command numerical replay and optional full four-figure reconstruction after extracting both packages. Does not modify the repository's source workbook, the archived inputs, or the paper; all generated output is placed in a new user-selected directory.
- `references.bib` — scholarly references from the V63 manuscript, provided for bibliographic traceability, not a substitute for publisher verification.
- `SHA256SUMS.txt`, `RUN_SUMMARY.json` — package hashes and scope-specific test record.

## Reproduce

Using Python 3.13 (tested on Linux; portable Python commands on Windows/macOS should also work subject to the specified packages), install the pinned dependencies:

```sh
python -m pip install -r nov2026_revision/requirements.txt
```

Then, from the repository root:

```sh
python nov2026_revision/reproduce_nov2026.py --output reproduced-nov2026
```

For full four-figure reconstruction and pixel comparison as well:

```sh
python nov2026_revision/reproduce_nov2026.py --output reproduced-nov2026 --figures
```

The script validates the SHA-256 of the **existing repository public workbook** before running, checks the bundled copy against it, extracts the replay ZIP into a fresh temporary directory, then runs the numerical analyses and conditional instrument audit in their documented order. The figure option runs the Python rendering scripts directly without Bash or artifact_tool, then reports PDF-pixel parity. The `run_all.sh` script remains in the historical source archive for backward compatibility. Pixel equality is an illustration/render audit, not independent laboratory validation.

## Important interpretation and rights

- A common positive rescaling of stored XLF preserves rank order, but does **not** prove the original instrument model, 10 cm³ sample volume, absolute SI units or calibration.
- BCR fractions are operational extraction pools; their sum is *not* an independently measured total digestion. Four-fraction and non-residual chemical objectives need not favor the same screening rule.
- The thesis author has permitted public source access, and an unmodified 2015 thesis PDF is now provided separately at [`../thesis/`](../thesis/README.md), without any open reuse licence. The original private workbook, unpublished magnetic raw source, reviewer reports, private access links, credentials and field-personal metadata are **not published** here. No patent, copyright or redistribution right is claimed for unavailable private artifacts.
- **Zenodo DOI:** `10.5281/zenodo.23019081` names an **earlier published data/software deposit**. It has **not** been verified as containing this November 2026 release. Do not cite it as a version-specific DOI for this update. Use the cited source-commit permalink for this GitHub update until a new version-specific archival DOI is actually published.
- Code: MIT; public data and documentation: CC BY 4.0. External geographic outlines retain their own source terms (Natural Earth public domain).

**Release policy:** This public repository is not a manuscript preprint and does not contain the current author-review paper PDF; the original historical thesis is a separately attributed reading copy, not an openly licensed dataset. A journal manuscript or updated Zenodo deposit should be released only after author approval and the required metadata/licensing checks.

## Portability correction (12.1.1)

This maintenance release removes the non-standard `artifact_tool` requirement and the Bash requirement from the Python entry point. The lock-hashed source workbook is read with a bounded Python-standard-library OOXML numeric extractor; **no original observations, analytical tables or figures have changed**. Exact workbook parity was checked against the prior reader over all 32 rows and 39 required columns; pixel-parity tests for all four figures remain 4/4 PASS in the tested environment. Installation is now documented with a conventional pip requirements file. On other operating systems, typographic rasterization can differ due to fonts and library versions; exact pixel equality is established only in the reported test environment.
