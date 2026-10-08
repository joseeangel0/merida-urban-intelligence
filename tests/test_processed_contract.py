"""Contract tests for the files in data/processed/ (TEAM_PLAN §3.2, reference values §3.5).

Each test skips when its Parquet file does not exist yet, so `pytest tests/` passes on a clean
checkout and checks the real outputs after `python -m src.pipeline transform`.
"""
import geopandas as gpd
import pandas as pd
import pytest
from pandas.api.types import infer_dtype

from src.config import DATA_PROCESSED
from src.transform.census import CENSUS_FILE, MEASURE_COLUMNS

# Expected columns, in contract order, with the kind reported by pandas.api.types.infer_dtype
AGEB_COLUMNS = {
    "cvegeo": "string",
    "cve_ent": "string",
    "cve_mun": "string",
    "cve_loc": "string",
    "cve_ageb": "string",
    "mun_name": "string",
    "loc_name": "string",
    "is_city_core": "boolean",
    "area_km2": "floating",
    "geometry": "geometry",
}
# Same names and order as dw.fact_census_ageb (sql/01_schema.sql), no geometry
CENSUS_COLUMNS = {
    "cvegeo": "string",
    **{
        name: "integer"
        for name in [
            "pop_total", "pop_female", "pop_male", "pop_0_14", "pop_15_64", "pop_65_plus",
            "pop_12_plus", "pop_18_plus", "pop_60_plus", "pea", "pea_female", "pea_male",
            "pop_inactive", "pop_employed", "pop_unemployed",
        ]
    },
    "avg_schooling": "floating",
    "households": "integer",
    "dwellings_total": "integer",
    "dwellings_inhabited": "integer",
    "avg_occupants": "floating",
    "n_suppressed_fields": "integer",
}
ECONOMIC_ACTIVITY_COLUMNS = {
    "scian_code": "string",
    "activity_name": "string",
    "subsector_code": "string",
    "sector_code": "string",
    "sector_name": "string",
    "activity_group": "string",
}
BUSINESS_COLUMNS = {
    "denue_id": "integer",
    "clee": "string",
    "establishment_name": "string",
    "scian_code": "string",
    "per_ocu_label": "string",
    "alta_date": "date",
    "cvegeo": "string",
    "cvegeo_reported": "string",
    "geometry": "geometry",
}
CRIME_COLUMNS = {
    "source_incident_id": "string",
    "crime_type": "string",
    "crime_type_raw": "string",
    "crime_category": "string",
    "incident_date": "date",
    "incident_hour": "integer",
    "cvegeo": "string",
    "geometry": "geometry",
}

# TEAM_PLAN §3.5 reference values
EXPECTED_AGEBS = 2_431
EXPECTED_CITY_CORE_AGEBS = 2_348
EXPECTED_ALCALDIAS = 16
EXPECTED_AREA_KM2 = 792.15
EXPECTED_POPULATION = 9_138_524
EXPECTED_PEA = 5_061_682
EXPECTED_POP_12_PLUS = 7_858_894
EXPECTED_LOW_POPULATION = 55  # pop_total < 100
EXPECTED_ZERO_POPULATION = 17
EXPECTED_ACTIVITIES = 931
EXPECTED_BUSINESSES = 461_231
EXPECTED_RETAIL_BUSINESSES = 211_431  # SCIAN sector 46
MIN_AGEB_AGREEMENT = 0.998  # spatial join vs DENUE's own AGEB code
EXPECTED_CRIMES = 112_285
# Files marked "≈" in §3.2 may move slightly if a source is downloaded again
ROW_TOLERANCE = 0.005

# TEAM_PLAN §3.1 business rules
SERVICE_SECTORS = {"51", "52", "53", "54", "55", "56", "61", "62", "71", "72", "81"}
BUSINESS_SIZE_LABELS = {  # dw.dim_business_size
    "0 a 5 personas",
    "6 a 10 personas",
    "11 a 30 personas",
    "31 a 50 personas",
    "51 a 100 personas",
    "101 a 250 personas",
    "251 y más personas",
}
CRIME_CATEGORIES = {"Property", "Violent", "Sexual", "Other"}
CRIME_YEAR = 2024
SUPPRESSED_CODES = {"*", "N/D"}


def read_processed(name: str) -> pd.DataFrame:
    """Read data/processed/<name>.parquet, skipping the test when the transform has not run yet."""
    path = DATA_PROCESSED / f"{name}.parquet"
    if not path.exists():
        pytest.skip(f"{path.name} not found; run `python -m src.pipeline transform` first")
    if name in {"census_ageb", "economic_activity"}:
        return pd.read_parquet(path)
    return gpd.read_parquet(path)


