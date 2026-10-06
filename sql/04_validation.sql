-- =====================================================================
-- 04_validation.sql  —  Warehouse validation
-- Every check RAISEs an EXCEPTION on failure, so `python -m src.pipeline validate`
-- stops the pipeline. While the crime layer is not loaded yet, crime checks only
-- emit a WARNING. Results are reported with RAISE NOTICE.
-- =====================================================================

-- 1. Record counts: every dw table matches its staging source -------------
DO $$
DECLARE
    pairs TEXT[][] := ARRAY[
        ['stg.ageb',        'dw.dim_geography'],
        ['stg.census_ageb', 'dw.fact_census_ageb'],
        ['stg.business',    'dw.fact_business'],
        ['stg.crime',       'dw.fact_crime_incident']
    ];
    n_stg BIGINT;
    n_dw  BIGINT;
BEGIN
    FOR i IN 1 .. array_length(pairs, 1) LOOP
        IF to_regclass(pairs[i][1]) IS NULL THEN
            RAISE WARNING '[counts] % does not exist yet, skipped', pairs[i][1];
            CONTINUE;
        END IF;
        EXECUTE format('SELECT count(*) FROM %s', pairs[i][1]) INTO n_stg;
        EXECUTE format('SELECT count(*) FROM %s', pairs[i][2]) INTO n_dw;
        IF n_stg <> n_dw THEN
            RAISE EXCEPTION '[counts] % has % rows but % has %', pairs[i][2], n_dw, pairs[i][1], n_stg;
        END IF;
        RAISE NOTICE '[counts] % = % rows (matches %)', pairs[i][2], n_dw, pairs[i][1];
    END LOOP;
END $$;

-- 2. Geography: 2,431 valid AGEB polygons in EPSG:6372, 792.15 km2 -------
DO $$
DECLARE
    n BIGINT; n_invalid BIGINT; n_srid BIGINT; total_km2 NUMERIC;
BEGIN
    SELECT count(*),
           count(*) FILTER (WHERE NOT ST_IsValid(geom)),
           count(*) FILTER (WHERE ST_SRID(geom) <> 6372),
           sum(area_km2)
      INTO n, n_invalid, n_srid, total_km2
      FROM dw.dim_geography;
    IF n <> 2431 THEN RAISE EXCEPTION '[geo] expected 2431 AGEBs, found %', n; END IF;
    IF n_invalid > 0 THEN RAISE EXCEPTION '[geo] % invalid geometries', n_invalid; END IF;
    IF n_srid > 0 THEN RAISE EXCEPTION '[geo] % geometries not in EPSG:6372', n_srid; END IF;
    IF abs(total_km2 - 792.15) > 0.1 THEN RAISE EXCEPTION '[geo] total area % km2, expected 792.15', total_km2; END IF;
    RAISE NOTICE '[geo] 2431 AGEBs, all valid, EPSG:6372, % km2', round(total_km2, 2);
END $$;

-- 3. Census: one row per AGEB, population matches INEGI ------------------
DO $$
DECLARE
    n_missing BIGINT; pop BIGINT;
BEGIN
    SELECT count(*) INTO n_missing
      FROM dw.dim_geography g
      LEFT JOIN dw.fact_census_ageb c ON c.geo_key = g.geo_key
     WHERE c.geo_key IS NULL;
    IF n_missing > 0 THEN RAISE EXCEPTION '[census] % AGEBs without census row', n_missing; END IF;
    SELECT sum(pop_total) INTO pop FROM dw.fact_census_ageb;
    IF pop IS DISTINCT FROM 9138524 THEN RAISE EXCEPTION '[census] total population %, expected 9138524', pop; END IF;
    RAISE NOTICE '[census] every AGEB has a census row, population = %', pop;
END $$;

-- 4. Points lie inside the AGEB they are assigned to ----------------------
DO $$
DECLARE
    n_biz BIGINT; n_crime BIGINT;
BEGIN
    SELECT count(*) INTO n_biz
      FROM dw.fact_business f JOIN dw.dim_geography g ON g.geo_key = f.geo_key
     WHERE NOT ST_Intersects(f.geom, g.geom);
    SELECT count(*) INTO n_crime
      FROM dw.fact_crime_incident f JOIN dw.dim_geography g ON g.geo_key = f.geo_key
     WHERE NOT ST_Intersects(f.geom, g.geom);
    IF n_biz + n_crime > 0 THEN
        RAISE EXCEPTION '[spatial] points outside their AGEB: % businesses, % incidents', n_biz, n_crime;
    END IF;
    RAISE NOTICE '[spatial] every business and incident lies inside its assigned AGEB';
