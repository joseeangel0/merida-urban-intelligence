# Team plan — Mérida Urban Intelligence

Everything each member needs: what to build, which files you own, the data contract your output must follow, a ready-to-paste AI prompt, and the **acceptance tests ("win conditions")** that prove your part is done.

| # | Member | GitHub | Role | Owns |
|---|---|---|---|---|
| 1 | **Jose Pech** | `joseeangel0` | Repo lead · DW architect | repo setup, `sql/01_schema.sql`, model diagram, `sql/03_views.sql`, `sql/04_validation.sql`, `src/analysis/data.py`, README integration |
| 2 | **Julio de Aquino** | `pyrawn` | Demographic layer | Census profiling, `src/transform/census.py`, correlation analysis |
| 3 | **Nora Horta** | `strangelove-t` | Economic layer | DENUE profiling, `src/transform/denue.py`, spatial weights, Global Moran + LISA |
| 4 | **Lorena Pérez** | `ldpl3012` | Geography & integration | geographic-unit decision, `src/transform/geography.py`, `src/transform/spatial.py`, `src/load/load_staging.py`, `sql/02_load.sql`, KPI maps |
| 5 | **Valeria Hernández** | `valnix140405` | Public-safety layer · report lead | crime dataset search, `src/transform/crime.py`, crime temporal analysis, bivariate Moran, report assembly |

---

## 0. Golden rules (read before anything else)

