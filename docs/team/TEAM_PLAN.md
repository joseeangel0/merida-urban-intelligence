# Team plan — Mexico City Urban Intelligence

Everything each member needs: what to build, which files you own, the data contract your output must follow, a ready-to-paste AI prompt, and the **acceptance tests ("win conditions")** that prove your part is done.

| # | Member | GitHub | Role | Owns |
|---|---|---|---|---|
| 1 | **Jose Pech** | `joseeangel0` | Repo lead · DW architect | repo setup, `sql/01_schema.sql`, model diagram, `sql/03_views.sql`, `sql/04_validation.sql`, `src/analysis/data.py`, README integration |
| 2 | **Julio de Aquino** | `pyrawn` | Demographic layer | Census profiling, `src/transform/census.py`, correlation analysis |
| 3 | **Nora Horta** | `strangelove-t` | Economic layer | DENUE profiling, `src/transform/denue.py`, spatial weights, Global Moran + LISA |
| 4 | **Lorena Pérez** | `ldpl3012` | Geography & integration | geographic-unit decision, `src/transform/geography.py`, `src/transform/spatial.py`, `src/load/load_staging.py`, `sql/02_load.sql`, KPI maps |
| 5 | **Valeria Hernández** | `valnix140405` | Public-safety layer | crime source record, `src/transform/crime.py`, crime temporal analysis, bivariate Moran, report section 6 |
| 6 | **Gustavo Fuentes** | `Audileleach` | Data quality, KPI queries & findings · report lead | source inventory and data-quality register, contract tests (`tests/`), `sql/05_kpi_queries.sql`, LISA hot-spot analysis by alcaldía, alcaldía comparison, report assembly |

> 🔄 **Scope change — 5 Oct 2026 (D1 evening).** The instructor answered our crime-data request: *no simulated data; with municipal-level crime data the spatial analysis would have to stay at state level; for high granularity use hoyodecrimen.com, but working with Mexico City.* We therefore keep the **urban AGEB** design and move the study area from Mérida to **Mexico City (CDMX, 16 alcaldías)**. Every contract below has been updated (sources, reference values, paths `31 → 09`). The Mérida work already merged (Lorena's assessment, Jose's search log) stays as Phase 1 evidence of the data assessment. **Gustavo Fuentes joins the team** (§4.6) and takes report assembly from Valeria and builds the alcaldía-level and hot-spot analysis on top of Nora's LISA.
>
> **If you already ran the setup:** `git pull`, then `python -m src.pipeline download` (new keys `*_09` and `crime_fgj_2024`). The old Yucatán folders in `data/raw/` (`denue_31`, `census_ageb_2020`, `marco_geo_2020`) can be deleted.

---

## 0. Golden rules (read before anything else)

1. **Your commits, your account.** Configure `git config --global user.email` with the email registered on your GitHub account. After your first push check that your avatar appears next to your commit. Unlinked commits = no collaboration credit for you.
2. **Commit in every phase.** Minimum: 2 commits in Phase 1, 2 in Phase 2, 2 in Phase 3, 1 in documentation/report. Small commits, clear messages (`feat(census): ...`). No bulk uploads.
3. **Branch → PR → someone else merges** ("Create a merge commit", never squash). See [`CONTRIBUTING.md`](../../CONTRIBUTING.md).
4. **Only edit the files you own.** If you need a change in someone else's file, ask them (or open a PR and tag them). This avoids merge conflicts with 6 AIs writing code in parallel.
5. **Respect the data contract (§3).** Column names, types, CRS and file names are fixed so the pieces fit together. If you need to change the contract, tell Jose first.
6. **Raw files are never modified.** Read from `data/raw/`, write to `data/processed/`. Neither folder is committed.
7. **Phase 3 reads from the warehouse.** Analysis notebooks load data with `gpd.read_postgis()` from `dw` views — never from CSV/parquet/raw files (explicit requirement of the brief).
8. **Everything in English** (code, comments, commits, docs, report).
9. **Before every PR:** `python -m src.pipeline all` runs without errors.
10. **AI is a tool, you are the author.** Read and understand what your AI generates — you must be able to explain your part.

## 1. Setup (everyone, Day 0)

```bash
git clone https://github.com/joseeangel0/merida-urban-intelligence.git
cd merida-urban-intelligence
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                      # Windows: copy .env.example .env
docker compose up -d --wait                               # needs Docker Desktop / OrbStack running
python -m src.pipeline download schema                    # downloads INEGI + FGJ files (~180 MB) and creates the empty DW
```

✅ Setup is done when `docker exec merida_dw psql -U merida -d merida_dw -c "\dt dw.*"` lists 10 tables.

Recommended AI setup: open the repo folder in Claude Code (or your AI of choice with file access) so it can read the code. Every prompt below starts by asking the AI to read this plan.

## 2. Timeline

| Day | Date | Phase | Goal at end of day |
|---|---|---|---|
| D0 | Sun 4 Oct | Setup | Repo, schema and plan published (Jose). Everyone cloned and ran setup. **Valeria starts the crime-data search tonight.** |
| D1 | Mon 5 Oct | **Phase 1 — Data & geography** | Profiling notebooks merged. Lorena: `geography.py` + `spatial.py` merged **by 14:00** (others depend on them). Valeria: crime dataset decided **by 14:00**. |
| D1 | Mon 5 Oct (evening) | **Scope change** | Jose: CDMX sources, reference values and this plan merged. Gustavo onboarded. |
| D2 | Tue 6 Oct | **Phase 1 close + Phase 2 — ETL & DW** | Lorena: `geography.py` + `spatial.py` for CDMX merged **by 10:00**. Profiling notebooks (CDMX) merged by 14:00. All transforms, staging, `02_load.sql`, views and validation merged; `python -m src.pipeline all` builds the full DW. |
| D3 | Wed 7 Oct | **Phase 3 — Analytics + docs** | Maps, correlation, Moran, LISA, bivariate merged. README sections and report sections written. **Code freeze 22:00.** |
| — | Delivery | Final | Jose tags `v1.0`, Valeria uploads the PDF report. |

Dependency chain (do not block others): `geography.py` → `spatial.py` → (`denue.py`, `crime.py`) → `load_staging.py` → `02_load.sql` → `03_views.sql` → analysis notebooks.
If you are blocked, write your code against the contract and test with a temporary stub — do not wait.

## 3. Decisions already taken and data contract

### 3.1 Decisions

