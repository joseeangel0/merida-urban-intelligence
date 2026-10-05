"""Build the municipality's urban-AGEB geography dimension."""
import geopandas as gpd
from shapely.geometry import MultiPolygon

from src.config import (
    CITY_LOC,
    CRS_PROJECTED,
    CVE_ENT,
    CVE_MUN,
    DATA_PROCESSED,
    DATA_RAW,
)

MARCO_GEO_DIR = DATA_RAW / "marco_geo_2020" / "conjunto_de_datos"
AGEB_FILE = MARCO_GEO_DIR / "31a.shp"
LOCALITY_FILE = MARCO_GEO_DIR / "31l.shp"
MUNICIPALITY_FILE = MARCO_GEO_DIR / "31mun.shp"
OUTPUT_FILE = DATA_PROCESSED / "ageb.parquet"


def _read_projected(path) -> gpd.GeoDataFrame:
    """Read a Marco Geoestadístico layer and normalize its known CRS."""
    frame = gpd.read_file(path)
    if frame.crs is None or not frame.crs.is_projected:
        raise ValueError(f"Expected a projected INEGI source CRS in {path}")
    return frame.to_crs(CRS_PROJECTED)


def run() -> gpd.GeoDataFrame:
    """Write and return the 526 urban AGEB polygons for Mérida municipality."""
    ageb = _read_projected(AGEB_FILE)
    localities = _read_projected(LOCALITY_FILE)
    municipalities = _read_projected(MUNICIPALITY_FILE)

    ageb = ageb.loc[
        ageb["CVE_ENT"].astype(str).eq(CVE_ENT)
        & ageb["CVE_MUN"].astype(str).eq(CVE_MUN)
    ].copy()
    localities = localities.loc[
        localities["CVE_ENT"].astype(str).eq(CVE_ENT)
        & localities["CVE_MUN"].astype(str).eq(CVE_MUN)
    ]
    municipalities = municipalities.loc[
        municipalities["CVE_ENT"].astype(str).eq(CVE_ENT)
        & municipalities["CVE_MUN"].astype(str).eq(CVE_MUN)
    ]

    if ageb.empty or localities.empty or len(municipalities) != 1:
        raise ValueError("INEGI Marco Geoestadístico is missing Mérida source features")
    if not ageb["CVEGEO"].is_unique or not localities["CVEGEO"].is_unique:
        raise ValueError("INEGI CVEGEO keys must be unique within the selected layers")

    locality_names = localities.set_index("CVEGEO")["NOMGEO"]
    ageb["loc_name"] = ageb["CVEGEO"].str[:9].map(locality_names)
    if ageb["loc_name"].isna().any():
        raise ValueError("At least one urban AGEB has no matching INEGI locality name")

    geometry = ageb.geometry
    if geometry.isna().any() or not geometry.is_valid.all():
        raise ValueError("Mérida urban AGEB source geometries must be present and valid")
    if not geometry.geom_type.isin(["Polygon", "MultiPolygon"]).all():
        raise ValueError("Mérida urban AGEB geometries must be polygonal")

    ageb.geometry = geometry.map(
        lambda geom: geom if geom.geom_type == "MultiPolygon" else MultiPolygon([geom])
    )
    result = gpd.GeoDataFrame(
        {
            "cvegeo": ageb["CVEGEO"].astype(str),
            "cve_ent": ageb["CVE_ENT"].astype(str),
            "cve_mun": ageb["CVE_MUN"].astype(str),
            "cve_loc": ageb["CVE_LOC"].astype(str),
            "cve_ageb": ageb["CVE_AGEB"].astype(str),
            "mun_name": municipalities.iloc[0]["NOMGEO"],
            "loc_name": ageb["loc_name"].astype(str),
            "is_city_core": ageb["CVE_LOC"].astype(str).eq(CITY_LOC),
            "area_km2": ageb.geometry.area / 1_000_000,
            "geometry": ageb.geometry,
        },
        geometry="geometry",
        crs=CRS_PROJECTED,
    )
    result = result[
        [
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
    ].reset_index(drop=True)

    assert len(result) == 526, f"Expected 526 urban AGEBs; got {len(result)}"
    assert result["cvegeo"].is_unique, "AGEB cvegeo values must be unique"
    assert int(result["is_city_core"].sum()) == 483
    assert result.crs.to_epsg() == 6372
    assert result.geom_type.eq("MultiPolygon").all()
    assert result.geometry.is_valid.all()
    assert abs(result["area_km2"].sum() - 259.86) <= 0.1

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    result.to_parquet(OUTPUT_FILE, index=False)
    print(
        f"Wrote {len(result)} AGEBs to {OUTPUT_FILE} "
        f"({result['area_km2'].sum():.4f} km²; EPSG:{result.crs.to_epsg()})"
    )
    return result
