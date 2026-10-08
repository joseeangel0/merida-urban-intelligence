# Data Sources Inventory and Quality Register

**Owner**: Gustavo Fuentes (`Audileleach`)  
**Scope**: Mexico City Urban Intelligence Data Warehouse (State `09`, 16 Alcaldías, 2,431 Urban AGEBs)  
**Contract Reference**: `docs/team/TEAM_PLAN.md` §3.1, §3.5 & §4.6

---

## 1. Source Inventory

The Data Warehouse integrates four official datasets published by Mexican government agencies (INEGI and FGJ CDMX). Raw files are downloaded into `data/raw/` via `python -m src.pipeline download` and validated against cryptographically pinned SHA-256 digests recorded in `data/raw/manifest.json`.

| Dataset Key | Name & Publisher | URL | Licence | Version / Date | Original Grain | CRS | Temporal Coverage | Key Variables | SHA-256 Digest |
|---|---|---|---|---|---|---|---|---|---|
| `census_ageb_2020_09` | **Censo de Población y Vivienda 2020** (INEGI) | [inegi.org.mx](https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/ageb_manzana/ageb_mza_urbana_09_cpv2020_csv.zip) | INEGI Términos de libre uso | CPV 2020 | One row per block/AGEB | Tabular (no geometry) | Reference date: 15–27 March 2020 | `POBTOT`, `PEA`, `P_12YMAS`, `P_0A14`, `P_15A64`, `P_65YMAS`, `VIVTOT` | `1f5f123b8e9a50991d1847271b5a2bf321e813e924e5bcf958cab612311c765a` |
| `denue_09` | **Directorio Estadístico Nacional de Unidades Económicas** (INEGI) | [inegi.org.mx](https://www.inegi.org.mx/contenidos/masiva/denue/denue_09_csv.zip) | INEGI Términos de libre uso | DENUE 05/2026 | One row per economic establishment | EPSG:4326 (`latitud`, `longitud`) | Active establishments up to May 2026 snapshot | `id`, `clee`, `nom_estab`, `codigo_act`, `per_ocu`, `fecha_alta`, coordinates | `ae608f30118f6313e9d537ea22918b2c9e9a3d3f19c2ddf5907f55dbb1642b19` |
| `marco_geo_2020_09` | **Marco Geoestadístico 2020** (INEGI) | [inegi.org.mx](https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/889463807469/09_ciudaddemexico.zip) | INEGI Términos de libre uso | Marco Geoestadístico 2020 | Shapefile polygons (Urban AGEBs: `09a.shp`) | EPSG:6372 (ITRF2008 / LCC) | 2020 census cartographic frame | `CVEGEO`, `CVE_ENT`, `CVE_MUN`, `CVE_LOC`, `CVE_AGEB`, MultiPolygon geometry | `685b912f5458138a70726cff41aff828473e14264c43289d3b21f86a9df00320` |
| `crime_fgj_2024` | **Carpetas de investigación 2024** (FGJ CDMX / Portal de Datos Abiertos CDMX) | [archivo.datos.cdmx.gob.mx](https://archivo.datos.cdmx.gob.mx/FGJ/carpetas/carpetasFGJ_2024.csv) | CC-BY-4.0 | Pinned 2024 snapshot (opened Jan–Jul 2024) | One row per investigation file (*carpeta*) | EPSG:4326 (`latitud`, `longitud`) | Filing window: 1 Jan – 31 Jul 2024; retained offences in 2024 | `delito`, `categoria_delito`, `fecha_inicio`, `fecha_hecho`, `hora_hecho`, coordinates | `2ac3f17189a61ab7b2eb95fb21470e46adaba6f92526c7b92d23190ed2431f84` |

---

## 2. Scope-Change Record: Transition from Mérida to Mexico City

On Day 1 (5 October 2026), the study area moved from Mérida (municipality `31050`) to Mexico City (state `09`, 16 alcaldías). The original search for georeferenced public-safety records in Yucatán (documented in `notebooks/13_profile_crime.ipynb` §1.1 and `docs/team/TEAM_PLAN.md` §4.5) confirmed that only aggregated monthly municipal totals were publicly available (SESNSP). State transparency portals, police geoprotocols and judicial bulletins lacked incident microdata with geographic coordinates.

When consulted regarding synthetic spatial estimation, course leadership stated:
> *"No simulated data. If you have municipal-level data, your spatial analysis must stay at state level. For high granularity you can consider hoyodecrimen.com, but working with Mexico City."*

To preserve point-in-polygon spatial integration, intra-urban contiguity weights and spatial econometric methods (Moran's $I$, LISA) without violating research ethics through synthetic simulation, the team adopted the official open microdata of Mexico City. All pipeline components, star schemas and analytical units were ported to CDMX's 2,431 urban AGEBs.

---

## 3. Data-Quality Register

This register documents observed empirical data defects across the four source datasets, their exact row counts, analytical impacts, resolution decisions, and assigned component owners.

| # | Issue Identified | Source Dataset | Evidence Count / Magnitude | Analytical Impact | Resolution Decision | Owner |
|---|---|---|---|---|---|---|
| 1 | **Orphan Census AGEBs (missing polygons)** | `census_ageb_2020_09` vs `marco_geo_2020_09` | 2 census AGEBs (`0901101101107`, `0901201351227`), Σ`POBTOT` = 7,108 residents | Cannot be mapped or assigned geographic boundaries; population would lack spatial boundaries. | Dropped during census transform with explicit counter warning; retains 2,431 matched urban AGEBs covering 99.2% of CDMX residents (9,138,524 people). | Julio / Gustavo (`census.py`) |
| 2 | **Confidentiality statistical suppression (`*` and `N/D`)** | `census_ageb_2020_09` | 249 suppressed measures across 73 urban AGEBs | Converting `*` to `0` would introduce false zeros into economic and demographic rates. | Replaced strictly with SQL `NULL`. Tracked via explicit integer column `n_suppressed_fields` in `fact_census_ageb`. | Julio / Gustavo (`census.py`) |
| 3 | **Economic establishments outside urban study area** | `denue_09` | 1,501 establishments out of 462,732 (0.32%) | Located in rural CDMX, roads or state borders outside the 2,431 urban AGEB polygons. | Filtered out during point-in-polygon spatial join (`within`). Exactly 461,231 establishments retained (99.8% agreement with reported codes). | Nora (`denue.py`) |
| 4 | **Missing or invalid crime coordinates** | `crime_fgj_2024` | 7,182 crime records lack coordinates or fall outside CDMX bounding box | Cannot be spatially assigned to an urban AGEB. | Excluded during coordinate validation in `spatial.points_from_latlon`. Logged in pipeline audit notices. | Valeria (`crime.py`) |
| 5 | **Geolocated crime outside urban AGEB polygons** | `crime_fgj_2024` | 199 validly geocoded crime records | Located in conservation zones or rural periphery lacking urban AGEB polygons. | Dropped during spatial join (`within`). Reconciles total retained incidents to exactly 112,285 files. | Valeria (`crime.py`) |
| 6 | **Filing date vs offence date mismatch (temporal right-censoring)** | `crime_fgj_2024` | 18,964 files opened in 2024 refer to offences from earlier years (11% of total) | Conflates previous years' criminality with 2024 spatial dynamics. | Analytical sample filters strictly for `fecha_hecho` occurring in 2024 (`CRIME_YEAR = 2024`), dropping pre-2024 offences. | Valeria (`crime.py`) |
| 7 | **Non-criminal administrative incidents in crime logs** | `crime_fgj_2024` | Category `HECHO NO DELICTIVO` | Overstates criminal victimization with administrative lost property or natural deaths. | Dropped during ETL (`categoria_delito != 'HECHO NO DELICTIVO'`). | Valeria (`crime.py`) |
| 8 | **Exact incident duplicates among geolocated records** | `crime_fgj_2024` | Records repeating identical offence, date, hour and exact coordinates | Risk of artificial inflation in crime counts. | Deduplicated after coordinate validation; duplicates lack coordinates in the raw file, preserving 112,285 geolocated rows. | Valeria (`crime.py`) |
| 9 | **Lack of primary incident identifier in source** | `crime_fgj_2024` | All 138,630 rows in raw CSV lack an incident ID | Unable to enforce entity integrity in dimensional model. | Synthesized stable, traceable natural key: `source_incident_id = 'fgj2024-' + row_number` (1-based, header excluded). | Valeria (`crime.py`) |
| 10 | **Host TLS certificate expiration** | `crime_fgj_2024` (host: `archivo.datos.cdmx.gob.mx`) | Expired Let's Encrypt certificate on 5 Oct 2026 | Automated pipeline download aborts under standard TLS verification. | Enforced strict TLS verification policy (no insecure flags); dataset pinned and cached with SHA-256 validation. | Team Lead (`download_sources.py`) |
| 11 | **Multi-source temporal misalignment** | All 4 sources | Census 2020, DENUE May 2026, FGJ Jan–Jul 2024 | Conflates different economic and demographic epochs; rates are descriptive cross-sections. | Explicitly documented in report Sections 1 & 6; rates are not treated as causal or simultaneous probabilities. | Valeria / Gustavo |
| 12 | **Partial-year crime coverage (7-month snapshot)** | `crime_fgj_2024` | Files opened strictly between 1 Jan and 31 Jul 2024 (213 calendar days) | Aug–Dec are unavailable; treating them as zero would severely distort seasonality. | Calendar-exposure models use 213 observed days (leap year Feb = 29); Aug–Dec set to `NULL`/`NA` (not 0); no annualization. | Valeria (`crime_patterns.py`) |
| 13 | **Extreme per-capita rate outliers in low-population AGEBs** | `v_kpi_ageb` | 55 AGEBs with `pop_total < 100` (17 with 0 residents) | Tiny denominators cause per-capita business and crime rates to explode (e.g. historic centre). | Flagged with boolean `low_population = TRUE`. Excluded by default in `src.analysis.data.load_kpis()`. | Jose (`03_views.sql` / `data.py`) |
| 14 | **Disconnected spatial graph components in contiguity weights** | `marco_geo_2020_09` | 6 disconnected spatial components if including outlying pueblos (all 2,431 AGEBs) | Breaks spatial lag calculations and standard spatial econometric assumptions. | Analysis restricted to the 2,348 city-core AGEBs (`cve_loc = '0001'`), with single Queen island attached to nearest neighbour. | Nora / Jose (`spatial_weights.py`) |

---

## 4. Verification and Reproducibility

Every dataset can be verified locally using the pipeline inspection commands:
```bash
# Verify checksums and raw manifest
python -m src.pipeline download

# Run data warehouse validation script
python -m src.pipeline validate
```
Validation confirms that all 2,431 AGEBs, 9,138,524 residents, 461,231 business establishments, and 112,285 criminal investigation files are properly indexed, loaded, and reconciled across dimensions and fact tables.
