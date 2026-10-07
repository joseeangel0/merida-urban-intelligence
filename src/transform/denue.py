"""Transform INEGI DENUE establishments into the economic data contract."""

from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.config import CVE_ENT, DATA_PROCESSED, DATA_RAW
from src.transform.spatial import assign_ageb, points_from_latlon


SERVICE_SECTORS = {"51", "52", "53", "54", "55", "56", "61", "62", "71", "72", "81"}
BUSINESS_SIZE_LABELS = {
    "0 a 5 personas",
    "6 a 10 personas",
    "11 a 30 personas",
    "31 a 50 personas",
    "51 a 100 personas",
    "101 a 250 personas",
    "251 y más personas",
}
SECTOR_NAMES = {
    "11": "Agriculture, forestry, fishing and hunting",
    "21": "Mining",
    "22": "Utilities",
    "23": "Construction",
    "31-33": "Manufacturing",
    "43": "Wholesale trade",
    "46": "Retail trade",
    "48-49": "Transportation, postal services and warehousing",
    "51": "Information",
    "52": "Finance and insurance",
    "53": "Real estate and rental and leasing",
    "54": "Professional, scientific and technical services",
    "55": "Management of companies and enterprises",
    "56": "Administrative support and waste management services",
    "61": "Educational services",
    "62": "Health care and social assistance",
    "71": "Arts, entertainment and recreation",
    "72": "Accommodation and food services",
    "81": "Other services except government activities",
    "93": "Government activities and international organizations",
}
DENUE_FILE = DATA_RAW / f"denue_{CVE_ENT}" / "conjunto_de_datos" / f"denue_inegi_{CVE_ENT}_.csv"
BUSINESS_FILE = DATA_PROCESSED / "business.parquet"
ECONOMIC_ACTIVITY_FILE = DATA_PROCESSED / "economic_activity.parquet"
# DENUE points inside CDMX urban AGEBs (TEAM_PLAN §3.5)
EXPECTED_BUSINESSES = 461_231
BUSINESS_TOLERANCE = 50
REQUIRED_COLUMNS = {
    "id",
    "clee",
    "nom_estab",
    "codigo_act",
    "nombre_act",
    "per_ocu",
    "fecha_alta",
    "cve_ent",
    "cve_mun",
    "cve_loc",
    "ageb",
    "latitud",
    "longitud",
}


def sector_code(scian_code: str) -> str:
    """Return the official two-digit sector, including combined SCIAN sectors."""
    sector = str(scian_code)[:2]
    if sector in {"31", "32", "33"}:
        return "31-33"
    if sector in {"48", "49"}:
        return "48-49"
    return sector


def activity_group(sector: str) -> str:
    """Map a sector to the project's Retail, Services, or Other grouping."""
    if sector == "46":
        return "Retail"
    if sector in SERVICE_SECTORS:
        return "Services"
    return "Other"


def parse_alta_date(values: pd.Series) -> pd.Series:
    """Parse DENUE YYYY-MM registration dates as the first day of each month."""
    return pd.to_datetime(values, format="%Y-%m", errors="coerce")


def read_denue(path: Path = DENUE_FILE) -> pd.DataFrame:
    """Read the immutable state-level DENUE CSV using its published encoding."""
    if not path.exists():
        raise FileNotFoundError(f"DENUE source not found: {path}; run the download step first")
    frame = pd.read_csv(path, encoding="latin-1", dtype=str)
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"DENUE source is missing columns: {', '.join(sorted(missing))}")
    return frame


