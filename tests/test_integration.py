"""Unit and integration contract tests for cross-source integration helpers."""

import numpy as np
import pandas as pd
import pytest
import geopandas as gpd

from src.analysis.integration import (
    PINNED_CRIME_SHA256,
    PINNED_MANIFEST_DIGESTS,
    _parse_census_population,
    build_source_integration_summary_table,
    census_polygon_compatibility,
    crime_temporal_and_grain_check,
    denue_code_compatibility,
    normalize_reported_cvegeo,
    plot_cross_source_temporal_coverage,
    verify_crime_provenance,
    verify_input_provenance,
)
from src.config import DATA_PROCESSED, DATA_RAW
from src.transform import spatial


@pytest.fixture(scope="module")
def census_results():
    census_path = (
        DATA_RAW
        / "census_ageb_2020_09"
        / "ageb_mza_urbana_09_cpv2020"
        / "conjunto_de_datos"
        / "conjunto_de_datos_ageb_urbana_09_cpv2020.csv"
    )
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


# ---------------------------------------------------------------------------
# Census validation tests
# ---------------------------------------------------------------------------


def test_parse_census_population():
    # Valid numeric strings and numbers
    valid_series = pd.Series(["100", "0", 250])
    parsed = _parse_census_population(valid_series)
    assert parsed.tolist() == [100.0, 0.0, 250.0]

    # Suppressed values become NaN
    suppressed_series = pd.Series(["100", "*", "N/D"])
    parsed_suppressed = _parse_census_population(suppressed_series)
    assert parsed_suppressed.iloc[0] == 100.0
    assert np.isnan(parsed_suppressed.iloc[1])
    assert np.isnan(parsed_suppressed.iloc[2])

    # Malformed tokens raise ValueError
    with pytest.raises(ValueError, match="Unexpected non-numeric census values in POBTOT"):
        _parse_census_population(pd.Series(["100", "bad", "12a"]))


def test_census_polygon_compatibility(census_results):
    assert census_results["raw_census_rows"] == 68941
    assert census_results["total_census_agebs"] == 2433
    assert census_results["matched_agebs"] == 2431
    assert census_results["orphan_count"] == 2
    assert census_results["matched_population"] == 9138524
    assert census_results["orphan_population"] == 7108
    assert census_results["orphan_keys"] == ["0901101101107", "0901201351227"]
    assert census_results["keys_match_polygons"] is True
    assert len(census_results["polygon_orphans"]) == 0


def test_census_orphan_details(census_results):
    orphans = census_results["orphan_summary"]
    assert len(orphans) == 2
    tlahuac = orphans.loc[orphans["cvegeo"] == "0901101101107"].iloc[0]
    tlalpan = orphans.loc[orphans["cvegeo"] == "0901201351227"].iloc[0]
    assert tlahuac["pop_total"] == 3050
    assert tlalpan["pop_total"] == 4058


# ---------------------------------------------------------------------------
# DENUE validation & synthetic probe tests
# ---------------------------------------------------------------------------


def test_normalize_reported_cvegeo():
    df = pd.DataFrame(
        {
            "cve_ent": ["9", "09", "09"],
            "cve_mun": ["15", "015", "015"],
            "cve_loc": ["1", "0001", ""],
            "ageb": ["260", "0260", "0260"],
        }
    )
    normalized = normalize_reported_cvegeo(df)
    assert normalized.iloc[0] == "0901500010260"
    assert normalized.iloc[1] == "0901500010260"
    assert pd.isna(normalized.iloc[2])  # empty loc must not become "0000"


def test_denue_synthetic_probe_partition():
    """3-row regression probe: match, valid-code discrepancy, unmatchable key."""
    if not (DATA_PROCESSED / "ageb.parquet").exists():
        pytest.skip("ageb.parquet missing")

    # Real CDMX centroid in Cuauhtémoc (0901500010260)
    probe_df = pd.DataFrame(
        {
            "id": [101, 102, 103],
            "latitud": [19.4326, 19.4326, 19.4326],
            "longitud": [-99.1332, -99.1332, -99.1332],
            "cve_ent": ["09", "09", "09"],
            "cve_mun": ["015", "015", "015"],
            "cve_loc": ["0001", "0001", ""],  # row 3 unmatchable
            "ageb": ["0771", "0999", "0771"],  # row 1 match, row 2 valid mismatch, row 3 missing loc
        }
    )

    res = denue_code_compatibility(probe_df)
    assert res["raw_count"] == 3
    assert res["retained_count"] == 3
    assert res["matched_cvegeo"] == 1
    assert res["discrepancy_cvegeo"] == 1
    assert res["unmatchable_cvegeo"] == 1
    # Complete partition: retained == matched + discrepancy + unmatchable
    assert (
        res["matched_cvegeo"] + res["discrepancy_cvegeo"] + res["unmatchable_cvegeo"]
        == res["retained_count"]
    )
    # Eligible denominator excludes unmatchable
    assert res["eligible_denominator"] == 2
    assert res["agreement_rate"] == 0.5
    # Preserves establishment id in audit sample
    assert "id" in res["audit_sample"].columns
    assert res["audit_sample"]["id"].tolist() == [101, 102, 103]


