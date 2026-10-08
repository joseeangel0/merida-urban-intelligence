-- =====================================================================
-- Mexico City Urban Intelligence — KPI Demonstration Queries
-- Owner: Gustavo Fuentes (Audileleach) · TEAM_PLAN §4.6 & README §6
--
-- Read-only analytical queries demonstrating that every required KPI,
-- summary statistic, and territorial comparison can be answered directly
-- from the Data Warehouse views (dw.v_kpi_ageb, dw.v_crime_by_type_time,
-- and dw.v_business_by_sector). Census numerators that the views do not
-- expose (PEA, age groups) come from dw.fact_census_ageb, and alcaldía
-- names from dw.dim_geography.
--
-- Convention: citywide_* columns are pooled ratios over all 2,431 urban
-- AGEBs (sum of numerators / sum of denominators); mean/min/max columns
-- describe the AGEB distribution and exclude low_population AGEBs for
-- per-capita KPIs.
--
-- Execution:
--   docker exec -i merida_dw psql -U merida -d merida_dw < sql/05_kpi_queries.sql
-- =====================================================================

\echo '=== KPI 01: Total Population (dw.v_kpi_ageb: pop_total) ==='
-- Distribution of resident population across the 2,431 urban AGEBs
SELECT
    COUNT(*)                                            AS total_agebs,
    SUM(pop_total)                                      AS cdmx_urban_population,
    ROUND(AVG(pop_total), 1)                            AS mean_pop_per_ageb,
    MIN(pop_total)                                      AS min_pop,
    MAX(pop_total)                                      AS max_pop,
    COUNT(*) FILTER (WHERE low_population)              AS low_population_agebs,
    COUNT(*) FILTER (WHERE pop_total = 0)               AS zero_population_agebs
FROM dw.v_kpi_ageb;

\echo '=== KPI 02: Population Density (dw.v_kpi_ageb: pop_density_km2) ==='
-- Citywide urban density and AGEB distribution (residents / km2)
SELECT
    ROUND(SUM(pop_total)::NUMERIC / NULLIF(SUM(area_km2), 0)::NUMERIC, 2)        AS citywide_density_km2,
    ROUND((AVG(pop_density_km2) FILTER (WHERE NOT low_population))::NUMERIC, 2) AS mean_ageb_density_km2,
    ROUND((MIN(pop_density_km2) FILTER (WHERE NOT low_population))::NUMERIC, 2) AS min_density_km2,
    ROUND((MAX(pop_density_km2) FILTER (WHERE NOT low_population))::NUMERIC, 2) AS max_density_km2
FROM dw.v_kpi_ageb;

\echo '=== KPI 03: Economically Active Population Rate (dw.v_kpi_ageb: pea_rate) ==='
-- PEA rate = PEA / P_12YMAS. Citywide rate over the AGEBs where both are published
-- (TEAM_PLAN §3.5 reference: 5,061,682 / 7,858,894), plus the AGEB distribution
SELECT
    COUNT(*) FILTER (WHERE k.pea_rate IS NOT NULL)                                  AS agebs_with_pea_data,
    COUNT(*) FILTER (WHERE k.pea_rate IS NULL)                                      AS suppressed_or_null_agebs,
    SUM(c.pea)                                                                      AS pea,
    SUM(c.pop_12_plus) FILTER (WHERE c.pea IS NOT NULL)                             AS pop_12_plus,
    ROUND(SUM(c.pea)::NUMERIC
          / NULLIF(SUM(c.pop_12_plus) FILTER (WHERE c.pea IS NOT NULL), 0), 4)     AS citywide_pea_rate,
    ROUND((AVG(k.pea_rate) FILTER (WHERE NOT k.low_population))::NUMERIC, 4)       AS mean_ageb_pea_rate,
    ROUND((MIN(k.pea_rate) FILTER (WHERE NOT k.low_population))::NUMERIC, 4)       AS min_pea_rate,
    ROUND((MAX(k.pea_rate) FILTER (WHERE NOT k.low_population))::NUMERIC, 4)       AS max_pea_rate
FROM dw.v_kpi_ageb k
JOIN dw.fact_census_ageb c USING (geo_key);

