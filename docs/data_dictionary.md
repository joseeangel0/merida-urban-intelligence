# Data dictionary

Concise dictionary of the `dw` schema (see [`sql/01_schema.sql`](../sql/01_schema.sql)). Each owner documents their tables; the column comments in the SQL are the source of truth for types.

## dim_geography — _owner: Lorena_

**`dw.dim_geography`** — grain: one row per urban AGEB in Mexico City. The
2020 Marco Geoestadístico layer contains **2,431 rows** across the 16 alcaldías:
**2,348** belong to the main locality of their alcaldía (`is_city_core = TRUE`)
and 83 belong to other urban localities. The mapped area totals **792.15 km²**.
`geo_key` is the warehouse surrogate key; `cvegeo` is the unique 13-character
INEGI geographic code (`cve_ent` + `cve_mun` + `cve_loc` + `cve_ageb`).

| Column | Type | Description |
|---|---|---|
| `geo_key` | serial PK | Warehouse surrogate key referenced by the census, business and crime facts |
| `cvegeo` | char(13), unique, not null | INEGI key: state (2) + municipality (3) + locality (4) + AGEB (4) |
| `cve_ent` | char(2), not null | State code; `09` for Mexico City |
| `cve_mun` | char(3), not null | Municipality/alcaldía code |
| `mun_name` | text, not null | Name of one of the 16 alcaldías |
| `cve_loc` | char(4), not null | Locality code; `0001` identifies the main locality in each alcaldía |
| `loc_name` | text, not null | INEGI locality name |
| `cve_ageb` | char(4), not null | Urban AGEB code within its locality |
| `is_city_core` | boolean, not null | True when `cve_loc = '0001'`; 2,348 AGEBs form the contiguous main city sample |
| `area_km2` | numeric(12,4), not null | Polygon area in square kilometres; positive, **792.15 km²** total |
| `geom` | geometry(MultiPolygon, 6372), not null | Urban AGEB boundary in Mexico ITRF2008 / Lambert Conformal Conic (EPSG:6372) |

The AGEB polygons originate in INEGI's Marco Geoestadístico 2020. The CRS is
projected in metres, so area and density calculations use consistent metric
units. The `cvegeo` used to match census aggregates is preserved alongside the
surrogate key; point facts reference `geo_key` after their coordinates have
been assigned to the containing polygon.

## dim_source, dim_date, dim_hour — _owner: Jose_

**dw.dim_source** — one row per original dataset (traceability).

| Column | Type | Description |
|---|---|---|
| `source_key` | smallint PK | Surrogate key |
| `source_code` | text UK | Key in `src/config.py:SOURCES` and `data/raw/manifest.json` |
| `source_name`, `publisher`, `url` | text | Official name, publisher and download URL |
| `version_label` | text, not null | Edition of the dataset, from `SOURCES[...]['version_label']` |
| `original_grain` | text | One row of the original file represents … |
| `sha256` | char(64), nullable | SHA-256 of the downloaded file (zip or CSV) from `manifest.json`; NULL when `manifest.json` has no entry for the source (not downloaded yet, or no manifest) |

Rows (4):

| `source_code` | `version_label` | Used by |
|---|---|---|
| `census_ageb_2020_09` | CPV 2020 | `fact_census_ageb` |
| `denue_09` | DENUE 05/2026 | `fact_business` |
| `marco_geo_2020_09` | Marco Geoestadístico 2020 | `dim_geography` (lineage only, no FK) |
| `crime_fgj_2024` | Carpetas de investigación 2024 | `fact_crime_incident` |

**dw.dim_date** — one row per calendar day between the earliest and latest of `stg.business.alta_date` and `stg.crime.incident_date` (`generate_series` in `sql/02_load.sql`). With DENUE 05/2026 the range is 2010-07-01 … 2026-04-01 (5,754 days). Facts with an unknown date have `date_key` NULL.

| Column | Type | Description |
|---|---|---|
| `date_key` | int PK | `YYYYMMDD` |
| `full_date` | date UK | Calendar date |
| `year`, `quarter`, `month`, `day` | smallint | Calendar parts |
| `month_name`, `day_name` | text | English names |
| `day_of_week` | smallint | ISO, 1 = Monday … 7 = Sunday |
| `is_weekend` | boolean | Saturday or Sunday |

**dw.dim_hour** — static, 25 rows.

| Column | Type | Description |
|---|---|---|
| `hour_key` | smallint PK | 0–23; −1 = hour unknown |
| `hour_label` | text | `HH:00-HH:59` |
| `time_band` | text | Night (00-05), Morning (06-11), Afternoon (12-17), Evening (18-23), Unknown |

## fact_census_ageb — _owner: Julio_

**dw.fact_census_ageb** — grain: one urban AGEB of Mexico City, Census 2020
snapshot (2,431 rows, one per `dim_geography` row). Source: the AGEB total rows
(`MZA = '000'`, `AGEB <> '0000'`) of INEGI *Principales resultados por AGEB y
manzana urbana* (`census_ageb_2020_09`); block, locality, alcaldía and state
total rows are not loaded. The 2 census AGEBs without a polygon in the 2020
frame (`0901101101107`, `0901201351227`, 7,108 residents) are dropped by
[`src/transform/census.py`](../src/transform/census.py).

