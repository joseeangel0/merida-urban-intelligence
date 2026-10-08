# 4. Key KPIs and spatial analysis

The economic layer retained 461,231 of 462,732 DENUE establishments (99.7%),
located inside Mexico City's 2,431 urban AGEBs. Of these, 211,431 belong to retail
sector 46. The spatial join agreed with DENUE's reported AGEB for 99.84% of
establishments; the 728 disagreements are consistent with points close to
geographic boundaries and are auditable through `cvegeo_reported`.

The warehouse exposes total businesses, business density per km², businesses per
1,000 residents, retail density, service density, and the dominant economic
sector and its share. Density and per-capita measures answer different questions:
the former describes spatial concentration, whereas the latter compares economic
presence with resident population. Per-capita values in AGEBs with fewer than 100
residents require particular caution.

Spatial autocorrelation uses the 2,348 city-core AGEBs of Mexico City (the main
locality of each alcaldía). The primary neighbourhood rule is row-standardised
Queen contiguity, with its single island connected to the nearest AGEB.
Row-standardised KNN-6 provides a sensitivity comparison. Rate indicators exclude
AGEBs with fewer than 100 residents. Global Moran's I and Local Moran cluster
inference use 999 permutations with a fixed seed and α = 0.05. The implemented
workflow reports I, its expected value, permutation z-score, pseudo p-value and
sample size for every indicator, then maps significant HH, LL, HL and LH clusters.

### 4.1 Global Spatial Autocorrelation (Moran's I)

Across the city-core sample (2,348 AGEBs; 2,297 for rate indicators after excluding $n=51$ low-population AGEBs with $<100$ residents), all four indicators exhibit statistically significant positive spatial autocorrelation ($p = 0.001$, 999 permutations, seed = 42, $E[I] = -0.0004$):

| Indicator | Weights | $n$ | Observed $I$ | $E[I]$ | $z_{\text{sim}}$ | Pseudo $p$ | Permutations |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Business density | Queen | 2,348 | 0.4618 | -0.0004 | 38.2189 | 0.001 | 999 |
| Business density | KNN-6 | 2,348 | 0.4583 | -0.0004 | 42.3570 | 0.001 | 999 |
| Crime rate per 1k residents | Queen | 2,297 | 0.2096 | -0.0004 | 17.2936 | 0.001 | 999 |
| Crime rate per 1k residents | KNN-6 | 2,297 | 0.1785 | -0.0004 | 17.0411 | 0.001 | 999 |
| Population density | Queen | 2,348 | 0.4342 | -0.0004 | 36.6669 | 0.001 | 999 |
| Population density | KNN-6 | 2,348 | 0.4508 | -0.0004 | 39.8869 | 0.001 | 999 |
| Economically active pop. rate (PEA) | Queen | 2,297 | 0.5063 | -0.0004 | 42.0699 | 0.001 | 999 |
| Economically active pop. rate (PEA) | KNN-6 | 2,297 | 0.4996 | -0.0004 | 44.6113 | 0.001 | 999 |

Results demonstrate strong stability between Queen contiguity and KNN-6 ($k=6$), confirming that the detected spatial clustering is robust to neighbourhood specification.

### 4.2 Local Spatial Patterns (LISA Clusters)

Local Moran analysis ($\alpha = 0.05$, Queen weights, 999 permutations, seed = 42) identifies significant spatial clusters and spatial outliers:

These are exploratory classifications based on nominal per-AGEB pseudo
p-values. No multiple-comparison adjustment is applied to the 2,348 business
and 2,297 crime tests, so the threshold does not control false discoveries
across the family of local tests. The counts below are not counts of
multiplicity-adjusted hotspots.

| Indicator | Total AGEBs | Significant ($p < 0.05$) | High-High (Hot spot) | Low-Low (Cold spot) | High-Low (Outlier) | Low-High (Outlier) | Not significant |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Business density | 2,348 | 482 (20.5%) | 109 | 312 | 33 | 28 | 1,866 |
| Crime rate per 1k | 2,297 | 540 (23.5%) | 110 | 344 | 10 | 76 | 1,757 |

- **Business density:** High-High clusters concentrate along central commercial corridors (Cuauhtémoc, Benito Juárez, and Miguel Hidalgo), whereas Low-Low clusters dominate peripheral residential areas.
- **Crime rate:** High-High clusters align with central commercial and transit hubs, while extensive Low-Low clusters cover peripheral residential zones.
- **Analytical Caution:** Spatial association describes geographic clustering under the chosen spatial weights; it does not demonstrate that commercial activity, population density, or economic participation causally induce criminal incidents in neighboring AGEBs.
