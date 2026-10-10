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

# Original sources (see data/raw/manifest.json for download dates).
# sha256 pins the exact file version the submitted results were built from. When the
# official URL fails or now serves a different file, the downloader falls back to a
# byte-identical copy published as a GitHub release asset (MIRROR_BASE + file name).
MIRROR_BASE = "https://github.com/joseeangel0/merida-urban-intelligence/releases/download/data-v1.0/"
SOURCES = {
    "census_ageb_2020_09": {
        "name": "INEGI Censo de Población y Vivienda 2020 - Principales resultados por AGEB y manzana urbana (Ciudad de México)",
        "publisher": "INEGI",
        "version_label": "CPV 2020",
        "licence": "INEGI Términos de libre uso de la información",
        "url": "https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/ageb_manzana/ageb_mza_urbana_09_cpv2020_csv.zip",
        "sha256": "1f5f123b8e9a50991d1847271b5a2bf321e813e924e5bcf958cab612311c765a",
        "original_grain": "One row per urban AGEB / urban block (with locality and municipality totals)",
    },
    "denue_09": {
        "name": "INEGI DENUE - Directorio Estadístico Nacional de Unidades Económicas (Ciudad de México)",
        "publisher": "INEGI",
        "version_label": "DENUE 05/2026",
        "licence": "INEGI Términos de libre uso de la información",
        "url": "https://www.inegi.org.mx/contenidos/masiva/denue/denue_09_csv.zip",
        "sha256": "ae608f30118f6313e9d537ea22918b2c9e9a3d3f19c2ddf5907f55dbb1642b19",
        "original_grain": "One row per economic establishment (point, lat/lon)",
    },
    "marco_geo_2020_09": {
        "name": "INEGI Marco Geoestadístico 2020 (Censo 2020) - Ciudad de México",
        "publisher": "INEGI",
        "version_label": "Marco Geoestadístico 2020",
        "licence": "INEGI Términos de libre uso de la información",
        "url": "https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/889463807469/09_ciudaddemexico.zip",
        "sha256": "685b912f5458138a70726cff41aff828473e14264c43289d3b21f86a9df00320",
        "original_grain": "One polygon per geostatistical unit (state, municipality, locality, AGEB, block)",
    },
    "crime_fgj_2024": {
        "name": "FGJ CDMX - Carpetas de investigación 2024 (Portal de Datos Abiertos CDMX; also served by hoyodecrimen.com)",
        "publisher": "Fiscalía General de Justicia de la Ciudad de México",
        "version_label": "Carpetas de investigación 2024",
        "url": "https://archivo.datos.cdmx.gob.mx/FGJ/carpetas/carpetasFGJ_2024.csv",
        "sha256": "2ac3f17189a61ab7b2eb95fb21470e46adaba6f92526c7b92d23190ed2431f84",
        "original_grain": "One row per investigation file (carpeta) opened in 2024: offence, category, date/time, lat/lon",
        "licence": "CC-BY-4.0",
        "format": "csv",
    },
}