| Topic | Decision | Reason / evidence (profiling on D0 for Mérida, D1 evening for CDMX) |
|---|---|---|
| Study area | **Mexico City** (state `09`, all 16 alcaldías) | Instructor, 5 Oct: no simulated data; municipal crime data ⇒ state-level analysis; for point data use hoyodecrimen.com / CDMX. The FGJ CDMX publishes one row per investigation file with lat/lon. Mérida (31050) was assessed first and dropped: no public point-level crime data (search log §4.5). |
| Unit of analysis | **Urban AGEB** of Mexico City | Census 2020 publishes indicators per urban AGEB, and the INEGI 2020 polygons (`09a.shp`) share the same `CVEGEO`: **2,431/2,431 polygons have a census row, 0 invalid geometries**. 2 census AGEB rows (`0901101101107`, `0901201351227`, 7,108 residents) have no polygon in the 2020 frame → dropped and counted in `census.py`. Lorena documents the alternatives. |
| Scope | 2,431 urban AGEBs: 2,348 in the main locality of each alcaldía (`cve_loc='0001'`, the contiguous city) + 83 in 17 other urban localities (outlying pueblos) | Rural areas have no AGEB-level census data. |
| CRS | Store everything in **EPSG:6372** (metres); lat/lon inputs are EPSG:4326 | The INEGI polygons are already in ITRF2008 LCC (= EPSG:6372); areas in km² are directly comparable. |
| Point → polygon | `within` predicate; points outside any urban AGEB are **dropped and counted** | DENUE: 461,231 / 462,732 (99.7 %) inside an urban AGEB. Crime 2024: ≈ 112.3 k / 119.7 k (93.8 %) — the rest have no coordinates or fall outside urban AGEBs. |
| Census suppression | `*` and `N/D` → `NULL`, never 0; count them in `n_suppressed_fields` | INEGI confidentiality rule. |
| PEA rate base | `pea / pop_12_plus` | PEA is defined for population aged 12+. |
| Retail | SCIAN sector **46** | "Comercio al por menor". |
| Services | SCIAN sectors **51, 52, 53, 54, 55, 56, 61, 62, 71, 72, 81** | Private services (93 = government, excluded). |
| Small populations | Flag `low_population = pop_total < 100` (55 AGEBs, 17 with 0 people); exclude them from rate-based statistics | Per-capita rates explode with tiny denominators. |
| Spatial weights | **Queen contiguity**, row-standardised, on the 2,348 city-core AGEBs; the 1 island attached to its nearest neighbour. Sensitivity check: **KNN k=6** on the same AGEBs | Queen on all 2,431 gives 6 disconnected components (outlying pueblos). |
| Significance | 999 permutations, α = 0.05 | |
| Crime source | **FGJ CDMX — Carpetas de investigación 2024** (`archivo.datos.cdmx.gob.mx`, CC-BY-4.0); the same data hoyodecrimen.com serves | Real, official, one row per investigation file with `latitud`/`longitud`, `delito`, `categoria_delito`, `fecha_hecho`, `hora_hecho`. 138,630 rows. |
| Crime filters | Keep `fecha_hecho` in **2024** (`config.CRIME_YEAR`); drop `categoria_delito = 'HECHO NO DELICTIVO'` | The file is organised by opening date: 11 % of rows refer to offences from earlier years; non-criminal events are not crime. Result ≈ 119.7 k incidents before the spatial join. |
| Crime id | `source_incident_id = 'fgj2024-' + row number in the raw file` (1-based, header excluded) | The FGJ file has no incident id; the row number is stable for a pinned file (SHA-256 in the manifest). |

### 3.2 Files in `data/processed/` (output of `src/transform/*`)

All GeoParquet files use **EPSG:6372** and the geometry column is named `geometry`.

| File | Owner | Rows (expected) | Columns (exact names) |
|---|---|---|---|
| `ageb.parquet` | Lorena | 2,431 | `cvegeo` (str, 13), `cve_ent`, `cve_mun`, `cve_loc`, `cve_ageb`, `mun_name` (alcaldía), `loc_name`, `is_city_core` (bool), `area_km2` (float), `geometry` (MultiPolygon) |
| `census_ageb.parquet` | Julio | 2,431 | `cvegeo` + every measure column of `dw.fact_census_ageb` with the same names (`pop_total` … `n_suppressed_fields`) — no geometry |
| `economic_activity.parquet` | Nora | ≈ 931 | `scian_code` (str, 6), `activity_name`, `subsector_code` (str, 3), `sector_code` (`'46'`, `'31-33'`, `'48-49'`, …), `sector_name` (English), `activity_group` (`Retail` / `Services` / `Other`) |
| `business.parquet` | Nora | ≈ 461,231 | `denue_id` (int64), `clee`, `establishment_name`, `scian_code`, `per_ocu_label` (exact DENUE text), `alta_date` (date, 1st of month, nullable), `cvegeo` (from spatial join), `cvegeo_reported` (from DENUE columns), `geometry` (Point) |
| `crime.parquet` | Valeria | ≈ 112 k | `source_incident_id` (str), `crime_type` (English, harmonised), `crime_type_raw`, `crime_category` (`Property` / `Violent` / `Other` …), `incident_date` (date, nullable), `incident_hour` (int −1…23, −1 = unknown), `cvegeo`, `geometry` (Point) |

Each transform module exposes `run()` and is called by `python -m src.pipeline transform`.

### 3.3 Shared spatial API — `src/transform/spatial.py` (Lorena)

```python
def load_ageb() -> gpd.GeoDataFrame: ...
    # reads data/processed/ageb.parquet

def points_from_latlon(df: pd.DataFrame, lat_col: str, lon_col: str) -> gpd.GeoDataFrame: ...
    # coerces to float, drops null/zero coordinates and those outside config.LATLON_BBOX (prints how many),
    # builds points in EPSG:4326 and returns them reprojected to EPSG:6372

def assign_ageb(points: gpd.GeoDataFrame) -> gpd.GeoDataFrame: ...
    # spatial join with predicate="within" against load_ageb(); adds column `cvegeo`;
    # drops points outside every AGEB and prints "kept X / Y (Z %)";
    # guarantees one row per input point (no duplicates)
```

### 3.4 Staging and warehouse

