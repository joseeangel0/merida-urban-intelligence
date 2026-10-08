# PR #28 verification

**Branch:** `lorena/geo-kpi-integration`

**Verified:** 2026-10-08

## Environment and inputs

- `docker info --format "{{.ServerVersion}}"` returned `28.2.2`.
- `.env` and Compose both target `localhost:5433/merida_dw`; the `db` service
  (`merida_dw`) was healthy after startup. `src.db` loads the repository `.env`,
  and both notebooks ran with the repository `.venv` Python 3.11 kernel.
- `census_ageb_2020_09.zip`, `denue_09.zip`, `marco_geo_2020_09.zip`, and
  `crime_fgj_2024.csv` were present locally. Each SHA-256 matched its
  `data/raw/manifest.json` entry. No TLS verification was disabled.

## Full pipeline

Commands run from the repository root:

```powershell
docker compose up -d --wait
C:\Users\Usuario\merida-urban-intelligence\.venv\Scripts\python.exe -m src.pipeline all
```

All seven stages completed: `download` (all sources present), `transform`,
`schema`, `stage`, `load`, `views`, and `validate`. Key final validation output:

```text
[geo] 2431 AGEBs, all valid, EPSG:6372, 792.15 km2
[census] every AGEB has a census row, population = 9138524
[spatial] every business and incident lies inside its assigned AGEB
[activity] activity groups consistent with SCIAN sectors
[kpi] v_kpi_ageb: 2431 AGEBs, population 9138524, businesses 461231, incidents 112285
[crime] v_crime_by_type_time reconciles with fact table (112285 incidents)
```

Post-run queries returned:

| Check | Result |
|---|---:|
| `SELECT count(*) FROM dw.v_kpi_ageb` | 2,431 |
| `SELECT sum(pop_total) FROM dw.v_kpi_ageb` | 9,138,524 |
| Distinct `(cve_mun, cve_loc)` pairs in `dw.dim_geography` | 33 |
| `dw.dim_geography` geometry | 2,431 `MULTIPOLYGON` rows, SRID 6372 |

## Executed notebooks and exports

Both notebooks were executed top-to-bottom in fresh kernels with:

```powershell
C:\Users\Usuario\merida-urban-intelligence\.venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=300 notebooks\30_kpi_maps.ipynb
C:\Users\Usuario\merida-urban-intelligence\.venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=300 notebooks\31_correlation.ipynb
```

Every code cell has a non-null execution count; resulting tables, figures and
messages are embedded in the notebooks. NB30 generated six individual
five-quantile KPI maps and the 2×3
`outputs/figures/kpi_choropleths_summary.png`. The individual maps and summary
were visually inspected for titles, units, five class labels and a 5 km scale
bar. The three NB31 scatterplots were visually inspected along with the results
table. NB31 generated three scatterplots and
`outputs/figures/31_correlation_results.csv`; each pair uses pairwise-complete
observations. Its primary city-core sample contains 2,297 AGEBs, and the
low-population-included sensitivity sample contains 2,348 AGEBs before
pairwise null removal (the three sensitivity pairwise sample sizes are 2,348,
2,331 and 2,321).

The NB31 interpretation is written against the exact coefficient, p-value,
normality and outlier values in the saved results table and calls out the
independence assumption of ordinary Pearson/Spearman p-values.