\echo '=== KPI 04: Population by Age Group (pct_0_14, pct_15_64, pct_65_plus) ==='
-- Share of the urban population in each age group (Σ group / Σ pop_total over the
-- AGEBs where the group is published), next to the unweighted mean of AGEB shares
SELECT
    ROUND(100.0 * SUM(c.pop_0_14)
          / NULLIF(SUM(c.pop_total) FILTER (WHERE c.pop_0_14 IS NOT NULL), 0), 2)    AS citywide_pct_0_14,
    ROUND(100.0 * SUM(c.pop_15_64)
          / NULLIF(SUM(c.pop_total) FILTER (WHERE c.pop_15_64 IS NOT NULL), 0), 2)   AS citywide_pct_15_64,
    ROUND(100.0 * SUM(c.pop_65_plus)
          / NULLIF(SUM(c.pop_total) FILTER (WHERE c.pop_65_plus IS NOT NULL), 0), 2) AS citywide_pct_65_plus,
    ROUND((AVG(k.pct_0_14) FILTER (WHERE NOT k.low_population))::NUMERIC, 2)        AS mean_ageb_pct_0_14,
    ROUND((AVG(k.pct_15_64) FILTER (WHERE NOT k.low_population))::NUMERIC, 2)       AS mean_ageb_pct_15_64,
    ROUND((AVG(k.pct_65_plus) FILTER (WHERE NOT k.low_population))::NUMERIC, 2)     AS mean_ageb_pct_65_plus
FROM dw.v_kpi_ageb k
JOIN dw.fact_census_ageb c USING (geo_key);

\echo '=== KPI 05: Total Economic Establishments (businesses_total) ==='
-- Total DENUE businesses inside CDMX urban AGEBs
SELECT
    COUNT(*)                                            AS total_agebs,
    SUM(businesses_total)                               AS total_establishments,
    ROUND(AVG(businesses_total), 1)                     AS mean_establishments_per_ageb,
    MIN(businesses_total)                               AS min_establishments,
    MAX(businesses_total)                               AS max_establishments
FROM dw.v_kpi_ageb;

\echo '=== KPI 06: Business Density (business_density_km2) ==='
-- Establishments per square kilometre
SELECT
    ROUND(SUM(businesses_total)::NUMERIC / NULLIF(SUM(area_km2), 0)::NUMERIC, 2) AS citywide_business_density_km2,
    ROUND(AVG(business_density_km2)::NUMERIC, 2)                                  AS mean_business_density_km2,
    ROUND(MIN(business_density_km2)::NUMERIC, 2)                                  AS min_business_density_km2,
    ROUND(MAX(business_density_km2)::NUMERIC, 2)                                  AS max_business_density_km2
FROM dw.v_kpi_ageb;

\echo '=== KPI 07: Businesses per 1,000 Residents (businesses_per_1k) ==='
-- Business intensity relative to resident population
SELECT
    ROUND(1000.0 * SUM(businesses_total) / NULLIF(SUM(pop_total), 0), 2)            AS citywide_businesses_per_1k,
    ROUND((AVG(businesses_per_1k) FILTER (WHERE NOT low_population))::NUMERIC, 2)  AS mean_businesses_per_1k,
    ROUND((MIN(businesses_per_1k) FILTER (WHERE NOT low_population))::NUMERIC, 2)  AS min_businesses_per_1k,
    ROUND((MAX(businesses_per_1k) FILTER (WHERE NOT low_population))::NUMERIC, 2)  AS max_businesses_per_1k
FROM dw.v_kpi_ageb;

\echo '=== KPI 08: Retail Density (retail_density_km2) ==='
-- SCIAN sector 46 establishments per km2
SELECT
    SUM(retail_total)                                                              AS total_retail_establishments,
    ROUND(SUM(retail_total)::NUMERIC / NULLIF(SUM(area_km2), 0)::NUMERIC, 2)       AS citywide_retail_density_km2,
    ROUND(AVG(retail_density_km2)::NUMERIC, 2)                                     AS mean_retail_density_km2,
    ROUND(MAX(retail_density_km2)::NUMERIC, 2)                                     AS max_retail_density_km2
FROM dw.v_kpi_ageb;