- `src/load/load_staging.py` (Lorena) writes each processed file to `stg.<file name>` (`stg.ageb`, `stg.census_ageb`, `stg.economic_activity`, `stg.business`, `stg.crime`) with `if_exists="replace"`, plus `stg.source` built from `data/raw/manifest.json` and `src/config.py:SOURCES`.
- `sql/02_load.sql` (Lorena) fills `dw.*` from `stg.*` resolving surrogate keys (`cvegeo → geo_key`, `scian_code → activity_key`, `per_ocu_label → size_key`, `crime_type → crime_type_key`, `date → date_key`, hour → `hour_key`). `dim_date` is generated with `generate_series` between the min and max dates in `stg.business` and `stg.crime`.
- `sql/03_views.sql` (Jose) creates the KPI views. **Contract for `dw.v_kpi_ageb`** (one row per AGEB, used by every Phase 3 notebook):

  `geo_key, cvegeo, loc_name, is_city_core, low_population, area_km2, pop_total, pop_density_km2, pea_rate, pct_0_14, pct_15_64, pct_65_plus, businesses_total, business_density_km2, businesses_per_1k, retail_total, retail_density_km2, services_total, service_density_km2, dominant_sector, dominant_sector_share, crime_total, crime_rate_per_1k, crimes_per_100_businesses, geom`

  Other views: `dw.v_crime_by_type_time` (AGEB × crime type × year-month × day of week × time band), `dw.v_business_by_sector` (AGEB × sector).

  ✅ **Done (Jose, D0):** views, `04_validation.sql` and `load_kpis()` are implemented and were tested end-to-end with the Mérida data; the reference values were updated for CDMX on D1 evening and the full run is repeated on D2 once the CDMX transforms are merged. Heads-up for analysts: per-capita KPIs have extreme outliers in AGEBs with few residents (historic centre, AGEBs dominated by markets or offices), so prefer Spearman and quantile classification, and keep `exclude_low_population=True`.
- `src/analysis/data.py` (Jose): `load_kpis(city_core_only=True, exclude_low_population=True) -> GeoDataFrame` reading `dw.v_kpi_ageb` with `gpd.read_postgis`. **All Phase 3 notebooks use this function.**

### 3.5 Reference values (CDMX, computed on D1 evening — use them in your tests)

| Check | Expected |
|---|---|
| Urban AGEB polygons in CDMX (`09a.shp`) | **2,431** (2,348 city core, 16 alcaldías), all valid, total area **792.15 km²** |
| Census AGEB rows (`MZA='000'`, `AGEB!='0000'`) | 2,433 (Σ`POBTOT` 9,145,632); **2,431** with a polygon, Σ`POBTOT` = **9,138,524** (state total 9,209,944 → urban AGEBs cover 99.2 %) |
| Σ`PEA` (non-suppressed) / Σ`P_12YMAS` (2,431 AGEBs) | 5,061,682 / 7,858,894 |
| AGEBs with `pop_total < 100` / `= 0` | 55 / 17 |
| DENUE rows CDMX | 462,732, 0 duplicated `id`, 931 SCIAN classes |
| DENUE points inside CDMX urban AGEBs | **461,231** (retail SCIAN 46: 211,431) |
| Agreement spatial-join AGEB vs DENUE's own `cve_mun+cve_loc+ageb` | **99.8 %** (99.84) |
| Crime rows (FGJ 2024 file) / offence in 2024 and not `HECHO NO DELICTIVO` / inside urban AGEBs | 138,630 / 119,666 / ≈ 112,285 (before removing ≈ 680 exact duplicates) |
| Queen weights, city core | 2,348 units, 3 components, 1 island, mean 6.0 neighbours |

---

## 4. Individual assignments

Each section has: **tasks per phase · AI prompt · win conditions · suggested commits · report/README share.**
Paste the prompt into your AI *from inside the repository folder*.

---

### 4.1 Jose Pech — Repo lead · DW architect

**Phase 1 (D0) — done in the first commits**
- Repository, structure, `requirements.txt`, `docker-compose.yml`, `.env.example`, `src/config.py`, `src/db.py`, `src/pipeline.py`, `src/extract/download_sources.py` (raw files + SHA-256 manifest), `CONTRIBUTING.md`, this plan.
- `sql/01_schema.sql` (star schema, grain of every table).
- Invite the 4 collaborators; protect `main` (require PR).

**Phase 2 (D1–D2)**
- `docs/warehouse_model.png` + `docs/warehouse_model.mmd` (Mermaid ER diagram of `dw`).
- `sql/03_views.sql`: `v_kpi_ageb`, `v_crime_by_type_time`, `v_business_by_sector` (contract §3.4).
- `sql/04_validation.sql`: `DO $$ ... RAISE EXCEPTION ... $$` blocks so the pipeline **fails** when a check fails (row counts vs staging, orphan keys, Σ population, Σ businesses, every KPI computable).
- Review and merge PRs daily.

**Phase 3 (D3)**
- `src/analysis/data.py` (`load_kpis`) — publish early on D2 so analysts can start.
- README integration (§5, §6, §8, §9), data dictionary for `dim_source`, `dim_date`, `dim_hour` and the views.
- Final run from a clean clone, tag `v1.0`.
- Report: section 3 "Data Warehouse architecture".

**AI prompt (Phase 2–3):**
```
You are helping Jose Pech in the repository merida-urban-intelligence (PostgreSQL/PostGIS geospatial
data warehouse for Mexico City). First read README.md, docs/team/TEAM_PLAN.md (sections 0, 3 and 4.1),
sql/01_schema.sql and src/pipeline.py.
Tasks, one commit each:
1. docs/warehouse_model.mmd: Mermaid erDiagram of every dw table with PK/FK and grain notes;
   render it to docs/warehouse_model.png (mermaid-cli via npx or mermaid.live).
2. sql/03_views.sql: create dw.v_kpi_ageb with EXACTLY the columns of the contract in TEAM_PLAN §3.4
   (rates use NULLIF to avoid division by zero; densities per km2; businesses_per_1k and crime_rate_per_1k
   per 1,000 residents; crimes_per_100_businesses; dominant_sector = sector with most establishments,
   ties broken alphabetically; low_population = pop_total < 100), plus dw.v_crime_by_type_time and
   dw.v_business_by_sector. Views must be re-runnable (CREATE OR REPLACE / DROP VIEW IF EXISTS).
3. sql/04_validation.sql: DO blocks that RAISE EXCEPTION when: dw row counts differ from stg; any fact
   has an orphan key; v_kpi_ageb has != 2431 rows; sum(pop_total) != 9138524; any KPI column is entirely NULL.
   End with RAISE NOTICE summarising the counts.
4. src/analysis/data.py: load_kpis(city_core_only=True, exclude_low_population=True) using
   geopandas.read_postgis and src.db.get_engine().
Do not edit files owned by other members (see TEAM_PLAN §4). Run `python -m src.pipeline all` before finishing.
```

