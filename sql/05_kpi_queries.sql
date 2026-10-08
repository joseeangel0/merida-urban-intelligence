-- =====================================================================
-- Mexico City Urban Intelligence — KPI Demonstration Queries
-- Owner: Gustavo Fuentes (Audileleach) · TEAM_PLAN §4.6 & README §6
--
-- Read-only analytical queries demonstrating that every required KPI,
-- summary statistic, and territorial comparison can be answered directly
-- from the Data Warehouse views (dw.v_kpi_ageb, dw.v_crime_by_type_time,
-- and dw.v_business_by_sector).
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
-- Overall urban density and quartiles (residents / km2)
SELECT
    ROUND(SUM(pop_total)::NUMERIC / SUM(area_km2)::NUMERIC, 2)  AS overall_urban_density_km2,
    ROUND(AVG(pop_density_km2)::NUMERIC, 2)                     AS mean_ageb_density_km2,
    ROUND(MIN(pop_density_km2)::NUMERIC, 2)                     AS min_density_km2,
    ROUND(MAX(pop_density_km2)::NUMERIC, 2)                     AS max_density_km2
FROM dw.v_kpi_ageb
WHERE NOT low_population;

\echo '=== KPI 03: Economically Active Population Rate (dw.v_kpi_ageb: pea_rate) ==='
-- PEA rate = PEA / P_12YMAS (excludes low population units)
SELECT
    COUNT(*) FILTER (WHERE pea_rate IS NOT NULL)        AS agebs_with_pea_data,
    COUNT(*) FILTER (WHERE pea_rate IS NULL)            AS suppressed_or_null_agebs,
    ROUND(AVG(pea_rate)::NUMERIC, 4)                    AS mean_pea_rate,
    ROUND(MIN(pea_rate)::NUMERIC, 4)                    AS min_pea_rate,
    ROUND(MAX(pea_rate)::NUMERIC, 4)                    AS max_pea_rate
FROM dw.v_kpi_ageb
WHERE NOT low_population;

\echo '=== KPI 04: Population by Age Group (pct_0_14, pct_15_64, pct_65_plus) ==='
-- Age shares (%) across CDMX urban population
SELECT
    ROUND(AVG(pct_0_14)::NUMERIC, 2)                    AS mean_pct_0_14,
    ROUND(AVG(pct_15_64)::NUMERIC, 2)                   AS mean_pct_15_64,
    ROUND(AVG(pct_65_plus)::NUMERIC, 2)                 AS mean_pct_65_plus
FROM dw.v_kpi_ageb
WHERE NOT low_population;

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
    ROUND(SUM(businesses_total)::NUMERIC / SUM(area_km2)::NUMERIC, 2) AS overall_business_density_km2,
    ROUND(AVG(business_density_km2)::NUMERIC, 2)                       AS mean_business_density_km2,
    ROUND(MIN(business_density_km2)::NUMERIC, 2)                       AS min_business_density_km2,
    ROUND(MAX(business_density_km2)::NUMERIC, 2)                       AS max_business_density_km2
FROM dw.v_kpi_ageb;

\echo '=== KPI 07: Businesses per 1,000 Residents (businesses_per_1k) ==='
-- Business intensity relative to resident population
SELECT
    ROUND(AVG(businesses_per_1k)::NUMERIC, 2)           AS mean_businesses_per_1k,
    ROUND(MIN(businesses_per_1k)::NUMERIC, 2)           AS min_businesses_per_1k,
    ROUND(MAX(businesses_per_1k)::NUMERIC, 2)           AS max_businesses_per_1k
FROM dw.v_kpi_ageb
WHERE NOT low_population;

\echo '=== KPI 08: Retail Density (retail_density_km2) ==='
-- SCIAN sector 46 establishments per km2
SELECT
    SUM(retail_total)                                                   AS total_retail_establishments,
    ROUND(SUM(retail_total)::NUMERIC / SUM(area_km2)::NUMERIC, 2)       AS overall_retail_density_km2,
    ROUND(AVG(retail_density_km2)::NUMERIC, 2)                          AS mean_retail_density_km2,
    ROUND(MAX(retail_density_km2)::NUMERIC, 2)                          AS max_retail_density_km2
FROM dw.v_kpi_ageb;

\echo '=== KPI 09: Service Density (service_density_km2) ==='
-- Private services sectors (51-56, 61, 62, 71, 72, 81) establishments per km2
SELECT
    SUM(services_total)                                                 AS total_service_establishments,
    ROUND(SUM(services_total)::NUMERIC / SUM(area_km2)::NUMERIC, 2)     AS overall_service_density_km2,
    ROUND(AVG(service_density_km2)::NUMERIC, 2)                         AS mean_service_density_km2,
    ROUND(MAX(service_density_km2)::NUMERIC, 2)                         AS max_service_density_km2
FROM dw.v_kpi_ageb;

\echo '=== KPI 10: Dominant Economic Activity by AGEB (dominant_sector) ==='
-- Distribution of dominant SCIAN sectors across AGEBs
SELECT
    COALESCE(dominant_sector, 'No establishments')      AS dominant_sector,
    COUNT(*)                                            AS ageb_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS ageb_share_pct,
    ROUND(AVG(dominant_sector_share)::NUMERIC, 2)       AS mean_within_ageb_share_pct
FROM dw.v_kpi_ageb
GROUP BY dominant_sector
ORDER BY ageb_count DESC;

