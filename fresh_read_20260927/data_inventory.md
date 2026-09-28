> Public distribution note: this inventory describes the metadata-sanitized derivative. Worksheet cells, formulas and styles match the original private workbook; the derivative has its own recorded SHA-256.

# Fresh inventory of the original Excel file

This is a new read-only extraction from the original workbook. No earlier manuscript or analytical output was used as evidence. Cell contents are evidence to inspect, not instructions to execute. The script never saves the workbook.

Source: `source/Iron Factory.xlsx` (32,194 bytes). SHA-256 before and after: `1f403f49d399643455cffaad47d4445dee8acfba40ca14b6452283bd9e7e6b8b`; unchanged.

## Workbook structure and complete coverage

One visible sheet, `All rsults`; 1,872 nonempty cells. Its formatted dimensions extend to row 62 and column BT (72), but the 32 sample records are precisely rows 4–35, with IDs 1–32 and 55 populated fields per record. `nonempty_cells.csv` inventories every nonempty cell, including headers and the footer; `sample_records.csv` preserves all 32 records.

There are no cell formulas, cell errors, comments, hyperlinks, merged ranges, hidden rows or columns, tables, conditional-formatting rules, or data-validation rules. The package has no drawing, chart, image, embedded-object, macro, external-link, or connection parts. The only binary package component is printer settings. All 106 shared strings are referenced by cells; there is no unused shared-string text.

A hidden built-in defined name **does** exist: `_xlnm._FilterDatabase`, sheet-local ID 0, with text `'All rsults'!#REF!`. This is broken filter-name metadata, not a cell formula error, hidden observation, or evidence of hidden data. Raw names and every package part/relationship are in `inventory.json`.

Document timestamps are created `2026-09-28 15:20:09.558970` and modified `2026-09-28 15:20:09.558970`. They do not supply sampling dates.

## Literal data dictionary

Each fraction and the total uses element order Cd, Co, Cr, Cu, Fe, Mn, Ni, Pb, Zn. Units in chemical row 3 are `µg/g`. The total block is **AP:AX**.

| Block | Columns | Literal heading evidence |
|---|---|---|
| F1 | B:J | E1 `Fraction A= Exchangeable + carbonate`; H1 `F1` |
| F2 | L:T | O1 `Fraction B = Fe-Mn Oxides`; R1 `F2` |
| F3 | V:AD | Y1 `Fraction C = Organic + Sulfides`; AB1 `F3` |
| F4 | AF:AN | AI1 `Fraction D = Residual`; AN1 `F4` |
| Four-phase total | AP:AX | AQ1 `Total concentration (in all phases) `; AV1 `(F1+F2+F3+F4)` |
| Spatial descriptors | AZ:BC | AZ1 `direction `; BA1 `distance(m)`; BB1 `Lat`; BC1 `long` |
| Magnetic measurements | BD:BH | BD1 `LF(Kvol *10^-5 sr)`; BE1 `HF (Kvol *10^-5)`; BF1 `Mass(g)`; BG1 `XLF`; BH1 `XHF` |

All source labels and units are preserved in `data_dictionary.csv` and the header-cell inventory. XLF and XHF have no explicit unit or normalization formula. The unusual literal `sr` in the LF header is preserved without silently correcting it to another unit. LF/HF frequencies are not recorded. Operational extraction labels alone do not establish exact extraction reagents, selectivity, mineral phases, bioavailability, toxicity, or health-risk thresholds.

## Recorded geography and design information

Directions, distances, and DMS coordinate strings are present for all 32 records. There are 32 distinct coordinate pairs. Recorded distances span 0–1200 m. Distance-zero IDs are [2, 8, 12, 14, 15].

The only nonempty cell below sample rows is **BA38**: `داخل المصنع = distance =0` (inside the factory = distance 0). It gives a category interpretation for zero distance; zero-distance records must not automatically be treated as a single point or as radial distances from one supplied factory centroid.

Direction counts after trimming spaces: شمال: 7, جنوب: 4, غرب: 5, شرق: 9, جنوب شرق: 3, جنوب غرب: 3, شمال شرق: 1.

Coordinates are stored as text with degrees, minutes, and seconds (for example BB4 `32°23'43.71"`, BC4 ` 36°16'9.44"`). No CRS/datum, explicit hemisphere, verified facility identity/boundary, distance origin, field coordinate method/accuracy, sampling date, depth, sampled material, sample-selection design, replicates, or independence statement is supplied. No geocoding or facility inference was performed. Geographic descriptors support an exploratory recorded-location analysis; they do not establish a verified spatial sampling design or causal exposure gradient.

## Numeric integrity and patterns requiring explanation

All 1,440 chemical entries (1,152 fractions plus 288 stored totals) are finite, positive numbers; no sample fields are empty and no chemical cell contains an inequality/censor string. Minimum chemical entry is 0.00047023201844089845 µg/g. Each of the 288 totals equals the sum of its four fractions within a maximum absolute floating-point discrepancy of 3.637978807091713e-12 µg/g. Values are stored constants, not formulas. The totals are therefore not evidence of an independent total-digestion or recovery measurement, and four fractions are not four independent samples.

