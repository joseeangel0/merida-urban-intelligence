"""Transform FGJ CDMX 2024 crime incidents into the processed spatial dimension.

Author: Valeria Hernández (valnix140405)
Project: Mexico City Urban Intelligence (Phase 2 — Transformation)
Contract: docs/team/TEAM_PLAN.md §3.2 and §4.5
"""
import unicodedata
import geopandas as gpd
import pandas as pd

from src.config import (
    CRIME_YEAR,
    CRS_PROJECTED,
    CRS_SOURCE_LATLON,
    DATA_PROCESSED,
    DATA_RAW,
    LATLON_BBOX,
)
from src.transform.spatial import assign_ageb

RAW_FILE = DATA_RAW / "crime_fgj_2024" / "crime_fgj_2024.csv"
FALLBACK_RAW_FILE = DATA_RAW / "crime_fgj_2024.csv"
OUTPUT_FILE = DATA_PROCESSED / "crime.parquet"

# Standard English crime type translations for top offences (unaccented keys)
CRIME_TYPE_TRANSLATIONS = {
    "VIOLENCIA FAMILIAR": "Family Violence",
    "AMENAZAS": "Threats",
    "FRAUDE": "Fraud",
    "ROBO DE ACCESORIOS DE AUTO": "Theft of Auto Parts and Accessories",
    "ROBO DE OBJETOS": "Theft of Personal Property",
    "USURPACION DE IDENTIDAD": "Identity Theft",
    "ROBO DE OBJETOS DEL INTERIOR DE UN VEHICULO": "Theft from Vehicle Interior",
    "ROBO A TRANSEUNTE EN VIA PUBLICA CON VIOLENCIA": "Robbery on Public Road with Violence",
    "ABUSO SEXUAL": "Sexual Abuse",
    "DANO EN PROPIEDAD AJENA CULPOSA POR TRANSITO VEHICULAR A AUTOMOVIL": "Accidental Property Damage to Vehicle in Traffic",
    "LESIONES INTENCIONALES POR GOLPES": "Intentional Assault and Battery",
    "ROBO A NEGOCIO SIN VIOLENCIA POR FARDEROS (TIENDAS DE AUTOSERVICIO)": "Shoplifting at Commercial Business (Self-Service)",
    "DESPOJO": "Dispossession / Squatting",
    "ROBO A CASA HABITACION SIN VIOLENCIA": "Residential Burglary without Violence",
    "NARCOMENUDEO POSESION SIMPLE": "Drug Possession (Simple)",
    "ROBO DE MOTOCICLETA SIN VIOLENCIA": "Motorcycle Theft without Violence",
    "LESIONES CULPOSAS POR TRANSITO VEHICULAR EN COLISION": "Involuntary Injury in Traffic Collision",
    "ROBO A NEGOCIO SIN VIOLENCIA POR FARDEROS": "Shoplifting at Commercial Business",
    "ABUSO DE CONFIANZA": "Breach of Trust / Embezzlement",
    "ROBO DE VEHICULO DE SERVICIO PARTICULAR SIN VIOLENCIA": "Private Vehicle Theft without Violence",
    "ROBO A NEGOCIO SIN VIOLENCIA": "Business Theft without Violence",
    "NARCOMENUDEO POSESION CON FINES DE VENTA, COMERCIO Y SUMINISTRO": "Drug Possession with Intent to Distribute",
    "TENTATIVA DE EXTORSION": "Attempted Extortion",
    "DELITOS ELECTORALES": "Electoral Offenses",
    "COBRANZA ILEGITIMA": "Unlawful Debt Collection",
    "ROBO DE PLACA DE AUTOMOVIL": "Theft of License Plate",
    "CONTRA LA INTIMIDAD SEXUAL": "Offense against Sexual Privacy",
    "ROBO A NEGOCIO CON VIOLENCIA": "Robbery at Business with Violence",
    "DANO EN PROPIEDAD AJENA INTENCIONAL A AUTOMOVIL": "Intentional Property Damage to Automobile",
    "ROBO A TRANSEUNTE EN PARQUES Y MERCADOS CON VIOLENCIA": "Robbery in Parks or Markets with Violence",
    "FALSIFICACION DE TITULOS AL PORTADOR Y DOCUMENTOS DE CREDITO PUBLICO": "Forgery of Bearer Securities and Public Credit",
    "ROBO A TRANSEUNTE DE CELULAR CON VIOLENCIA": "Cell Phone Robbery with Violence",
    "HOMICIDIO DOLOSO": "Intentional Homicide",
    "LESIONES DOLOSAS POR DISPARO DE ARMA DE FUEGO": "Intentional Assault by Firearm Discharge",
    "VIOLACION": "Rape",
    "SECUESTRO": "Kidnapping",
    "ROBO A REPARTIDOR CON Y SIN VIOLENCIA": "Robbery of Delivery Personnel",
    "ROBO A PASAJERO A BORDO DEL METRO CON Y SIN VIOLENCIA": "Robbery on Subway (Metro)",
    "ROBO A PASAJERO A BORDO DE MICROBUS CON Y SIN VIOLENCIA": "Robbery on Public Bus / Microbus",
    "ROBO A CASA HABITACION CON VIOLENCIA": "Residential Burglary with Violence",
    "ROBO A PASAJERO A BORDO DE TAXI CON VIOLENCIA": "Robbery on Taxi with Violence",
    "ROBO A CUENTAHABIENTE SALIENDO DEL CAJERO CON VIOLENCIA": "Robbery of Bank Customer leaving ATM with Violence",
    "ROBO A TRANSPORTISTA CON Y SIN VIOLENCIA": "Robbery of Freight Cargo / Carrier",
}