**Suppressed values.** INEGI publishes `*` when a value could identify a
household and `N/D` when it is not available. Both are stored as NULL, never 0,
and counted in `n_suppressed_fields`; zeros are genuine zeros. In Mexico City 73
AGEBs (0.30 % of the population) have at least one suppressed field, there are
no `N/D` codes, and `pop_total` is never suppressed. Sums skip NULLs, so compute
a rate only where both terms are non-NULL.

| Column | Type | Source variable | Description | Unit |
|---|---|---|---|---|
| `geo_key` | int PK, FK | `cvegeo` | AGEB in `dim_geography` | — |
| `source_key` | smallint FK | — | `census_ageb_2020_09` in `dim_source` | — |
| `census_year` | smallint | — | Always 2020 | year |
| `pop_total` | int, not null | `POBTOT` | Total residents | residents |
| `pop_female`, `pop_male` | int | `POBFEM`, `POBMAS` | Residents by sex; add up to `pop_total` | residents |
| `pop_0_14`, `pop_15_64`, `pop_65_plus` | int | `POB0_14`, `POB15_64`, `POB65_MAS` | Broad age groups; may add up to less than `pop_total` (age not specified) | residents |
| `pop_12_plus` | int | `P_12YMAS` | Residents aged 12+, the base of `pea_rate` | residents |
| `pop_18_plus`, `pop_60_plus` | int | `P_18YMAS`, `P_60YMAS` | Adults, older adults | residents |
| `pea` | int | `PEA` | Economically active population (aged 12+) | residents |
| `pea_female`, `pea_male` | int | `PEA_F`, `PEA_M` | Economically active by sex; add up to `pea` | residents |
| `pop_inactive` | int | `PE_INAC` | Economically inactive (aged 12+) | residents |
| `pop_employed`, `pop_unemployed` | int | `POCUPADA`, `PDESOCUP` | Employed / unemployed; add up to `pea` | residents |
| `avg_schooling` | numeric(5,2) | `GRAPROES` | Average years of schooling (aged 15+) | years |
| `households` | int | `TOTHOG` | Census households | households |
| `dwellings_total`, `dwellings_inhabited` | int | `VIVTOT`, `TVIVHAB` | Total / inhabited dwellings | dwellings |
| `avg_occupants` | numeric(5,2) | `PROM_OCUP` | Average occupants per inhabited private dwelling | residents / dwelling |
| `n_suppressed_fields` | smallint, not null | derived | Number of the 20 source variables above published as `*` or `N/D` (0–20) | count |

Reference totals, asserted by `census.py`: Σ `pop_total` = 9,138,524 (also
checked by `sql/04_validation.sql`; 99.2 % of the state total, 9,209,944, the
rest live in rural localities or the 2 AGEBs without polygon), Σ `pea` =
5,061,682, Σ `pop_12_plus` = 7,858,894. Profiling and the variable list:
[`notebooks/11_profile_census.ipynb`](../notebooks/11_profile_census.ipynb).

## dim_economic_activity, dim_business_size, fact_business — _owner: Nora_

**dw.dim_economic_activity** — one row per six-digit SCIAN class represented by
an establishment inside the study area.

| Column | Type | Description / source |
|---|---|---|
| `activity_key` | serial PK | Warehouse surrogate key |
| `scian_code` | char(6), unique | `codigo_act`; six-digit SCIAN class |
| `activity_name` | text | `nombre_act`; activity label published by DENUE |
| `subsector_code` | char(3) | First three digits of `scian_code` |
| `sector_code` | text | SCIAN sector; official combined values `31-33` and `48-49` are retained |
| `sector_name` | text | English sector name |
| `activity_group` | text | `Retail` for sector 46; `Services` for 51–56, 61, 62, 71, 72 and 81; otherwise `Other` |

**dw.dim_business_size** — static lookup for DENUE's published employment
bands. The original Spanish label is the natural key because DENUE provides a
range rather than an exact employee count.

| Column | Type | Description |
|---|---|---|
| `size_key` | smallserial PK | Warehouse surrogate key |
| `per_ocu_label` | text, unique | Exact DENUE `per_ocu` label |
| `employees_min` | integer | Inclusive lower bound |
| `employees_max` | integer, nullable | Inclusive upper bound; NULL for `251 y más personas` |
| `size_class` | text | Analytical class: Micro, Small, Medium or Large |

**dw.fact_business** — grain: one DENUE establishment whose point geometry is
inside a Mexico City urban AGEB. The full state file is spatially joined; reported
AGEB codes do not determine inclusion.