\echo '=== KPI 09: Service Density (service_density_km2) ==='
-- Private services sectors (51-56, 61, 62, 71, 72, 81) establishments per km2
SELECT
    SUM(services_total)                                                            AS total_service_establishments,
    ROUND(SUM(services_total)::NUMERIC / NULLIF(SUM(area_km2), 0)::NUMERIC, 2)     AS citywide_service_density_km2,
    ROUND(AVG(service_density_km2)::NUMERIC, 2)                                    AS mean_service_density_km2,
    ROUND(MAX(service_density_km2)::NUMERIC, 2)                                    AS max_service_density_km2
FROM dw.v_kpi_ageb;

\echo '=== KPI 10: Dominant Economic Activity by AGEB (dominant_sector) ==='
-- Distribution of dominant SCIAN sectors across AGEBs; dominant_sector_share is a 0-1 fraction
SELECT
    COALESCE(dominant_sector, 'No establishments')        AS dominant_sector,
    COUNT(*)                                              AS ageb_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)    AS ageb_share_pct,
    ROUND((100 * AVG(dominant_sector_share))::NUMERIC, 1) AS mean_dominant_share_pct
FROM dw.v_kpi_ageb
GROUP BY dominant_sector
ORDER BY ageb_count DESC;

\echo '=== KPI 11: Total Crime Incidents (crime_total) ==='
-- Total investigation files retained in urban AGEBs (offences of 1 Jan - 31 Jul 2024)
SELECT
    COUNT(*)                                            AS total_agebs,
    SUM(crime_total)                                    AS total_incidents,
    ROUND(AVG(crime_total), 1)                          AS mean_incidents_per_ageb,
    COUNT(*) FILTER (WHERE crime_total = 0)             AS zero_crime_agebs,
    MAX(crime_total)                                    AS max_incidents_single_ageb
FROM dw.v_kpi_ageb;

\echo '=== KPI 12: Crime Rate per 1,000 Residents (crime_rate_per_1k) ==='
-- Investigation files per 1,000 residents
SELECT
    ROUND(1000.0 * SUM(crime_total) / NULLIF(SUM(pop_total), 0), 2)                AS citywide_crime_rate_per_1k,
    ROUND((AVG(crime_rate_per_1k) FILTER (WHERE NOT low_population))::NUMERIC, 2) AS mean_ageb_crime_rate_per_1k,
    ROUND((MIN(crime_rate_per_1k) FILTER (WHERE NOT low_population))::NUMERIC, 2) AS min_ageb_crime_rate,
    ROUND((MAX(crime_rate_per_1k) FILTER (WHERE NOT low_population))::NUMERIC, 2) AS max_ageb_crime_rate
FROM dw.v_kpi_ageb;

\echo '=== KPI 13: Crime relative to Business Activity (crimes_per_100_businesses) ==='
-- Incidents per 100 establishments (the ratio is NULL in AGEBs without establishments)
SELECT
    ROUND(100.0 * SUM(crime_total) / NULLIF(SUM(businesses_total), 0), 2)  AS citywide_crimes_per_100_biz,
    ROUND(AVG(crimes_per_100_businesses)::NUMERIC, 2)                      AS mean_ageb_crimes_per_100_biz,
    ROUND(MIN(crimes_per_100_businesses)::NUMERIC, 2)                      AS min_crimes_per_100_biz,
    ROUND(MAX(crimes_per_100_businesses)::NUMERIC, 2)                      AS max_crimes_per_100_biz
FROM dw.v_kpi_ageb;

\echo '=== KPI 14a: Incidents by Category and Time Band (dw.v_crime_by_type_time) ==='
-- Incident counts cross-tabulated by analytical category and time band
SELECT
    time_band,
    SUM(incidents) FILTER (WHERE crime_category = 'Property') AS property_crimes,
    SUM(incidents) FILTER (WHERE crime_category = 'Violent')  AS violent_crimes,
    SUM(incidents) FILTER (WHERE crime_category = 'Sexual')   AS sexual_crimes,
    SUM(incidents) FILTER (WHERE crime_category = 'Other')    AS other_crimes,
    SUM(incidents)                                            AS total_incidents,
    ROUND(100.0 * SUM(incidents) / SUM(SUM(incidents)) OVER (), 2) AS share_pct
