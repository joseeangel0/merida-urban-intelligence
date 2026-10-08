# Valeria's README support for Jose

*Author: Valeria Hernández (`valnix140405`). Scope: support plan V3.*

The current README already documents the FGJ transform and public-safety
limitations. The shorter blocks below are optional assembly inputs for Jose's
final integration, rather than an additional crime-method specification. Keep
the existing detailed funnel, translation rules, provenance and evidence links
if these summaries are used. Section 1 of the report is maintained separately
in [1_problem_data_sources.md](../../report/sections/1_problem_data_sources.md).

## Suggested text for README section 4: crime cleaning decisions

The FGJ sample uses offence year 2024 (`fecha_hecho`), not the investigation
opening year, and excludes `HECHO NO DELICTIVO`. For the pinned extract,
138,630 raw files yield 119,666 eligible offences; removing 7,182 invalid
coordinates leaves 112,484 geolocated files. Shared spatial helpers project
EPSG:4326 coordinates to EPSG:6372; deduplication among valid-coordinate files
removes zero records, and strict `within` assignment excludes 199 outside or
boundary points, retaining **112,285 investigation files** in urban AGEBs.
Original row-based identifiers and offence labels preserve traceability;
unknown hours remain -1. These counts describe the pinned source version.

## Suggested text for README section 10: assumptions and limitations

- **Different source dates:** Census March 2020, FGJ 2024 and DENUE 05/2026
  are not simultaneous observations. A 2026 business location does not
  establish exposure at the time of a 2024 offence; resident denominators
  omit visitors and commuters.
- **Partial crime coverage:** the FGJ filing extract ends on 31 July 2024.
  Later reports are absent, July is exposed to right censoring, and
  August-December are unavailable rather than zero. Do not annualise these
  counts or interpret seven months as annual seasonality.
- **Association and selection:** investigation files measure reported events,
  subject to underreporting and geographic exclusions. Spatial correlations
  and Moran statistics describe area-level association, not causal effects
  or individual victimisation risk; boundaries and aggregation can alter it.

## Evidence for integration

- [Crime transform](../../src/transform/crime.py),
  [label mapping](../../src/transform/crime_labels.py) and
  [shared spatial helpers](../../src/transform/spatial.py).
- [Executed profiling](../../notebooks/13_profile_crime.ipynb) and
  [crime analysis record](../crime_analysis.md).
- [Report limitations](../../report/sections/6_limitations.md) and
  [findings/captions for Gustavo](../../report/valeria_findings_handoff.md).

These documentation changes introduce no new source, KPI, filter or dataset
contract. They can be reviewed independently of teammates' open work.
