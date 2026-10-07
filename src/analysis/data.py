"""Data access for Phase 3. Analyses read from the warehouse views only."""
import geopandas as gpd
import pandas as pd

from src.db import get_engine


def load_kpis(city_core_only: bool = True, exclude_low_population: bool = True) -> gpd.GeoDataFrame:
    """One row per urban AGEB with every KPI and its polygon (EPSG:6372), from dw.v_kpi_ageb.

    city_core_only          keep the main locality of each alcaldía (cve_loc 0001), the contiguous area used for spatial weights
    exclude_low_population  drop AGEBs with < 100 residents, whose per-capita rates are unstable
    """
    filters = []
    if city_core_only:
        filters.append("is_city_core")
    if exclude_low_population:
        filters.append("NOT low_population")
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    sql = f"SELECT * FROM dw.v_kpi_ageb {where} ORDER BY cvegeo"
    return gpd.read_postgis(sql, get_engine(), geom_col="geom").reset_index(drop=True)


def load_view(view: str) -> pd.DataFrame:
    """Any non-spatial dw view, e.g. load_view('v_crime_by_type_time')."""
    return pd.read_sql(f"SELECT * FROM dw.{view}", get_engine())