def _normalize(text: str) -> str:
    """Strip accents and whitespace, converting to uppercase ASCII."""
    nfkd = unicodedata.normalize("NFKD", str(text))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).strip().upper()


def _map_crime_category(del_norm: str) -> str:
    """Categorize offence into high-level criminological groups based purely on normalised delito."""
    # Sexual offences
    if any(k in del_norm for k in [
        "SEXUAL", "ESTUPRO", "INTIMIDAD SEXUAL", "TRATA DE PERSONAS", "PORNOGRAFIA"
    ]) or ("VIOLACI" in del_norm and "CORRESPONDENCIA" not in del_norm and "SELLOS" not in del_norm):
        return "Sexual"

    # Violent offences
    if any(k in del_norm for k in [
        "HOMICIDIO", "FEMINICIDIO", "VIOLENCIA FAMILIAR", "AMENAZAS", "LESIONES",
        "SECUESTRO", "PRIVACION DE LA LIBERTAD", "DISPAROS DE ARMA", "DISCRIMINACION",
        "TORTURA", "ASFIXIA", "ABANDONO DE PERSONA", "PLAGIO", "SUICIDIO"
    ]):
        return "Violent"

    # Property offences
    if any(k in del_norm for k in [
        "ROBO", "FRAUDE", "DESPOJO", "ABUSO DE CONFIANZA", "DANO EN PROPIEDAD",
        "EXTORSION", "USURPACI", "COBRANZA ILEGITIMA", "ENCUBRIMIENTO POR RECEPTACION",
        "ALLANAMIENTO", "FALSIFICACION", "ENRIQUECIMIENTO"
    ]):
        return "Property"

    return "Other"


def _clean_fallback_title(text: str) -> str:
    """Format Spanish offence name in clean title case without blind word substitutions."""
    words = text.strip().split()
    lowercase_words = {"de", "del", "a", "en", "por", "con", "sin", "y", "o", "al", "la", "las", "el", "los"}
    formatted = []
    for i, w in enumerate(words):
        lw = w.lower()
        if i > 0 and lw in lowercase_words:
            formatted.append(lw)
        else:
            formatted.append(w.capitalize())
    return " ".join(formatted)


def _map_crime_type(delito: str) -> str:
    """Return a clean, harmonised English label or cleaned title for Spanish delito."""
    del_norm = _normalize(delito)
    return CRIME_TYPE_TRANSLATIONS.get(del_norm, _clean_fallback_title(delito))


def _parse_hour(val: str) -> int:
    """Parse hora_hecho into an integer hour between 0 and 23 (-1 if missing/unknown)."""
    if pd.isna(val):
        return -1
    parts = str(val).split(":")
    try:
        hour = int(parts[0])
        return hour if 0 <= hour <= 23 else -1
    except (ValueError, IndexError):
        return -1


def _points_from_latlon(df: pd.DataFrame, lat_col: str, lon_col: str) -> gpd.GeoDataFrame:
    """Validate coordinates against CDMX bounds and reproject to EPSG:6372."""
    missing = {lat_col, lon_col}.difference(df.columns)
    if missing:
        raise KeyError(f"Missing coordinate column(s): {', '.join(sorted(missing))}")

    points = df.copy()
    points[lat_col] = pd.to_numeric(points[lat_col], errors="coerce")
    points[lon_col] = pd.to_numeric(points[lon_col], errors="coerce")

    bbox = LATLON_BBOX
    valid = (
        points[lat_col].between(bbox["lat_min"], bbox["lat_max"], inclusive="both")
        & points[lon_col].between(bbox["lon_min"], bbox["lon_max"], inclusive="both")
        & points[lat_col].ne(0)
        & points[lon_col].ne(0)
    )
    dropped = int((~valid).sum())
    points = points.loc[valid].copy()
    print(f"[crime] Dropped {dropped} invalid/out-of-CDMX coordinates from {len(df)} rows.")

    geometry = gpd.points_from_xy(points[lon_col], points[lat_col])
    result = gpd.GeoDataFrame(points, geometry=geometry, crs=CRS_SOURCE_LATLON)
    return result.to_crs(CRS_PROJECTED)