FROM dw.v_crime_by_type_time
GROUP BY time_band
ORDER BY
    CASE time_band
        WHEN 'Night (00-05)' THEN 1
        WHEN 'Morning (06-11)' THEN 2
        WHEN 'Afternoon (12-17)' THEN 3
        WHEN 'Evening (18-23)' THEN 4
        ELSE 5
    END;

\echo '=== KPI 14b: Top 10 Crime Types with Weekend and Night Shares (dw.v_crime_by_type_time) ==='
-- Incidents by harmonised crime type; shares of incidents on weekends and at night (00-05)
SELECT
    crime_type,
    crime_category,
    SUM(incidents)                                                                          AS incidents,
    ROUND(100.0 * SUM(incidents) FILTER (WHERE is_weekend) / SUM(incidents), 1)              AS weekend_share_pct,
    ROUND(100.0 * SUM(incidents) FILTER (WHERE time_band = 'Night (00-05)') / SUM(incidents), 1) AS night_share_pct
FROM dw.v_crime_by_type_time
GROUP BY crime_type, crime_category
ORDER BY incidents DESC
LIMIT 10;

\echo '=== KPI 14c: Incidents by Month and Category (dw.v_crime_by_type_time) ==='
-- Monthly incidents; the FGJ file covers investigations opened 1 Jan - 31 Jul 2024
SELECT
    year,
    month,
    month_name,
    SUM(incidents) FILTER (WHERE crime_category = 'Property') AS property_crimes,
    SUM(incidents) FILTER (WHERE crime_category = 'Violent')  AS violent_crimes,
    SUM(incidents) FILTER (WHERE crime_category = 'Sexual')   AS sexual_crimes,
    SUM(incidents) FILTER (WHERE crime_category = 'Other')    AS other_crimes,
    SUM(incidents)                                            AS total_incidents
FROM dw.v_crime_by_type_time
GROUP BY year, month, month_name
ORDER BY year, month;

\echo '=== Additional Analysis A: Top 10 AGEBs by Business Density ==='
SELECT
    k.cvegeo,
    g.mun_name                                AS alcaldia,
    k.businesses_total,
    ROUND(k.area_km2::NUMERIC, 3)             AS area_km2,
    ROUND(k.business_density_km2::NUMERIC, 1) AS business_density_km2,
    k.dominant_sector
FROM dw.v_kpi_ageb k
JOIN dw.dim_geography g USING (geo_key)
ORDER BY k.business_density_km2 DESC NULLS LAST
LIMIT 10;

\echo '=== Additional Analysis B: Top 10 AGEBs by Crime Rate (pop >= 100) ==='
SELECT
    k.cvegeo,
    g.mun_name                                AS alcaldia,
    k.pop_total,
    k.crime_total,
    ROUND(k.crime_rate_per_1k::NUMERIC, 2)    AS crime_rate_per_1k,
    k.businesses_total
FROM dw.v_kpi_ageb k
JOIN dw.dim_geography g USING (geo_key)
WHERE NOT k.low_population
ORDER BY k.crime_rate_per_1k DESC NULLS LAST
LIMIT 10;

\echo '=== Additional Analysis C: Top 10 AGEBs by Crime Incidents (no denominator) ==='
-- Absolute counts, unaffected by small resident populations
SELECT
    k.cvegeo,
    g.mun_name                                AS alcaldia,
    k.crime_total,
    k.pop_total,
    k.businesses_total,
    ROUND(k.crimes_per_100_businesses::NUMERIC, 2) AS crimes_per_100_businesses
FROM dw.v_kpi_ageb k
JOIN dw.dim_geography g USING (geo_key)
ORDER BY k.crime_total DESC, k.cvegeo
LIMIT 10;

\echo '=== Additional Analysis D: Top 10 AGEBs by Population Density (pop >= 100) ==='
SELECT
    k.cvegeo,
    g.mun_name                                AS alcaldia,
    k.pop_total,
    ROUND(k.area_km2::NUMERIC, 3)             AS area_km2,
    ROUND(k.pop_density_km2::NUMERIC, 1)      AS pop_density_km2
FROM dw.v_kpi_ageb k
JOIN dw.dim_geography g USING (geo_key)
WHERE NOT k.low_population
ORDER BY k.pop_density_km2 DESC NULLS LAST
LIMIT 10;