def test_denue_code_compatibility(denue_results):
    assert denue_results["raw_count"] == 462732
    assert denue_results["valid_coords_count"] == 462729
    assert denue_results["invalid_coords_count"] == 3
    assert denue_results["retained_count"] == 461231
    assert denue_results["outside_count"] == 1498
    assert denue_results["matched_cvegeo"] == 460503
    assert denue_results["discrepancy_cvegeo"] == 728
    assert denue_results["unmatchable_cvegeo"] == 0
    assert denue_results["eligible_denominator"] == 461231
    assert denue_results["agreement_rate"] == pytest.approx(0.998422, abs=1e-5)
    # Complete partition invariant
    assert (
        denue_results["retained_count"]
        + denue_results["outside_count"]
        + denue_results["invalid_coords_count"]
        == denue_results["raw_count"]
    )


def test_denue_zero_denominator(monkeypatch):
    polygons = gpd.GeoDataFrame({"cvegeo": []}, geometry=[], crs=6372)
    monkeypatch.setattr(spatial, "load_ageb", lambda: polygons)
    empty_df = pd.DataFrame(
        columns=["cve_ent", "cve_mun", "cve_loc", "ageb", "latitud", "longitud"]
    )
    res = denue_code_compatibility(empty_df)
    assert np.isnan(res["agreement_rate"])


# ---------------------------------------------------------------------------
# Crime profiling & temporal tests
# ---------------------------------------------------------------------------


def test_crime_temporal_and_grain(crime_results):
    assert crime_results["raw_count"] == 138630
    assert crime_results["sha256_digest"] == PINNED_CRIME_SHA256
    assert crime_results["filing_start"] == "2024-01-01"
    assert crime_results["filing_end"] == "2024-07-31"
    assert crime_results["filing_months_count"] == 7
    assert crime_results["calendar_days_count"] == 213
    assert crime_results["february_days_count"] == 29
    assert crime_results["observed_filing_months"] == [1, 2, 3, 4, 5, 6, 7]
    assert crime_results["unobserved_filing_months"] == [8, 9, 10, 11, 12]
    assert crime_results["invalid_dates_count"] == 11
    assert crime_results["invalid_filing_dates_count"] == 0
    assert crime_results["earlier_years_count"] == 15492
    assert crime_results["year_2024_count"] == 123127
    assert crime_results["eligible_count"] == 119666
    assert crime_results["valid_coords_count"] == 112484
    assert crime_results["duplicates_count"] == 0
    assert crime_results["retained_count"] == 112285
    assert crime_results["outside_count"] == 199


# ---------------------------------------------------------------------------
# Provenance preflight tests
# ---------------------------------------------------------------------------


def test_verify_input_provenance():
    required = [
        DATA_RAW / f"{key}.zip" for key in PINNED_MANIFEST_DIGESTS if key != "crime_fgj_2024"
    ] + [DATA_RAW / "crime_fgj_2024.csv", DATA_RAW / "crime_fgj_2024/crime_fgj_2024.csv",
         DATA_PROCESSED / "ageb.parquet"]
    if not all(path.exists() for path in required):
        pytest.skip("Complete pinned inputs and transformed geography are required")
    verified = verify_input_provenance()
    assert isinstance(verified, dict)
    for key, expected_hash in PINNED_MANIFEST_DIGESTS.items():
        if key in verified:
            assert verified[key] == expected_hash


def test_verify_input_provenance_failure(tmp_path):
    # Create corrupted zip file
    fake_zip = tmp_path / "census_ageb_2020_09.zip"
    fake_zip.write_text("corrupted content", encoding="utf-8")
    with pytest.raises(ValueError, match="Raw input provenance verification failed"):
        verify_input_provenance(raw_dir=tmp_path)


def test_verify_crime_provenance(tmp_path):
    if not (DATA_RAW / "crime_fgj_2024.csv").exists() and not (DATA_RAW / "crime_fgj_2024/crime_fgj_2024.csv").exists():
        pytest.skip("Pinned FGJ source is missing")
    digest = verify_crime_provenance()
    assert digest == PINNED_CRIME_SHA256

    corrupt_file = tmp_path / "corrupted_crime.csv"
    corrupt_file.write_text("id,delito\n1,test", encoding="utf-8")
    with pytest.raises(ValueError, match="Crime raw SHA-256 mismatch"):
        verify_crime_provenance(corrupt_file)


# ---------------------------------------------------------------------------
# Summary table and temporal figure generation tests
# ---------------------------------------------------------------------------


def test_summary_table_generation(census_results, denue_results, crime_results):
    table = build_source_integration_summary_table(census_results, denue_results, crime_results)
    assert isinstance(table, pd.DataFrame)
    assert len(table) == 4
    assert table["Retained in Urban AGEBs"].tolist() == [2431, 2431, 461231, 112285]
    # Census row checks
    census_row = table.iloc[1]
    assert census_row["Raw Records"] == 68941
    assert census_row["Filtered / Eligible"] == 2433
    assert census_row["Retention % (Raw)"] == pytest.approx(3.53, abs=0.01)
    assert census_row["Retention % (Eligible)"] == pytest.approx(99.92, abs=0.01)


def test_temporal_figure_nan_semantics(tmp_path, crime_results):
    fig, axes = plot_cross_source_temporal_coverage(
        output_path=tmp_path / "temporal_test.png",
        filing_monthly=crime_results["monthly_filings"].drop(index=2),
        offence_monthly=crime_results["monthly_retained_offences"],
    )
    assert fig is not None
    assert len(axes) == 3
    assert (tmp_path / "temporal_test.png").exists()
    # An observed empty February is zero; unobserved Aug-Dec must be missing.
    heights = [bar.get_height() for bar in axes[1].patches if hasattr(bar, "get_height")]
    assert heights[1] == 0
    assert all(np.isnan(heights[i]) for i in [*range(7, 12), *range(19, 24)])
