"""Temporal aggregation regressions: weights, calendar exposure and missing bins."""

import pandas as pd
import pytest

from src.analysis.crime_patterns import CRIME_COVERAGE, censoring_sensitivity, temporal_tables

FULL_YEAR = {"coverage_start": "2024-01-01", "coverage_end": "2024-12-31"}


@pytest.fixture
def view_rows():
    return pd.DataFrame({
        "year": [2024, 2024, 2024],
        "month": [2, 2, 1],
        "day_of_week": [1, 2, 1],
        "time_band": ["Unknown", "Morning (06-11)", "Morning (06-11)"],
        "crime_type": ["Fraud", "Fraud", "Threats"],
        "crime_category": ["Property", "Property", "Violent"],
        "incidents": [29, 53, 24],
    })


def test_sums_incident_weights_and_includes_zero_periods(view_rows):
    tables = temporal_tables(view_rows, **FULL_YEAR)
    for name in ["monthly", "weekday", "time_band", "crime_type"]:
        assert tables[name]["incidents"].sum() == 106
    assert tables["monthly"].loc[3, "incidents"] == 0
    assert len(tables["monthly"]) == 12
    assert tables["time_band"].loc["Unknown", "incidents"] == 29
    assert tables["crime_type"].iloc[0]["crime_type"] == "Fraud"
    assert tables["crime_type"].iloc[0]["incidents"] == 82


def test_default_window_is_the_profiled_source_coverage(view_rows):
    tables = temporal_tables(view_rows)
    assert tables["monthly"].attrs["coverage"] == " to ".join(CRIME_COVERAGE)
    assert tables["monthly"]["calendar_days"].sum() == 213
    assert pd.isna(tables["monthly"].loc[8, "incidents"])
    assert tables["monthly"]["right_censored"].tolist() == [month == 7 for month in range(1, 13)]


def test_labels_are_english(view_rows):
    tables = temporal_tables(view_rows)
    assert tables["monthly"].loc[[1, 12], "month_name"].tolist() == ["Jan", "Dec"]
    assert tables["weekday"].loc[[1, 7], "day_name"].tolist() == ["Monday", "Sunday"]


def test_calendar_denominators_handle_leap_year_and_weekday_frequency(view_rows):
    tables = temporal_tables(view_rows, **FULL_YEAR)
    assert tables["monthly"].loc[2, "calendar_days"] == 29
    assert tables["monthly"]["calendar_days"].sum() == 366
    assert tables["weekday"].loc[1, "calendar_days"] == 53
    assert tables["weekday"].loc[2, "calendar_days"] == 53
    assert tables["weekday"].loc[3, "calendar_days"] == 52
    assert tables["weekday_time_band_per_day"].loc[1, "Unknown"] == pytest.approx(29 / 53)
    assert tables["weekday_time_band_per_day"].loc[2, "Morning (06-11)"] == 1


@pytest.mark.parametrize(
    ("column", "value"),
    [("year", 2023), ("month", 13), ("day_of_week", 8),
     ("incidents", -1), ("incidents", 1.5), ("month", None),
     ("time_band", "unreviewed"), ("crime_type", None)],
)
def test_rejects_incomplete_or_invalid_temporal_data(view_rows, column, value):
    view_rows[column] = view_rows[column].astype(object)
    view_rows.loc[0, column] = value
    with pytest.raises(ValueError):
        temporal_tables(view_rows)


def test_rejects_conflicting_category_for_the_same_type(view_rows):
    view_rows.loc[1, "crime_category"] = "Violent"
    with pytest.raises(ValueError, match="exactly one category"):
        temporal_tables(view_rows)


def test_rejects_empty_warehouse_view(view_rows):
    with pytest.raises(ValueError, match="empty"):
        temporal_tables(view_rows.iloc[:0])


def test_partial_snapshot_keeps_unobserved_months_missing_and_adjusts_exposure(view_rows):
    tables = temporal_tables(view_rows, coverage_start="2024-01-01", coverage_end="2024-07-31")
    assert tables["monthly"]["incidents"].sum() == 106
    assert tables["monthly"]["calendar_days"].sum() == 213
    assert tables["monthly"].loc[5, "incidents"] == 0
    assert pd.isna(tables["monthly"].loc[8, "incidents"])
    assert pd.isna(tables["monthly"].loc[8, "incidents_per_day"])
    assert tables["weekday"].loc[1, "calendar_days"] == 31
    assert tables["weekday"].loc[5, "calendar_days"] == 30
    assert tables["weekday_time_band_per_day"].loc[1, "Unknown"] == pytest.approx(29 / 31)
    for name in ["month_by_category", "day_of_week_by_category", "time_band_by_category"]:
        assert tables[name].sum().sum() == 106
        assert tables[name]["Sexual"].sum() == 0
    assert tables["month_by_category"].loc[8].isna().all()
    assert tables["time_band_by_category"].loc["Unknown", "Property"] == 29
    assert tables["day_of_week_by_category"].loc[1, "Violent"] == 24


def test_rejects_view_months_outside_the_declared_source_window(view_rows):
    with pytest.raises(ValueError, match="outside"):
        temporal_tables(view_rows, coverage_start="2024-01-01", coverage_end="2024-01-31")


def test_censoring_sensitivity_drops_the_months_after_the_cutoff(view_rows):
    # Full window Jan-Feb 2024 (60 days); complete months = January only (31 days).
    comparison = censoring_sensitivity(view_rows, "2024-01-31", coverage_end="2024-02-29")
    assert comparison.loc[1, "full_window_per_day"] == pytest.approx((29 + 24) / 9)
    assert comparison.loc[1, "complete_months_per_day"] == pytest.approx(24 / 5)
    assert comparison.loc[2, "complete_months_per_day"] == 0
    assert comparison.loc[1, "change_pct"] == pytest.approx(100 * ((24 / 5) / (53 / 9) - 1))
    assert comparison.loc[1, "complete_months_rank"] == 1


@pytest.mark.parametrize("cutoff", ["2024-01-15", "2024-02-29", "2024-03-31"])
def test_censoring_sensitivity_requires_a_month_end_inside_the_window(view_rows, cutoff):
    with pytest.raises(ValueError, match="sensitivity_end"):
        censoring_sensitivity(view_rows, cutoff, coverage_end="2024-02-29")
