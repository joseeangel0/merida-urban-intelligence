# Valeria's findings for report assembly

*Author: Valeria Hernández. Analysis reviewed with Gustavo's corrections in #24.*

This is an assembly input for Gustavo's section 5, not an additional numbered
report section. Reuse the short findings below alongside sections 1 and 6;
assign final figure numbers consistently across the PDF. The numerical evidence
comes from the executed [notebook 33](../notebooks/33_crime_patterns_bivariate.ipynb)
and its warehouse exports.

## Finding 1: weekday pattern survives exclusion of July

Friday has the highest calendar-adjusted investigation-file average in both
the January–July snapshot (567.30 files per Friday) and the January–June
sensitivity (585.62). Excluding July raises every weekday average by
2.6–5.2%. This supports a descriptive weekday pattern within the retained
records, without establishing annual seasonality. July is right-censored by
the filing cutoff; the sensitivity does not correct reporting lag.

Evidence: [weekday sensitivity table](../outputs/figures/crime_weekday_sensitivity.csv)
and [weekday figure](../outputs/figures/crime_weekday_2024.png).

Suggested caption for the
[required temporal figure](../outputs/figures/crime_temporal_patterns.png):

> Recorded FGJ investigation files by offence month, weekday and time band,
> grouped by analytical category across all 2,431 urban AGEBs (112,285 files).
> July is hatched as partial because later reports are missing;
> August–December are unavailable. Unknown hours remain separate. Source:
> dw.v_crime_by_type_time, pinned January–July 2024 filing extract.

## Finding 2: business density is associated with neighbouring crime rates

Business density at each AGEB is positively associated with the spatial lag
of neighbouring recorded crime rates in the filtered 2,297-AGEB sample.
Raw bivariate Moran's I is 0.201020 with Queen and 0.206815 with KNN-6;
both permutation pseudo p-values are 0.001 (999 permutations, seed 42).
The positive association persists under log1p sensitivity. This is neither a
causal effect nor a significance-tested local hotspot result.

Evidence: [Moran results](../outputs/figures/33_bivariate_business_crime.csv)
and [descriptive quadrant shares](../outputs/figures/33_bivariate_quadrants.csv).

Suggested caption for the
[required bivariate figure](../outputs/figures/bivariate_moran_business_crime.png):

> Standardised business density versus the spatial lag of standardised crime
> rate, using row-standardised Queen and KNN-6 weights on the same 2,297
> city-core AGEBs with at least 100 residents. Raw and log1p specifications use
> 999 permutations and seed 42. Quadrant shares are descriptive. Source:
> dw.v_kpi_ageb; Census 2020, FGJ January–July 2024 and DENUE 05/2026.

## Assembly checks

- Keep both source-date mismatch and partial crime coverage with the figures;
  describe investigation files rather than all crime or victims.
- Temporal counts use all urban AGEBs; bivariate statistics use the filtered
  city core. Do not treat their samples as identical.
- Pair the compact [section 1](sections/1_problem_data_sources.md) and
  [section 6](sections/6_limitations.md) with the findings, without copying the
  README's tables or the full notebook output into the 4–6 page PDF.
- Add the other members' findings and at least three maps/figures overall,
  as required by TEAM_PLAN. The final findings section and PDF remain Gustavo's
  deliverables.