| Column | Type | Description / source |
|---|---|---|
| `business_key` | bigserial PK | Warehouse surrogate key |
| `denue_id` | bigint, unique | DENUE `id` |
| `clee` | text | DENUE legal/economic-establishment identifier |
| `geo_key` | integer FK | AGEB containing the establishment point (`within`) |
| `activity_key` | integer FK | Six-digit SCIAN class |
| `size_key` | smallint FK | DENUE employment band |
| `date_key` | integer FK, nullable | `fecha_alta` month represented as its first calendar day; this is a registration/start month, not the snapshot date |
| `source_key` | smallint FK | DENUE source lineage |
| `establishment_name` | text, nullable | `nom_estab` |
| `cvegeo_reported` | char(13), nullable | `cve_ent + cve_mun + cve_loc + ageb`; retained to audit the spatial assignment |
| `establishment_count` | smallint | Additive measure, always 1 per fact row |
| `geom` | Point, EPSG:6372 | Projected DENUE longitude/latitude |

## dim_crime_type, fact_crime_incident — _owner: Valeria_

**dw.dim_crime_type** — one row per harmonised crime type (dimension).

| Column | Type | Description |
|---|---|---|
| `crime_type_key` | serial PK | Surrogate key for the crime type |
| `crime_type` | text UK | Unique harmonised English crime label (e.g. `Family Violence`, `Threats`, `Fraud`, `Robbery on Public Road with Violence`) |
| `crime_type_raw` | text | Original Spanish statutory offence description as reported by FGJ CDMX (`delito`, e.g. `VIOLENCIA FAMILIAR`) |
| `crime_category` | text | Standard high-level criminological macro-category: `Property`, `Violent`, `Sexual`, `Other` |

Crime labels are explicitly translated from all 231 normalized criminal `delito`
values in the pinned 2024 offence-year sample using
[`src/transform/crime_labels.py`](../src/transform/crime_labels.py). Accent variants
share a label, while `crime_type_raw` preserves the source spelling. An unknown
label raises an error before coordinate filtering so incomplete English coverage
cannot silently enter the warehouse. These are analytical translations, not a
replacement for the original statutory descriptions.

Categories depend only on normalized `delito`, with one category per `crime_type`.
Any label containing `CULPOS` (negligent injury, homicide or property damage) maps
to `Other` before the sexual, violent and property rules. This prevents traffic
collisions, falls and other negligent offences from inflating `Violent` counts;
intentional injury and homicide retain their existing classification.

**dw.fact_crime_incident** — grain: one row per georeferenced crime incident located strictly inside an urban AGEB occurring in 2024.

| Column | Type | Description |
|---|---|---|
| `incident_key` | bigserial PK | Surrogate key for the incident |
| `source_incident_id` | text | Stable 1-based identifier referencing the raw source line (`fgj2024-{line_number}`) |
| `geo_key` | int FK | Foreign key to `dw.dim_geography` (urban AGEB containing the incident point via spatial join) |
| `crime_type_key` | int FK | Foreign key to `dw.dim_crime_type` |
| `date_key` | int FK | Foreign key to `dw.dim_date` (`YYYYMMDD` from `fecha_hecho`), nullable |
| `hour_key` | smallint FK | Foreign key to `dw.dim_hour` (0–23; −1 = unknown/unrecorded hour) |
| `source_key` | smallint FK | Foreign key to `dw.dim_source` (`crime_fgj_2024`) |
| `incident_count` | smallint | Additive count measure (always 1 per incident row) |
| `geom` | geometry(Point, 6372) | Incident point coordinates reprojected to Mexico ITRF2008 LCC (EPSG:6372) |

## KPI views (`sql/03_views.sql`) — _owner: Jose_

**dw.v_kpi_ageb** — one row per urban AGEB (2,431). Formulas: [README §6](../README.md#6-kpis).

| Column | Type | Unit |
|---|---|---|
| `geo_key`, `cvegeo`, `loc_name`, `is_city_core` | — | from `dim_geography` |
| `low_population` | boolean | `pop_total < 100` |
| `area_km2` | float | km² |
| `pop_total` | int | persons |
| `pop_density_km2` | float | persons / km² |
| `pea_rate` | float | proportion 0–1 |
| `pct_0_14`, `pct_15_64`, `pct_65_plus` | float | % of `pop_total` |
| `businesses_total`, `retail_total`, `services_total` | int | establishments |
| `business_density_km2`, `retail_density_km2`, `service_density_km2` | float | establishments / km² |
| `businesses_per_1k` | float | establishments per 1,000 residents |
| `dominant_sector` | text | SCIAN sector name |
| `dominant_sector_share` | float | proportion 0–1 |
| `crime_total` | int | incidents |
| `crime_rate_per_1k` | float | incidents per 1,000 residents |
| `crimes_per_100_businesses` | float | incidents per 100 establishments |
| `geom` | MultiPolygon, EPSG:6372 | AGEB polygon |

**dw.v_crime_by_type_time** — grain: AGEB × crime type × year-month × day of week × time band. Columns: `geo_key`, `cvegeo`, `crime_type`, `crime_category`, `year`, `month`, `month_name`, `day_of_week`, `day_name`, `is_weekend`, `time_band`, `incidents`. Calendar columns are `NULL` for incidents without a date.

**dw.v_business_by_sector** — grain: AGEB × SCIAN sector. Columns: `geo_key`, `cvegeo`, `sector_code`, `sector_name`, `activity_group`, `establishments`, `share_in_ageb`.