**Win conditions**
- [ ] A teammate can go from `git clone` to a populated DW with only the README commands.
- [ ] `python -m src.pipeline all` ends with the validation NOTICE and no exception.
- [ ] `SELECT count(*) FROM dw.v_kpi_ageb` = 2,431; `SELECT sum(pop_total) FROM dw.v_kpi_ageb` = 9,138,524.
- [ ] Diagram shows every table, PK/FK and grain.
- [ ] Each of the 6 members has ≥ 6 linked commits on `main` spread across D1–D3 (`git shortlog -sne main`).

**Suggested commits:** `chore(repo): project scaffold…` · `sql(dw): star schema…` · `docs(dw): dimensional model diagram` · `sql(kpi): KPI views` · `test(dw): validation queries` · `feat(analysis): load_kpis helper` · `docs(readme): DW model and reproduction`.

---

### 4.2 Julio de Aquino — Demographic layer

**Phase 1 (D1)** — `notebooks/11_profile_census.ipynb`
- Load `data/raw/census_ageb_2020_09/.../conjunto_de_datos_ageb_urbana_09_cpv2020.csv` (read every column as `str`).
- Explain the file structure: block rows vs AGEB total rows (`MZA='000'`) vs locality/municipality totals (`AGEB='0000'`).
- Filter CDMX AGEB rows, profile the KPI variables (missing, `*`, `N/D`, zeros, distributions), compare Σ AGEB population with the state total, and by alcaldía.
- Write the **variable list** required by the demographic KPIs (variable → KPI → unit).

**Phase 2 (D2)** — `src/transform/census.py`
- `run()`: filter → build `cvegeo = ENTIDAD + MUN + LOC + AGEB` → drop (and count) the 2 AGEBs without a polygon in `ageb.parquet` → rename to the `dw.fact_census_ageb` column names → `*`/`N/D` → NULL → numeric types → `n_suppressed_fields` → write `data/processed/census_ageb.parquet`.
- Data dictionary section for `fact_census_ageb`.

**Phase 3 (D3)** — `notebooks/31_correlation.ipynb`
- Data from `src.analysis.data.load_kpis()` only.
- ≥ 3 relationships (suggested: population density vs business density; crime rate vs businesses per 1k; PEA rate vs crime rate; % 65+ vs service density). Check normality/outliers → justify **Spearman** vs Pearson; report coefficient, p-value, n; scatter plots to `outputs/figures/`.
- Sensitivity: with vs without `low_population` AGEBs.

**AI prompt (Phase 1–2):**
```
You are helping Julio de Aquino in the repository merida-urban-intelligence. First read README.md,
docs/team/TEAM_PLAN.md (sections 0, 3 and 4.2), sql/01_schema.sql (table dw.fact_census_ageb) and src/config.py.
Phase 1: create notebooks/11_profile_census.ipynb that profiles the INEGI Census 2020 AGEB file in
data/raw/census_ageb_2020_09 (read as dtype=str). Explain the row hierarchy (block, AGEB total MZA='000',
locality/municipality totals), keep the CDMX AGEB rows, quantify '*' and 'N/D' per KPI variable,
show distributions, compare the AGEB population sum with the municipality total, and end with a markdown
table "source variable -> KPI -> unit". Expected: 2,433 AGEB rows (2,431 with a polygon), sum POBTOT = 9,138,524 for the 2,431.
Phase 2: create src/transform/census.py with run() that writes data/processed/census_ageb.parquet with
column cvegeo (13 chars) plus EXACTLY the measure columns of dw.fact_census_ageb (same names), suppressed
values as NULL (never 0), nullable integer dtypes (Int64), and n_suppressed_fields. Add asserts for the
win conditions in TEAM_PLAN §4.2. Do not modify files owned by other members. Commit in small steps.
```

**Win conditions**
- [ ] `census_ageb.parquet`: 2,431 rows, `cvegeo` unique, all 13 chars, all present in `ageb.parquet`.
- [ ] Σ `pop_total` = 9,138,524; no `pop_total` NULL; suppressed values are NULL, not 0.
- [ ] Σ `pea` = 5,061,682 and Σ `pop_12_plus` = 7,858,894.
- [ ] Notebook states why AGEB rows ≠ state total (64,312 residents outside urban AGEBs + 7,108 in the 2 AGEBs without polygon).
- [ ] Correlation notebook: ≥ 3 relationships, method justified, n reported, figures saved, interpretation without causal language.

**Suggested commits:** `analysis(census): profiling notebook` · `docs(census): KPI variable list` · `feat(census): AGEB census transform` · `docs(census): data dictionary` · `analysis(spatial): correlation analysis` · `docs(report): problem and data sources section`.

**README/report:** README §2 demographic row + §4 census decisions; report section 1 "Problem and data sources".

---

### 4.3 Nora Horta — Economic layer

**Phase 1 (D1)** — `notebooks/12_profile_denue.ipynb`
- Load `data/raw/denue_09/conjunto_de_datos/denue_inegi_09_.csv` (**`encoding="latin-1"`**, dtype `str`).
- Profile: coordinates (nulls, ranges), duplicated `id`, `codigo_act` (SCIAN) by sector, `per_ocu` bands, `fecha_alta` (snapshot date vs. registration date).
- Define the SCIAN → sector → `activity_group` mapping (retail = 46; services = 51–56, 61, 62, 71, 72, 81). Sector names in English, include combined sectors 31-33 and 48-49.

**Phase 2 (D2)** — `src/transform/denue.py`
- `run()`: whole-state DENUE → `spatial.points_from_latlon` → `spatial.assign_ageb` (the **geometry** decides membership, not `cve_mun`) → `cvegeo_reported = '31' + cve_mun + cve_loc + ageb` → `alta_date` from `fecha_alta` (`YYYY-MM` → 1st of month) → write `business.parquet` and `economic_activity.parquet`.
- Data dictionary for `dim_economic_activity`, `dim_business_size`, `fact_business`.

