-- =====================================================================
-- 02_load.sql — Load available staging tables into the dimensional model.
-- Re-runnable; fixed reference dimensions (hour and business size) persist.
-- Missing staging tables are reported, allowing partial pipeline runs while
-- data transforms are still being completed.
-- =====================================================================

TRUNCATE TABLE
    dw.fact_census_ageb,
    dw.fact_business,
    dw.fact_crime_incident,
    dw.dim_source,
    dw.dim_geography,
    dw.dim_date,
    dw.dim_economic_activity,
    dw.dim_crime_type
RESTART IDENTITY CASCADE;

DO $load$
DECLARE
    date_sources TEXT;
    date_sql TEXT;
    table_name TEXT;
    row_count BIGINT;
BEGIN
    IF to_regclass('stg.source') IS NULL THEN
        RAISE EXCEPTION 'Required staging table stg.source is missing; run the stage step first';
    END IF;

    INSERT INTO dw.dim_source (
        source_code, source_name, publisher, url, version_label, original_grain, sha256
    )
    SELECT
        source_code, source_name, publisher, url, version_label, original_grain, sha256
    FROM stg.source;

    IF to_regclass('stg.ageb') IS NOT NULL THEN
        INSERT INTO dw.dim_geography (
            cvegeo, cve_ent, cve_mun, cve_loc, cve_ageb, mun_name, loc_name,
            is_city_core, area_km2, geom
        )
        SELECT
            cvegeo, cve_ent, cve_mun, cve_loc, cve_ageb, mun_name, loc_name,
            is_city_core, area_km2,
            ST_Multi(
                ST_Transform(
                    CASE WHEN ST_SRID(geometry) = 0
                         THEN ST_SetSRID(geometry, 6372)
                         ELSE geometry
                    END,
                    6372
                )
            )::geometry(MultiPolygon, 6372)
        FROM stg.ageb;
    ELSE
        RAISE NOTICE '[load] stg.ageb is missing; dim_geography and dependent facts will be empty';
    END IF;

    date_sources := '';
    IF to_regclass('stg.business') IS NOT NULL THEN
        date_sources := 'SELECT alta_date::date AS event_date FROM stg.business';
    ELSE
        RAISE NOTICE '[load] stg.business is missing; fact_business will be empty';
    END IF;
    IF to_regclass('stg.crime') IS NOT NULL THEN
        IF date_sources <> '' THEN
            date_sources := date_sources || ' UNION ALL ';
        END IF;
        date_sources := date_sources || 'SELECT incident_date::date AS event_date FROM stg.crime';
    ELSE
        RAISE NOTICE '[load] stg.crime is missing; fact_crime_incident will be empty';
    END IF;

    IF date_sources <> '' THEN
        date_sql := format(
            'INSERT INTO dw.dim_date (
                 date_key, full_date, year, quarter, month, month_name, day,
                 day_of_week, day_name, is_weekend
             )
             SELECT
                 to_char(d.full_date, ''YYYYMMDD'')::integer,
                 d.full_date,
                 extract(year FROM d.full_date)::smallint,
                 extract(quarter FROM d.full_date)::smallint,
                 extract(month FROM d.full_date)::smallint,
                 (ARRAY[''January'', ''February'', ''March'', ''April'', ''May'', ''June'',
                        ''July'', ''August'', ''September'', ''October'', ''November'', ''December''])
                    [extract(month FROM d.full_date)::integer],
                 extract(day FROM d.full_date)::smallint,
                 extract(isodow FROM d.full_date)::smallint,
                 (ARRAY[''Monday'', ''Tuesday'', ''Wednesday'', ''Thursday'', ''Friday'',
                        ''Saturday'', ''Sunday''])[extract(isodow FROM d.full_date)::integer],
                 extract(isodow FROM d.full_date) IN (6, 7)
             FROM generate_series(
                 (SELECT min(event_date) FROM (%s) AS source_dates),
                 (SELECT max(event_date) FROM (%s) AS source_dates),
                 interval ''1 day''
             ) AS d(full_date)',
            date_sources,
            date_sources
        );
        EXECUTE date_sql;
    END IF;

    IF to_regclass('stg.economic_activity') IS NOT NULL THEN
        INSERT INTO dw.dim_economic_activity (
            scian_code, activity_name, subsector_code, sector_code, sector_name, activity_group
        )
        SELECT DISTINCT
            scian_code, activity_name, subsector_code, sector_code, sector_name, activity_group
        FROM stg.economic_activity;
    ELSE
        RAISE NOTICE '[load] stg.economic_activity is missing; dim_economic_activity and fact_business will be empty';
    END IF;

    IF to_regclass('stg.crime') IS NOT NULL THEN
        INSERT INTO dw.dim_crime_type (crime_type, crime_type_raw, crime_category)
        SELECT DISTINCT ON (crime_type) crime_type, crime_type_raw, crime_category
        FROM stg.crime;
    ELSE
        RAISE NOTICE '[load] stg.crime is missing; dim_crime_type will be empty';
    END IF;

    IF to_regclass('stg.census_ageb') IS NOT NULL THEN
        INSERT INTO dw.fact_census_ageb (
            geo_key, source_key, census_year, pop_total, pop_female, pop_male,
            pop_0_14, pop_15_64, pop_65_plus, pop_12_plus, pop_18_plus, pop_60_plus,
            pea, pea_female, pea_male, pop_inactive, pop_employed, pop_unemployed,
            avg_schooling, households, dwellings_total, dwellings_inhabited,
            avg_occupants, n_suppressed_fields
        )
        SELECT
            g.geo_key, s.source_key, 2020, c.pop_total, c.pop_female, c.pop_male,
            c.pop_0_14, c.pop_15_64, c.pop_65_plus, c.pop_12_plus, c.pop_18_plus,
            c.pop_60_plus, c.pea, c.pea_female, c.pea_male, c.pop_inactive,
            c.pop_employed, c.pop_unemployed, c.avg_schooling, c.households,
            c.dwellings_total, c.dwellings_inhabited, c.avg_occupants,
            c.n_suppressed_fields
        FROM stg.census_ageb AS c
        JOIN dw.dim_geography AS g USING (cvegeo)
        JOIN dw.dim_source AS s ON s.source_code = 'census_ageb_2020_09';
    ELSE
        RAISE NOTICE '[load] stg.census_ageb is missing; fact_census_ageb will be empty';
    END IF;

    IF to_regclass('stg.business') IS NOT NULL
       AND to_regclass('stg.economic_activity') IS NOT NULL THEN
        INSERT INTO dw.fact_business (
            denue_id, clee, geo_key, activity_key, size_key, date_key, source_key,
            establishment_name, cvegeo_reported, establishment_count, geom
        )
        SELECT
            b.denue_id, b.clee, g.geo_key, a.activity_key, z.size_key, d.date_key,
            s.source_key, b.establishment_name, b.cvegeo_reported, 1,
            ST_Transform(
                CASE WHEN ST_SRID(b.geometry) = 0
                     THEN ST_SetSRID(b.geometry, 6372)
                     ELSE b.geometry
                END,
                6372
            )::geometry(Point, 6372)
        FROM stg.business AS b
        JOIN dw.dim_geography AS g USING (cvegeo)
        JOIN dw.dim_economic_activity AS a USING (scian_code)
        JOIN dw.dim_business_size AS z USING (per_ocu_label)
        JOIN dw.dim_source AS s ON s.source_code = 'denue_09'
        LEFT JOIN dw.dim_date AS d ON d.full_date = b.alta_date::date;
    ELSIF to_regclass('stg.business') IS NOT NULL THEN
        RAISE NOTICE '[load] stg.economic_activity is missing; fact_business will be empty';
    END IF;

    IF to_regclass('stg.crime') IS NOT NULL THEN
        INSERT INTO dw.fact_crime_incident (
            source_incident_id, geo_key, crime_type_key, date_key, hour_key,
            source_key, incident_count, geom
        )
        SELECT
            c.source_incident_id, g.geo_key, t.crime_type_key, d.date_key,
            CASE WHEN c.incident_hour BETWEEN 0 AND 23
                 THEN c.incident_hour::smallint
                 ELSE -1::smallint
            END,
            s.source_key, 1,
            ST_Transform(
                CASE WHEN ST_SRID(c.geometry) = 0
                     THEN ST_SetSRID(c.geometry, 6372)
                     ELSE c.geometry
                END,
                6372
            )::geometry(Point, 6372)
        FROM stg.crime AS c
        JOIN dw.dim_geography AS g USING (cvegeo)
        JOIN dw.dim_crime_type AS t USING (crime_type)
        JOIN dw.dim_source AS s ON s.source_code = 'crime_fgj_2024'
        LEFT JOIN dw.dim_date AS d ON d.full_date = c.incident_date::date;
    END IF;

    FOREACH table_name IN ARRAY ARRAY[
        'dim_source', 'dim_geography', 'dim_date', 'dim_hour',
        'dim_economic_activity', 'dim_business_size', 'dim_crime_type',
        'fact_census_ageb', 'fact_business', 'fact_crime_incident'
    ] LOOP
        EXECUTE format('SELECT count(*) FROM dw.%I', table_name) INTO row_count;
        RAISE NOTICE '[counts] dw.% = % rows', table_name, row_count;
    END LOOP;
END
$load$;
