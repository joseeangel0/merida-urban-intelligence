# 5. Main findings

*Author: Jose Pech (assembled from notebooks 30–35 and Valeria's findings handoff)*

All values come from the warehouse views (`dw.v_kpi_ageb`,
`dw.v_crime_by_type_time`, `dw.v_business_by_sector`) through the executed
notebooks. Crime counts are FGJ investigation files for offences dated
January–July 2024; they are not annualised.

## Finding 1: the centre concentrates establishments and recorded crime

Cuauhtémoc, Benito Juárez and Miguel Hidalgo hold 15.3% of the urban
population but 25.4% of establishments and 28.1% of investigation files.
Their crime rate is 22.6 files per 1,000 residents, against 10.4 in the other
13 alcaldías, and they rank 1–3 on that KPI. Cuauhtémoc has the highest
business density (2,089 establishments per km², more than twice Venustiano
Carranza's 913) and the most businesses per 1,000 residents (124). Iztapalapa,
the most populous alcaldía (1.84 million residents), has the lowest crime rate
(8.4).

Evidence: [notebook 35](../../notebooks/35_alcaldia_comparison.ipynb),
[alcaldía figure](../../outputs/figures/35_alcaldia_comparison.png),
[KPI choropleths](../../outputs/figures/kpi_choropleths_summary.png).

## Finding 2: the ranking depends on the denominator

Per establishment, the gap between the centre and the rest of the city almost
disappears: 26.9 against 23.5 crimes per 100 establishments. Cuauhtémoc ranks
only 9th (23.8), behind Benito Juárez (35.6), Coyoacán (32.5) and Iztacalco
(30.9). The centre receives a large daytime population that the resident
denominator does not count, so the per-resident rate overstates resident
exposure there.

The same effect appears at AGEB level. Crime rate and businesses per 1,000
residents share the resident denominator: Pearson r = 0.794, but Spearman
ρ = 0.580 (n = 2,297). The rank coefficient is the more reliable summary,
and part of the linear coefficient is a ratio artifact. Population density
and business density have a weaker monotone association (ρ = 0.358). PEA
rate and crime rate are only weakly associated (ρ = 0.190).

Evidence: [notebook 31](../../notebooks/31_correlation.ipynb),
[correlation results](../../outputs/figures/31_correlation_results.csv).

## Finding 3: business and crime hot spots overlap only partly

All four indicators tested are positively spatially autocorrelated (Global
Moran's I between 0.18 and 0.51, pseudo p = 0.001 under Queen and KNN-6).
Locally, 76 of the 109 business-density High-High AGEBs (70%) are in
Cuauhtémoc. Crime-rate High-High AGEBs are more spread out: Cuauhtémoc holds
47 of 110 (43%), followed by Miguel Hidalgo (14), Benito Juárez (10),
Gustavo A. Madero (9) and Venustiano Carranza (8). 35 AGEBs are High-High for
both indicators, 31 of them in Cuauhtémoc. The largest crime cold spot is in
Iztapalapa (164 Low-Low AGEBs).

Business hot spots are stable under KNN-6 (88% stay High-High); crime hot
spots are less so (59%; 110 → 72). Under a stricter p < 0.01 cutoff, 45
business and 30 crime High-High AGEBs remain. The labels are exploratory
screens, not confirmed single-AGEB discoveries.

Evidence: [notebook 32](../../notebooks/32_global_moran_lisa.ipynb),
[notebook 34](../../notebooks/34_lisa_hotspots.ipynb),
[cluster map](../../outputs/maps/34_hotspot_clusters_alcaldia.png).

## Finding 4: business density is associated with neighbouring crime rates

Bivariate Moran's I between business density and the spatial lag of the
crime rate is 0.201 with Queen and 0.207 with KNN-6 weights (pseudo
p = 0.001, 999 permutations, seed 42, n = 2,297). The association persists
under a log1p transformation (0.179 and 0.183). This describes a spatial
association, not a causal effect.

Evidence: [notebook 33](../../notebooks/33_crime_patterns_bivariate.ipynb),
[bivariate figure](../../outputs/figures/bivariate_moran_business_crime.png).

## Finding 5: recorded crime peaks in the afternoon and on Fridays

The afternoon band (12:00–17:59) has 33.7% of investigation files and the
night band (00:00–05:59) has 13.2%. Friday has the highest calendar-adjusted
average, both in January–July (567.3 files per Friday) and in the
January–June sensitivity that excludes the right-censored July (585.6).
Family violence is the most frequent offence type (18.0%), followed by
threats (10.1%) and fraud (7.9%). Seven months cannot establish annual
seasonality.

Evidence: [notebook 33](../../notebooks/33_crime_patterns_bivariate.ipynb),
[temporal figure](../../outputs/figures/crime_temporal_patterns.png),
[weekday sensitivity](../../outputs/figures/crime_weekday_sensitivity.csv).