**Phase 3 (D3)** — `src/analysis/spatial_weights.py` + `notebooks/32_global_moran_lisa.ipynb`
- `build_weights(gdf, kind="queen" | "knn", k=6)`: row-standardised; for Queen attach islands to nearest neighbour (`libpysal.weights.attach_islands`). Shared with Valeria and Gustavo — **publish it first thing on D3** (or late D2), they depend on it.
- Global Moran's I (esda, 999 permutations) for ≥ 2 indicators (suggested 4: business density, crime rate, population density, PEA rate), Queen vs KNN-6 table, Moran scatterplots.
- `local_clusters(gdf, column, w, permutations=999, alpha=0.05, seed=42)` in the same module: Local Moran's I returning one label per row (`HH`, `LL`, `HL`, `LH`, `ns`) plus `p_sim`, aligned with the input rows. **Gustavo reuses it** (§4.6), so publish it together with `build_weights`.
- LISA for ≥ 2 indicators: cluster maps (HH, LL, HL, LH, not significant) to `outputs/maps/`, list of significant AGEBs.

**AI prompt (Phase 1–2):**
```
You are helping Nora Horta in the repository merida-urban-intelligence. First read README.md,
docs/team/TEAM_PLAN.md (sections 0, 3 and 4.3), sql/01_schema.sql (dim_economic_activity, dim_business_size,
fact_business) and src/transform/spatial.py.
Phase 1: notebooks/12_profile_denue.ipynb profiling INEGI DENUE Ciudad de México (data/raw/denue_09, encoding latin-1,
dtype str): coordinates, duplicated ids, SCIAN sectors (first 2 digits), per_ocu bands, fecha_alta; define the
SCIAN sector mapping with English sector names (combined sectors 31-33, 48-49) and activity_group
(Retail = 46; Services = 51,52,53,54,55,56,61,62,71,72,81; Other = rest), justified in markdown.
Phase 2: src/transform/denue.py with run() that uses spatial.points_from_latlon and spatial.assign_ageb on the
WHOLE state file, and writes data/processed/business.parquet and economic_activity.parquet with EXACTLY the
columns of TEAM_PLAN §3.2. Report kept/dropped counts and the agreement % between cvegeo and cvegeo_reported.
Add asserts for the win conditions in TEAM_PLAN §4.3. Do not modify files owned by others. Commit in small steps.
```

**Win conditions**
- [ ] `business.parquet`: 461,231 ± 50 rows, `denue_id` unique, every `cvegeo` in `ageb.parquet`, CRS 6372, no duplicates after the join.
- [ ] Agreement `cvegeo == cvegeo_reported` ≥ 99.5 % (reference 99.8 %), mismatches explained (boundary points).
- [ ] Every `scian_code` in `business.parquet` exists in `economic_activity.parquet`; every `per_ocu_label` matches `dw.dim_business_size`.
- [ ] Retail ≈ 211.4 k establishments; the sector table is in the notebook.
- [ ] Moran notebook: I, E[I], z, pseudo p-value per indicator, Queen vs KNN comparison, interpretation; LISA maps saved.
- [ ] `build_weights` and `local_clusters` merged by D3 12:00 (Valeria and Gustavo depend on them).

**Suggested commits:** `analysis(denue): profiling notebook` · `feat(denue): SCIAN sector mapping` · `feat(denue): DENUE transform with spatial join` · `docs(denue): data dictionary` · `feat(spatial): spatial weights builder` · `analysis(spatial): global Moran` · `analysis(spatial): LISA clusters` · `docs(report): KPIs and spatial analysis section`.

**README/report:** README §2 economic row, §4 DENUE decisions, §7 Moran/LISA; report section 4 "Key KPIs and spatial analysis".

---

### 4.4 Lorena Pérez — Geography & integration

**Phase 1 (D1, priority — others depend on you)** — `notebooks/10_geographic_assessment.ipynb`
- Candidate units: municipality, locality, AGEB, block, colonia (not an INEGI unit), hexagonal grid. For each: availability in the census, official polygons, shared identifier, resolution, privacy suppression → decision table → **justify urban AGEB**.
- Load `09a.shp` (AGEB), `09l.shp` (locality names), `09mun.shp` from `data/raw/marco_geo_2020_09/conjunto_de_datos/`: CRS, `is_valid`, identifiers, map of the 2,431 AGEBs (`outputs/maps/00_study_area.png`).
- Point-to-polygon proof of concept with a DENUE sample (and crime sample once Valeria has it).
- `src/transform/geography.py` → `ageb.parquet`; `src/transform/spatial.py` (API §3.3). **Merged for Mérida on D1; CDMX update merged by D2 10:00** — read `CVE_ENT`, `CVE_MUN` (`None` = every alcaldía), `CITY_LOC` and `LATLON_BBOX` from `src/config.py` instead of literals, `mun_name` per AGEB (16 alcaldías), asserts with the §3.5 values. Keep the Mérida section of the notebook as evidence and add the CDMX run + a short note on the scope change.

**Phase 2 (D2)**
- `src/load/load_staging.py`: processed files → `stg.*` (+ `stg.source` from the manifest).
- `sql/02_load.sql`: `stg.*` → `dw.*` (keys, `dim_date` via `generate_series`, `ST_Multi` for geometries, `TRUNCATE ... RESTART IDENTITY CASCADE` first so it is re-runnable).
- Data dictionary for `dim_geography`.

**Phase 3 (D3)** — `notebooks/30_kpi_maps.ipynb`
- Choropleth maps (quantiles, `mapclassify`) of ≥ 6 KPIs across the three layers, from `load_kpis()`, saved in `outputs/maps/`. Small-multiples figure for the report. Maps only — the tabular comparison of alcaldías is Gustavo's (§4.6).

**AI prompt (Phase 1):**
```
You are helping Lorena Pérez in the repository merida-urban-intelligence. First read README.md,
docs/team/TEAM_PLAN.md (sections 0, 3 and 4.4), sql/01_schema.sql (dim_geography) and src/config.py.
1. notebooks/10_geographic_assessment.ipynb: compare candidate geographic units (municipality, locality, urban
   AGEB, block, colonia, hex grid) in a decision table (census availability, official polygons, shared key,
   resolution, confidentiality suppression) and justify urban AGEB. Load 09a.shp, 09l.shp and 09mun.shp from
   data/raw/marco_geo_2020_09/conjunto_de_datos with geopandas: report CRS, geometry validity, CVEGEO structure;
   keep CVE_ENT='09' (all alcaldías); map the 2,431 AGEBs to outputs/maps/00_study_area.png; test point-in-polygon with a
   DENUE sample (data/raw/denue_09, latin-1).
2. src/transform/geography.py run() -> data/processed/ageb.parquet with EXACTLY the columns of TEAM_PLAN §3.2
   (EPSG:6372, MultiPolygon, area_km2 from the projected geometry, loc_name from 09l.shp).
3. src/transform/spatial.py implementing EXACTLY the API in TEAM_PLAN §3.3.
Add asserts for the win conditions in TEAM_PLAN §4.4. Do not modify files owned by others. Commit in small steps.
```

