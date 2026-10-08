# 1. Problem and data sources

*Author: Valeria Hernández*

Mexico City's population, economic establishments and reported crime are unevenly
distributed. This project integrates those three domains in a geospatial Data
Warehouse to compare territorial indicators and examine spatial association
across the **16 alcaldías**, using **2,431 urban AGEBs** as the common unit.
Questions include where business density and recorded crime rates are high,
how crime records vary by type and time, and whether neighbouring areas show
related patterns. These are descriptive questions, not estimates of causal
effects or individual victimisation risk.

The project first assessed Mérida, but the available municipal crime totals
could not support incident-to-AGEB assignment. Following the instructor's
requirement to use real records, the team moved to CDMX, where FGJ publishes
investigation files with coordinates. The earlier search and assessment remain
as Phase 1 evidence in notebook 13; no incidents are simulated.

Four official sources provide the population denominators, economic points,
geographic boundaries and public-safety records:

| Source | Version and temporal coverage | Original grain | Role in the warehouse |
|---|---|---|---|
| INEGI Census, results by AGEB and urban block | Census 2020 | Block and AGEB records, with higher-level totals | AGEB total rows provide population, age, economic participation and housing measures |
| INEGI DENUE, Ciudad de México | 05/2026 snapshot | One economic establishment, with coordinates and SCIAN activity | Establishments assigned to urban AGEBs; business and sector indicators |
| INEGI Marco Geoestadístico, Ciudad de México | 2020 cartographic frame | Geostatistical polygons, including urban AGEBs | Shared geographic identifiers, projected areas and point-to-AGEB assignment |
| FGJ CDMX, Carpetas de investigación 2024 | Pinned file: investigation opening dates **1 January–31 July 2024**; retained offences dated 2024 | One investigation file, with offence, date/time and coordinates | Recorded crime counts and distributions; **January–July snapshot**, not a complete year |

The integrated warehouse retains 2,431 matched census/geography units,
**9,138,524 residents**, **461,231 establishments** and **112,285** geolocated
investigation files. These are the retained urban-AGEB sample, not complete
counts for every geographic or reporting domain in the source data. Rural CDMX
is outside the analysis. Projected geometries use EPSG:6372; source point
coordinates use EPSG:4326.

Census 2020, FGJ January–July 2024 and DENUE 05/2026 measure different periods.
DENUE registration dates do not establish that every current establishment
was present when the crime occurred. Resident population is an older denominator
and does not measure visitors or commuters. FGJ files measure reported and
recorded events: later reports, unreported crime and records without suitable
coordinates are absent. August–December are unavailable rather than observed
zero-crime months; counts and rates are not annualised.

Source URLs, publishers, licences and pinned hashes are recorded in
[`src/config.py`](../../src/config.py) and
[`data/raw/manifest.json`](../../data/raw/manifest.json). INEGI sources use its
free-use terms; the FGJ source is recorded as CC-BY-4.0. The FGJ CSV SHA-256 is
`2ac3f17189a61ab7b2eb95fb21470e46adaba6f92526c7b92d23190ed2431f84`.
Raw downloads remain unchanged and are not committed. Phase 3 reads warehouse
views through the shared analysis helpers; notebook 33 supplies the temporal
and bivariate evidence, while section 6 states the interpretation limits.
