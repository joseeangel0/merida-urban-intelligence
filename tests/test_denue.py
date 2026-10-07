from datetime import date

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from src.transform.denue import (
    REQUIRED_COLUMNS,
    activity_group,
    build_business,
    build_economic_activity,
    parse_alta_date,
    read_denue,
    sector_code,
)


@pytest.fixture
def source() -> gpd.GeoDataFrame:
    """Three spatially assigned DENUE rows, as returned by spatial.assign_ageb."""
    return gpd.GeoDataFrame(
        {
            "id": ["1", "2", "3"],
            "clee": ["A", "B", "C"],
            "nom_estab": ["Shop", "Office", None],
            "codigo_act": ["461110", "541110", "311111"],
            "nombre_act": ["Retail activity", "Legal services", "Manufacturing"],
            "per_ocu": ["0 a 5 personas", "6 a 10 personas", "11 a 30 personas"],
            "fecha_alta": ["2020-01", "2021-02", "bad"],
            "cve_ent": ["09", "09", "09"],
            "cve_mun": ["015", "015", "015"],
            "cve_loc": ["0001", "0001", "0001"],
            "ageb": ["001A", "002B", "003C"],
            "cvegeo": ["090150001001A", "090150001002B", "090150001003C"],
        },
        geometry=[Point(1, 1), Point(2, 2), Point(3, 3)],
        crs="EPSG:6372",
    )


def test_sector_code_combines_official_multi_sector_groups():
    assert sector_code("311111") == "31-33"
    assert sector_code("491110") == "48-49"
    assert sector_code("461110") == "46"


def test_activity_group_classifies_retail_services_and_other():
    assert activity_group("46") == "Retail"
    assert activity_group("54") == "Services"
    assert activity_group("31-33") == "Other"


def test_parse_alta_date_uses_first_day_and_coerces_invalid_values():
    result = parse_alta_date(pd.Series(["2026-04", "", None, "bad"]))

    assert result.iloc[0] == pd.Timestamp("2026-04-01")
    assert result.iloc[1:].isna().all()


def test_economic_activity_has_exact_contract_and_unique_scian_codes(source):
    duplicated = pd.concat([source, source.iloc[[0]]], ignore_index=True)

    result = build_economic_activity(duplicated)

    assert result.columns.tolist() == [
        "scian_code",
        "activity_name",
        "subsector_code",
        "sector_code",
        "sector_name",
        "activity_group",
    ]
    assert len(result) == 3
    assert result["scian_code"].is_unique
    indexed = result.set_index("scian_code")
    assert indexed.loc["461110", "sector_name"] == "Retail trade"
    assert indexed.loc["541110", "activity_group"] == "Services"
    assert indexed.loc["311111", "sector_code"] == "31-33"


def test_business_has_exact_contract_and_projected_geometry(source):
    result = build_business(source)

    assert result.columns.tolist() == [
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
    assert str(result["denue_id"].dtype) == "int64"
    assert result.crs.to_epsg() == 6372
    assert result.loc[0, "cvegeo_reported"] == "090150001001A"
    assert type(result.loc[0, "alta_date"]) is date
    assert result.loc[0, "alta_date"] == date(2020, 1, 1)
    assert result["denue_id"].is_unique


def test_business_reported_cvegeo_uses_the_reported_state_code(source):
    source.loc[1, "cve_ent"] = "9"

    result = build_business(source)

    assert result.loc[1, "cvegeo_reported"] == "090150001002B"
    assert result["cvegeo_reported"].eq(result["cvegeo"]).all()


def test_read_denue_requires_the_state_code_column(tmp_path):
    path = tmp_path / "denue.csv"
    pd.DataFrame(columns=sorted(REQUIRED_COLUMNS - {"cve_ent"})).to_csv(path, index=False)

    with pytest.raises(ValueError, match="cve_ent"):
        read_denue(path)


def test_business_rejects_unknown_employment_bands(source):
    source.loc[0, "per_ocu"] = "unknown"

    with pytest.raises(ValueError, match="employment band"):
        build_business(source)
