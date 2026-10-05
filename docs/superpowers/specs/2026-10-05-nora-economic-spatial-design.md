# Nora Economic and Spatial Analysis Design

## Scope

Complete Nora Horta's owned deliverables: DENUE profiling, the economic ETL,
economic warehouse documentation, reusable spatial weights, Global Moran's I,
LISA analysis, maps, and Nora's report contribution. Files owned by other team
members remain unchanged except for shared documentation sections explicitly
assigned to Nora.

## Data flow

The existing downloader retrieves the complete Yucatan DENUE CSV. The profiling
notebook examines that immutable source and documents its quality. The production
transform reads the same CSV, validates coordinates, creates projected points,
and uses the existing shared spatial API to assign establishments to urban AGEBs.
It writes the two GeoParquet/Parquet files defined by the team contract.

The warehouse loader, schema, and KPI views remain team-owned integration
boundaries. Phase 3 analysis reads `dw.v_kpi_ageb` through
`src.analysis.data.load_kpis()` and never reads raw or processed files.

## Components

### DENUE profiling

`notebooks/12_profile_denue.ipynb` records row counts, coordinate completeness and
ranges, duplicate IDs, SCIAN sector frequencies, employment bands, and
`fecha_alta` coverage. It explains that `fecha_alta` is a registration/start-date
field rather than the DENUE snapshot date. It also presents the sector and
activity-group mapping used by the transform.

### Economic transformation

`src/transform/denue.py` exposes small functions for locating and reading the raw
CSV, normalizing sector codes, deriving the economic-activity dimension, parsing
registration dates, and building final business records. `run()` composes those
functions with `points_from_latlon()` and `assign_ageb()`.

The complete Yucatan dataset is spatially joined before establishments are
selected. Municipality membership is determined by point geometry, while the
reported codes are retained as `cvegeo_reported` for auditing. Output columns,
types, CRS, and filenames exactly follow `TEAM_PLAN.md` section 3.2.

Sector grouping rules are fixed:

- Retail: SCIAN sector 46.
- Services: sectors 51, 52, 53, 54, 55, 56, 61, 62, 71, 72, and 81.
- Other: every remaining sector.
- Manufacturing codes 31, 32, and 33 use combined sector `31-33`.
- Transportation codes 48 and 49 use combined sector `48-49`.

The seven `per_ocu` labels must match `dw.dim_business_size` exactly. Invalid or
unrecognized required values fail with an actionable error rather than silently
producing unusable warehouse rows.

### Spatial weights

`src/analysis/spatial_weights.py` provides only the required public function:
`build_weights(gdf, kind="queen", k=6)`. Queen contiguity and KNN use libpysal,
all weights are row-standardized, and Queen islands are connected to their
nearest neighbor. Input identifiers are kept aligned with GeoDataFrame rows so
analysis results can be joined back without positional ambiguity.

### Global Moran and LISA analysis

`notebooks/32_global_moran_lisa.ipynb` loads warehouse KPIs, explicitly states its
analysis sample, builds Queen and KNN-6 weights on the same observations, and
runs 999-permutation Global Moran statistics for at least two complete indicators.
The preferred set is business density, crime rate, population density, and PEA
rate when each is available.

For every tested indicator, the notebook reports Moran's I, expected I, z-score,
pseudo p-value, permutation count, and observation count. It compares Queen with
KNN-6, produces Moran scatterplots, and creates LISA cluster maps for at least two
indicators using HH, LL, HL, LH, and non-significant categories. Interpretations
describe spatial association without causal language.

The prescribed Queen reference uses all 483 city-core AGEBs. Rate analyses may
exclude low-population observations only when the same filtered sample is used
for both Queen and KNN weights and the departure from the 483-AGEB reference is
reported explicitly.

## Validation

Unit tests use small synthetic tables and geometries to verify mapping, date
parsing, output contracts, invalid-value failures, Queen island attachment, KNN
neighbor counts, and row standardization. Each behavior is developed test-first.

Real-data acceptance checks verify approximately 56,667 unique establishments,
EPSG:6372, valid AGEB references, at least 99.5 percent agreement between spatial
and reported AGEBs, full SCIAN dimension coverage, exact business-size labels,
and approximately 19,400 retail establishments. Final verification runs the
Nora-owned tests, notebook execution where dependencies are present, and the full
pipeline when every team-owned module and the database are available.

## Documentation and outputs

Nora completes the economic tables in `docs/data_dictionary.md`, the assigned
README economic/ETL/spatial sections, report section 4, and one or two findings
for section 5. Generated plots are stored under `outputs/maps/` or
`outputs/figures/`. Generated raw and processed data remain untracked.

## External dependencies

The economic transform depends on Lorena's `ageb.parquet`. Warehouse analysis
depends on the team staging/load modules, PostgreSQL/PostGIS, census data, and any
crime indicators selected for analysis. Missing team-owned dependencies do not
block unit-tested Nora components; unavailable analyses are documented and run
once their inputs exist.
