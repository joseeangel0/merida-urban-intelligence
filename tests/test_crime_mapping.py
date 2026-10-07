"""Regression checks for PR #10's English-label and negligent-crime review."""

import pandas as pd
import pytest

from src.transform import crime


@pytest.mark.parametrize(
    ("raw", "english", "category"),
    [
        ("HOMICIDIO POR ARMA DE FUEGO", "Homicide with a Firearm", "Violent"),
        ("FEMINICIDIO POR ARMA BLANCA", "Femicide with a Bladed Weapon", "Violent"),
        ("PLAGIO O SECUESTRO", "Kidnapping", "Violent"),
        ("ACOSO SEXUAL", "Sexual Harassment", "Sexual"),
        ("VIOLACIÓN EQUIPARADA", "Offence Legally Equivalent to Rape", "Sexual"),
        ("VIOLACION DE CORRESPONDENCIA", "Violation of Correspondence Privacy", "Other"),
        ("LESIONES CULPOSAS POR TRANSITO VEHICULAR EN COLISION", "Negligent Injury in a Traffic Collision", "Other"),
        ("LESIONES CULPOSAS POR CAIDA", "Negligent Injury from a Fall", "Other"),
        ("HOMICIDIO CULPOSO POR ARMA DE FUEGO", "Negligent Homicide with a Firearm", "Other"),
        ("DANO EN PROPIEDAD AJENA CULPOSA", "Negligent Damage to Another Person's Property", "Other"),
        ("LESIONES INTENCIONALES POR GOLPES", "Intentional Assault and Battery", "Violent"),
        ("ROBO A PASAJERO A BORDO DE METRO SIN VIOLENCIA", "Theft from a Metro Passenger without Violence", "Property"),
    ],
)
def test_reviewed_offences(raw, english, category):
    assert crime._map_crime_type(raw) == english
    assert crime._map_crime_category(crime._normalize(raw)) == category


def test_accent_variants_share_a_type_and_category():
    labels = ["VIOLACION", "VIOLACIÓN", "  violación  "]
    assert {crime._map_crime_type(label) for label in labels} == {"Rape"}
    assert {crime._map_crime_category(crime._normalize(label)) for label in labels} == {"Sexual"}


def test_unknown_label_has_no_spanish_fallback():
    with pytest.raises(ValueError, match="Missing English crime label"):
        crime._map_crime_type("UNREVIEWED OFFENCE")


def test_unknown_label_fails_before_coordinate_filter(tmp_path, monkeypatch):
    """Even an ungeolocated eligible record must have a reviewed translation."""
    raw_file = tmp_path / "crime.csv"
    pd.DataFrame({
        "fecha_hecho": ["2024-01-01"],
        "categoria_delito": ["DELITO DE BAJO IMPACTO"],
        "delito": ["UNREVIEWED OFFENCE"],
        "latitud": [None],
        "longitud": [None],
    }).to_csv(raw_file, index=False)
    monkeypatch.setattr(crime, "RAW_FILE", raw_file)

    def unexpected_coordinate_filter(*args):
        pytest.fail("Translation coverage must be checked before coordinates")

    monkeypatch.setattr(crime, "points_from_latlon", unexpected_coordinate_filter)
    with pytest.raises(ValueError, match="UNREVIEWED OFFENCE"):
        crime.run()


@pytest.mark.skipif(not crime.RAW_FILE.exists(), reason="Pinned FGJ source is not downloaded")
def test_real_2024_source_is_fully_translated():
    frame = pd.read_csv(crime.RAW_FILE, dtype=str)
    eligible = frame.loc[
        pd.to_datetime(frame["fecha_hecho"], errors="coerce").dt.year.eq(crime.CRIME_YEAR)
        & frame["categoria_delito"].ne("HECHO NO DELICTIVO")
    ]
    crime._validate_translation_coverage(eligible["delito"])
    labels = eligible["delito"].map(crime._normalize).drop_duplicates()
    mapped = pd.DataFrame({
        "crime_type": labels.map(crime._map_crime_type),
        "crime_category": labels.map(crime._map_crime_category),
    })
    assert mapped.groupby("crime_type")["crime_category"].nunique().eq(1).all()
    assert mapped.loc[labels.str.contains("CULPOS"), "crime_category"].eq("Other").all()
