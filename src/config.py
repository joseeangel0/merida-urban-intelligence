"""Project-wide constants and paths. Every module imports from here."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
SQL_DIR = ROOT / "sql"
OUTPUT_MAPS = ROOT / "outputs" / "maps"
OUTPUT_FIGURES = ROOT / "outputs" / "figures"

# Geographic scope: municipality of Mérida, Yucatán
CVE_ENT = "31"
CVE_MUN = "050"
CITY_LOC = "0001"  # Mérida city locality (contiguous urban area)

# CRS
CRS_SOURCE_LATLON = "EPSG:4326"  # DENUE / crime coordinates (WGS84)
CRS_PROJECTED = "EPSG:6372"      # Mexico ITRF2008 LCC, metres (INEGI Marco Geoestadístico)

# Database schemas
SCHEMA_STAGING = "stg"
SCHEMA_DW = "dw"

# Original sources (see data/raw/manifest.json for hashes and download dates)
SOURCES = {
    "census_ageb_2020": {
        "name": "INEGI Censo de Población y Vivienda 2020 - Principales resultados por AGEB y manzana urbana (Yucatán)",
        "publisher": "INEGI",
        "url": "https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/ageb_manzana/ageb_mza_urbana_31_cpv2020_csv.zip",
        "original_grain": "One row per urban AGEB / urban block (with locality and municipality totals)",
    },
    "denue_31": {
        "name": "INEGI DENUE - Directorio Estadístico Nacional de Unidades Económicas (Yucatán)",
        "publisher": "INEGI",
        "url": "https://www.inegi.org.mx/contenidos/masiva/denue/denue_31_csv.zip",
        "original_grain": "One row per economic establishment (point, lat/lon)",
    },
    "marco_geo_2020": {
        "name": "INEGI Marco Geoestadístico 2020 (Censo 2020) - Yucatán",
        "publisher": "INEGI",
        "url": "https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/889463807469/31_yucatan.zip",
        "original_grain": "One polygon per geostatistical unit (state, municipality, locality, AGEB, block)",
    },
    # "crime": added by the public-safety owner once the dataset is chosen (see docs/team/TEAM_PLAN.md)
}