def build_economic_activity(frame: pd.DataFrame) -> pd.DataFrame:
    """Build one dimension row per six-digit SCIAN class in the business data."""
    activities = (
        frame[["codigo_act", "nombre_act"]]
        .drop_duplicates("codigo_act")
        .rename(columns={"codigo_act": "scian_code", "nombre_act": "activity_name"})
        .copy()
    )
    activities["scian_code"] = activities["scian_code"].astype("string").str.zfill(6)
    activities["subsector_code"] = activities["scian_code"].str[:3]
    activities["sector_code"] = activities["scian_code"].map(sector_code)
    unknown = sorted(set(activities["sector_code"]) - SECTOR_NAMES.keys())
    if unknown:
        raise ValueError(f"Unknown SCIAN sector code(s): {', '.join(unknown)}")
    activities["sector_name"] = activities["sector_code"].map(SECTOR_NAMES)
    activities["activity_group"] = activities["sector_code"].map(activity_group)
    return activities[
        [
            "scian_code",
            "activity_name",
            "subsector_code",
            "sector_code",
            "sector_name",
            "activity_group",
        ]
    ].sort_values("scian_code", ignore_index=True)


def build_business(frame: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Select and rename spatially assigned DENUE rows to the fact contract."""
    unknown_sizes = sorted(set(frame["per_ocu"].dropna()) - BUSINESS_SIZE_LABELS)
    if unknown_sizes:
        raise ValueError(f"Unknown DENUE employment band(s): {', '.join(unknown_sizes)}")
    if frame["id"].duplicated().any():
        raise ValueError("DENUE id values must be unique")

    business = frame.copy()
    business["denue_id"] = pd.to_numeric(business["id"], errors="raise").astype("int64")
    business["scian_code"] = business["codigo_act"].astype("string").str.zfill(6)
    business["alta_date"] = parse_alta_date(business["fecha_alta"]).dt.date
    business["cvegeo_reported"] = (
        business["cve_ent"].astype("string").str.zfill(2)
        + business["cve_mun"].astype("string").str.zfill(3)
        + business["cve_loc"].astype("string").str.zfill(4)
        + business["ageb"].astype("string").str.zfill(4)
    )
    business = business.rename(
        columns={
            "nom_estab": "establishment_name",
            "per_ocu": "per_ocu_label",
        }
    )
    columns = [
        "denue_id",
        "clee",
        "establishment_name",
        "scian_code",
        "per_ocu_label",
        "alta_date",
        "cvegeo",
        "cvegeo_reported",
        "geometry",
    ]
    result = gpd.GeoDataFrame(business[columns], geometry="geometry", crs=frame.crs)
    if result.crs is None or result.crs.to_epsg() != 6372:
        raise ValueError(f"Expected business points in EPSG:6372; got {result.crs}")
    return result.reset_index(drop=True)


def run() -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """Transform state-level DENUE and write the two contracted output files."""
    source = read_denue()
    points = points_from_latlon(source, "latitud", "longitud")
    assigned = assign_ageb(points)
    business = build_business(assigned)
    economic_activity = build_economic_activity(assigned)

    agreement = business["cvegeo"].eq(business["cvegeo_reported"]).mean()
    retail_codes = set(
        economic_activity.loc[economic_activity["activity_group"].eq("Retail"), "scian_code"]
    )
    retail_count = int(business["scian_code"].isin(retail_codes).sum())
    if abs(len(business) - EXPECTED_BUSINESSES) > BUSINESS_TOLERANCE:
        raise ValueError(
            f"Expected {EXPECTED_BUSINESSES:,} ± {BUSINESS_TOLERANCE} businesses; got {len(business):,}"
        )
    if agreement < 0.995:
        raise ValueError(f"Spatial/reported AGEB agreement is only {agreement:.2%}")
    if not set(business["scian_code"]).issubset(set(economic_activity["scian_code"])):
        raise ValueError("Some business SCIAN codes are missing from the activity dimension")

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    business.to_parquet(BUSINESS_FILE, index=False)
    economic_activity.to_parquet(ECONOMIC_ACTIVITY_FILE, index=False)
    print(
        f"Wrote {len(business):,} businesses ({agreement:.2%} AGEB agreement; "
        f"{retail_count:,} Retail) and {len(economic_activity):,} SCIAN classes."
    )
    return business, economic_activity


if __name__ == "__main__":
    run()
