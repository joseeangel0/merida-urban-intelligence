# Crime temporal patterns and bivariate Moran

*Analysis: Valeria Hernández. Review corrections: Gustavo Fuentes (#24).*

[`notebooks/33_crime_patterns_bivariate.ipynb`](../notebooks/33_crime_patterns_bivariate.ipynb)
reads `dw.v_crime_by_type_time` with `load_view()` and `dw.v_kpi_ageb` with
`load_kpis()`. Temporal summaries sum `incidents` across all 2,431 urban AGEBs
and reconcile to **112,285** retained files. Calendar-day averages use the
profiled **1 January–31 July 2024** window (213 days); August–December remain
unavailable, rather than zero-crime months. Unknown hours are retained
separately (170 files). July is right-censored: offences whose files were
opened after the 31 July cutoff are missing, so its per-day average is 23.4%
below January–June and the charts hatch it as partial. Excluding July raises
every weekday average by 2.6–5.2% and Friday remains the highest weekday
([`crime_weekday_sensitivity.csv`](../outputs/figures/crime_weekday_sensitivity.csv)).
April and May have the highest monthly averages (565.23 and 562.87 files/day,
0.4% apart); the ranking is not robust to reporting lag and does not establish
seasonality.
Charts and summary tables are exported to `outputs/figures/`, including the
month, weekday and time-band comparison by analytical category in
[`crime_temporal_patterns.png`](../outputs/figures/crime_temporal_patterns.png).

The bivariate analysis tests business density at each AGEB against the spatial
lag of crime rate in its neighbours, using Nora's row-standardised
`build_weights`. The default city-core and low-population filters retain
**2,297 AGEBs** (51 low-population city-core AGEBs excluded; no additional
incomplete pairs). Queen and KNN-6 use the same ordered sample, each with two
components and no remaining islands. With **999 permutations**, seed **42**:

| Indicator scale | Queen I | KNN-6 I | `p_sim` (each) |
|---|---:|---:|---:|
| Raw (primary) | 0.201020 | 0.206815 | 0.001 |
| log1p (sensitivity) | 0.178525 | 0.182574 | 0.001 |

The scatterplot quadrants ([`33_bivariate_quadrants.csv`](../outputs/figures/33_bivariate_quadrants.csv))
are descriptive. On the raw scale about half of the AGEBs are LL (49.9% with
Queen) and only 10.8% HH, because a few extreme AGEBs pull the means up; on the
log1p scale HH (31.8%) and LL (23.9%) are more balanced. HL is large in every
specification (26.2–31.6%): many AGEBs with above-average business density
border below-average crime rates.

These specifications show positive spatial association in this sample. PySAL's
`p_sim` is the smaller-tail permutation pseudo p-value, with a minimum of 0.001
for 999 permutations; sensitivity checks have no multiple-comparison correction.
They do not control for same-AGEB correlation or preserve the spatial structure
of the permuted crime indicator. Source-date differences, resident denominators,
urban intensity and reporting processes limit interpretation; no causal effect
is estimated. Figure: [`bivariate_moran_business_crime.png`](../outputs/figures/bivariate_moran_business_crime.png).
Permutation z-scores are included in the notebook table and exported result CSV.
Execution metadata and package versions: [`33_crime_analysis_metadata.json`](../outputs/figures/33_crime_analysis_metadata.json).
Report handoff: [section 1, problem and sources](../report/sections/1_problem_data_sources.md)
and [section 6, limitations](../report/sections/6_limitations.md).