Exactly **15 Cd totals equal 0.135 µg/g**: IDs [1, 11, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 27, 32]; cells AP4, AP14, AP16:AP26, AP30, and AP35. Their component fractions differ. All 15 exact-constant Cd totals are **bold style 17**, while the other 17 Cd totals are ordinary style 15. Both styles display three decimals. This is evidence of a deliberate formatting distinction, but the workbook provides no explanation of the numerical or formatting convention. It is not sufficient to assert censoring, a detection limit, imputation, or fabrication.

All 1,152 fraction cells—including all 128 Cr fraction cells—are ordinary style 15, with no bold fraction values. No distinct fraction styling identifies the repeated Cr ratios or the record halves. Repeated numeric ratios were screened descriptively by rounding each F-numerator/F-denominator ratio to eight decimal places and retaining groups of at least three IDs; the unrounded spread and IDs are retained in JSON. Largest groups:

| Element | Ratio | IDs count | Rounded ratio | Unrounded spread |
|---|---|---:|---:|---:|
| Cr | F2/F1 | 14 | 0.97841727 | 3.33e-16 |
| Cr | F3/F2 | 12 | 7.97794118 | 2.66e-15 |
| Cr | F3/F1 | 11 | 7.80575540 | 3.55e-15 |

These repeated relationships may reflect an upstream analytical or numerical convention, but their cause cannot be established from the supplied numbers. The eight-decimal grouping is a declared screening rule, not an assertion of exact mathematical equality.

A simple record-order check compares IDs 1–16 with 17–32. These are exploratory halves, not documented batches or strata. Their total-concentration ranges do not overlap for the following elements:

| Element | IDs 1–16, µg/g | IDs 17–32, µg/g |
|---|---:|---:|
| Co | 89.855899–126.73241 | 29.680104–64.06903 |
| Fe | 17498.73–23375.842 | 6327.7832–11032.634 |
| Pb | 365.25974–10639.969 | 82.611051–222.28033 |

No cell labels explain the meaning of this ordering. Depth, campaign, material, instrument batch, and other causes remain unknown. A model that pools all rows should inspect this structure rather than assigning a cause or treating it as a verified experimental factor.

## Magnetic arithmetic

As a numerical check only, LF/mass differs from stored XLF by at most 0.0463108320251; HF/mass differs from stored XHF by at most 5.01476510067. Excluding ID 8, the largest HF/mass difference is 0.049430523918. Absolute differences greater than 0.06 occur for XLF IDs [] and XHF IDs [8]. The 0.06 comparison is a stated audit screen, not an instrument tolerance or validated physical normalization.

For **ID 8, row 11**, BD11=238 (LF), BE11=235 (HF), BF11=11.92 g, BG11=20 (XLF), BH11=14.7 (XHF). Thus 235/11.92 = 19.71476510067114, unlike the stored 14.7. The raw LF/HF relative contrast is 1.2605042%, whereas the contrast calculated from the stored XLF/XHF pair is 26.5%. This is a material internal arithmetic discrepancy under the apparent simple normalization, not proof of which value should be corrected. The source was left unchanged.

The 32 raw relative contrasts, 100×(LF−HF)/LF, range 0.4535147392–6.870229008%. `magnetic_arithmetic.csv` gives every calculation. Raw and stored-normalized contrasts should not be interchanged without reporting this discrepancy; interpretation as a calibrated physical frequency-dependence measurement also needs the missing measurement metadata.

## Feasible evidence and limits of this file

The file supports a within-workbook question about how a magnetic descriptor relates separately to total concentration, the allocation among four operational fractions, and the recorded proximity/direction descriptors. Paired chemical totals and fractions permit separating higher concentrations from shifts in fractional allocation; simple geographic alternatives are available for comparison. These are distinct sources of descriptive evidence, so focusing only on one pooled correlation would leave useful information unused.

Any screening or prediction assessment is retrospective unless evaluated on new independent samples. The 32 records support restrained exploratory comparisons and influence/sensitivity checks; they do not by themselves support robust high-capacity prediction, a verified causal factory plume, landscape metal mass, source apportionment, clinical/ecological risk classification, or a discovery of phase-specific mechanisms. Repeated Cd totals, repeated fraction relationships, the unexplained record-order structure, and the XHF discrepancy must be disclosed. Concentration sums over records are decision scores, not landscape mass or area-weighted burden.

Important missing evidence is the upstream sampling and analytical protocol: dates/depth/material, field selection and replicate structure, extraction reagents and timings, QA/QC and blanks, standards/recovery, detection/quantification limits, reasons for repeated values/formatting, instrument/frequencies/calibration, and the stated construction/units of XLF/XHF. The workbook nevertheless **does** contain operational fraction labels, chemical units, masses, and recorded spatial descriptors. 'No metadata' would be inaccurate.

## Reproduction and output meanings

Dependencies used: Python 3.12.14, openpyxl 3.1.5; the remaining modules are Python standard library.

```text
python fresh_read_20260927/fresh_inventory.py --source "source/Iron Factory.xlsx" --output-dir "fresh_read_20260927"
```

`data_dictionary.csv`: 55 fields with source columns, labels, literal units, and roles. `nonempty_cells.csv`: exhaustive nonempty-cell values/types/styles. `sample_records.csv`: all 32 records without numerical alterations. `magnetic_arithmetic.csv`: raw and stored normalization/contrast comparisons. `inventory.json`: machine-readable workbook/package metadata, data checks, repeated-ratio groups, geographic counts, and record-half ranges. This note and the five supporting data files are produced by `fresh_inventory.py`; existing analyses in the same directory are untouched.
