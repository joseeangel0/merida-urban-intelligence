# 1. Problem and data sources

*Author: Valeria Hernández*

## 1.1 Problem statement

Mexico City's residential population, economic activity and reported crime
describe different uses of urban space. The warehouse brings them together at
urban AGEB level across the 16 alcaldías to compare territorial indicators and
examine neighbouring patterns. The questions concern where recorded activity
concentrates and how investigation files vary over time; they do not estimate
individual victimisation risk or causal effects.

## 1.2 The four official datasets

- **INEGI Census 2020**, reference date **15 March 2020**: resident population,
  broad age groups and economically active population (PEA, residents aged
  12+). The source mixes urban block, AGEB and higher-level totals; only urban
  AGEB total rows provide the demographic denominators. Confidentiality
  suppression (`*`) and unavailable values (`N/D`) remain NULL, never zero.
- **INEGI DENUE 05/2026**: one record per economic establishment in the active
  directory, with longitude/latitude, SCIAN activity and published employment
  bands (`per_ocu`), rather than exact employee counts. `fecha_alta` records
  registration timing; it does not turn this snapshot into a historical panel
  of business presence or survival.
- **INEGI Marco Geoestadístico 2020**: the common geographic identifiers and
  **2,431 urban AGEB polygons** across the 16 alcaldías. Warehouse geometries
  use **EPSG:6372 (Mexico ITRF2008 / LCC)**; areas are calculated from projected
  polygons. Geographic keys remain strings with their leading zeros.
- **FGJ CDMX, Carpetas de investigación 2024**: one record per investigation
  file, with offence, offence date/time and coordinates. `fecha_hecho` is the
  offence date; `fecha_inicio` is the file-opening date. The pinned extract
  contains files opened only from **1 January to 31 July 2024**. The analytical
  sample keeps offences dated 2024 and excludes `HECHO NO DELICTIVO`; records
  describe investigation files, not individual victims or all crimes.

## 1.3 Temporal coverage and alignment

The common 2020 geographic frame makes spatial assignment reproducible and
supports descriptive comparison of differently dated observations. It does
not demonstrate that populations, establishments or land use stayed unchanged
between Census 2020, FGJ 2024 and DENUE 2026. A business observed in 2026 was
not necessarily present when a 2024 offence occurred, and Census residents do
not measure visitors or commuters.

Crime coverage is a partial-year snapshot. Late-July offences reported after
the filing cutoff are missing, exposing July to right censoring.
August-December are unavailable, not observed zero-crime months; the project
does not annualise the files or infer annual seasonality. Spatial association
does not establish causal effects. Section 6 develops these interpretation
limits.

CDMX replaced the initial Mérida study because municipal crime totals could
not support incident-to-AGEB assignment. The Phase 1 assessment remains in
[notebook 13](../../notebooks/13_profile_crime.ipynb); no incidents are simulated.
The [README](../../README.md#2-data-sources),
[source configuration](../../src/config.py) and
[manifest](../../data/raw/manifest.json) retain the detailed inventory,
licences and hashes; INEGI free-use terms and FGJ CC-BY-4.0 are recorded there.
