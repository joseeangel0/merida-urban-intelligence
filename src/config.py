"""Project-wide constants and paths. Every module imports from here."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
SQL_DIR = ROOT / "sql"
OUTPUT_MAPS = ROOT / "outputs" / "maps"
OUTPUT_FIGURES = ROOT / "outputs" / "figures"

# Geographic scope: Mexico City (CDMX), all 16 alcaldías.
# The project started with Mérida, Yucatán (31050); it moved to CDMX because the only
# public crime data for Mérida is aggregated by municipality (SESNSP) and the instructor
# requires real, georeferenced incidents (see docs/team/TEAM_PLAN.md §3.1).
CVE_ENT = "09"
CVE_MUN = None     # None = every municipality (alcaldía) of the state
CITY_LOC = "0001"  # main urban locality of each alcaldía (contiguous urban area)

# Valid lat/lon window for point sources (WGS84), slightly larger than CDMX
LATLON_BBOX = {"lat_min": 19.0, "lat_max": 19.6, "lon_min": -99.4, "lon_max": -98.9}

# Crime incidents are kept when the offence date (fecha_hecho) falls in this year
CRIME_YEAR = 2024

# CRS
CRS_SOURCE_LATLON = "EPSG:4326"  # DENUE / crime coordinates (WGS84)
CRS_PROJECTED = "EPSG:6372"      # Mexico ITRF2008 LCC, metres (INEGI Marco Geoestadístico)

# Database schemas
SCHEMA_STAGING = "stg"
SCHEMA_DW = "dw"

# Original sources (see data/raw/manifest.json for hashes and download dates)
SOURCES = {
    "census_ageb_2020_09": {
        "name": "INEGI Censo de Población y Vivienda 2020 - Principales resultados por AGEB y manzana urbana (Ciudad de México)",
        "publisher": "INEGI",
        "licence": "INEGI Términos de libre uso de la información",
        "url": "https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/ageb_manzana/ageb_mza_urbana_09_cpv2020_csv.zip",
        "original_grain": "One row per urban AGEB / urban block (with locality and municipality totals)",
    },
    "denue_09": {
        "name": "INEGI DENUE - Directorio Estadístico Nacional de Unidades Económicas (Ciudad de México)",
        "publisher": "INEGI",
        "licence": "INEGI Términos de libre uso de la información",
        "url": "https://www.inegi.org.mx/contenidos/masiva/denue/denue_09_csv.zip",
        "original_grain": "One row per economic establishment (point, lat/lon)",
    },
    "marco_geo_2020_09": {
        "name": "INEGI Marco Geoestadístico 2020 (Censo 2020) - Ciudad de México",
        "publisher": "INEGI",
        "licence": "INEGI Términos de libre uso de la información",
        "url": "https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/889463807469/09_ciudaddemexico.zip",
        "original_grain": "One polygon per geostatistical unit (state, municipality, locality, AGEB, block)",
    },
    "crime_fgj_2024": {
        "name": "FGJ CDMX - Carpetas de investigación 2024 (Portal de Datos Abiertos CDMX; also served by hoyodecrimen.com)",
        "publisher": "Fiscalía General de Justicia de la Ciudad de México",
        "url": "https://archivo.datos.cdmx.gob.mx/FGJ/carpetas/carpetasFGJ_2024.csv",
        "original_grain": "One row per investigation file (carpeta) opened in 2024: offence, category, date/time, lat/lon",
        "licence": "CC-BY-4.0",
        "format": "csv",
    },
}
