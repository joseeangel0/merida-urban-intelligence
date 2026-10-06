# Nora Economic and Spatial Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver Nora's tested DENUE transformation, economic documentation, spatial-weights helper, profiling and Moran/LISA notebooks, and report contribution.

**Architecture:** Keep raw-data profiling in a reproducible notebook and production transformations in `src/transform/denue.py`. Reuse the existing coordinate and AGEB assignment API, then keep spatial statistics behind one small `build_weights()` function used by a warehouse-only analysis notebook.

**Tech Stack:** Python 3.11+, unittest, pandas, GeoPandas, PyArrow, libpysal, esda, matplotlib, Jupyter.

---

### Task 1: Prepare the environment and source data

**Files:**
- Runtime only: `.venv/`, `data/raw/denue_31/`, `data/raw/marco_geo_2020/`

- [ ] **Step 1: Create the virtual environment**

Run: `python3 -m venv .venv`

- [ ] **Step 2: Install existing project dependencies**

Run: `.venv/bin/pip install -r requirements.txt`
Expected: installation exits with status 0; no dependency is added to `requirements.txt`.

- [ ] **Step 3: Confirm the source-data state**

Run: `test -f data/raw/denue_31/conjunto_de_datos/denue_inegi_31_.csv && echo present || echo missing`

- [ ] **Step 4: Download existing configured sources if DENUE is missing**

Run: `.venv/bin/python -m src.pipeline download`
Expected: DENUE and geographic archives are extracted under `data/raw/` and recorded in the manifest.

- [ ] **Step 5: Build the existing geography dependency**

Run: `.venv/bin/python -m src.transform.geography`
Expected: `data/processed/ageb.parquet` contains 526 EPSG:6372 AGEBs.

### Task 2: Implement DENUE mapping and parsing test-first

**Files:**
- Create: `tests/test_denue.py`
- Create: `src/transform/denue.py`

- [ ] **Step 1: Write failing mapping tests**

Test `sector_code()` for ordinary, `31-33`, and `48-49` sectors; test `activity_group()` for Retail, Services, and Other; test `parse_alta_date()` for `YYYY-MM`, missing values, and invalid values.

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m unittest tests.test_denue -v`
Expected: FAIL because `src.transform.denue` does not exist.

- [ ] **Step 3: Implement the minimum mapping and parsing helpers**

Use constants for service sectors and exact DENUE size labels. Parse dates with `pandas.to_datetime(..., format="%Y-%m", errors="coerce")`.

- [ ] **Step 4: Verify GREEN**

Run: `.venv/bin/python -m unittest tests.test_denue -v`
Expected: all mapping and parsing tests pass.

### Task 3: Implement economic and business outputs test-first

**Files:**
- Modify: `tests/test_denue.py`
- Modify: `src/transform/denue.py`

- [ ] **Step 1: Write failing table-contract tests**

Use a small in-memory DENUE frame to require exact economic-activity columns, unique SCIAN rows, English sector names, exact business columns, integer IDs, `cvegeo_reported`, and preservation of projected point geometry.

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m unittest tests.test_denue -v`
Expected: FAIL because the table builders do not exist.

- [ ] **Step 3: Implement the minimum table builders and `run()`**

Read the Latin-1 CSV as strings; validate required columns and business-size labels; build points from the full state; assign AGEBs; derive audit codes and dates; write the two contract outputs.

- [ ] **Step 4: Verify GREEN**

Run: `.venv/bin/python -m unittest tests.test_denue -v`
Expected: all DENUE unit tests pass.

- [ ] **Step 5: Run real-data acceptance checks**

Run: `.venv/bin/python -m src.transform.denue`
Expected: 56,667 +/- 5 unique business rows, EPSG:6372, at least 99.5% reported/spatial agreement, full SCIAN coverage, and approximately 19,400 Retail rows.

### Task 4: Create the DENUE profiling notebook

**Files:**
- Create: `notebooks/12_profile_denue.ipynb`

- [ ] **Step 1: Build the notebook with deterministic cells**

Include source loading, shape/dtypes, coordinate quality, duplicate IDs, SCIAN sector table, `per_ocu` table, `fecha_alta` coverage, and Markdown explaining the mapping and date semantics.

- [ ] **Step 2: Execute the notebook**

