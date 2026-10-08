"""Unit and integration contract tests for cross-source integration helpers."""

import pandas as pd
import pytest

from src.analysis.integration import (
    build_source_integration_summary_table,
    census_polygon_compatibility,
    crime_temporal_and_grain_check,
    denue_code_compatibility,
)
from src.config import DATA_RAW, DATA_PROCESSED


@pytest.fixture(scope="module")
def census_results():
    census_path = DATA_RAW / "census_ageb_2020_09" / "ageb_mza_urbana_09_cpv2020" / "conjunto_de_datos" / "conjunto_de_datos_ageb_urbana_09_cpv2020.csv"
    if not census_path.exists() or not (DATA_PROCESSED / "ageb.parquet").exists():
        pytest.skip("Census or AGEB processed files missing")
    return census_polygon_compatibility()


@pytest.fixture(scope="module")
def denue_results():
    denue_path = DATA_RAW / "denue_09" / "conjunto_de_datos" / "denue_inegi_09_.csv"
    if not denue_path.exists() or not (DATA_PROCESSED / "ageb.parquet").exists():
        pytest.skip("DENUE or AGEB processed files missing")
    return denue_code_compatibility()


@pytest.fixture(scope="module")
def crime_results():
    crime_path = DATA_RAW / "crime_fgj_2024" / "crime_fgj_2024.csv"
    if not crime_path.exists():
        crime_path = DATA_RAW / "crime_fgj_2024.csv"
    if not crime_path.exists() or not (DATA_PROCESSED / "ageb.parquet").exists():
        pytest.skip("Crime or AGEB processed files missing")
    return crime_temporal_and_grain_check(crime_path)


def test_census_polygon_compatibility(census_results):
    assert census_results["total_census_agebs"] == 2433
    assert census_results["matched_agebs"] == 2431
    assert census_results["orphan_count"] == 2
    assert census_results["matched_population"] == 9138524
    assert census_results["orphan_population"] == 7108
    assert census_results["orphan_keys"] == ["0901101101107", "0901201351227"]


def test_census_orphan_details(census_results):
    orphans = census_results["orphan_summary"]
    assert len(orphans) == 2
    tlahuac = orphans.loc[orphans["cvegeo"] == "0901101101107"].iloc[0]
    tlalpan = orphans.loc[orphans["cvegeo"] == "0901201351227"].iloc[0]
    assert tlahuac["pop_total"] == 3050
    assert tlalpan["pop_total"] == 4058


def test_denue_code_compatibility(denue_results):
    assert denue_results["raw_count"] == 462732
    assert denue_results["valid_coords_count"] == 462729
    assert denue_results["retained_count"] == 461231
    assert denue_results["outside_count"] == 1501
    assert denue_results["matched_cvegeo"] == 460503
    assert denue_results["mismatched_cvegeo"] == 728
    assert denue_results["agreement_rate"] == pytest.approx(0.998422, abs=1e-5)


def test_crime_temporal_and_grain(crime_results):
    assert crime_results["raw_count"] == 138630
    assert crime_results["filing_start"] == "2024-01-01"
    assert crime_results["filing_end"] == "2024-07-31"
    assert crime_results["filing_months_count"] == 7
    assert crime_results["year_2024_count"] == 123127
    assert crime_results["eligible_count"] == 119666
    assert crime_results["valid_coords_count"] == 112484
    assert crime_results["duplicates_count"] == 0
    assert crime_results["retained_count"] == 112285
    assert crime_results["outside_count"] == 199


def test_summary_table_generation(census_results, denue_results, crime_results):
    table = build_source_integration_summary_table(census_results, denue_results, crime_results)
    assert isinstance(table, pd.DataFrame)
    assert len(table) == 4
    assert table["Retained in Urban AGEBs"].tolist() == [2431, 2431, 461231, 112285]