@pytest.fixture(scope="module")
def ageb() -> gpd.GeoDataFrame:
    return read_processed("ageb")


@pytest.fixture(scope="module")
def census() -> pd.DataFrame:
    return read_processed("census_ageb")


@pytest.fixture(scope="module")
def economic_activity() -> pd.DataFrame:
    return read_processed("economic_activity")


@pytest.fixture(scope="module")
def business() -> gpd.GeoDataFrame:
    return read_processed("business")


@pytest.fixture(scope="module")
def crime() -> gpd.GeoDataFrame:
    return read_processed("crime")


def assert_columns(frame: pd.DataFrame, expected: dict[str, str]) -> None:
    """Exact column names and order, and the inferred kind of every column."""
    assert frame.columns.tolist() == list(expected)
    kinds = {
        column: "geometry" if column == "geometry" else infer_dtype(frame[column], skipna=True)
        for column in frame.columns
    }
    assert kinds == expected


def assert_points(frame: gpd.GeoDataFrame) -> None:
    assert frame.crs is not None and frame.crs.to_epsg() == 6372
    assert frame.geometry.name == "geometry"
    assert frame.geom_type.eq("Point").all()
    assert not frame.geometry.is_empty.any()


def assert_row_count(frame: pd.DataFrame, expected: int) -> None:
    assert len(frame) == pytest.approx(expected, rel=ROW_TOLERANCE)


# --- ageb.parquet (Lorena) -------------------------------------------------------------------


def test_ageb_columns_and_types(ageb):
    assert_columns(ageb, AGEB_COLUMNS)


def test_ageb_geometry_is_valid_multipolygon_in_epsg_6372(ageb):
    assert ageb.crs is not None and ageb.crs.to_epsg() == 6372
    assert ageb.geometry.name == "geometry"
    assert ageb.geom_type.eq("MultiPolygon").all()
    assert ageb.is_valid.all()


def test_ageb_rows_keys_and_area_match_reference_values(ageb):
    assert len(ageb) == EXPECTED_AGEBS
    assert ageb["cvegeo"].is_unique
    assert ageb["cvegeo"].str.fullmatch(r"09\d{3}\d{4}[0-9A-Z]{4}").all()
    assert ageb["cvegeo"].eq(ageb["cve_ent"] + ageb["cve_mun"] + ageb["cve_loc"] + ageb["cve_ageb"]).all()
    assert ageb["is_city_core"].eq(ageb["cve_loc"].eq("0001")).all()
    assert ageb["is_city_core"].sum() == EXPECTED_CITY_CORE_AGEBS
    assert ageb["mun_name"].nunique() == EXPECTED_ALCALDIAS
    assert ageb["area_km2"].gt(0).all()
    assert ageb["area_km2"].sum() == pytest.approx(EXPECTED_AREA_KM2, abs=0.1)
    assert ageb["area_km2"].to_numpy() == pytest.approx(ageb.area.to_numpy() / 1e6, rel=1e-6)


# --- census_ageb.parquet (Julio, transform by Gustavo) ---------------------------------------


def test_census_columns_and_types(census):
    assert "geometry" not in census.columns
    assert_columns(census, CENSUS_COLUMNS)


def test_census_has_one_row_per_ageb_polygon(census, ageb):
    assert len(census) == EXPECTED_AGEBS
    assert census["cvegeo"].is_unique
    assert set(census["cvegeo"]) == set(ageb["cvegeo"])


def test_census_totals_match_reference_values(census):
    assert census["pop_total"].notna().all()
    assert census["pop_total"].sum() == EXPECTED_POPULATION
    assert census["pea"].sum() == EXPECTED_PEA
    assert census["pop_12_plus"].sum() == EXPECTED_POP_12_PLUS
    assert census["pop_total"].lt(100).sum() == EXPECTED_LOW_POPULATION
    assert census["pop_total"].eq(0).sum() == EXPECTED_ZERO_POPULATION


def test_census_suppression_count_matches_null_measures(census):
    """Every suppressed field is NULL; a '*' stored as 0 would leave fewer NULLs than suppressions."""
    measures = census.drop(columns=["cvegeo", "n_suppressed_fields"])
    assert measures.isna().sum(axis=1).eq(census["n_suppressed_fields"]).all()