def run() -> gpd.GeoDataFrame:
    """Read FGJ CDMX 2024 crime file, apply business filters, assign AGEBs, and write crime.parquet."""
    raw_path = RAW_FILE if RAW_FILE.exists() else FALLBACK_RAW_FILE
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw crime dataset not found at {RAW_FILE} or {FALLBACK_RAW_FILE}")

    print(f"[crime] Loading raw investigation files from {raw_path}...")
    df = pd.read_csv(raw_path, dtype=str, encoding="utf-8")
    raw_count = len(df)
    print(f"[crime] Loaded {raw_count:,} raw rows.")

    # 1. source_incident_id based on 1-indexed line number of raw CSV (header excluded)
    df["source_incident_id"] = [f"fgj2024-{i + 1}" for i in range(raw_count)]

    # 2. Filter offence year to CRIME_YEAR (2024)
    df["dt_hecho"] = pd.to_datetime(df["fecha_hecho"], errors="coerce")
    df = df[df["dt_hecho"].dt.year == CRIME_YEAR].copy()
    print(f"[crime] Filtered to year {CRIME_YEAR}: {len(df):,} incidents.")

    # 3. Drop non-criminal records (HECHO NO DELICTIVO)
    df = df[df["categoria_delito"] != "HECHO NO DELICTIVO"].copy()
    print(f"[crime] Filtered out 'HECHO NO DELICTIVO': {len(df):,} incidents.")

    # 4. Coordinate validation and reprojection to EPSG:6372
    points_gdf = _points_from_latlon(df, "latitud", "longitud")

    # 5. Remove exact duplicates among geolocated records
    dup_mask = points_gdf.duplicated(subset=["delito", "fecha_hecho", "hora_hecho", "latitud", "longitud"])
    dups_count = int(dup_mask.sum())
    points_gdf = points_gdf.loc[~dup_mask].copy()
    print(f"[crime] Dropped {dups_count} exact duplicates among geolocated incidents; retained {len(points_gdf):,} incidents.")

    # 6. Parse incident date and hour
    points_gdf["incident_date"] = points_gdf["dt_hecho"].dt.date
    points_gdf["incident_hour"] = points_gdf["hora_hecho"].map(_parse_hour).astype("int16")

    # 7. Harmonise crime types and categories (deterministic 1-to-1 category per crime_type)
    points_gdf["crime_type_raw"] = points_gdf["delito"]
    points_gdf["crime_type"] = points_gdf["delito"].map(_map_crime_type)
    points_gdf["crime_category"] = points_gdf["delito"].map(lambda d: _map_crime_category(_normalize(d)))

    # 8. Spatial join with urban AGEBs (predicate within)
    print("[crime] Performing spatial join with Mexico City urban AGEBs...")
    assigned_gdf = assign_ageb(points_gdf)

    # 9. Format columns matching data contract §3.2
    contract_columns = [
        "source_incident_id",
        "crime_type",
        "crime_type_raw",
        "crime_category",
        "incident_date",
        "incident_hour",
        "cvegeo",
        "geometry",
    ]
    result = assigned_gdf[contract_columns].reset_index(drop=True)

    # 10. Assertions matching team plan win conditions and code review
    assert abs(len(result) - 112_285) / 112_285 <= 0.005, f"Expected ≈112,285 incidents, got {len(result):,}"
    assert result.groupby("crime_type")["crime_category"].nunique().eq(1).all(), (
        "Each crime_type must map to exactly one crime_category"
    )
    assert result["source_incident_id"].is_unique, "source_incident_id must be unique"
    assert result["cvegeo"].notna().all(), "Every retained incident must have an assigned cvegeo"
    assert result["incident_hour"].between(-1, 23).all(), "incident_hour must be within -1..23"
    assert result.crs.to_epsg() == 6372, f"Expected EPSG:6372, got {result.crs}"
    assert set(result.columns) == set(contract_columns), "Columns must match contract §3.2"

    # 11. Write processed GeoParquet
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(OUTPUT_FILE)
    print(f"[crime] Wrote {len(result):,} incidents to {OUTPUT_FILE} successfully.")

    return result


if __name__ == "__main__":
    run()