**AI prompt (Phase 2):**
```
Continue as Lorena's assistant. Read docs/team/TEAM_PLAN.md §3.4 and sql/01_schema.sql.
1. src/load/load_staging.py run(): write every file in data/processed to stg.<name> with geopandas to_postgis /
   pandas to_sql (if_exists="replace"), and stg.source from data/raw/manifest.json + src/config.SOURCES.
2. sql/02_load.sql: re-runnable load from stg.* into dw.* (TRUNCATE dw facts and non-static dims RESTART
   IDENTITY CASCADE; insert dim_source, dim_geography (ST_Multi, SRID 6372), dim_date (generate_series between
   min and max dates of stg.business and stg.crime), dim_economic_activity, dim_crime_type, then the three facts
   resolving surrogate keys by natural key). Unknown hour -> hour_key -1.
Run `python -m src.pipeline schema stage load` and show the row counts per table.
```

**Win conditions**
- [ ] `ageb.parquet`: 2,431 rows, `cvegeo` unique, 2,348 `is_city_core`, 16 `mun_name` values, all valid, EPSG:6372, Σ `area_km2` = 792.15 ± 0.1.
- [ ] `spatial.assign_ageb` on the DENUE CDMX file keeps 461,231 points and returns no duplicates.
- [ ] After `stage load`: `dw.dim_geography` = 2,431, and every `dw` table count equals its `stg` source (facts) — validated by `04_validation.sql`.
- [ ] Re-running `python -m src.pipeline schema stage load` twice gives identical counts.
- [ ] ≥ 6 KPI maps with legend, title, units and north/scale or basemap.

**Suggested commits:** `analysis(geo): geographic unit assessment` · `feat(geo): AGEB polygons transform` · `feat(geo): shared point-in-polygon API` · `feat(dw): staging loader` · `sql(dw): load staging into star schema` · `docs(geo): data dictionary` · `analysis(maps): KPI choropleths` · `docs(report): geographic integration section`.

**README/report:** README §3 Geographic strategy (full), §4 spatial join; report section 2 "Geographic integration strategy".

---

### 4.5 Valeria Hernández — Public-safety layer

**Phase 1 (D1–D2) — crime source: decided ✅**

The search for Mérida (D0, Jose) found no public point-level crime dataset. Record this log in your notebook — it is evidence for the data assessment and the reason for the scope change:

