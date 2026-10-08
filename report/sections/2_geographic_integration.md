# 2. Geographic integration strategy

**Author: Lorena Pérez**

## 2.1 Selecting a common unit

The geography must support a meaningful comparison between Census residents,
DENUE establishments and georeferenced FGJ investigation files. The selection
balances statistical compatibility, polygon availability, spatial detail and
the ability to identify the same area across sources.

| Candidate unit | Suitability for the integrated analysis |
|---|---|
| Municipality / alcaldía | The 16 alcaldías are stable administrative units and provide a useful citywide summary, but each is too large to reveal neighbourhood-scale patterns. The Census and point sources can be aggregated to them, but doing so discards most local variation. |
| Locality | INEGI provides locality identifiers and boundaries, and the Census has locality totals. Localities are fewer and uneven in size; the full study area spans 35 urban localities, including the main locality and outlying pueblos. Their totals do not give the same consistent, detailed cross-source resolution as the AGEB layer. |
| Colonia | Familiar to residents and useful for service delivery, but colonias are not a single, consistently defined INEGI statistical geography. Boundaries and names vary by source, and Census rows cannot be joined to colonias without an additional allocation model. |
| Hexagonal grid | A regular grid is useful for visualising point patterns and supports flexible cell sizes, but it has no direct Census identifier. Census counts would need areal interpolation, which introduces allocation assumptions and can create false precision. |
| **Urban AGEB (selected)** | The Census publishes urban-AGEB totals and INEGI's Marco Geoestadístico 2020 supplies matching polygons and `CVEGEO` identifiers. All **2,431** polygons have a Census row and valid geometry; the same polygons support point-in-polygon assignment for DENUE and FGJ. The unit preserves substantially more within-city detail than alcaldías without interpolating demographic counts. |

The selected geography covers **2,431 urban AGEBs**: **2,348** in the main
locality (`cve_loc = '0001'`) and 83 in 17 other urban localities. The main
locality subset represents the contiguous city-core sample for analyses that
need a connected study area. Rural localities do not have AGEB-level Census
data and are outside the analysis. The two Census AGEB rows without a polygon
in the 2020 frame are excluded and recorded in the Census transform.

## 2.2 Coordinate reference system

All point and polygon geometries are stored in **EPSG:6372 (Mexico ITRF2008 /
Lambert Conformal Conic)**. The Marco Geoestadístico 2020 polygons use this
projected CRS; DENUE and FGJ coordinates arrive as longitude/latitude in
EPSG:4326 and are transformed before spatial assignment. EPSG:6372 uses metres,
which keeps the layers aligned and makes polygon area and density calculations
consistent without repeatedly reprojecting the analysis geometry. The
`dim_geography.geom` column is a `MultiPolygon` with SRID 6372.

## 2.3 Point-to-polygon integration

The integration uses a strict `within` predicate: a DENUE or FGJ point is
assigned to the urban AGEB polygon that contains it. Coordinates are validated
and projected to EPSG:6372 first. Records with missing or invalid coordinates,
outside the study-area polygons, or exactly on a boundary are not assigned;
they are counted rather than allocated to a nearest area. The transform
enforces one output assignment per retained point.

| Source | Input records used for coverage | Assigned to urban AGEB | Captured |
|---|---:|---:|---:|
| DENUE 05/2026 | 462,732 Mexico City establishment records | 461,231 | **99.7%** |
| FGJ investigation files, offences dated 2024 | 119,666 eligible 2024 criminal records | 112,285 | **93.8%** |

For DENUE, three records have coordinates outside Mexico City; **461,231**
establishments are assigned to urban AGEBs from the 462,732-record snapshot.
The assigned AGEB agrees with DENUE's reported code for 99.84% of
establishments, with remaining differences kept auditable through
`cvegeo_reported`. For FGJ, the starting total is the offence-year and
criminal-event filtered sample; missing/invalid coordinates and points outside
urban AGEB boundaries explain the lower captured count. The FGJ extract covers
January–July 2024 only, so it is not a full-year crime count.

AGEBs provide a shared geographic key, not a shared observation date or
population at risk: Census residents describe 2020, DENUE reflects the 2026
snapshot, and FGJ counts describe the available 2024 offence records. Rates
and cross-source associations are therefore descriptive, and they should not
be interpreted as causal effects.

## 2.4 Reproducibility

The geography and spatial assignment contracts are implemented in
[`src/transform/geography.py`](../../src/transform/geography.py) and
[`src/transform/spatial.py`](../../src/transform/spatial.py). The KPI map and
correlation workflows read the warehouse view through
[`src/analysis/data.py`](../../src/analysis/data.py); the associated notebook
outputs are in [`outputs/maps/`](../../outputs/maps/) and
[`outputs/figures/`](../../outputs/figures/).
