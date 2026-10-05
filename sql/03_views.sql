-- =====================================================================
-- 03_views.sql  —  KPI views on top of the dw star schema
-- Re-runnable. Every Phase 3 analysis reads from these views
-- (src/analysis/data.py:load_kpis), never from raw or processed files.
-- =====================================================================

DROP VIEW IF EXISTS dw.v_kpi_ageb;
DROP VIEW IF EXISTS dw.v_business_by_sector;
DROP VIEW IF EXISTS dw.v_crime_by_type_time;

-- ---------------------------------------------------------------------
-- Establishments per AGEB and SCIAN sector.
-- Grain: AGEB x sector (only combinations with at least one establishment).
-- ---------------------------------------------------------------------
CREATE VIEW dw.v_business_by_sector AS
SELECT
    g.geo_key,
    g.cvegeo,
    a.sector_code,
    a.sector_name,
    a.activity_group,
    SUM(b.establishment_count)::INTEGER AS establishments,
    SUM(b.establishment_count)::DOUBLE PRECISION
        / SUM(SUM(b.establishment_count)) OVER (PARTITION BY g.geo_key) AS share_in_ageb
FROM dw.fact_business b
JOIN dw.dim_geography g          ON g.geo_key = b.geo_key
JOIN dw.dim_economic_activity a  ON a.activity_key = b.activity_key
GROUP BY g.geo_key, g.cvegeo, a.sector_code, a.sector_name, a.activity_group;

-- ---------------------------------------------------------------------
-- KPI "Incidents by Type and Time".
-- Grain: AGEB x crime type x year-month x day of week x time band.
-- Incidents without date keep NULL calendar attributes; unknown hour -> 'Unknown'.
-- ---------------------------------------------------------------------
CREATE VIEW dw.v_crime_by_type_time AS
SELECT
    g.geo_key,
    g.cvegeo,
    t.crime_type,
    t.crime_category,
    d.year,
    d.month,
    d.month_name,
    d.day_of_week,
    d.day_name,
    d.is_weekend,
    h.time_band,
    SUM(f.incident_count)::INTEGER AS incidents
FROM dw.fact_crime_incident f
JOIN dw.dim_geography g    ON g.geo_key = f.geo_key
JOIN dw.dim_crime_type t   ON t.crime_type_key = f.crime_type_key
JOIN dw.dim_hour h         ON h.hour_key = f.hour_key
LEFT JOIN dw.dim_date d    ON d.date_key = f.date_key
GROUP BY g.geo_key, g.cvegeo, t.crime_type, t.crime_category, d.year, d.month, d.month_name,
         d.day_of_week, d.day_name, d.is_weekend, h.time_band;

-- ---------------------------------------------------------------------
-- All territorial KPIs, one row per urban AGEB (contract: TEAM_PLAN §3.4).
-- Densities per km2; per-capita rates per 1,000 residents; shares in %.
-- Ratios use NULLIF, so an empty denominator yields NULL (never a division error).
-- low_population flags AGEBs with < 100 residents, whose rates are unstable.
-- ---------------------------------------------------------------------
CREATE VIEW dw.v_kpi_ageb AS
WITH business AS (
    SELECT
        b.geo_key,
        SUM(b.establishment_count)                                            AS businesses_total,
        SUM(b.establishment_count) FILTER (WHERE a.activity_group = 'Retail')   AS retail_total,
        SUM(b.establishment_count) FILTER (WHERE a.activity_group = 'Services') AS services_total
    FROM dw.fact_business b
    JOIN dw.dim_economic_activity a ON a.activity_key = b.activity_key
    GROUP BY b.geo_key
),
dominant AS (
    -- sector with most establishments; ties broken alphabetically
    SELECT DISTINCT ON (geo_key) geo_key, sector_name, share_in_ageb
    FROM dw.v_business_by_sector
    ORDER BY geo_key, establishments DESC, sector_name
),
crime AS (
    SELECT geo_key, SUM(incident_count) AS crime_total
    FROM dw.fact_crime_incident
    GROUP BY geo_key
),
base AS (
    SELECT
        g.geo_key,
        g.cvegeo,
        g.loc_name,
        g.is_city_core,
        g.area_km2::DOUBLE PRECISION                AS area_km2,
        c.pop_total,
        c.pop_0_14,
        c.pop_15_64,
        c.pop_65_plus,
        c.pop_12_plus,
        c.pea,
        COALESCE(b.businesses_total, 0)::INTEGER    AS businesses_total,
        COALESCE(b.retail_total, 0)::INTEGER        AS retail_total,
        COALESCE(b.services_total, 0)::INTEGER      AS services_total,
        d.sector_name                               AS dominant_sector,
        d.share_in_ageb                             AS dominant_sector_share,
        COALESCE(k.crime_total, 0)::INTEGER         AS crime_total,
        g.geom
    FROM dw.dim_geography g
    LEFT JOIN dw.fact_census_ageb c ON c.geo_key = g.geo_key
    LEFT JOIN business b            ON b.geo_key = g.geo_key
    LEFT JOIN dominant d            ON d.geo_key = g.geo_key
    LEFT JOIN crime k               ON k.geo_key = g.geo_key
)
SELECT
    geo_key,
    cvegeo,
    loc_name,
    is_city_core,
    COALESCE(pop_total, 0) < 100                                         AS low_population,
    area_km2,
    -- Demographic
    pop_total,
    pop_total / area_km2                                                 AS pop_density_km2,
    pea::DOUBLE PRECISION / NULLIF(pop_12_plus, 0)                       AS pea_rate,
    100 * pop_0_14::DOUBLE PRECISION    / NULLIF(pop_total, 0)                           AS pct_0_14,
    100 * pop_15_64::DOUBLE PRECISION   / NULLIF(pop_total, 0)                           AS pct_15_64,
    100 * pop_65_plus::DOUBLE PRECISION / NULLIF(pop_total, 0)                           AS pct_65_plus,
    -- Economic
    businesses_total,
    businesses_total / area_km2                                          AS business_density_km2,
    1000 * businesses_total::DOUBLE PRECISION / NULLIF(pop_total, 0)                     AS businesses_per_1k,
    retail_total,
    retail_total / area_km2                                              AS retail_density_km2,
    services_total,
    services_total / area_km2                                            AS service_density_km2,
    dominant_sector,
    dominant_sector_share,
    -- Public safety
    crime_total,
    1000 * crime_total::DOUBLE PRECISION / NULLIF(pop_total, 0)                          AS crime_rate_per_1k,
    100 * crime_total::DOUBLE PRECISION / NULLIF(businesses_total, 0)                    AS crimes_per_100_businesses,
    geom
FROM base;
