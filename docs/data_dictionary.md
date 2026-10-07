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

_TODO_

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