END $$;

-- 5. Dimensions referenced by the facts are complete ----------------------
DO $$
DECLARE
    n_other BIGINT; n_groups BIGINT;
BEGIN
    SELECT count(DISTINCT activity_group) INTO n_groups FROM dw.dim_economic_activity;
    IF n_groups <> 3 THEN RAISE EXCEPTION '[activity] expected Retail/Services/Other, found % groups', n_groups; END IF;
    SELECT count(*) INTO n_other
      FROM dw.fact_business f JOIN dw.dim_economic_activity a USING (activity_key)
     WHERE a.sector_code = '46' AND a.activity_group <> 'Retail';
    IF n_other > 0 THEN RAISE EXCEPTION '[activity] % SCIAN 46 establishments not classified as Retail', n_other; END IF;
    RAISE NOTICE '[activity] activity groups consistent with SCIAN sectors';
END $$;

-- 6. KPI view: one row per AGEB, totals reconcile with the facts, every KPI computable
DO $$
DECLARE
    n BIGINT; pop BIGINT; biz BIGINT; biz_fact BIGINT; crimes BIGINT; crimes_fact BIGINT;
    col TEXT; n_values BIGINT;
    crime_cols TEXT[] := ARRAY['crime_total', 'crime_rate_per_1k', 'crimes_per_100_businesses'];
    kpi_cols   TEXT[] := ARRAY['pop_total', 'pop_density_km2', 'pea_rate', 'pct_0_14', 'pct_15_64',
                               'pct_65_plus', 'businesses_total', 'business_density_km2', 'businesses_per_1k',
                               'retail_total', 'retail_density_km2', 'services_total', 'service_density_km2',
                               'dominant_sector', 'dominant_sector_share'];
BEGIN
    SELECT count(*), sum(pop_total), sum(businesses_total), sum(crime_total)
      INTO n, pop, biz, crimes
      FROM dw.v_kpi_ageb;
    SELECT count(*) INTO biz_fact FROM dw.fact_business;
    SELECT count(*) INTO crimes_fact FROM dw.fact_crime_incident;

    IF n <> 2431 THEN RAISE EXCEPTION '[kpi] v_kpi_ageb has % rows, expected 2431', n; END IF;
    IF pop IS DISTINCT FROM 9138524 THEN RAISE EXCEPTION '[kpi] population %, expected 9138524', pop; END IF;
    IF biz <> biz_fact THEN RAISE EXCEPTION '[kpi] businesses % <> fact_business %', biz, biz_fact; END IF;
    IF crimes <> crimes_fact THEN RAISE EXCEPTION '[kpi] incidents % <> fact_crime_incident %', crimes, crimes_fact; END IF;

    FOREACH col IN ARRAY kpi_cols || crime_cols LOOP
        EXECUTE format('SELECT count(*) FROM dw.v_kpi_ageb WHERE %I IS NOT NULL AND %I::text <> ''0''', col, col)
           INTO n_values;
        IF n_values = 0 THEN
            IF col = ANY (crime_cols) AND crimes_fact = 0 THEN
                RAISE WARNING '[kpi] % has no values: crime layer not loaded yet', col;
            ELSE
                RAISE EXCEPTION '[kpi] % has no non-zero values', col;
            END IF;
        END IF;
    END LOOP;

    RAISE NOTICE '[kpi] v_kpi_ageb: 2431 AGEBs, population %, businesses %, incidents %', pop, biz, crimes;
END $$;

-- 7. Incidents by type and time reconcile with the fact table -------------
DO $$
DECLARE
    n_view BIGINT; n_fact BIGINT;
BEGIN
    SELECT COALESCE(sum(incidents), 0) INTO n_view FROM dw.v_crime_by_type_time;
    SELECT count(*) INTO n_fact FROM dw.fact_crime_incident;
    IF n_view <> n_fact THEN RAISE EXCEPTION '[crime] v_crime_by_type_time sums % but fact has %', n_view, n_fact; END IF;
    RAISE NOTICE '[crime] v_crime_by_type_time reconciles with fact table (% incidents)', n_fact;
END $$;
