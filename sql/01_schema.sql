-- =====================================================================
-- 01_schema.sql  —  Urban Intelligence Data Warehouse (Mexico City)
-- Star schema in PostgreSQL/PostGIS. Re-runnable: drops and recreates dw.
--
-- Unit of analysis: urban AGEB (INEGI Marco Geoestadístico 2020),
-- Mexico City (state 09, 16 alcaldías). All geometries in EPSG:6372 (metres).
--
--   stg.*  staging tables written by Python (src/load/load_staging.py)
--   dw.*   dimensional model populated by sql/02_load.sql
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS postgis;

DROP SCHEMA IF EXISTS dw CASCADE;
CREATE SCHEMA dw;
CREATE SCHEMA IF NOT EXISTS stg;

-- ---------------------------------------------------------------------
-- DIMENSIONS
-- ---------------------------------------------------------------------

-- Source traceability: one row per original dataset
CREATE TABLE dw.dim_source (
    source_key      SMALLSERIAL PRIMARY KEY,
    source_code     TEXT NOT NULL UNIQUE,      -- matches keys in src/config.py SOURCES
    source_name     TEXT NOT NULL,
    publisher       TEXT NOT NULL,
    url             TEXT,
    version_label   TEXT,                      -- e.g. 'CPV 2020', 'DENUE 05/2026'
    original_grain  TEXT NOT NULL,
    sha256          CHAR(64)                   -- from data/raw/manifest.json
);

-- Geography: one row per urban AGEB of Mexico City
CREATE TABLE dw.dim_geography (
    geo_key         SERIAL PRIMARY KEY,
    cvegeo          CHAR(13) NOT NULL UNIQUE,  -- ENT(2)+MUN(3)+LOC(4)+AGEB(4)
    cve_ent         CHAR(2)  NOT NULL,
    cve_mun         CHAR(3)  NOT NULL,
    cve_loc         CHAR(4)  NOT NULL,
    cve_ageb        CHAR(4)  NOT NULL,
    mun_name        TEXT     NOT NULL,
    loc_name        TEXT     NOT NULL,
    is_city_core    BOOLEAN  NOT NULL,         -- TRUE when cve_loc = '0001' (main locality of the alcaldía)
    area_km2        NUMERIC(12,4) NOT NULL CHECK (area_km2 > 0),
    geom            GEOMETRY(MultiPolygon, 6372) NOT NULL
);
CREATE INDEX ix_dim_geography_geom ON dw.dim_geography USING GIST (geom);

-- Calendar: one row per day
CREATE TABLE dw.dim_date (
    date_key        INTEGER PRIMARY KEY,       -- YYYYMMDD
    full_date       DATE NOT NULL UNIQUE,
    year            SMALLINT NOT NULL,
    quarter         SMALLINT NOT NULL,
    month           SMALLINT NOT NULL,
    month_name      TEXT NOT NULL,
    day             SMALLINT NOT NULL,
    day_of_week     SMALLINT NOT NULL,         -- ISO: 1 = Monday ... 7 = Sunday
    day_name        TEXT NOT NULL,
    is_weekend      BOOLEAN NOT NULL
);

-- Hour of day (static reference data); -1 = unknown hour
CREATE TABLE dw.dim_hour (
    hour_key        SMALLINT PRIMARY KEY CHECK (hour_key BETWEEN -1 AND 23),
    hour_label      TEXT NOT NULL,
    time_band       TEXT NOT NULL
);
INSERT INTO dw.dim_hour (hour_key, hour_label, time_band)
SELECT h,
       lpad(h::text, 2, '0') || ':00-' || lpad(h::text, 2, '0') || ':59',
       CASE WHEN h BETWEEN 0 AND 5  THEN 'Night (00-05)'
            WHEN h BETWEEN 6 AND 11 THEN 'Morning (06-11)'
            WHEN h BETWEEN 12 AND 17 THEN 'Afternoon (12-17)'
            ELSE 'Evening (18-23)' END
FROM generate_series(0, 23) AS h
UNION ALL SELECT -1, 'Unknown', 'Unknown';

-- Economic activity: one row per SCIAN 6-digit class present in DENUE
CREATE TABLE dw.dim_economic_activity (
    activity_key    SERIAL PRIMARY KEY,
    scian_code      CHAR(6) NOT NULL UNIQUE,
    activity_name   TEXT NOT NULL,
    subsector_code  CHAR(3) NOT NULL,
    sector_code     TEXT NOT NULL,             -- '46', '31-33', '48-49', ...
    sector_name     TEXT NOT NULL,
    activity_group  TEXT NOT NULL CHECK (activity_group IN ('Retail', 'Services', 'Other'))
);

-- Business size: one row per DENUE employment band (static reference data)
CREATE TABLE dw.dim_business_size (
    size_key        SMALLSERIAL PRIMARY KEY,
    per_ocu_label   TEXT NOT NULL UNIQUE,      -- exact DENUE label
    employees_min   INTEGER NOT NULL,
    employees_max   INTEGER,                   -- NULL = open-ended
    size_class      TEXT NOT NULL CHECK (size_class IN ('Micro', 'Small', 'Medium', 'Large'))
);
INSERT INTO dw.dim_business_size (per_ocu_label, employees_min, employees_max, size_class) VALUES
    ('0 a 5 personas',       0,    5, 'Micro'),
    ('6 a 10 personas',      6,   10, 'Micro'),
    ('11 a 30 personas',    11,   30, 'Small'),
    ('31 a 50 personas',    31,   50, 'Small'),
    ('51 a 100 personas',   51,  100, 'Medium'),
    ('101 a 250 personas', 101,  250, 'Medium'),
    ('251 y más personas', 251, NULL, 'Large');

