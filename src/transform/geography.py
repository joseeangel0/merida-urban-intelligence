"""Build the Mexico City urban-AGEB geography dimension."""
from pathlib import Path

import geopandas as gpd
from shapely.geometry import MultiPolygon

from src.config import (
    CITY_LOC,
    CRS_PROJECTED,
    CVE_ENT,
    CVE_MUN,
    DATA_PROCESSED,
    DATA_RAW,
    ROOT,
)

MARCO_GEO_DIR = DATA_RAW / "marco_geo_2020_09" / "conjunto_de_datos"
AGEB_FILE = MARCO_GEO_DIR / "09a.shp"
LOCALITY_FILE = MARCO_GEO_DIR / "09l.shp"
MUNICIPALITY_FILE = MARCO_GEO_DIR / "09mun.shp"
OUTPUT_FILE = DATA_PROCESSED / "ageb.parquet"

AGEB_COLUMNS = [
    "cvegeo",
    "cve_ent",
    "cve_mun",
    "cve_loc",
    "cve_ageb",
    "mun_name",
    "loc_name",
    "is_city_core",
    "area_km2",
    "geometry",
]


def _read_projected(path: Path) -> gpd.GeoDataFrame:
    """Read a Marco Geoestadístico layer and normalize its known CRS."""
    frame = gpd.read_file(path)
    if frame.crs is None or not frame.crs.is_projected:
        raise ValueError(f"Expected a projected INEGI source CRS in {path}")
    return frame.to_crs(CRS_PROJECTED)


def _filter_state(frame: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Keep the configured state and, when set, the configured municipality."""
    selected = frame.loc[frame["CVE_ENT"].astype(str).eq(CVE_ENT)].copy()
    if CVE_MUN is not None:
        selected = selected.loc[selected["CVE_MUN"].astype(str).eq(CVE_MUN)].copy()
    return selected


def run() -> gpd.GeoDataFrame:
    """Write and return the urban AGEB polygons for the configured scope (2,431 for all of CDMX)."""
    ageb = _filter_state(_read_projected(AGEB_FILE))
    localities = _filter_state(_read_projected(LOCALITY_FILE))
    municipalities = _filter_state(_read_projected(MUNICIPALITY_FILE))

    if ageb.empty or localities.empty or municipalities.empty:
        raise ValueError("INEGI Marco Geoestadístico is missing configured state features")
    if not ageb["CVEGEO"].is_unique:
        raise ValueError("INEGI AGEB CVEGEO keys must be unique")
    if not localities["CVEGEO"].is_unique or not municipalities["CVEGEO"].is_unique:
        raise ValueError("INEGI locality and municipality CVEGEO keys must be unique")

    locality_names = localities.set_index("CVEGEO")["NOMGEO"]
    municipality_names = municipalities.set_index("CVE_MUN")["NOMGEO"]
    locality_name = ageb["CVEGEO"].astype(str).str[:9].map(locality_names)
    municipality_name = ageb["CVE_MUN"].astype(str).map(municipality_names)
    if locality_name.isna().any() or municipality_name.isna().any():
        raise ValueError("At least one urban AGEB has no matching locality or alcaldía")

    geometry = ageb.geometry
    if geometry.isna().any() or not geometry.is_valid.all():
        raise ValueError("Urban AGEB source geometries must be present and valid")
    if not geometry.geom_type.isin(["Polygon", "MultiPolygon"]).all():
        raise ValueError("Urban AGEB source geometries must be polygonal")

    geometry = geometry.map(
        lambda geom: geom if geom.geom_type == "MultiPolygon" else MultiPolygon([geom])
    )
    result = gpd.GeoDataFrame(
        {
            "cvegeo": ageb["CVEGEO"].astype(str),
            "cve_ent": ageb["CVE_ENT"].astype(str),
            "cve_mun": ageb["CVE_MUN"].astype(str),
            "cve_loc": ageb["CVE_LOC"].astype(str),
            "cve_ageb": ageb["CVE_AGEB"].astype(str),
            "mun_name": municipality_name.astype(str),
            "loc_name": locality_name.astype(str),
            "is_city_core": ageb["CVE_LOC"].astype(str).eq(CITY_LOC),
            "geometry": geometry,
        },
        geometry="geometry",
        crs=CRS_PROJECTED,
    )
    result["area_km2"] = result.geometry.area / 1_000_000
    result = result[AGEB_COLUMNS].reset_index(drop=True)

    assert list(result.columns) == AGEB_COLUMNS
    assert result["cvegeo"].is_unique, "AGEB cvegeo values must be unique"
    assert result.crs.to_epsg() == 6372
    assert result.geom_type.eq("MultiPolygon").all()
    assert result.geometry.is_valid.all()

    if CVE_MUN is None:
        assert len(result) == 2_431, f"Expected 2,431 urban AGEBs; got {len(result)}"
        assert int(result["is_city_core"].sum()) == 2_348
        assert result["mun_name"].nunique() == 16
        assert abs(result["area_km2"].sum() - 792.15) <= 0.1

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    result.to_parquet(OUTPUT_FILE, index=False)
    rel_path = OUTPUT_FILE.relative_to(ROOT)
    print(
        f"Wrote {len(result):,} urban AGEBs to {rel_path} "
        f"({result['area_km2'].sum():.4f} km²; EPSG:{result.crs.to_epsg()})"
    )
    return result