def test_census_suppressed_raw_values_are_null_never_zero(census):
    """Cell-by-cell check against the raw INEGI file: '*' and 'N/D' -> NULL, published numbers kept."""
    if not CENSUS_FILE.exists():
        pytest.skip(f"{CENSUS_FILE.name} not found; run `python -m src.pipeline download` first")
    raw = pd.read_csv(CENSUS_FILE, dtype=str, encoding="utf-8-sig", keep_default_na=False)
    raw = raw.loc[raw["MZA"].eq("000") & raw["AGEB"].ne("0000")]
    raw = raw.set_index(raw["ENTIDAD"] + raw["MUN"] + raw["LOC"] + raw["AGEB"])
    raw = raw.loc[census["cvegeo"], list(MEASURE_COLUMNS)].rename(columns=MEASURE_COLUMNS)
    processed = census.set_index("cvegeo")[list(MEASURE_COLUMNS.values())]

    suppressed = raw.isin(SUPPRESSED_CODES)
    assert suppressed.to_numpy().any(), "expected some INEGI suppressed values in the raw file"
    assert processed.isna().eq(suppressed).all().all()
    published = raw.mask(suppressed).apply(pd.to_numeric).astype("Float64")
    assert published.eq(processed.astype("Float64")).fillna(True).all().all()


# --- economic_activity.parquet (Nora) ---------------------------------------------------------


def test_economic_activity_columns_and_types(economic_activity):
    assert_columns(economic_activity, ECONOMIC_ACTIVITY_COLUMNS)


def test_economic_activity_codes_and_groups(economic_activity):
    assert_row_count(economic_activity, EXPECTED_ACTIVITIES)
    assert economic_activity["scian_code"].is_unique
    assert economic_activity["scian_code"].str.fullmatch(r"\d{6}").all()
    assert economic_activity["subsector_code"].eq(economic_activity["scian_code"].str[:3]).all()
    assert economic_activity.notna().all().all()

    groups = economic_activity.set_index("sector_code")["activity_group"]
    assert groups.isin(["Retail", "Services", "Other"]).all()
    assert groups.eq("Retail").eq(groups.index == "46").all()
    assert groups.eq("Services").eq(groups.index.isin(SERVICE_SECTORS)).all()


# --- business.parquet (Nora) ------------------------------------------------------------------


def test_business_columns_and_types(business):
    assert_columns(business, BUSINESS_COLUMNS)
    assert business["denue_id"].dtype == "int64"


def test_business_geometry_is_point_in_epsg_6372(business):
    assert_points(business)


def test_business_rows_and_keys(business):
    assert_row_count(business, EXPECTED_BUSINESSES)
    assert business["denue_id"].is_unique
    assert business["scian_code"].str.startswith("46").sum() == pytest.approx(
        EXPECTED_RETAIL_BUSINESSES, rel=ROW_TOLERANCE
    )


def test_business_references_ageb_activity_and_size(business, ageb, economic_activity):
    assert business["cvegeo"].isin(ageb["cvegeo"]).all()
    assert business["scian_code"].isin(economic_activity["scian_code"]).all()
    assert business["per_ocu_label"].isin(BUSINESS_SIZE_LABELS).all()


def test_business_alta_date_is_first_of_month(business):
    alta = pd.to_datetime(business["alta_date"].dropna())
    assert alta.dt.day.eq(1).all()


def test_business_spatial_join_agrees_with_denue_ageb(business):
    agreement = business["cvegeo"].eq(business["cvegeo_reported"]).mean()
    assert agreement >= MIN_AGEB_AGREEMENT


# --- crime.parquet (Valeria) ------------------------------------------------------------------


def test_crime_columns_and_types(crime):
    assert_columns(crime, CRIME_COLUMNS)


def test_crime_geometry_is_point_in_epsg_6372(crime):
    assert_points(crime)


def test_crime_rows_and_keys(crime):
    assert_row_count(crime, EXPECTED_CRIMES)
    assert crime["source_incident_id"].is_unique
    assert crime["source_incident_id"].str.fullmatch(rf"fgj{CRIME_YEAR}-[1-9]\d*").all()


def test_crime_references_ageb(crime, ageb):
    assert crime["cvegeo"].notna().all()
    assert crime["cvegeo"].isin(ageb["cvegeo"]).all()


def test_crime_hour_date_and_labels(crime):
    assert crime["incident_hour"].between(-1, 23).all()
    dates = pd.to_datetime(crime["incident_date"].dropna())
    assert dates.dt.year.eq(CRIME_YEAR).all()
    assert crime["crime_category"].isin(CRIME_CATEGORIES).all()
    assert crime[["crime_type", "crime_type_raw"]].notna().all().all()
    assert crime.groupby("crime_type")["crime_category"].nunique().eq(1).all()
    # crime_type is the harmonised English label: no Spanish accents or "ñ"
    assert not crime["crime_type"].str.contains("[áéíóúñÁÉÍÓÚÑ]").any()
