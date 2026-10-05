"""Shared coordinate validation and point-to-AGEB assignment helpers."""
import geopandas as gpd
import pandas as pd

from src.config import CRS_PROJECTED, CRS_SOURCE_LATLON, DATA_PROCESSED

AGEB_FILE = DATA_PROCESSED / "ageb.parquet"
YUCATAN_BOUNDS = {
    "longitude": (-92.0, -86.0),
    "latitude": (19.0, 22.5),
}


def load_ageb() -> gpd.GeoDataFrame:
    """Read the processed AGEB polygons."""
    if not AGEB_FILE.exists():
        raise FileNotFoundError(
            f"{AGEB_FILE} is missing; run src.transform.geography.run() first"
        )
    ageb = gpd.read_parquet(AGEB_FILE)
    if ageb.crs is None or ageb.crs.to_epsg() != 6372:
        raise ValueError(f"Expected AGEB polygons in EPSG:6372; got {ageb.crs}")
    if "cvegeo" not in ageb.columns or "geometry" not in ageb.columns:
        raise ValueError("AGEB parquet must contain cvegeo and geometry columns")
    return ageb


def points_from_latlon(
    df: pd.DataFrame, lat_col: str, lon_col: str
) -> gpd.GeoDataFrame:
    """Validate Yucatán coordinates and return points reprojected to EPSG:6372."""
    missing = {lat_col, lon_col}.difference(df.columns)
    if missing:
        raise KeyError(f"Missing coordinate column(s): {', '.join(sorted(missing))}")

    points = df.copy()
    points[lat_col] = pd.to_numeric(points[lat_col], errors="coerce")
    points[lon_col] = pd.to_numeric(points[lon_col], errors="coerce")
    min_lon, max_lon = YUCATAN_BOUNDS["longitude"]
    min_lat, max_lat = YUCATAN_BOUNDS["latitude"]
    valid = (
        points[lat_col].between(min_lat, max_lat, inclusive="both")
        & points[lon_col].between(min_lon, max_lon, inclusive="both")
        & points[lat_col].ne(0)
        & points[lon_col].ne(0)
    )
    dropped = int((~valid).sum())
    points = points.loc[valid].copy()
    print(f"Dropped {dropped} invalid/out-of-Yucatán coordinates from {len(df)} rows.")

    geometry = gpd.points_from_xy(points[lon_col], points[lat_col])
    result = gpd.GeoDataFrame(points, geometry=geometry, crs=CRS_SOURCE_LATLON)
    return result.to_crs(CRS_PROJECTED)


def assign_ageb(points: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Keep points within an urban AGEB and add its cvegeo, without join duplicates."""
    if points.crs is None or points.crs.to_epsg() != 6372:
        raise ValueError(f"Expected input points in EPSG:6372; got {points.crs}")
    if "cvegeo" in points.columns:
        raise ValueError("Input points already contain cvegeo; rename it before assignment")

    total = len(points)
    indexed = points.reset_index(drop=True)
    indexed.index.name = "_input_row"
    joined = gpd.sjoin(
        indexed,
        load_ageb()[["cvegeo", "geometry"]],
        how="left",
        predicate="within",
    )
    matches = joined.loc[joined["index_right"].notna()].copy()
    if matches.index.has_duplicates:
        raise ValueError("A point matched multiple AGEB polygons; assignment is ambiguous")

    result = matches.drop(columns="index_right").reset_index(drop=True)
    kept = len(result)
    percentage = kept / total * 100 if total else 0.0
    print(f"kept {kept} / {total} ({percentage:.1f}%)")
    assert len(result) == kept
    return result
