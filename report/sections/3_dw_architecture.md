# 3. Data Warehouse architecture

*Author: Jose Pech*

## 3.1 Pipeline

The solution follows a RAW → CLEAN → SPATIAL JOIN → PostgreSQL/PostGIS pipeline (Figure X, `docs/pipeline.png`). The four original sources are downloaded by a script and stored unchanged, together with a SHA-256 manifest that fixes the exact version used. One Python module per source cleans the data and writes a file with a fixed column contract; a shared spatial module converts every latitude/longitude pair into a point in EPSG:6372 and assigns it to the urban AGEB that contains it. The cleaned files are written to a staging schema (`stg`) and moved into the dimensional schema (`dw`) by SQL, where the surrogate keys are resolved. The whole sequence is executed by a single command, and the last step is a validation script that aborts the run if any check fails, so a warehouse that is built is also a warehouse that has been verified.

## 3.2 Dimensional model

The warehouse is a star schema with three fact tables that share conformed dimensions (Figure Y, `docs/warehouse_model.png`):

| Fact table | Grain | Main dimensions |
|---|---|---|
| `fact_census_ageb` | one urban AGEB (Census 2020 snapshot) | geography, source |
| `fact_business` | one DENUE establishment | geography, economic activity (SCIAN), business size, date, source |
| `fact_crime_incident` | one crime incident | geography, crime type, date, hour, source |

`dim_geography` is the dimension that integrates the three sources: it holds the 2,431 urban AGEB polygons of Mexico City, their `CVEGEO` identifier and their area in km². The census joins through the identifier; establishments and incidents join through their location.

Three design decisions shape the model:

1. **Facts keep the finest available grain.** Establishments and incidents are stored one row per record with their point geometry, not pre-aggregated per AGEB. Aggregation happens only in views, so every KPI can be recomputed, audited or re-aggregated to a different unit without returning to the raw files.
2. **A single projected CRS.** All geometries are stored in EPSG:6372 (Mexico ITRF2008 / LCC, metres), the CRS of the INEGI cartography. Areas and densities are computed directly, without reprojection at query time.
3. **Traceability as a dimension.** `dim_source` records the publisher, URL, original grain and file hash of each dataset, and every fact row references it. `fact_business.cvegeo_reported` keeps the AGEB that DENUE assigns to each establishment, so the spatial join can be audited (99.8 % agreement).

## 3.3 Analytical layer and validation

The views in `sql/03_views.sql` turn the facts into the required indicators: `v_kpi_ageb` has one row per AGEB with the 13 territorial KPIs and the polygon, `v_crime_by_type_time` provides the distribution of incidents by type, month, weekday and time band, and `v_business_by_sector` supports the dominant-activity indicator. Phase 3 notebooks read only from these views.

The validation script checks that every warehouse table has the same number of rows as its staging source, that the 2,431 polygons are valid and add up to 792.15 km², that the census population equals INEGI's figure for those AGEBs (9,138,524), that every point lies inside its assigned AGEB, and that the KPI view reconciles with the fact tables.

| Table | Rows |
|---|---|
| `dim_geography` | 2,431 |
| `fact_census_ageb` | 2,431 |
| `fact_business` | 461,231 |
| `fact_crime_incident` | 112,285 |