-- Crime type: one row per harmonised crime type
CREATE TABLE dw.dim_crime_type (
    crime_type_key  SERIAL PRIMARY KEY,
    crime_type      TEXT NOT NULL UNIQUE,      -- harmonised English label
    crime_type_raw  TEXT,                      -- label as published by the source
    crime_category  TEXT NOT NULL              -- e.g. 'Property', 'Violent', 'Other'
);

-- ---------------------------------------------------------------------
-- FACTS
-- ---------------------------------------------------------------------

-- Grain: one row per urban AGEB, Census 2020 snapshot.
-- INEGI suppressed values ('*') and 'N/D' are stored as NULL.
CREATE TABLE dw.fact_census_ageb (
    geo_key             INTEGER PRIMARY KEY REFERENCES dw.dim_geography (geo_key),
    source_key          SMALLINT NOT NULL REFERENCES dw.dim_source (source_key),
    census_year         SMALLINT NOT NULL DEFAULT 2020,
    pop_total           INTEGER NOT NULL,      -- POBTOT
    pop_female          INTEGER,               -- POBFEM
    pop_male            INTEGER,               -- POBMAS
    pop_0_14            INTEGER,               -- POB0_14
    pop_15_64           INTEGER,               -- POB15_64
    pop_65_plus         INTEGER,               -- POB65_MAS
    pop_12_plus         INTEGER,               -- P_12YMAS (base for PEA rate)
    pop_18_plus         INTEGER,               -- P_18YMAS
    pop_60_plus         INTEGER,               -- P_60YMAS
    pea                 INTEGER,               -- PEA
    pea_female          INTEGER,               -- PEA_F
    pea_male            INTEGER,               -- PEA_M
    pop_inactive        INTEGER,               -- PE_INAC
    pop_employed        INTEGER,               -- POCUPADA
    pop_unemployed      INTEGER,               -- PDESOCUP
    avg_schooling       NUMERIC(5,2),          -- GRAPROES
    households          INTEGER,               -- TOTHOG
    dwellings_total     INTEGER,               -- VIVTOT
    dwellings_inhabited INTEGER,               -- TVIVHAB
    avg_occupants       NUMERIC(5,2),          -- PROM_OCUP
    n_suppressed_fields SMALLINT NOT NULL DEFAULT 0
);

-- Grain: one row per DENUE establishment located inside an urban AGEB.
CREATE TABLE dw.fact_business (
    business_key        BIGSERIAL PRIMARY KEY,
    denue_id            BIGINT NOT NULL UNIQUE,
    clee                TEXT,
    geo_key             INTEGER  NOT NULL REFERENCES dw.dim_geography (geo_key),
    activity_key        INTEGER  NOT NULL REFERENCES dw.dim_economic_activity (activity_key),
    size_key            SMALLINT NOT NULL REFERENCES dw.dim_business_size (size_key),
    date_key            INTEGER  REFERENCES dw.dim_date (date_key),  -- DENUE fecha_alta (1st of month)
    source_key          SMALLINT NOT NULL REFERENCES dw.dim_source (source_key),
    establishment_name  TEXT,
    cvegeo_reported     CHAR(13),              -- AGEB reported by DENUE, to audit the spatial join
    establishment_count SMALLINT NOT NULL DEFAULT 1,
    geom                GEOMETRY(Point, 6372) NOT NULL
);
CREATE INDEX ix_fact_business_geo ON dw.fact_business (geo_key);
CREATE INDEX ix_fact_business_activity ON dw.fact_business (activity_key);
CREATE INDEX ix_fact_business_geom ON dw.fact_business USING GIST (geom);

-- Grain: one row per georeferenced crime incident located inside an urban AGEB.
CREATE TABLE dw.fact_crime_incident (
    incident_key        BIGSERIAL PRIMARY KEY,
    source_incident_id  TEXT,
    geo_key             INTEGER  NOT NULL REFERENCES dw.dim_geography (geo_key),
    crime_type_key      INTEGER  NOT NULL REFERENCES dw.dim_crime_type (crime_type_key),
    date_key            INTEGER  REFERENCES dw.dim_date (date_key),
    hour_key            SMALLINT NOT NULL DEFAULT -1 REFERENCES dw.dim_hour (hour_key),
    source_key          SMALLINT NOT NULL REFERENCES dw.dim_source (source_key),
    incident_count      SMALLINT NOT NULL DEFAULT 1,
    geom                GEOMETRY(Point, 6372) NOT NULL
);
CREATE INDEX ix_fact_crime_geo ON dw.fact_crime_incident (geo_key);
CREATE INDEX ix_fact_crime_type ON dw.fact_crime_incident (crime_type_key);
CREATE INDEX ix_fact_crime_date ON dw.fact_crime_incident (date_key);
CREATE INDEX ix_fact_crime_geom ON dw.fact_crime_incident USING GIST (geom);
