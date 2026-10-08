# 6. Limitations and Interpretation Cautions

*Author: Valeria Hernández*

## 6.1 Different source dates and partial crime coverage

The warehouse combines Census **2020**, the DENUE **05/2026** snapshot and
FGJ offences dated **2024**. These are different temporal frames, not a
simultaneous measurement of the city. In particular, the pinned FGJ CSV
contains investigation files opened only from **1 January to 31 July 2024**
(`fecha_inicio`, source SHA-256 recorded in the manifest). The retained
offence dates span the same seven months. August–December are unavailable;
their absence does not mean that no crime occurred.

Counts and `crime_rate_per_1k` describe this retained snapshot and are not
annualised. Monthly and weekday averages in notebook 33 use the 213-day
filing window. Offences reported after July remain absent, particularly
affecting interpretation of July; calendar adjustments cannot remove that
right censoring. Excluding July raises the weekday averages by 2.6–5.2%
without changing the highest weekday (Friday). Seven observed months do not
establish annual seasonality.
Resident denominators also omit commuters and visitors, so a rate in a
commercial or transit area is not an individual victimisation probability.

## 6.2 Investigation files and geographic selection

FGJ records are reported investigation files, not all crimes, victims or
emergency calls. Reporting and administrative recording vary by offence and
area. The offence-date and non-criminal-event filters retain 119,666 files;
7,182 lack valid study-area coordinates and another 199 geolocated records
fall outside the strict urban-AGEB assignment, leaving **112,285** records.
Missing coordinates and exclusions may be spatially uneven. Unknown hours
remain explicit (**170** files), rather than being assigned to midnight.

English labels and macro-categories are analytical mappings. Negligent
(`CULPOS`) offences are classified as `Other`; overall crime counts must not
be interpreted as intentional violent crime. Source row identifiers preserve
traceability only for the pinned file and its original row order.

## 6.3 Suppression and unstable resident rates

INEGI `*` and `N/D` values remain SQL NULL, never zero. The census layer
contains **249 suppressed measures across 73 AGEBs**, tracked through
`n_suppressed_fields`. A ratio requires both numerator and denominator;
zero denominators produce NULL. Aggregated ratios should sum valid paired
numerators and denominators before division and disclose coverage.

Of the 2,431 urban AGEBs, **55** have fewer than 100 residents and **17** have
none. The spatial rate analysis preserves the shared city-core and
low-population exclusions: **2,297** AGEBs remain, after excluding 51
low-population city-core units. Temporal counts use all urban AGEBs because
they do not divide by resident population. These samples answer different
questions and their totals should not be compared as if identical.

## 6.4 Spatial association, neighbourhoods and aggregation

Notebook 33 tests business density at each AGEB against neighbouring crime
rates. Raw bivariate Moran's I is **0.201020** with Queen and **0.206815** with
KNN-6; log1p sensitivities are **0.178525** and **0.182574**. Each uses
row-standardised weights, **999 permutations**, seed **42**, and the same
2,297 ordered AGEBs; all four `p_sim` values are **0.001**. This is the
smallest attainable smaller-tail permutation pseudo p-value, not zero.
The graphs retain two components after island attachment.

The positive associations describe this sample. Permuting the crime values
does not preserve their spatial autocorrelation or condition on same-AGEB
correlation; these exploratory checks have no multiple-comparison correction.
Urban intensity, reporting and source-date differences may contribute to the
pattern. No causal effect or local hotspot is identified by this global
statistic or by the descriptive scatterplot quadrant shares. Boundaries and scale can alter associations (MAUP), and area-level
results cannot establish individual behaviour (ecological fallacy).

## 6.5 Study-area change and report evidence

Mérida was assessed first, but the search found municipal crime totals without
public incident coordinates. The instructor rejected simulated incidents and
recommended CDMX for point-level analysis. The Phase 1 search log remains in
notebook 13; the current study covers CDMX's 16 alcaldías at urban AGEB level.
Urban coverage does not represent rural CDMX or support extrapolation to Mérida.

Executed evidence and figure exports are in
[`notebook 33`](../../notebooks/33_crime_patterns_bivariate.ipynb), including the
[temporal chart](../../outputs/figures/crime_temporal_patterns.png) and
[bivariate comparison](../../outputs/figures/bivariate_moran_business_crime.png).
Gustavo can use these descriptive findings alongside the stated limitations
when assembling the report.
