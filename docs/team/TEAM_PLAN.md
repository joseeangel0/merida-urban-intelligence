# Team plan — Mexico City Urban Intelligence

Everything each member needs: what to build, which files you own, the data contract your output must follow, a ready-to-paste AI prompt, and the **acceptance tests ("win conditions")** that prove your part is done.

| # | Member | GitHub | Role | Status & Owns |
|---|---|---|---|---|
| 1 | **Jose Pech** | `joseeangel0` | Repo lead · DW architect | **Active:** repo setup, `sql/01_schema.sql`, model diagram, `sql/03_views.sql`, `sql/04_validation.sql`, `src/analysis/data.py`, execute NB 32, finalize report sec. 4, README integration |
| 2 | **Julio de Aquino** | `pyrawn` | Demographic layer | **Inactive (D3):** Phase 1 profiling done (`11_profile_census.ipynb`). Transform completed by Gustavo (PR #19); correlation reassigned to Lorena; report sec. 1 to Valeria |
| 3 | **Nora Horta** | `strangelove-t` | Economic layer | **Inactive (D3):** Phase 1 profiling, `denue.py` transform, and `spatial_weights.py` merged. LISA notebook execution & report sec. 4 finalized by Jose |
| 4 | **Lorena Pérez** | `ldpl3012` | Geography & integration | **Active:** geographic-unit decision, `src/transform/geography.py`, `src/transform/spatial.py`, `src/load/load_staging.py`, `sql/02_load.sql`, `notebooks/30_kpi_maps.ipynb`, `notebooks/31_correlation.ipynb`, report sec. 2 |
| 5 | **Valeria Hernández** | `valnix140405` | Public-safety layer | **Active:** crime source record, `src/transform/crime.py`, `notebooks/33_crime_patterns_bivariate.ipynb`, report sec. 1 & 6 |
| 6 | **Gustavo Fuentes** | `Audileleach` | Data quality, KPI queries & findings · report lead | **Active:** census transform (PR #19), source inventory (`data_sources.md`), `14_integration_check.ipynb`, contract tests (`tests/`), `sql/05_kpi_queries.sql`, `notebooks/34_lisa_hotspots.ipynb`, `notebooks/35_alcaldia_comparison.ipynb`, report sec. 5 & assembly (`technical_report.pdf`) |

> 🔄 **Scope change — 5 Oct 2026 (D1 evening).** The instructor answered our crime-data request: *no simulated data; with municipal-level crime data the spatial analysis would have to stay at state level; for high granularity use hoyodecrimen.com, but working with Mexico City.* We therefore keep the **urban AGEB** design and move the study area from Mérida to **Mexico City (CDMX, 16 alcaldías)**. Every contract below has been updated (sources, reference values, paths `31 → 09`). The Mérida work already merged (Lorena's assessment, Jose's search log) stays as Phase 1 evidence of the data assessment. **Gustavo Fuentes joins the team** (§4.6) and takes report assembly from Valeria and builds the alcaldía-level and hot-spot analysis on top of Nora's LISA.
>
> ⚡ **Phase 3 Active Squad & Workload Rebalancing — 8 Oct 2026 (D3).** Nora and Julio have stepped back from active development. To finish on schedule, the remaining 4 active members (**Jose, Lorena, Valeria, Gustavo**) absorb all pending tasks and work in parallel without blocking dependencies:
> - **Lorena**: Completes `dim_geography` in `docs/data_dictionary.md`, `notebooks/30_kpi_maps.ipynb`, absorbs `notebooks/31_correlation.ipynb`, and writes report section 2.
> - **Valeria**: Shares FGJ crime file (`crime_fgj_2024.csv`), completes `notebooks/33_crime_patterns_bivariate.ipynb`, and absorbs report section 1.
> - **Gustavo**: Writes `docs/data_sources.md`, `notebooks/14_integration_check.ipynb`, `sql/05_kpi_queries.sql`, `notebooks/34_lisa_hotspots.ipynb`, `notebooks/35_alcaldia_comparison.ipynb`, report section 5, and assembles `report/technical_report.pdf`.
> - **Jose** (Lead): Runs and saves `notebooks/32_global_moran_lisa.ipynb` outputs, finalizes report section 4, integrates README §7, verifies clean clone, and tags `v1.0`.

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
- Staging loads every available processed Parquet file. If a transform has not produced its staging table yet, the load reports it and leaves that dependent dimension/fact empty; it always prints row counts for all warehouse tables.
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
| Crime rows (FGJ 2024 file) / offence in 2024 and not `HECHO NO DELICTIVO` / inside urban AGEBs | 138,630 / 119,666 / ≈ 112,285 (the ≈ 680 rows that repeat `delito`, date and hour have no coordinates, so dedup does not change this count) |
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

**Phase 3 (D3) — Active closeout & integration**
- `src/analysis/data.py` (`load_kpis`) — published and working with `dw.v_kpi_ageb`.
- Run and save outputs for `notebooks/32_global_moran_lisa.ipynb` (Nora's notebook, already written; run with `seed=42`, save cluster maps to `outputs/maps/`).
- Finalize `report/sections/4_kpis_spatial_analysis.md` with the Global Moran / LISA table from notebook 32.
- Report section 3 "Data Warehouse architecture" (`report/sections/3_dw_architecture.md`) — completed.
- README integration (§7 spatial analysis findings, §8 reproduction, §9 structure), clean clone test, tag `v1.0`.

**AI prompt (Phase 3 closeout):**
```
You are helping Jose Pech in the repository merida-urban-intelligence. Read README.md and docs/team/TEAM_PLAN.md §4.1.
Tasks:
1. Run notebooks/32_global_moran_lisa.ipynb so all cells have execution counts and figures, ensuring cluster maps are written to outputs/maps/.
2. In report/sections/4_kpis_spatial_analysis.md, finalize the brief summary table of Moran I values and LISA cluster counts.
3. In README.md §7, replace the _TODO_ with a concise summary of the spatial analysis findings.
4. Verify clean clone execution: python -m src.pipeline all && pytest tests/.
```

**Win conditions**
- [ ] A teammate can go from `git clone` to a populated DW with only the README commands.
- [ ] `python -m src.pipeline all` ends with the validation NOTICE and no exception.
- [ ] `SELECT count(*) FROM dw.v_kpi_ageb` = 2,431; `SELECT sum(pop_total) FROM dw.v_kpi_ageb` = 9,138,524.
- [ ] `notebooks/32_global_moran_lisa.ipynb` committed with outputs and maps saved to `outputs/maps/`.
- [ ] Report sections 3 and 4 completed.
- [ ] Tag `v1.0` created on a clean working tree.

**Suggested commits:** `analysis(spatial): execute global moran and lisa notebook` · `docs(report): finalize spatial kpis report section` · `docs(readme): spatial findings and release instructions` · `chore(repo): release tag v1.0`.

---

### 4.2 Julio de Aquino — Demographic layer (Inactive — contributions recorded)

**Phase 1 (D1) — Done ✅**
- Profiling merged in `notebooks/11_profile_census.ipynb` (PR #9).
- Census variable mapping table documented.

**Phase 2 (D2) — Done ✅ (Completed by Gustavo, PR #19)**
- `src/transform/census.py` implemented, writing `data/processed/census_ageb.parquet` (2,431 rows, Σ pop = 9,138,524).
- Data dictionary section for `dw.fact_census_ageb` filled in `docs/data_dictionary.md`.
- Unit tests merged in `tests/test_census.py` (37 tests passing).

**Phase 3 (D3) — Reassigned to Active Squad**
- `notebooks/31_correlation.ipynb`: Reassigned to **Lorena Pérez** (§4.4).
- Report section 1 "Problem and data sources": Reassigned to **Valeria Hernández** (§4.5).

---

### 4.3 Nora Horta — Economic layer (Inactive — contributions recorded)

**Phase 1 (D1) — Done ✅**
- Profiling merged in `notebooks/12_profile_denue.ipynb` (PR #7).

**Phase 2 (D2) — Done ✅**
- `src/transform/denue.py` implemented, writing `business.parquet` (461,231 rows) and `economic_activity.parquet` (PR #7).
- Data dictionary sections for `dim_economic_activity`, `dim_business_size`, `fact_business` completed.
- `src/analysis/spatial_weights.py` (`build_weights`, `local_clusters`) implemented and merged.

**Phase 3 (D3) — Reassigned to Active Squad**
- `notebooks/32_global_moran_lisa.ipynb`: Drafted; execution, cell outputs and map saving reassigned to **Jose Pech** (§4.1).
- Report section 4 "Key KPIs and spatial analysis": Drafted; final summary table reassigned to **Jose Pech** (§4.1).

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

**Phase 3 (D3) — Active deliverables**
- `docs/data_dictionary.md`: Complete the `## dim_geography` section (replaces `_TODO_`).
- `notebooks/30_kpi_maps.ipynb`: Choropleth maps (quantiles, `mapclassify`) of ≥ 6 KPIs across the three layers, from `load_kpis()`, saved in `outputs/maps/`. Small-multiples figure for the report.
- `notebooks/31_correlation.ipynb` *(absorbed from Julio)*: Read via `load_kpis()`, test ≥ 3 pairs (population density vs business density, crime rate vs businesses per 1k, PEA rate vs crime rate), justify Spearman vs Pearson, report $r$, p-value, $n$, sensitivity with/without `low_population`, save figures to `outputs/figures/`.
- Report section 2 "Geographic integration strategy" (`report/sections/2_geographic_integration.md`): candidate unit assessment (justifying urban AGEB), CRS EPSG:6372, and spatial join results (% retained/dropped).

**AI prompt (Phase 3):**
```
You are helping Lorena Pérez in the repository merida-urban-intelligence (Mexico City Urban Intelligence DW).
Read README.md, docs/team/TEAM_PLAN.md §4.4, and sql/01_schema.sql.
Tasks, one commit each on branch lorena/<task>:
1. docs/data_dictionary.md: fill "## dim_geography — _owner: Lorena_" completely. Document table grain (one row per urban AGEB in CDMX, 2,431 rows), PK geo_key, cvegeo (13 chars), cve_ent, cve_mun, mun_name (16 alcaldías), cve_loc, loc_name, cve_ageb, is_city_core (2,348 core), area_km2 (total 792.15 km2), and geom (MultiPolygon EPSG:6372).
2. notebooks/30_kpi_maps.ipynb: load data ONLY via `from src.analysis.data import load_kpis`. Generate choropleth maps for at least 6 KPIs: pop_density_km2, pea_rate, business_density_km2, retail_density_km2, crime_rate_per_1k, crimes_per_100_businesses using mapclassify quantiles (k=5). Save individual maps to outputs/maps/ and create a combined 2x3 small-multiples figure (outputs/figures/kpi_choropleths_summary.png).
3. notebooks/31_correlation.ipynb: load data via `load_kpis(city_core_only=True, exclude_low_population=True)`. Test >= 3 pairs (pop_density_km2 vs business_density_km2, crime_rate_per_1k vs businesses_per_1k, pea_rate vs crime_rate_per_1k). Check normality/outliers, compare Spearman vs Pearson, report sample size, coefficient, and p-value. Test sensitivity including the low-population AGEBs. Save scatter plots to outputs/figures/.
4. report/sections/2_geographic_integration.md: document unit comparison (municipality vs locality vs colonia vs hex grid vs urban AGEB), CRS selection (EPSG:6372), and spatial join results (DENUE: 99.7% captured; FGJ 2024: 93.8% captured).
```

**Win conditions**
- [ ] `docs/data_dictionary.md`: `dim_geography` section fully filled (no `_TODO_`).
- [ ] `notebooks/30_kpi_maps.ipynb`: Executed with cell outputs. ≥ 6 KPI maps with legend, title, units and scale/basemap.
- [ ] `notebooks/31_correlation.ipynb`: Executed with cell outputs. ≥ 3 relationships, Spearman justified, sensitivity evaluated, figures saved.
- [ ] Report section 2 delivered to `report/sections/2_geographic_integration.md`.

**Suggested commits:** `docs(geo): document dim_geography in data dictionary` · `analysis(maps): kpi choropleth mapping` · `analysis(spatial): demographic and economic correlations` · `docs(report): geographic integration section`.

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
- `run()`: read `data/raw/crime_fgj_2024/crime_fgj_2024.csv` (dtype `str`; the downloader stores the published `carpetasFGJ_2024.csv` under the source key) → `source_incident_id` (§3.1) → filters (§3.1) → harmonise crime types to English (`crime_type` from `delito`, `crime_category` from the accent-normalised `delito`, one category per `crime_type` (`categoria_delito` is `DELITO DE BAJO IMPACTO` for 87 % of rows): e.g. `Property` / `Violent` / `Sexual` / `Other`, documented in a mapping table) → `incident_date` from `fecha_hecho`, `incident_hour` from `hora_hecho` (−1 if unknown) → `points_from_latlon` → `assign_ageb` → `crime.parquet` (contract §3.2). Remove exact duplicates among rows with valid coordinates (same `delito`, date, hour, coordinates; pandas treats empty coordinates as equal, so dedup after the coordinate filter) and document how many.
- Data dictionary for `dim_crime_type`, `fact_crime_incident`.

**Phase 3 (D3) — Active deliverables**
- Share/distribute `crime_fgj_2024.csv` (SHA-256 `2ac3f171...`) so teammates can run full pipeline loads locally.
- `notebooks/33_crime_patterns_bivariate.ipynb`:
  - Temporal patterns of crime (by month, weekday, and time band) from `load_view('v_crime_by_type_time')` — charts to `outputs/figures/`.
  - **Bivariate Moran's I** (`esda.moran.Moran_BV`, 999 permutations, seed 42) for business density vs crime rate using `load_kpis()` and `build_weights()`; bivariate Moran scatterplot and cluster interpretation (association ≠ causation).
- Report section 1 "Problem and data sources" (`report/sections/1_problem_data_sources.md` — *absorbed from Julio*): problem statement, 4 datasets, temporal coverage.
- Report section 6 "Limitations and interpretation cautions" (`report/sections/6_limitations.md`): completed and merged ✅.

**AI prompt (Phase 3):**
```
You are helping Valeria Hernández in the repository merida-urban-intelligence (Mexico City Urban Intelligence DW).
Read README.md, docs/team/TEAM_PLAN.md §4.5, and sql/01_schema.sql.
Tasks, one commit each on branch valeria/<task>:
1. notebooks/33_crime_patterns_bivariate.ipynb:
   - Part 1: Temporal analysis. Load view dw.v_crime_by_type_time with `from src.analysis.data import load_view; df = load_view('v_crime_by_type_time')`. Plot monthly trends, day-of-week, and time bands (Morning, Afternoon, Evening, Night) by crime category. Save figure to outputs/figures/crime_temporal_patterns.png.
   - Part 2: Bivariate spatial association. Load data via `from src.analysis.data import load_kpis; gdf = load_kpis(city_core_only=True, exclude_low_population=True)`. Build Queen weights with `from src.analysis.spatial_weights import build_weights; w = build_weights(gdf, kind="queen")`. Calculate Bivariate Moran's I using `from esda.moran import Moran_BV; bv = Moran_BV(gdf['business_density_km2'], gdf['crime_rate_per_1k'], w, permutations=999, seed=42)`. Plot Moran scatterplot, report I, p-value, and z-score. Explain neighborhood rule and that association != causation. Save figure to outputs/figures/bivariate_moran_business_crime.png.
2. report/sections/1_problem_data_sources.md: write report Section 1 "Problem and data sources". Explain the urban analytical problem, the 4 selected official sources (Census 2020, DENUE 05/2026, Marco Geo 2020, FGJ Crime 2024), their grains, and temporal coverage mismatch.
```

**Win conditions**
- [ ] `notebooks/33_crime_patterns_bivariate.ipynb`: Executed with cell outputs. Temporal charts and Bivariate Moran scatterplot saved to `outputs/figures/`.
- [ ] Bivariate Moran: $I$, pseudo p-value, permutations (999), weights documented; explicit disclaimer that association $\neq$ causality.
- [ ] Report section 1 written to `report/sections/1_problem_data_sources.md`.
- [ ] Section 6 of the report merged ✅.

**Suggested commits:** `analysis(crime): temporal crime patterns and bivariate moran` · `docs(report): problem and data sources section`.

**README/report:** README §2 public-safety row, §4 crime decisions, §10 cautions; report sections 1 and 6.

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
| 1. Problem and data sources | Valeria *(reassigned from Julio)* | Why, which sources, temporal coverage of each |
| 2. Geographic integration strategy | Lorena | Unit choice, CRS, point-in-polygon results (kept/dropped %) |
| 3. Data Warehouse architecture | Jose | Diagram, grains, pipeline in one figure (completed ✅) |
| 4. Key KPIs and spatial analysis | Jose *(finalizing Nora's draft)* | KPI table, Moran/LISA results |
| 5. Main findings (with maps) | Gustavo (each member sends 1–2 findings from their analysis) | Maps/figures + interpretation |
| 6. Limitations and cautions | Valeria | Temporal mismatch, suppression, MAUP, data origin, association ≠ causation (completed ✅) |

## 6. Final checklist (Jose, before tagging v1.0)

- [ ] Fresh clone → README commands → full DW + validation passes.
- [ ] Every KPI in the brief has a column in `dw.v_kpi_ageb` or a view (Incidents by type and time → `v_crime_by_type_time`).
- [ ] Correlation (≥ 3), Global Moran (≥ 2), LISA, bivariate Moran (≥ 1), neighbourhood rule explained.
- [ ] Data dictionary complete, diagram present, maps/figures in `outputs/`.
- [ ] README: all `_TODO_` replaced; assumptions and cautions written.
- [ ] `git shortlog -sne main` shows all 6 members with linked accounts across D1–D3.
- [ ] Report PDF in `report/` and submitted.