| Source checked | Result |
|---|---|
| SESNSP — [datos abiertos de incidencia delictiva](https://www.gob.mx/sesnsp/acciones-y-programas/datos-abiertos-de-incidencia-delictiva) | **Real but aggregated**: monthly counts per municipality and crime type, 2015–2025 (XLSX). No coordinates. |
| Fiscalía General del Estado de Yucatán (fge.yucatan.gob.mx) | No open data; only procedures and press releases. |
| Yucatán transparency open-data portal (transparencia.yucatan.gob.mx/datos_abiertos.php) | Only budget/expenditure datasets. |
| Mérida Geoportal (merida.gob.mx/geoportal) | Layers for COVID, jobs, bus stops, health, sports units — no public-safety layer. |
| CEISP Yucatán Data Observatory (ceisp.gob.mx/ObservatorioDatos, registration required) | Only 104 monthly PDF reports (2018–2026); on 4 Oct 2026 the server returned `null` download links for every file tested. No CSV/API/map. |
| 911 open data | Only CDMX and Puebla publish geolocated calls. |
| Kaggle, GitHub, Zenodo, Figshare, academic repositories (UADY, CentroGeo) | Nothing for Mérida. |
| **Instructor reply (5 Oct 2026)** | *"No simulated data. If you have municipal-level data, your spatial analysis must stay at state level. For high granularity you can consider hoyodecrimen.com, but working with Mexico City."* → **study area moved to CDMX.** |

**Selected source:** FGJ CDMX — *Carpetas de investigación* 2024 ([dataset page](https://datos.cdmx.gob.mx/dataset/carpetas-de-investigacion-fgj-de-la-ciudad-de-mexico), file `carpetasFGJ_2024.csv`, CC-BY-4.0). It is the official source behind hoyodecrimen.com (whose API only returns points within a radius, so it is not suitable for a full download). Already registered in `src/config.py:SOURCES` as `crime_fgj_2024`; `python -m src.pipeline download` stores it in `data/raw/crime_fgj_2024/`.

> ⚠️ On 5 Oct 2026 `archivo.datos.cdmx.gob.mx` served an **expired TLS certificate**, so the download step fails for this file only (the INEGI files download fine). Do **not** disable certificate verification in the code. Retry later (Let's Encrypt certificates are usually renewed within days); if it is still expired on D2 at 10:00, tell Jose so the team decides how to obtain and pin the file.

Then `notebooks/13_profile_crime.ipynb`:
- Columns and meaning (`fecha_inicio` = file opened vs `fecha_hecho` = offence date; `delito` vs `categoria_delito`; `colonia_*`, `alcaldia_*`).
- Profiling: null/out-of-bbox coordinates, offence year distribution, `HECHO NO DELICTIVO`, exact duplicates, unknown hours, categories.
- The filters of §3.1 (offence year 2024, drop non-criminal events) justified with counts.
- Point-in-polygon test with `spatial.assign_ageb` and a **funnel table**: rows read → offence not in 2024 → non-criminal → invalid coordinates → duplicates → outside urban AGEBs → loaded.
- The search log above + instructor reply.

**Phase 2 (D2)** — `src/transform/crime.py`
- `run()`: read `data/raw/crime_fgj_2024/crime_fgj_2024.csv` (dtype `str`; the downloader stores the published `carpetasFGJ_2024.csv` under the source key) → `source_incident_id` (§3.1) → filters (§3.1) → harmonise crime types to English (`crime_type` from `delito`, `crime_category` from `categoria_delito`: e.g. `Property` / `Violent` / `Sexual` / `Other`, documented in a mapping table) → `incident_date` from `fecha_hecho`, `incident_hour` from `hora_hecho` (−1 if unknown) → `points_from_latlon` → `assign_ageb` → `crime.parquet` (contract §3.2). Remove exact duplicates (same `delito`, date, hour, coordinates) and document how many.
- Data dictionary for `dim_crime_type`, `fact_crime_incident`.

**Phase 3 (D3)** — `notebooks/33_crime_patterns_bivariate.ipynb`
- Incidents by type and time (month, weekday, time band) from `dw.v_crime_by_type_time` — charts to `outputs/figures/`.
- **Bivariate Moran's I** (`esda.Moran_BV`, 999 permutations) for ≥ 1 pair, e.g. business density vs crime rate, using Nora's `build_weights`; bivariate LISA map optional. Explain the neighbourhood rule and that association ≠ causation.
- Report section 6 "Limitations and interpretation cautions" (`report/sections/6_limitations.md`): temporal mismatch (Census 2020, DENUE 2025–26, crime 2024), reported crime ≠ all crime, suppression, MAUP, scope change from Mérida.

**AI prompt (Phase 1–2):**
```
You are helping Valeria Hernández in the repository merida-urban-intelligence (now a Mexico City data warehouse).
Read docs/team/TEAM_PLAN.md (sections 0, 3 and 4.5), sql/01_schema.sql (dim_crime_type, fact_crime_incident),
src/config.py and src/transform/spatial.py.
Phase 1: notebooks/13_profile_crime.ipynb profiling data/raw/crime_fgj_2024/crime_fgj_2024.csv (dtype=str):
explain fecha_inicio vs fecha_hecho, profile coordinates, offence years, categoria_delito, HECHO NO DELICTIVO,
duplicates and unknown hours; apply the filters of TEAM_PLAN §3.1 with counts; run spatial.assign_ageb and end
with a funnel table. Include the search log and the instructor reply from §4.5 as markdown.
Phase 2: src/transform/crime.py with run() that applies the same rules, builds source_incident_id as
'fgj2024-<row number>', harmonises crime types to English with a crime_category (mapping table in the code),
parses incident_date and incident_hour (-1 when unknown), removes exact duplicates (report how many), builds
points with spatial.points_from_latlon, assigns AGEBs with spatial.assign_ageb and writes
data/processed/crime.parquet with EXACTLY the contract columns. Add asserts for the win conditions in
TEAM_PLAN §4.5. Do not modify files owned by others. Commit in small steps.
```

**Win conditions**
- [ ] Search log, instructor reply and selected source (URL, date, licence, grain) recorded in the notebook.
- [ ] `crime.parquet` follows the contract; ≈ 112 k rows; `source_incident_id` unique; every `cvegeo` in `ageb.parquet`; `incident_hour` within −1…23; all `incident_date` in 2024; CRS 6372.
- [ ] Notebook reports the funnel table (rows read → … → loaded).
- [ ] Bivariate Moran: I, pseudo p-value, permutations, weights used, interpretation without causal claims.
- [ ] Section 6 of the report delivered to Gustavo by D3 18:00.

**Suggested commits:** `analysis(crime): source search log and instructor decision` · `analysis(crime): profiling and point-in-polygon test` · `feat(crime): crime type mapping` · `feat(crime): crime transform` · `docs(crime): data dictionary` · `analysis(crime): incidents by type and time` · `analysis(spatial): bivariate Moran` · `docs(report): limitations section`.

**README/report:** README §2 public-safety row, §4 crime decisions, §10 cautions; report section 6.

---

### 4.6 Gustavo Fuentes — Data quality, KPI queries & findings · report lead

Joined on D1 evening. Your work is cross-cutting: you check that the pieces fit, prove that every KPI can be queried from the warehouse, run the local spatial analysis and turn everyone's results into the report. **Do D0 setup first (§1) and accept the repository invitation** (sent to `Audileleach`).

**Phase 1 (D2 morning)** — source inventory and data-quality register
- `docs/data_sources.md`:
  - **Inventory**, one row per source: publisher, dataset name, URL, licence, version/date, original grain, CRS, temporal coverage, key variables, SHA-256 (from `data/raw/manifest.json`).
  - **Scope-change record**: why Mérida was dropped (link to the search log in §4.5) and the instructor's reply, in 5–8 lines.
  - **Data-quality register**: issue · source · evidence (count) · impact · decision · owner. Seed it with the issues already known: 2 census AGEBs without polygon (7,108 residents), INEGI `*`/`N/D` suppression, DENUE points outside urban AGEBs (1,501), crime rows without coordinates, crime file organised by opening date (11 % earlier offences), exact duplicates in the crime file, no incident id in the FGJ file, expired TLS certificate on the FGJ host (5 Oct), temporal mismatch between sources. Ask each owner for their counts and keep it updated until D3.
- `notebooks/14_integration_check.ipynb` (reads `data/raw` — allowed in Phase 1): cross-source evidence only, not a repeat of the profiling notebooks:
  - `CVEGEO` compatibility census ↔ polygons (2,431 matched, 2 orphans) and DENUE reported codes ↔ polygons;
  - temporal coverage chart of the three sources (Census 2020 reference date, DENUE `fecha_alta`, crime `fecha_hecho`);
  - one summary table "records per source → inside urban AGEBs", taking counts from §3.5.

**Phase 2 (D2)** — contract tests and KPI queries
- `tests/test_processed_contract.py` (pytest): one test per file in §3.2 checking exact column names and order, dtypes, CRS 6372, geometry type, key uniqueness, every `cvegeo` present in `ageb.parquet`, `incident_hour` in −1…23, suppressed census values are `NULL` (no 0 where the raw value was `*`), row counts within the §3.5 tolerances. Tests **skip** (not fail) when a file does not exist yet, so they can be merged early. Run with `pytest tests/` after `python -m src.pipeline transform`.
- `sql/05_kpi_queries.sql`: read-only analytical queries on the `dw` views proving that **every KPI in the brief** can be computed from the warehouse — one commented query per KPI (14), plus: top-10 AGEBs per main KPI, KPIs **aggregated by alcaldía** (sums first, then ratios — never the mean of AGEB ratios), incidents by type × time band, crime per 100 businesses by dominant sector. Each query starts with a comment saying which KPI/question it answers. Run it with `docker exec -i merida_dw psql -U merida -d merida_dw < sql/05_kpi_queries.sql` and paste a sample of the output into the PR.
- Review at least 2 teammates' PRs against the contract (comment; do not edit their files).

**Phase 3 (D3)** — local spatial analysis and area comparison
- `notebooks/34_lisa_hotspots.ipynb` — builds on Nora's LISA, does not repeat it. Data from `load_kpis()` only; clusters from Nora's `build_weights` + `local_clusters` on the same sample and indicators:
  - **where the clusters are**: count and share of HH / LL / HL / LH AGEBs per alcaldía and indicator (table + one map with alcaldía boundaries to `outputs/maps/`);
  - **do hot spots coincide?** cross-tab of business-density vs crime-rate cluster labels (e.g. how many business HH AGEBs are also crime HH), with the list of overlapping AGEBs;
  - **robustness**: share of AGEBs that keep the same label with Queen vs KNN-6 weights;
  - interpretation without causal language, plus the multiple-testing caveat (pseudo p-values on 2,348 units).
- `notebooks/35_alcaldia_comparison.ipynb`: compare the 16 alcaldías — population, densities, businesses per 1k, dominant sector, crime rate, crimes per 100 businesses (aggregated correctly: sums then ratios), a ranking table and one small-multiples or bar figure to `outputs/figures/`; centre (Cuauhtémoc, Benito Juárez, Miguel Hidalgo) vs periphery.
- README §7: hot-spot overlap and area comparison (next to Nora's LISA subsection).

**Report lead (D3)**
- Collect every `report/sections/*.md`, write `report/sections/5_findings.md` (main findings: 1–2 from each member + your hot-spot and alcaldía results, each backed by a map/figure).
- Assemble `report/technical_report.pdf` (4–6 pages, all six sections, ≥ 3 maps/figures, figure numbers consistent). Check that it does **not** repeat the README. Deadlines for teammates' sections: D3 18:00.

**AI prompt (Phase 1–2):**
```
You are helping Gustavo Fuentes in the repository merida-urban-intelligence (now a Mexico City geospatial data
warehouse). First read README.md, docs/team/TEAM_PLAN.md (sections 0, 3 and 4.6), src/config.py,
data/raw/manifest.json, sql/01_schema.sql and sql/03_views.sql.
1. docs/data_sources.md: source inventory table (publisher, name, URL, licence, version/date, original grain, CRS,
   temporal coverage, key variables, SHA-256 from the manifest), a short scope-change record (Mérida -> CDMX,
   instructor reply in TEAM_PLAN §4.5) and a data-quality register (issue, source, evidence count, impact, decision,
   owner) seeded with the issues listed in TEAM_PLAN §4.6. Do not invent numbers: use §3.5 or compute them.
2. notebooks/14_integration_check.ipynb: CVEGEO compatibility census vs polygons vs DENUE reported codes, temporal
   coverage of the three sources, summary table records -> inside urban AGEBs.
3. tests/test_processed_contract.py: pytest checks of every data/processed file against TEAM_PLAN §3.2 and §3.5;
   skip when a file is missing.
4. sql/05_kpi_queries.sql: read-only queries on dw views, one per KPI of the brief (README §6), plus top-10 AGEBs,
   KPIs by alcaldía (sum numerators and denominators, then divide with NULLIF), incidents by type x time band.
Do not modify files owned by other members (TEAM_PLAN §4). Commit in small steps.
```

**AI prompt (Phase 3):**
```
Continue as Gustavo's assistant. Read TEAM_PLAN §3.1 (spatial weights), src/analysis/data.py and
src/analysis/spatial_weights.py and Nora's notebooks/32_global_moran_lisa.ipynb. notebooks/34_lisa_hotspots.ipynb:
load_kpis() only; reuse build_weights and local_clusters (do not reimplement LISA) on the same sample and indicators
as Nora; tables of cluster counts/shares per alcaldía, a cross-tab of business-density vs crime-rate cluster labels
with the overlapping AGEBs, and the share of AGEBs whose label is stable between Queen and KNN-6; one map with
alcaldía boundaries to outputs/maps/; interpretation without causal language. notebooks/35_alcaldia_comparison.ipynb: aggregate v_kpi_ageb by mun_name
(sums then ratios), ranking table and one figure to outputs/figures/.
```

**Win conditions**
- [ ] `docs/data_sources.md` lists all 4 sources with licence and SHA-256; data-quality register has ≥ 8 issues with counts.
- [ ] `pytest tests/` passes (or skips) on a clean checkout and passes after `python -m src.pipeline transform`.
- [ ] `sql/05_kpi_queries.sql` runs without errors on the populated DW and covers all 14 KPIs of README §6.
- [ ] Hot-spot notebook: clusters per alcaldía, business × crime overlap table, Queen vs KNN stability, one map saved; reuses Nora's functions.
- [ ] Alcaldía comparison: 16 rows, ratios computed from sums, one figure saved.
- [ ] `report/technical_report.pdf` 4–6 pages, ≥ 3 maps/figures, all six required sections.

**Suggested commits:** `docs(repo): source inventory` · `docs(repo): data-quality register` · `analysis(geo): cross-source integration check` · `test(dw): processed-file contract tests` · `sql(kpi): KPI demonstration queries` · `sql(kpi): KPIs by alcaldía` · `analysis(spatial): LISA hot spots by alcaldía` · `analysis(spatial): business and crime hot-spot overlap` · `analysis(kpi): alcaldía comparison` · `docs(report): findings section` · `docs(report): technical report PDF`.

**README/report:** README §7 hot-spot overlap + area comparison, §10 data-quality summary (from the register); report section 5 + assembly.

---

## 5. Report (4–6 pages PDF, do NOT repeat the README)

Each member writes their section as `report/sections/<n>_<topic>.md` (own commit); Gustavo assembles.

| Section | Owner | Content |
|---|---|---|
| 1. Problem and data sources | Julio | Why, which sources, temporal coverage of each |
| 2. Geographic integration strategy | Lorena | Unit choice, CRS, point-in-polygon results (kept/dropped %) |
| 3. Data Warehouse architecture | Jose | Diagram, grains, pipeline in one figure |
| 4. Key KPIs and spatial analysis | Nora | KPI table, Moran/LISA results |
| 5. Main findings (with maps) | Gustavo (each member sends 1–2 findings from their analysis) | Maps/figures + interpretation |
| 6. Limitations and cautions | Valeria | Temporal mismatch, suppression, MAUP, data origin, association ≠ causation |

## 6. Final checklist (Jose, before tagging v1.0)

- [ ] Fresh clone → README commands → full DW + validation passes.
- [ ] Every KPI in the brief has a column in `dw.v_kpi_ageb` or a view (Incidents by type and time → `v_crime_by_type_time`).
- [ ] Correlation (≥ 3), Global Moran (≥ 2), LISA, bivariate Moran (≥ 1), neighbourhood rule explained.
- [ ] Data dictionary complete, diagram present, maps/figures in `outputs/`.
- [ ] README: all `_TODO_` replaced; assumptions and cautions written.
- [ ] `git shortlog -sne main` shows all 6 members with linked accounts across D1–D3.
- [ ] Report PDF in `report/` and submitted.
