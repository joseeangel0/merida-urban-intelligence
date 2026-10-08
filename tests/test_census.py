import pandas as pd
import pytest

from src.transform.census import (
    MEASURE_COLUMNS,
    OUTPUT_COLUMNS,
    clean_measures,
    read_census,
    select_ageb_rows,
)


def census_row(mun, loc, ageb, mza, **overrides):
    """One census row with every measure set to '10' unless overridden."""
    row = {"ENTIDAD": "09", "MUN": mun, "LOC": loc, "AGEB": ageb, "MZA": mza}
    row.update(dict.fromkeys(MEASURE_COLUMNS, "10"))
    row.update(overrides)
    return row


@pytest.fixture
def census() -> pd.DataFrame:
    """Every aggregation level of the INEGI file: state, alcaldía, locality, AGEB and block rows."""
    return pd.DataFrame(
        [
            census_row("000", "0000", "0000", "000"),
            census_row("002", "0000", "0000", "000"),
            census_row("002", "0001", "0000", "000"),
            census_row("002", "0001", "0010", "000", GRAPROES="11.25", PDESOCUP="0"),
            census_row("002", "0001", "0010", "001"),
            census_row("002", "0001", "002A", "000", POB0_14="*", PDESOCUP="*", GRAPROES="N/D"),
        ]
    )


def test_select_ageb_rows_keeps_only_ageb_totals_and_builds_cvegeo(census):
    result = select_ageb_rows(census)

    assert result["cvegeo"].tolist() == ["0900200010010", "090020001002A"]


def test_select_ageb_rows_rejects_duplicated_keys(census):
    with pytest.raises(ValueError, match="unique"):
        select_ageb_rows(pd.concat([census, census.iloc[[3]]], ignore_index=True))


def test_clean_measures_has_exact_contract_and_nullable_types(census):
    result = clean_measures(select_ageb_rows(census))

    assert result.columns.tolist() == OUTPUT_COLUMNS
    assert str(result["pop_total"].dtype) == "Int64"
    assert str(result["avg_schooling"].dtype) == "Float64"
    assert str(result["n_suppressed_fields"].dtype) == "int16"
    assert result.loc[0, "avg_schooling"] == 11.25


def test_clean_measures_stores_suppressed_values_as_null_not_zero(census):
    result = clean_measures(select_ageb_rows(census)).set_index("cvegeo")

    suppressed = result.loc["090020001002A"]
    assert pd.isna(suppressed["pop_0_14"])
    assert pd.isna(suppressed["pop_unemployed"])
    assert pd.isna(suppressed["avg_schooling"])
    assert suppressed["n_suppressed_fields"] == 3
    assert result.loc["0900200010010", "pop_unemployed"] == 0
    assert result.loc["0900200010010", "n_suppressed_fields"] == 0


def test_clean_measures_rejects_unexpected_codes(census):
    census.loc[3, "PEA"] = "n.a."

    with pytest.raises(ValueError, match="n.a."):
        clean_measures(select_ageb_rows(census))


def test_read_census_keeps_codes_and_leading_zeros_as_text(tmp_path, census):
    path = tmp_path / "census.csv"
    census.to_csv(path, index=False)

    result = read_census(path)

    assert result.loc[5, "AGEB"] == "002A"
    assert result.loc[3, "LOC"] == "0001"
    assert result.loc[5, "GRAPROES"] == "N/D"
    assert result.loc[5, "POB0_14"] == "*"


def test_read_census_requires_every_measure_column(tmp_path, census):
    path = tmp_path / "census.csv"
    census.drop(columns="PEA").to_csv(path, index=False)

    with pytest.raises(ValueError, match="PEA"):
        read_census(path)