Run: `.venv/bin/jupyter nbconvert --to notebook --execute --inplace notebooks/12_profile_denue.ipynb --ExecutePreprocessor.timeout=600`
Expected: every cell completes and saved outputs include the required profiling tables.

- [ ] **Step 3: Validate notebook structure**

Run: `.venv/bin/python -m json.tool notebooks/12_profile_denue.ipynb >/dev/null`
Expected: exit status 0.

### Task 5: Implement spatial weights test-first

**Files:**
- Create: `tests/test_spatial_weights.py`
- Create: `src/analysis/spatial_weights.py`

- [ ] **Step 1: Write failing geometry tests**

Construct a small polygon GeoDataFrame with a Queen island. Require valid `kind` handling, Queen island attachment, KNN neighbor count, row-standardized weights, and preserved observation IDs.

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m unittest tests.test_spatial_weights -v`
Expected: FAIL because `src.analysis.spatial_weights` does not exist.

- [ ] **Step 3: Implement `build_weights()`**

Use `libpysal.weights.Queen.from_dataframe`, `KNN.from_dataframe`, and `attach_islands`; reject unsupported kinds and invalid `k`; set `transform = "R"` before returning.

- [ ] **Step 4: Verify GREEN**

Run: `.venv/bin/python -m unittest tests.test_spatial_weights -v`
Expected: all weights tests pass with no unhandled island warnings.

### Task 6: Create the Moran/LISA analysis notebook

**Files:**
- Create: `notebooks/32_global_moran_lisa.ipynb`
- Generate: `outputs/figures/32_moran_*.png`
- Generate: `outputs/maps/32_lisa_*.png`

- [ ] **Step 1: Build warehouse-only analysis cells**

Load city-core KPIs via `load_kpis`, choose complete indicators, build Queen and KNN-6 on identical rows, run 999-permutation Moran statistics, report I/E[I]/z/p/n, create scatterplots, calculate LISA clusters, list significant AGEBs, and save at least two cluster maps.

- [ ] **Step 2: Execute when warehouse dependencies are available**

Run: `.venv/bin/jupyter nbconvert --to notebook --execute --inplace notebooks/32_global_moran_lisa.ipynb --ExecutePreprocessor.timeout=900`
Expected: executed results and required figures. If the team warehouse is unavailable, validate syntax and retain a clear prerequisite cell rather than fabricate results.

- [ ] **Step 3: Validate notebook structure and code syntax**

Run a Python check that loads the notebook JSON and compiles every code cell.
Expected: every code cell compiles.

### Task 7: Complete Nora-owned documentation

**Files:**
- Modify: `docs/data_dictionary.md`
- Modify: `README.md`
- Create: `report/sections/4_kpis_spatial_analysis.md`

- [ ] **Step 1: Document economic dimensions and fact grain**

Describe every column in `dim_economic_activity`, `dim_business_size`, and `fact_business`, including source fields, units, date interpretation, spatial membership, and audit geography.

- [ ] **Step 2: Replace Nora-owned README placeholders**

Document DENUE cleaning, classification, spatial integration, weights, Moran/LISA methods, and limitations without editing another member's unfinished content.

- [ ] **Step 3: Write report section 4 from verified outputs**

Include the economic KPI definitions, neighborhood rule, Moran/LISA result table when available, map references, and non-causal interpretation. Explicitly label unavailable team-dependent results instead of inventing values.

### Task 8: Final verification

**Files:**
- All files above

- [ ] **Step 1: Run unit tests**

Run: `.venv/bin/python -m unittest discover -s tests -v`
Expected: all tests pass.

- [ ] **Step 2: Run source and notebook syntax checks**

Run: `.venv/bin/python -m compileall -q src tests`
Expected: exit status 0.

- [ ] **Step 3: Run repository whitespace checks**

Run: `git diff --check`
Expected: no output.

- [ ] **Step 4: Run the complete pipeline when team dependencies exist**

Run: `.venv/bin/python -m src.pipeline all`
Expected: all stages and SQL validation pass. Otherwise record the exact missing team-owned dependency and retain successful Nora-level checks.

- [ ] **Step 5: Review the final diff**

Run: `git status --short && git diff --stat && git diff -- src tests docs README.md report`
Expected: only Nora-owned implementation, tests, notebooks, outputs, and documentation are changed.