\echo '=== Additional Analysis E: KPIs Aggregated by Alcaldía (16 Alcaldías) ==='
-- Sums of numerators and denominators per alcaldía, then division with NULLIF —
-- never the mean of AGEB ratios. Dominant sector = sector with most establishments
-- in the alcaldía (ties alphabetical, as in dw.v_kpi_ageb).
WITH ageb AS (
    SELECT g.mun_name, k.pop_total, k.area_km2, k.businesses_total, k.retail_total,
           k.services_total, k.crime_total, c.pea, c.pop_12_plus
    FROM dw.v_kpi_ageb k
    JOIN dw.dim_geography g USING (geo_key)
    JOIN dw.fact_census_ageb c USING (geo_key)
),
sector AS (
    SELECT
        g.mun_name,
        s.sector_name,
        SUM(s.establishments) AS establishments,
        ROW_NUMBER() OVER (PARTITION BY g.mun_name
                           ORDER BY SUM(s.establishments) DESC, s.sector_name) AS sector_rank
    FROM dw.v_business_by_sector s
    JOIN dw.dim_geography g USING (geo_key)
    GROUP BY g.mun_name, s.sector_name
)
SELECT
    a.mun_name                                                                       AS alcaldia,
    COUNT(*)                                                                         AS ageb_count,
    SUM(a.pop_total)                                                                 AS pop_total,
    ROUND(SUM(a.area_km2)::NUMERIC, 2)                                               AS area_km2,
    ROUND(SUM(a.pop_total)::NUMERIC / NULLIF(SUM(a.area_km2), 0)::NUMERIC, 1)        AS pop_density_km2,
    ROUND(SUM(a.pea)::NUMERIC
          / NULLIF(SUM(a.pop_12_plus) FILTER (WHERE a.pea IS NOT NULL), 0), 4)      AS pea_rate,
    SUM(a.businesses_total)                                                          AS businesses_total,
    ROUND(SUM(a.businesses_total)::NUMERIC / NULLIF(SUM(a.area_km2), 0)::NUMERIC, 1) AS business_density_km2,
    ROUND(SUM(a.retail_total)::NUMERIC / NULLIF(SUM(a.area_km2), 0)::NUMERIC, 1)     AS retail_density_km2,
    ROUND(SUM(a.services_total)::NUMERIC / NULLIF(SUM(a.area_km2), 0)::NUMERIC, 1)   AS service_density_km2,
    ROUND(1000.0 * SUM(a.businesses_total) / NULLIF(SUM(a.pop_total), 0), 1)         AS businesses_per_1k,
    MAX(s.sector_name)                                                               AS dominant_sector,
    ROUND(100.0 * MAX(s.establishments) / NULLIF(SUM(a.businesses_total), 0), 1)     AS dominant_sector_share_pct,
    SUM(a.crime_total)                                                               AS crime_total,
    ROUND(1000.0 * SUM(a.crime_total) / NULLIF(SUM(a.pop_total), 0), 2)              AS crime_rate_per_1k,
    ROUND(100.0 * SUM(a.crime_total) / NULLIF(SUM(a.businesses_total), 0), 2)        AS crimes_per_100_businesses
FROM ageb a
JOIN sector s ON s.mun_name = a.mun_name AND s.sector_rank = 1
GROUP BY a.mun_name
ORDER BY crime_rate_per_1k DESC;

\echo '=== Additional Analysis F: Crime per 100 Businesses by Dominant Sector ==='
-- Sectors that dominate only a handful of AGEBs (agebs_dominated < 10) rest on very few
-- establishments, so their ratios are unstable; read them together with agebs_dominated.
SELECT
    dominant_sector,
    COUNT(*)                                                                AS agebs_dominated,
    SUM(businesses_total)                                                   AS total_establishments,
    SUM(crime_total)                                                        AS total_crimes,
    ROUND(100.0 * SUM(crime_total) / NULLIF(SUM(businesses_total), 0), 2)   AS crimes_per_100_businesses
FROM dw.v_kpi_ageb
WHERE dominant_sector IS NOT NULL
GROUP BY dominant_sector
ORDER BY crimes_per_100_businesses DESC;
