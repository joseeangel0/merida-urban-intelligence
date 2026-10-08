"""Transform INEGI Census 2020 urban-AGEB results into the demographic data contract."""
from pathlib import Path

import pandas as pd

from src.config import CVE_ENT, DATA_PROCESSED, DATA_RAW, ROOT
from src.transform.spatial import load_ageb

CENSUS_DIR = DATA_RAW / f"census_ageb_2020_{CVE_ENT}" / f"ageb_mza_urbana_{CVE_ENT}_cpv2020"
CENSUS_FILE = CENSUS_DIR / "conjunto_de_datos" / f"conjunto_de_datos_ageb_urbana_{CVE_ENT}_cpv2020.csv"
OUTPUT_FILE = DATA_PROCESSED / "census_ageb.parquet"

# Census variable -> dw.fact_census_ageb column, in table order (sql/01_schema.sql)
MEASURE_COLUMNS = {
    "POBTOT": "pop_total",
    "POBFEM": "pop_female",
    "POBMAS": "pop_male",
    "POB0_14": "pop_0_14",
    "POB15_64": "pop_15_64",
    "POB65_MAS": "pop_65_plus",
    "P_12YMAS": "pop_12_plus",
    "P_18YMAS": "pop_18_plus",
    "P_60YMAS": "pop_60_plus",
    "PEA": "pea",
    "PEA_F": "pea_female",
    "PEA_M": "pea_male",
    "PE_INAC": "pop_inactive",
    "POCUPADA": "pop_employed",
    "PDESOCUP": "pop_unemployed",
    "GRAPROES": "avg_schooling",
    "TOTHOG": "households",
    "VIVTOT": "dwellings_total",
    "TVIVHAB": "dwellings_inhabited",
    "PROM_OCUP": "avg_occupants",
}
DECIMAL_COLUMNS = {"avg_schooling", "avg_occupants"}
# INEGI confidentiality suppression and "not available": stored as NULL, never 0
SUPPRESSED_CODES = ["*", "N/D"]
KEY_COLUMNS = ["ENTIDAD", "MUN", "LOC", "AGEB", "MZA"]
OUTPUT_COLUMNS = ["cvegeo", *MEASURE_COLUMNS.values(), "n_suppressed_fields"]

# CDMX urban AGEBs with a polygon (TEAM_PLAN §3.5)
EXPECTED_AGEBS = 2_431
EXPECTED_POPULATION = 9_138_524
EXPECTED_PEA = 5_061_682
EXPECTED_POP_12_PLUS = 7_858_894


def read_census(path: Path = CENSUS_FILE) -> pd.DataFrame:
    """Read the census CSV as text, so '*', 'N/D' and zero-padded keys stay as published."""
    if not path.exists():
        raise FileNotFoundError(f"Census source not found: {path}; run the download step first")
    frame = pd.read_csv(path, dtype=str, encoding="utf-8-sig", keep_default_na=False)
    missing = set(KEY_COLUMNS).union(MEASURE_COLUMNS).difference(frame.columns)
    if missing:
        raise ValueError(f"Census source is missing columns: {', '.join(sorted(missing))}")
    return frame


def select_ageb_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep the urban AGEB total rows (MZA '000', AGEB not '0000') and build their CVEGEO.

    Block rows and the locality, alcaldía and state totals would count residents twice.
    """
    rows = frame.loc[frame["MZA"].eq("000") & frame["AGEB"].ne("0000")].copy()
    rows["cvegeo"] = rows["ENTIDAD"] + rows["MUN"] + rows["LOC"] + rows["AGEB"]
    if not rows["cvegeo"].is_unique:
        raise ValueError("Census AGEB rows must have unique CVEGEO keys")
    return rows.reset_index(drop=True)


def clean_measures(rows: pd.DataFrame) -> pd.DataFrame:
    """Rename to the fact-table columns, store '*' and 'N/D' as NULL and count them per AGEB."""
    values = rows[list(MEASURE_COLUMNS)]
    suppressed = values.isin(SUPPRESSED_CODES)
    numeric = values.mask(suppressed).apply(pd.to_numeric, errors="coerce")
    unexpected = numeric.isna() & ~suppressed
    if unexpected.any().any():
        codes = sorted(set(values.where(unexpected).stack().dropna()))
        raise ValueError(f"Unexpected non-numeric census values: {codes}")

    result = numeric.rename(columns=MEASURE_COLUMNS)
    for column in result.columns:
        result[column] = result[column].astype("Float64" if column in DECIMAL_COLUMNS else "Int64")
    result.insert(0, "cvegeo", rows["cvegeo"])
    result["n_suppressed_fields"] = suppressed.sum(axis=1).astype("int16")
    return result[OUTPUT_COLUMNS].reset_index(drop=True)


def run() -> pd.DataFrame:
    """Write the census measures of every urban AGEB with a polygon to census_ageb.parquet."""
    rows = select_ageb_rows(read_census())
    polygon_keys = set(load_ageb()["cvegeo"])
    has_polygon = rows["cvegeo"].isin(polygon_keys)
    dropped = rows.loc[~has_polygon]
    dropped_population = int(pd.to_numeric(dropped["POBTOT"], errors="coerce").sum())
    print(
        f"Dropped {len(dropped)} census AGEBs without a polygon ({dropped_population:,} residents): "
        f"{', '.join(dropped['cvegeo'])}"
    )
    result = clean_measures(rows.loc[has_polygon])

    assert len(result) == EXPECTED_AGEBS, f"Expected {EXPECTED_AGEBS:,} AGEBs; got {len(result):,}"
    assert result["cvegeo"].is_unique, "census cvegeo values must be unique"
    assert result["cvegeo"].str.len().eq(13).all(), "census cvegeo values must have 13 characters"
    assert set(result["cvegeo"]) == polygon_keys, "every AGEB polygon must have exactly one census row"
    assert result["pop_total"].notna().all(), "pop_total must never be NULL"
    assert result["pop_total"].sum() == EXPECTED_POPULATION, f"Σ pop_total = {result['pop_total'].sum():,}"
    assert result["pea"].sum() == EXPECTED_PEA, f"Σ pea = {result['pea'].sum():,}"
    assert result["pop_12_plus"].sum() == EXPECTED_POP_12_PLUS, f"Σ pop_12_plus = {result['pop_12_plus'].sum():,}"

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    result.to_parquet(OUTPUT_FILE, index=False)
    print(
        f"Wrote {len(result):,} urban AGEBs to {OUTPUT_FILE.relative_to(ROOT)} "
        f"(population {result['pop_total'].sum():,}; "
        f"{int(result['n_suppressed_fields'].gt(0).sum())} AGEBs with suppressed fields)"
    )
    return result


if __name__ == "__main__":
    run()
