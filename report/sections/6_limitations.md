# 6. Limitations and interpretation cautions

*Author: Valeria Hernández*

## 6.1 Temporal comparison and reporting lag

Census 2020, FGJ January-July 2024 and DENUE 05/2026 are not simultaneous
observations. Later business locations cannot establish the economic exposure
at the time of an offence. The FGJ filing cutoff also omits offences reported
after July; July is especially exposed to right censoring. August-December
remain unavailable, and neither calendar-day averages nor the January-June
sensitivity correct reporting lag. Seven months cannot establish annual
seasonality, and counts and rates are not annualised.

## 6.2 Reporting and geographic selection

Investigation files measure reported and administratively recorded events.
Differences in reporting, missing coordinates and strict urban-polygon
assignment can produce spatially uneven selection. Unknown hours remain
separate. English labels and macro-categories are analytical mappings;
negligent offences belong to `Other`, so overall counts do not measure
intentional violent crime alone. Source-row identifiers are reproducible only
for the pinned file and its original row order. The detailed exclusion funnel
is in [README section 4](../../README.md#fgj-public-safety-layer).

## 6.3 Resident denominators and suppression

Resident rates omit commuters and visitors and are not individual
victimisation probabilities. Tiny populations can inflate these ratios; the
bivariate analysis therefore retains the default city-core and low-population
filters. Temporal counts include all urban AGEBs and answer a different
question. INEGI suppressed values remain NULL, never zero; zero-denominator
ratios are NULL. Area aggregates must sum valid paired numerators and
denominators before division and disclose missing-data coverage.

## 6.4 Spatial inference and aggregation

Bivariate Moran tests business density at an AGEB against neighbouring crime
rates, rather than same-AGEB correlation. Its randomisation does not preserve
the crime indicator's spatial autocorrelation or control for same-AGEB
correlation. Exploratory sensitivity checks lack multiple-comparison
correction; scatterplot quadrants are descriptive, not local significance
tests. Neither global association nor these quadrants identify causal effects
or local hotspots. Boundaries and aggregation scale can change associations
(MAUP); area-level results do not establish individual behaviour (ecological
fallacy).

## 6.5 Scope and evidence

Interpretation applies to the observed urban CDMX sample, not rural CDMX or
Mérida. Detailed statistics and sample diagnostics are in
[notebook 33](../../notebooks/33_crime_patterns_bivariate.ipynb) and the
[analysis record](../../docs/crime_analysis.md). The
[temporal figure](../../outputs/figures/crime_temporal_patterns.png) marks
partial coverage; the
[bivariate figure](../../outputs/figures/bivariate_moran_business_crime.png)
shows both neighbourhood rules and scales.