1. **Your commits, your account.** Configure `git config --global user.email` with the email registered on your GitHub account. After your first push check that your avatar appears next to your commit. Unlinked commits = no collaboration credit for you.
2. **Commit in every phase.** Minimum: 2 commits in Phase 1, 2 in Phase 2, 2 in Phase 3, 1 in documentation/report. Small commits, clear messages (`feat(census): ...`). No bulk uploads.
3. **Branch → PR → someone else merges** ("Create a merge commit", never squash). See [`CONTRIBUTING.md`](../../CONTRIBUTING.md).
4. **Only edit the files you own.** If you need a change in someone else's file, ask them (or open a PR and tag them). This avoids merge conflicts with 5 AIs writing code in parallel.
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
python -m src.pipeline download schema                    # downloads INEGI files (~70 MB) and creates the empty DW
```

✅ Setup is done when `docker exec merida_dw psql -U merida -d merida_dw -c "\dt dw.*"` lists 10 tables.

Recommended AI setup: open the repo folder in Claude Code (or your AI of choice with file access) so it can read the code. Every prompt below starts by asking the AI to read this plan.

## 2. Timeline

| Day | Date | Phase | Goal at end of day |
|---|---|---|---|
| D0 | Sun 4 Oct | Setup | Repo, schema and plan published (Jose). Everyone cloned and ran setup. **Valeria starts the crime-data search tonight.** |
| D1 | Mon 5 Oct | **Phase 1 — Data & geography** | Profiling notebooks merged. Lorena: `geography.py` + `spatial.py` merged **by 14:00** (others depend on them). Valeria: crime dataset decided **by 14:00**. |
| D2 | Tue 6 Oct | **Phase 2 — ETL & DW** | All transforms, staging, `02_load.sql`, views and validation merged; `python -m src.pipeline all` builds the full DW. |
| D3 | Wed 7 Oct | **Phase 3 — Analytics + docs** | Maps, correlation, Moran, LISA, bivariate merged. README sections and report sections written. **Code freeze 22:00.** |
| — | Delivery | Final | Jose tags `v1.0`, Valeria uploads the PDF report. |

Dependency chain (do not block others): `geography.py` → `spatial.py` → (`denue.py`, `crime.py`) → `load_staging.py` → `02_load.sql` → `03_views.sql` → analysis notebooks.
If you are blocked, write your code against the contract and test with a temporary stub — do not wait.

## 3. Decisions already taken and data contract

### 3.1 Decisions

| Topic | Decision | Reason / evidence (from profiling on D0) |
|---|---|---|
| Unit of analysis | **Urban AGEB** of the municipality of Mérida (31050) | Census 2020 publishes indicators per urban AGEB, and the INEGI 2020 polygons (`31a.shp`) share the same `CVEGEO`: **526/526 match, 0 invalid geometries**. Lorena documents the alternatives. |
| Scope | 526 urban AGEBs: 483 in Mérida city (`cve_loc='0001'`) + 43 in 5 urban comisarías | Rural areas have no AGEB-level census data. |
| CRS | Store everything in **EPSG:6372** (metres); lat/lon inputs are EPSG:4326 | The INEGI polygons are already in ITRF2008 LCC (= EPSG:6372); areas in km² are directly comparable. |
| Point → polygon | `within` predicate; points outside any urban AGEB are **dropped and counted** | DENUE: 99.6 % of Mérida establishments fall inside an urban AGEB. |
| Census suppression | `*` and `N/D` → `NULL`, never 0; count them in `n_suppressed_fields` | INEGI confidentiality rule. |
| PEA rate base | `pea / pop_12_plus` | PEA is defined for population aged 12+. |
| Retail | SCIAN sector **46** | "Comercio al por menor". |
| Services | SCIAN sectors **51, 52, 53, 54, 55, 56, 61, 62, 71, 72, 81** | Private services (93 = government, excluded). |
| Small populations | Flag `low_population = pop_total < 100` (32 AGEBs, 6 with 0 people); exclude them from rate-based statistics | Per-capita rates explode with tiny denominators. |
| Spatial weights | **Queen contiguity**, row-standardised, on the 483 city-core AGEBs; the 1 island attached to its nearest neighbour. Sensitivity check: **KNN k=6** on the same AGEBs | Queen on all 526 gives 8 disconnected components (comisarías are separate towns). |
| Significance | 999 permutations, α = 0.05 | |

### 3.2 Files in `data/processed/` (output of `src/transform/*`)

All GeoParquet files use **EPSG:6372** and the geometry column is named `geometry`.

| File | Owner | Rows (expected) | Columns (exact names) |
|---|---|---|---|
| `ageb.parquet` | Lorena | 526 | `cvegeo` (str, 13), `cve_ent`, `cve_mun`, `cve_loc`, `cve_ageb`, `mun_name`, `loc_name`, `is_city_core` (bool), `area_km2` (float), `geometry` (MultiPolygon) |
| `census_ageb.parquet` | Julio | 526 | `cvegeo` + every measure column of `dw.fact_census_ageb` with the same names (`pop_total` … `n_suppressed_fields`) — no geometry |
| `economic_activity.parquet` | Nora | ≈ 900 | `scian_code` (str, 6), `activity_name`, `subsector_code` (str, 3), `sector_code` (`'46'`, `'31-33'`, `'48-49'`, …), `sector_name` (English), `activity_group` (`Retail` / `Services` / `Other`) |
| `business.parquet` | Nora | ≈ 56,667 | `denue_id` (int64), `clee`, `establishment_name`, `scian_code`, `per_ocu_label` (exact DENUE text), `alta_date` (date, 1st of month, nullable), `cvegeo` (from spatial join), `cvegeo_reported` (from DENUE columns), `geometry` (Point) |
| `crime.parquet` | Valeria | depends on source | `source_incident_id` (str), `crime_type` (English, harmonised), `crime_type_raw`, `crime_category` (`Property` / `Violent` / `Other` …), `incident_date` (date, nullable), `incident_hour` (int −1…23, −1 = unknown), `cvegeo`, `geometry` (Point) |

Each transform module exposes `run()` and is called by `python -m src.pipeline transform`.

### 3.3 Shared spatial API — `src/transform/spatial.py` (Lorena)

```python
def load_ageb() -> gpd.GeoDataFrame: ...
    # reads data/processed/ageb.parquet

def points_from_latlon(df: pd.DataFrame, lat_col: str, lon_col: str) -> gpd.GeoDataFrame: ...
    # coerces to float, drops null/zero/out-of-Yucatán-bbox coordinates (prints how many),
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

  ✅ **Done (Jose, D0):** views, `04_validation.sql` and `load_kpis()` are implemented and were tested end-to-end with the real INEGI data. Heads-up for analysts: per-capita KPIs have extreme outliers in AGEBs with few residents (e.g. `businesses_per_1k` up to ≈ 13,900 in the historic centre), so prefer Spearman and quantile classification, and keep `exclude_low_population=True`.
- `src/analysis/data.py` (Jose): `load_kpis(city_core_only=True, exclude_low_population=True) -> GeoDataFrame` reading `dw.v_kpi_ageb` with `gpd.read_postgis`. **All Phase 3 notebooks use this function.**

### 3.5 Reference values (computed on D0 — use them in your tests)

| Check | Expected |
|---|---|
| Urban AGEB polygons in Mérida | **526** (483 city core), all valid, total area **259.86 km²** |
| Census AGEB rows (`MZA='000'`, `AGEB!='0000'`, `MUN='050'`) | **526**, Σ`POBTOT` = **957,399** (municipality total 995,129 → urban AGEBs cover 96.2 %) |
| Σ`PEA` (non-suppressed) / Σ`P_12YMAS` | 508,151 / 804,569 |
| AGEBs with `pop_total < 100` / `= 0` | 32 / 6 |
| DENUE rows Yucatán / `cve_mun='050'` | 146,384 / 56,909, 0 duplicated `id` |
| DENUE points (whole state) inside Mérida urban AGEBs | **56,667** (56,664 coded as Mérida + 3 coded as other municipalities) |
| Agreement spatial-join AGEB vs DENUE's own `cve_loc+ageb` | **99.8 %** |
| Queen weights, city core | 483 units, 3 components, 1 island, mean 5.4 neighbours |

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
data warehouse for Mérida, Yucatán). First read README.md, docs/team/TEAM_PLAN.md (sections 0, 3 and 4.1),
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
   has an orphan key; v_kpi_ageb has != 526 rows; sum(pop_total) != 957399; any KPI column is entirely NULL.
   End with RAISE NOTICE summarising the counts.
4. src/analysis/data.py: load_kpis(city_core_only=True, exclude_low_population=True) using
   geopandas.read_postgis and src.db.get_engine().
Do not edit files owned by other members (see TEAM_PLAN §4). Run `python -m src.pipeline all` before finishing.
```

**Win conditions**
- [ ] A teammate can go from `git clone` to a populated DW with only the README commands.
- [ ] `python -m src.pipeline all` ends with the validation NOTICE and no exception.
- [ ] `SELECT count(*) FROM dw.v_kpi_ageb` = 526; `SELECT sum(pop_total) FROM dw.v_kpi_ageb` = 957,399.
- [ ] Diagram shows every table, PK/FK and grain.
- [ ] Each of the 5 members has ≥ 6 linked commits on `main` spread across D1–D3 (`git shortlog -sne main`).

**Suggested commits:** `chore(repo): project scaffold…` · `sql(dw): star schema…` · `docs(dw): dimensional model diagram` · `sql(kpi): KPI views` · `test(dw): validation queries` · `feat(analysis): load_kpis helper` · `docs(readme): DW model and reproduction`.

---

### 4.2 Julio de Aquino — Demographic layer

**Phase 1 (D1)** — `notebooks/11_profile_census.ipynb`
- Load `data/raw/census_ageb_2020/.../conjunto_de_datos_ageb_urbana_31_cpv2020.csv` (read every column as `str`).
- Explain the file structure: block rows vs AGEB total rows (`MZA='000'`) vs locality/municipality totals (`AGEB='0000'`).
- Filter Mérida AGEB rows, profile the KPI variables (missing, `*`, `N/D`, zeros, distributions), compare Σ AGEB population with the municipality total.
- Write the **variable list** required by the demographic KPIs (variable → KPI → unit).

**Phase 2 (D2)** — `src/transform/census.py`
- `run()`: filter → build `cvegeo = '31' + '050' + LOC + AGEB` → rename to the `dw.fact_census_ageb` column names → `*`/`N/D` → NULL → numeric types → `n_suppressed_fields` → write `data/processed/census_ageb.parquet`.
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
data/raw/census_ageb_2020 (read as dtype=str). Explain the row hierarchy (block, AGEB total MZA='000',
locality/municipality totals), keep Mérida (MUN='050') AGEB rows, quantify '*' and 'N/D' per KPI variable,
show distributions, compare the AGEB population sum with the municipality total, and end with a markdown
table "source variable -> KPI -> unit". Expected: 526 AGEB rows, sum POBTOT = 957,399.
Phase 2: create src/transform/census.py with run() that writes data/processed/census_ageb.parquet with
column cvegeo (13 chars) plus EXACTLY the measure columns of dw.fact_census_ageb (same names), suppressed
values as NULL (never 0), nullable integer dtypes (Int64), and n_suppressed_fields. Add asserts for the
win conditions in TEAM_PLAN §4.2. Do not modify files owned by other members. Commit in small steps.
```

**Win conditions**
- [ ] `census_ageb.parquet`: 526 rows, `cvegeo` unique, all 13 chars, all present in `ageb.parquet`.
- [ ] Σ `pop_total` = 957,399; no `pop_total` NULL; suppressed values are NULL, not 0.
- [ ] Σ `pea` = 508,151 and Σ `pop_12_plus` = 804,569.
- [ ] Notebook states why AGEB rows ≠ municipal total (rural population 37,730 not in urban AGEBs).
- [ ] Correlation notebook: ≥ 3 relationships, method justified, n reported, figures saved, interpretation without causal language.

**Suggested commits:** `analysis(census): profiling notebook` · `docs(census): KPI variable list` · `feat(census): AGEB census transform` · `docs(census): data dictionary` · `analysis(spatial): correlation analysis` · `docs(report): problem and data sources section`.

**README/report:** README §2 demographic row + §4 census decisions; report section 1 "Problem and data sources".

---

### 4.3 Nora Horta — Economic layer

**Phase 1 (D1)** — `notebooks/12_profile_denue.ipynb`
- Load `data/raw/denue_31/conjunto_de_datos/denue_inegi_31_.csv` (**`encoding="latin-1"`**, dtype `str`).
- Profile: coordinates (nulls, ranges), duplicated `id`, `codigo_act` (SCIAN) by sector, `per_ocu` bands, `fecha_alta` (snapshot date vs. registration date).
- Define the SCIAN → sector → `activity_group` mapping (retail = 46; services = 51–56, 61, 62, 71, 72, 81). Sector names in English, include combined sectors 31-33 and 48-49.

**Phase 2 (D2)** — `src/transform/denue.py`
- `run()`: whole-state DENUE → `spatial.points_from_latlon` → `spatial.assign_ageb` (the **geometry** decides membership, not `cve_mun`) → `cvegeo_reported = '31' + cve_mun + cve_loc + ageb` → `alta_date` from `fecha_alta` (`YYYY-MM` → 1st of month) → write `business.parquet` and `economic_activity.parquet`.
- Data dictionary for `dim_economic_activity`, `dim_business_size`, `fact_business`.

**Phase 3 (D3)** — `src/analysis/spatial_weights.py` + `notebooks/32_global_moran_lisa.ipynb`
- `build_weights(gdf, kind="queen" | "knn", k=6)`: row-standardised; for Queen attach islands to nearest neighbour (`libpysal.weights.attach_islands`). Shared with Valeria.
- Global Moran's I (esda, 999 permutations) for ≥ 2 indicators (suggested 4: business density, crime rate, population density, PEA rate), Queen vs KNN-6 table, Moran scatterplots.
- LISA for ≥ 2 indicators: cluster maps (HH, LL, HL, LH, not significant) to `outputs/maps/`, list of significant AGEBs.

**AI prompt (Phase 1–2):**
```
You are helping Nora Horta in the repository merida-urban-intelligence. First read README.md,
docs/team/TEAM_PLAN.md (sections 0, 3 and 4.3), sql/01_schema.sql (dim_economic_activity, dim_business_size,
fact_business) and src/transform/spatial.py.
Phase 1: notebooks/12_profile_denue.ipynb profiling INEGI DENUE Yucatán (data/raw/denue_31, encoding latin-1,
dtype str): coordinates, duplicated ids, SCIAN sectors (first 2 digits), per_ocu bands, fecha_alta; define the
SCIAN sector mapping with English sector names (combined sectors 31-33, 48-49) and activity_group
(Retail = 46; Services = 51,52,53,54,55,56,61,62,71,72,81; Other = rest), justified in markdown.
Phase 2: src/transform/denue.py with run() that uses spatial.points_from_latlon and spatial.assign_ageb on the
WHOLE state file, and writes data/processed/business.parquet and economic_activity.parquet with EXACTLY the
columns of TEAM_PLAN §3.2. Report kept/dropped counts and the agreement % between cvegeo and cvegeo_reported.
Add asserts for the win conditions in TEAM_PLAN §4.3. Do not modify files owned by others. Commit in small steps.
```

**Win conditions**
- [ ] `business.parquet`: 56,667 ± 5 rows, `denue_id` unique, every `cvegeo` in `ageb.parquet`, CRS 6372, no duplicates after the join.
- [ ] Agreement `cvegeo == cvegeo_reported` ≥ 99.5 % (reference 99.8 %), mismatches explained (boundary points).
- [ ] Every `scian_code` in `business.parquet` exists in `economic_activity.parquet`; every `per_ocu_label` matches `dw.dim_business_size`.
- [ ] Retail ≈ 19.4 k establishments; the sector table is in the notebook.
- [ ] Moran notebook: I, E[I], z, pseudo p-value per indicator, Queen vs KNN comparison, interpretation; LISA maps saved.

**Suggested commits:** `analysis(denue): profiling notebook` · `feat(denue): SCIAN sector mapping` · `feat(denue): DENUE transform with spatial join` · `docs(denue): data dictionary` · `feat(spatial): spatial weights builder` · `analysis(spatial): global Moran` · `analysis(spatial): LISA clusters` · `docs(report): KPIs and spatial analysis section`.

**README/report:** README §2 economic row, §4 DENUE decisions, §7 Moran/LISA; report section 4 "Key KPIs and spatial analysis".

---

### 4.4 Lorena Pérez — Geography & integration

**Phase 1 (D1, priority — others depend on you)** — `notebooks/10_geographic_assessment.ipynb`
- Candidate units: municipality, locality, AGEB, block, colonia (not an INEGI unit), hexagonal grid. For each: availability in the census, official polygons, shared identifier, resolution, privacy suppression → decision table → **justify urban AGEB**.
- Load `31a.shp` (AGEB), `31l.shp` (locality names), `31mun.shp` from `data/raw/marco_geo_2020/conjunto_de_datos/`: CRS, `is_valid`, identifiers, map of the 526 AGEBs (`outputs/maps/00_study_area.png`).
- Point-to-polygon proof of concept with a DENUE sample (and crime sample once Valeria has it).
- `src/transform/geography.py` → `ageb.parquet`; `src/transform/spatial.py` (API §3.3). **Merge both by D1 14:00.**

**Phase 2 (D2)**
- `src/load/load_staging.py`: processed files → `stg.*` (+ `stg.source` from the manifest).
- `sql/02_load.sql`: `stg.*` → `dw.*` (keys, `dim_date` via `generate_series`, `ST_Multi` for geometries, `TRUNCATE ... RESTART IDENTITY CASCADE` first so it is re-runnable).
- Data dictionary for `dim_geography`.

**Phase 3 (D3)** — `notebooks/30_kpi_maps.ipynb`
- Choropleth maps (quantiles, `mapclassify`) of ≥ 6 KPIs across the three layers, from `load_kpis()`, saved in `outputs/maps/`. Small-multiples figure for the report. Short comparison of areas (centre vs periphery, north vs south).

**AI prompt (Phase 1):**
```
You are helping Lorena Pérez in the repository merida-urban-intelligence. First read README.md,
docs/team/TEAM_PLAN.md (sections 0, 3 and 4.4), sql/01_schema.sql (dim_geography) and src/config.py.
1. notebooks/10_geographic_assessment.ipynb: compare candidate geographic units (municipality, locality, urban
   AGEB, block, colonia, hex grid) in a decision table (census availability, official polygons, shared key,
   resolution, confidentiality suppression) and justify urban AGEB. Load 31a.shp, 31l.shp and 31mun.shp from
   data/raw/marco_geo_2020/conjunto_de_datos with geopandas: report CRS, geometry validity, CVEGEO structure;
   keep CVE_MUN='050'; map the 526 AGEBs to outputs/maps/00_study_area.png; test point-in-polygon with a
   DENUE sample (data/raw/denue_31, latin-1).
2. src/transform/geography.py run() -> data/processed/ageb.parquet with EXACTLY the columns of TEAM_PLAN §3.2
   (EPSG:6372, MultiPolygon, area_km2 from the projected geometry, loc_name from 31l.shp).
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
- [ ] `ageb.parquet`: 526 rows, `cvegeo` unique, 483 `is_city_core`, all valid, EPSG:6372, Σ `area_km2` = 259.86 ± 0.1.
- [ ] `spatial.assign_ageb` on the DENUE state file keeps 56,667 points and returns no duplicates.
- [ ] After `stage load`: `dw.dim_geography` = 526, and every `dw` table count equals its `stg` source (facts) — validated by `04_validation.sql`.
- [ ] Re-running `python -m src.pipeline schema stage load` twice gives identical counts.
- [ ] ≥ 6 KPI maps with legend, title, units and north/scale or basemap.

**Suggested commits:** `analysis(geo): geographic unit assessment` · `feat(geo): AGEB polygons transform` · `feat(geo): shared point-in-polygon API` · `feat(dw): staging loader` · `sql(dw): load staging into star schema` · `docs(geo): data dictionary` · `analysis(maps): KPI choropleths` · `docs(report): geographic integration section`.

**README/report:** README §3 Geographic strategy (full), §4 spatial join; report section 2 "Geographic integration strategy".

---

### 4.5 Valeria Hernández — Public-safety layer · report lead

**Phase 1 (D0–D1) — 🚨 highest-risk task: find the crime dataset (deadline D1 14:00)**

**Search already done on D0 (Jose) — no public point-level crime dataset exists for Mérida.** Record this log in your notebook (it is evidence for the data assessment):

| Source checked | Result |
|---|---|
| SESNSP — [datos abiertos de incidencia delictiva](https://www.gob.mx/sesnsp/acciones-y-programas/datos-abiertos-de-incidencia-delictiva) | **Real but aggregated**: monthly counts per municipality and crime type, 2015–2025 (XLSX). No coordinates. **Download it anyway** (Mérida = `31050`): useful for calibration/validation in any scenario. |
| Fiscalía General del Estado de Yucatán (fge.yucatan.gob.mx) | No open data; only procedures and press releases. |
| Yucatán transparency open-data portal (transparencia.yucatan.gob.mx/datos_abiertos.php) | Only budget/expenditure datasets. |
| Mérida Geoportal (merida.gob.mx/geoportal) | Layers for COVID, jobs, bus stops, health, sports units — no public-safety layer. |
| CEISP Yucatán Data Observatory (ceisp.gob.mx/ObservatorioDatos, registration required) | Only 104 monthly PDF reports (2018–2026); on 4 Oct 2026 the server returned `null` download links for every file tested. No CSV/API/map. **The site looked broken, not empty: retry tomorrow at a different time** (log in at ceisp.gob.mx → Observatorio de datos → Seguridad Pública → Informes). If a PDF opens, check whether it has tables or maps **by colonia** for Mérida; if not, ask for the reports by phone (999) 689-15-30 or the site's contact form. |
| 911 open data | Only CDMX and Puebla publish geolocated calls. |
| Kaggle, GitHub, Zenodo, Figshare, academic repositories (UADY, CentroGeo) | Nothing for Mérida. |

Steps:
1. **Today:** write to the instructor (the brief allows "instructor-approved datasets"):
   > *Dear Professor, for the Unit 2 project we searched for a georeferenced crime dataset for Mérida (SESNSP, Fiscalía General del Estado, the state open-data portal, the Mérida Geoportal, the CEISP data observatory, 911 open data, Kaggle/GitHub/Zenodo). The only official data are SESNSP municipal monthly totals by crime type, without coordinates; the CEISP observatory only offers monthly PDF reports and its download links currently fail. Is there a dataset you recommend or can share? If not, would you accept either (a) incidents collected from local news and geocoded by us, or (b) simulated incident points calibrated to the official SESNSP monthly totals for Mérida, clearly labelled as simulated? Thank you.*
   Also ask classmates from other teams whether the instructor shared a crime file with them.
2. While waiting for the answer: download the SESNSP municipal file, filter Mérida, and write `crime.py` against the contract (§3.2) so only the input changes once the source is decided. If you find a source not in the table above, add it.
3. A dataset is acceptable if: inside Mérida, one row per incident with lat/lon, crime type, date (ideally hour), documented origin. Ideally ≥ 1,000 incidents.
4. Whatever the outcome, record the source (URL, date, licence, original grain) and add it to `src/config.py:SOURCES` and the manifest (tell Jose). **If the data are simulated, every map, table and the report must say so.** Never present simulated data as real.

Then `notebooks/13_profile_crime.ipynb`: profiling (coordinates, types, dates, duplicates, points outside Mérida) and a point-in-polygon test with `spatial.assign_ageb`.

**Phase 2 (D2)** — `src/transform/crime.py`
- `run()`: clean → harmonise crime types to English (`crime_type`, `crime_category`) → `incident_date`, `incident_hour` (−1 if unknown) → points → `assign_ageb` → `crime.parquet` (contract §3.2). Remove exact duplicates (same type, timestamp, coordinates) and document how many.
- Data dictionary for `dim_crime_type`, `fact_crime_incident`.

**Phase 3 (D3)** — `notebooks/33_crime_patterns_bivariate.ipynb`
- Incidents by type and time (month, weekday, time band) from `dw.v_crime_by_type_time` — charts to `outputs/figures/`.
- **Bivariate Moran's I** (`esda.Moran_BV`, 999 permutations) for ≥ 1 pair, e.g. business density vs crime rate, using Nora's `build_weights`; bivariate LISA map optional. Explain the neighbourhood rule and that association ≠ causation.

**Report lead (D3):** collect each member's section from `report/sections/*.md`, assemble the 4–6 page PDF (`report/technical_report.pdf`), make sure it does **not** repeat the README, and write section 5 "Limitations and interpretation cautions".

**AI prompt (Phase 1 search):**
```
You are helping Valeria Hernández in the repository merida-urban-intelligence. Read docs/team/TEAM_PLAN.md
(sections 0, 3 and 4.5). Search the web for a public dataset of georeferenced crime incidents (latitude/longitude,
crime type, date) for the municipality of Mérida, Yucatán, Mexico. The table in §4.5 lists sources already checked
(do not repeat them); look only for new ones. For each source give: URL, publisher, spatial granularity, temporal coverage, variables,
licence, and whether it meets the criteria in §4.5 step 3. Do not invent sources or URLs; if a link cannot be
verified say so. End with a ranked recommendation.
```

**AI prompt (Phase 2):**
```
Continue as Valeria's assistant. Read sql/01_schema.sql (dim_crime_type, fact_crime_incident),
TEAM_PLAN §3.2 and src/transform/spatial.py. Create src/transform/crime.py with run() that reads the chosen crime
dataset from data/raw/crime/, harmonises crime types to English with a crime_category, parses incident_date and
incident_hour (-1 when unknown), removes exact duplicates (report how many), builds points with
spatial.points_from_latlon, assigns AGEBs with spatial.assign_ageb and writes data/processed/crime.parquet with
EXACTLY the contract columns. Add asserts for the win conditions in TEAM_PLAN §4.5. Commit in small steps.
```

**Win conditions**
- [ ] Crime source documented (URL, date, licence, grain) and approved/acknowledged by the instructor, by D1 14:00.
- [ ] `crime.parquet` follows the contract; every `cvegeo` in `ageb.parquet`; `incident_hour` within −1…23; CRS 6372.
- [ ] Notebook reports: rows read → invalid coordinates → duplicates → outside urban AGEBs → loaded (a funnel table).
- [ ] Bivariate Moran: I, pseudo p-value, permutations, weights used, interpretation without causal claims.
- [ ] `report/technical_report.pdf` 4–6 pages, with ≥ 3 maps/figures, all six required sections.

**Suggested commits:** `analysis(crime): source search log` · `analysis(crime): profiling and point-in-polygon test` · `feat(crime): crime transform` · `docs(crime): data dictionary` · `analysis(crime): incidents by type and time` · `analysis(spatial): bivariate Moran` · `docs(report): limitations section` · `docs(report): technical report PDF`.

**README/report:** README §2 public-safety row, §4 crime decisions, §10 cautions; report section 5 + assembly.

---

## 5. Report (4–6 pages PDF, do NOT repeat the README)

Each member writes their section as `report/sections/<n>_<topic>.md` (own commit); Valeria assembles.

| Section | Owner | Content |
|---|---|---|
| 1. Problem and data sources | Julio | Why, which sources, temporal coverage of each |
| 2. Geographic integration strategy | Lorena | Unit choice, CRS, point-in-polygon results (kept/dropped %) |
| 3. Data Warehouse architecture | Jose | Diagram, grains, pipeline in one figure |
| 4. Key KPIs and spatial analysis | Nora | KPI table, Moran/LISA results |
| 5. Main findings (with maps) | All (each adds 1–2 findings from their analysis) | Maps/figures + interpretation |
| 6. Limitations and cautions | Valeria | Temporal mismatch, suppression, MAUP, data origin, association ≠ causation |

## 6. Final checklist (Jose, before tagging v1.0)

- [ ] Fresh clone → README commands → full DW + validation passes.
- [ ] Every KPI in the brief has a column in `dw.v_kpi_ageb` or a view (Incidents by type and time → `v_crime_by_type_time`).
- [ ] Correlation (≥ 3), Global Moran (≥ 2), LISA, bivariate Moran (≥ 1), neighbourhood rule explained.
- [ ] Data dictionary complete, diagram present, maps/figures in `outputs/`.
- [ ] README: all `_TODO_` replaced; assumptions and cautions written.
- [ ] `git shortlog -sne main` shows all 5 members with linked accounts across D1–D3.
- [ ] Report PDF in `report/` and submitted.
