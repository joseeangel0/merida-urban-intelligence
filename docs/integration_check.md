# NB14 prerequisites and approval evidence

NB14 is Phase 1 cross-source evidence (TEAM_PLAN 4.6 and issue #26). It reads
real raw inputs and the processed geography; it does not replace Gustavo's
five-file processed-contract suite, findings/PDF, Lorena's NB30/31 or the final
README/release work. Those are separate coordinated deliverables.

## Preparing the pinned inputs

Use Python >=3.11 and install `requirements.txt`. Prepare these four approved
files under `data/raw/`: `census_ageb_2020_09.zip`, `denue_09.zip`,
`marco_geo_2020_09.zip` and `crime_fgj_2024.csv`. The stable SHA-256 versions are
in `src/analysis/provenance.py`; the download manifest records provenance but
is not an independent source of expected hashes because download rewrites it.
The FGJ CSV is distributed outside Git and must be supplied locally.

In a clean checkout, run:

```bash
python -m src.pipeline download transform
python -c "from src.analysis.integration import verify_input_provenance; print(verify_input_provenance())"
```

With all four approved files cached, download extracts the ZIPs and copies the
plain FGJ CSV without retrieving a new version from the internet. The geography
transform creates `data/processed/ageb.parquet`. Existing extraction directories
are skipped by ordinary download, which is why archive-only checks are inadequate.
Preflight requires the consumed census and DENUE CSVs, both FGJ copies, and the
AGEB/locality/alcaldia shapefile components, including any accompanying encoding
files/indexes. It compares extraction bytes against the verified ZIP members.

The processed Parquet must have the owner's exact geography columns/order, CRS,
MultiPolygon type, unique complete key set, source attributes/names, city-core
flag, projected areas and source-equivalent geometry. The comparison reuses
geography's scope/projection helpers and is read-only: it never runs the transform
over an input it is checking. Topological geometry equality permits ring ordering
and Polygon-to-MultiPolygon wrapping; altered boundaries fail without a tolerance.

Run NB14 top-to-bottom in a fresh kernel rooted in the checkout. Its first code
cell performs all checks before publishing reference counts. Missing inputs,
unexpected versions and stale/altered extraction or polygons stop execution.
No source files or manifest are changed by NB14/preflight.

## Recovering from a provenance failure

Keep the failing raw files as evidence. Do not force-download, overwrite them,
change pinned hashes to match them, or disable TLS verification. Identify the
source/member named by the error and coordinate an unexpected version with its
owner. Prepare a separate clean checkout and copy only independently verified
approved archives/plain FGJ file into its empty `data/raw/` (retain the tracked
manifest and `.gitkeep`). Re-run `download transform` there, then preflight and
NB14. This produces fresh extraction and processed data without destroying the
old evidence. `stage` loads Parquet into PostgreSQL; it does not extract raw
sources or regenerate geography.

Before approval, run `python -m src.pipeline all` against a **disposable**
PostgreSQL/PostGIS development database, then `pytest tests/`. Schema rebuilds
`stg` and `dw`; never point this verification at a database that must be preserved.
Existing `.env` files must not be overwritten. Record blockers, skipped steps,
input versions and whether inputs were cached or obtained live. CI alone does
not establish these acceptance gates.

## Population coverage

Matched `POBTOT` is required by the existing census warehouse contract; `*` or
`N/D` in a matched AGEB raises an error naming the key. Malformed numeric tokens
also fail. Orphan detail uses nullable integers. A nonempty entirely suppressed
orphan group has an unavailable total, never zero; partial groups expose the
known subtotal plus observed/missing counts and a completeness flag. A genuine
observed zero remains zero. An empty orphan group has no excluded residents and
is distinguished by its zero record count. NB14 prints the coverage explicitly.

## Issue #26 edge-case evidence map

| Approval gate | Evidence |
|---|---|
| Leading zeros, component widths, alphabetic AGEB, missing/malformed codes | `test_integration_spatial.py::test_key_normalization_preserves_alpha_and_missing_components` and `test_partition_handles_malformed_keys_and_zero_eligible_comparisons`; `test_census.py::test_select_ageb_rows_keeps_only_ageb_totals_and_builds_cvegeo`. |
| Mixed census grains and duplicate joins | Shared `select_ageb_rows`; census selection/duplicate tests; duplicate processed polygon test in `test_integration_spatial.py`; preflight compares the complete source key set. |
| All 2,431 AGEBs and exact retained key set | NB14 census assertions and `test_integration.py::test_census_polygon_compatibility`; no city-core/population filter. Preflight verifies all source polygons, not only the count. |
| Coordinate order, null/nonnumeric/zero/out-of-range/swapped axes, CRS and IDs | `test_integration_spatial.py::test_coordinate_validation_preserves_ids_and_projects_longitude_first` and `test_assignment_rejects_missing_or_incompatible_crs`; default shared spatial helpers. |
| Strict boundary exclusion and ambiguous matches | `test_within_excludes_boundary_and_outside_points` and `test_ambiguous_polygon_assignment_fails` in `test_integration_spatial.py`. |
| Complete DENUE partitions and zero eligible denominator | `test_integration.py` pinned funnel/three-row probe; `test_integration_spatial.py` malformed/all-unmatchable probe. NB14 reconciles retained + outside + invalid to raw. |
| Census suppression, unavailable/partial aggregates and malformed numerics | Aggregate-level tests in `test_integration_edges.py` for matched required population, `*`/`N/D` orphan groups, partial coverage, genuine zero, empty groups and malformed tokens; shared census suppression tests. |
| Filing versus offence dates, missing dates, earlier offences, leap year, cutoff | `test_integration.py::test_crime_temporal_and_grain`; NB14 reports both invalid-date counts, earlier offences, derived 213-day interval and 29 February days. The temporal figure test distinguishes observed-empty February from unavailable Aug-Dec. July interpretation qualifies attribution. |
| DENUE registration dates versus observation snapshot | Shared `parse_alta_date` and `test_denue.py::test_parse_alta_date_uses_first_day_and_coerces_invalid_values`; NB14 reports unavailable registration count and distinguishes 05/2026 snapshot from registration history/survivorship. |
| Actual-input provenance and stale extraction | `test_integration_edges.py` complete matching fixture, unchanged-ZIP/stale-CSV and DBF/encoding cases, missing archives/members/Parquet, changed FGJ versions, unverified extra sidecar, and altered geometry/attributes/CRS with valid counts. Passing/failing checks preserve bytes. |
| Fresh-kernel execution, actionable prerequisites, portability and repeatability | NB14 starts with preflight; missing/empty prerequisite tests and recovery above. Verify fresh-kernel execution, source bytes unchanged and the exported summary reproduced. Pinned-data tests explicitly skip when real prerequisites are absent; skips are not a successful integration run. |

Synthetic data in regression fixtures is only used to exercise rejection and
missingness behavior; it is never an analytical incident dataset or warehouse input.

## Verification of the review correction (8 October 2026)

- `python -m src.pipeline all`: all seven steps completed without skipped modules
  or SQL files, using fresh extraction of the four cached approved inputs and a
  disposable PostgreSQL 16/PostGIS 3.5 database. Warehouse validation reproduced
  2,431 AGEBs, 9,138,524 residents, 461,231 businesses and 112,285 investigation files.
- `pytest tests/` after transforms: **123 passed, 0 skipped**. A separate checkout
  containing code/tests but no datasets: **113 passed, 10 expected input-dependent
  skips**. Both runs had the same three existing PySAL deprecation warnings.
- Ruff's repository-selected checks passed for `src` and `tests`; all **21** source
  modules imported successfully. Local Python was 3.13; CI uses 3.12.
- NB14 executed all **five** code cells from a fresh kernel; its summary CSV
  reproduced and both temporal PNG exports were regenerated and inspected.
  Byte hashes of all **109 raw files** were unchanged across notebook execution.
  Matched population coverage is 2,431 observed / 0 missing; orphan coverage is
  2 observed / 0 missing. Invalid filing dates are 0, invalid offence dates 11,
  and unavailable DENUE registration months 36.

These checks used cached real inputs; live source retrieval was not verified.
No environment file, raw/processed dataset or generated manifest change is part
of the correction commit.