\echo '=== KPI 11: Total Crime Incidents (crime_total) ==='
-- Total investigation files retained in urban AGEBs (Jan-Jul 2024 snapshot)
SELECT
    COUNT(*)                                            AS total_agebs,
    SUM(crime_total)                                    AS total_incidents,
    ROUND(AVG(crime_total), 1)                          AS mean_incidents_per_ageb,
    COUNT(*) FILTER (WHERE crime_total = 0)             AS zero_crime_agebs,
    MAX(crime_total)                                    AS max_incidents_single_ageb
FROM dw.v_kpi_ageb;

\echo '=== KPI 12: Crime Rate per 1,000 Residents (crime_rate_per_1k) ==='
-- Investigation files per 1,000 residents (excluding low_population)
SELECT
    ROUND(1000.0 * SUM(crime_total)::NUMERIC / SUM(pop_total)::NUMERIC, 2) AS overall_crime_rate_per_1k,
    ROUND(AVG(crime_rate_per_1k)::NUMERIC, 2)                              AS mean_ageb_crime_rate_per_1k,
    ROUND(MIN(crime_rate_per_1k)::NUMERIC, 2)                              AS min_ageb_crime_rate,
    ROUND(MAX(crime_rate_per_1k)::NUMERIC, 2)                              AS max_ageb_crime_rate
FROM dw.v_kpi_ageb
WHERE NOT low_population;

\echo '=== KPI 13: Crime relative to Business Activity (crimes_per_100_businesses) ==='
-- Incidents per 100 establishments (excluding AGEBs without establishments)
SELECT
    ROUND(100.0 * SUM(crime_total)::NUMERIC / SUM(businesses_total)::NUMERIC, 2) AS overall_crimes_per_100_biz,
    ROUND(AVG(crimes_per_100_businesses)::NUMERIC, 2)                            AS mean_ageb_crimes_per_100_biz,
    ROUND(MIN(crimes_per_100_businesses)::NUMERIC, 2)                            AS min_crimes_per_100_biz,
    ROUND(MAX(crimes_per_100_businesses)::NUMERIC, 2)                            AS max_crimes_per_100_biz
FROM dw.v_kpi_ageb
WHERE businesses_total > 0;

\echo '=== KPI 14: Incidents by Category and Time Band (dw.v_crime_by_type_time) ==='
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

\echo '=== Additional Analysis A: Top 10 AGEBs by Business Density ==='
SELECT
    cvegeo,
    loc_name,
    businesses_total,
    ROUND(area_km2::NUMERIC, 3)             AS area_km2,
    ROUND(business_density_km2::NUMERIC, 1) AS business_density_km2,
    dominant_sector
FROM dw.v_kpi_ageb
ORDER BY business_density_km2 DESC
LIMIT 10;

\echo '=== Additional Analysis B: Top 10 AGEBs by Crime Rate (pop >= 100) ==='
SELECT
    cvegeo,
    loc_name,
    pop_total,
    crime_total,
    ROUND(crime_rate_per_1k::NUMERIC, 2)    AS crime_rate_per_1k,
    businesses_total
FROM dw.v_kpi_ageb
WHERE NOT low_population
ORDER BY crime_rate_per_1k DESC
LIMIT 10;

\echo '=== Additional Analysis C: KPIs Aggregated by Alcaldía (16 Alcaldías) ==='
-- NOTE: Correct statistical aggregation requires summing numerators and denominators
-- before division with NULLIF, never averaging AGEB-level ratios.
SELECT
    g.mun_name                                                          AS alcaldia,
    COUNT(k.geo_key)                                                    AS ageb_count,
    SUM(k.pop_total)                                                    AS pop_total,
    ROUND(SUM(k.area_km2)::NUMERIC, 2)                                  AS area_km2,
    ROUND(SUM(k.pop_total)::NUMERIC / NULLIF(SUM(k.area_km2), 0)::NUMERIC, 1) AS pop_density_km2,
    SUM(k.businesses_total)                                             AS businesses_total,
    ROUND(SUM(k.businesses_total)::NUMERIC / NULLIF(SUM(k.area_km2), 0)::NUMERIC, 1) AS business_density_km2,
    ROUND(1000.0 * SUM(k.businesses_total)::NUMERIC / NULLIF(SUM(k.pop_total), 0)::NUMERIC, 1) AS biz_per_1k_residents,
    SUM(k.crime_total)                                                  AS crime_total,
    ROUND(1000.0 * SUM(k.crime_total)::NUMERIC / NULLIF(SUM(k.pop_total), 0)::NUMERIC, 2) AS crime_rate_per_1k,
    ROUND(100.0 * SUM(k.crime_total)::NUMERIC / NULLIF(SUM(k.businesses_total), 0)::NUMERIC, 2) AS crimes_per_100_biz
FROM dw.v_kpi_ageb k
JOIN dw.dim_geography g ON g.geo_key = k.geo_key
GROUP BY g.mun_name
ORDER BY crime_rate_per_1k DESC;

\echo '=== Additional Analysis D: Crime per 100 Businesses by Dominant Sector ==='
SELECT
    dominant_sector,
    COUNT(*)                                                            AS agebs_dominated,
    SUM(businesses_total)                                               AS total_establishments,
    SUM(crime_total)                                                    AS total_crimes,
    ROUND(100.0 * SUM(crime_total)::NUMERIC / NULLIF(SUM(businesses_total), 0)::NUMERIC, 2) AS crimes_per_100_businesses
FROM dw.v_kpi_ageb
WHERE dominant_sector IS NOT NULL
GROUP BY dominant_sector
ORDER BY crimes_per_100_businesses DESC;
