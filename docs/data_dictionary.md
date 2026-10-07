# Data dictionary

Concise dictionary of the `dw` schema (see [`sql/01_schema.sql`](../sql/01_schema.sql)). Each owner documents their tables; the column comments in the SQL are the source of truth for types.

## dim_geography — _owner: Lorena_

_TODO_

## dim_source, dim_date, dim_hour — _owner: Jose_

**dw.dim_source** — one row per original dataset (traceability).

| Column | Type | Description |
|---|---|---|
| `source_key` | smallint PK | Surrogate key |
| `source_code` | text UK | Key in `src/config.py:SOURCES` and `data/raw/manifest.json` |
| `source_name`, `publisher`, `url` | text | Official name, publisher and download URL |
| `version_label` | text | Edition of the dataset (e.g. `CPV 2020`) |
| `original_grain` | text | One row of the original file represents … |
| `sha256` | char(64) | Hash of the downloaded zip (proves the raw file is unchanged) |

**dw.dim_date** — one row per calendar day between the earliest and latest date in the facts.

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

_TODO: column, description, source variable, unit, handling of suppressed values._

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

_TODO_

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
