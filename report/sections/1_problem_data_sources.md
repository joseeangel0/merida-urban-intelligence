# 1. Problem and data sources

*Author: Valeria Hernández*

Mexico City's residential population, economic activity and reported crime
describe different uses of urban space. The warehouse brings them together at
urban AGEB level across the 16 alcaldías to compare territorial indicators and
examine neighbouring patterns. The questions concern where recorded activity
concentrates and how investigation files vary over time; they do not estimate
individual victimisation risk or causal effects.

Four official datasets supply complementary observations. INEGI Census **2020**
provides demographic denominators from AGEB total rows in a file that also
contains block and higher-level totals. INEGI DENUE **05/2026** contributes one
record per economic establishment, with coordinates and SCIAN activity. INEGI
Marco Geoestadístico **2020** supplies the geostatistical polygons from which
urban AGEB boundaries and shared identifiers are selected. FGJ CDMX
*Carpetas de investigación 2024* supplies one record per investigation file,
with offence, date/time and coordinates. Its pinned extract contains files
opened only from **1 January to 31 July 2024**; retained offences are dated
2024, so the crime evidence is a partial-year snapshot.

These dates constrain comparison: a business observed in 2026 was not
necessarily present when a 2024 offence occurred, and Census residents do not
measure visitors or commuters. August-December crime coverage is unavailable;
the project does not annualise the observed files. Section 6 develops these
interpretation limits.

CDMX replaced the initial Mérida study because municipal crime totals could
not support incident-to-AGEB assignment. The Phase 1 assessment remains in
[notebook 13](../../notebooks/13_profile_crime.ipynb); no incidents are simulated.
The [README](../../README.md#2-data-sources),
[source configuration](../../src/config.py) and
[manifest](../../data/raw/manifest.json) retain the detailed inventory,
licences and hashes; INEGI free-use terms and FGJ CC-BY-4.0 are recorded there.
