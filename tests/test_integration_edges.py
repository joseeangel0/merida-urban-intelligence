"""Synthetic regression fixtures, never used as analytical source records."""
import hashlib
import zipfile

import geopandas as gpd
import pandas as pd
import pytest
from shapely import affinity
from shapely.geometry import MultiPolygon, box

from src.analysis import provenance
from src.analysis.integration import census_polygon_compatibility
from src.transform.geography import AGEB_COLUMNS


@pytest.fixture
def pinned_inputs(tmp_path, monkeypatch):
    """Tiny complete fixture with a deliberately test-only pinned version."""
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    raw.mkdir()
    processed.mkdir()
    geometries = [box(2800000, 800000, 2800100, 800100), box(2800100, 800000, 2800200, 800100)]
    frame = gpd.GeoDataFrame(
        {"CVEGEO": ["0901500010771", "0901500010999"], "CVE_ENT": ["09"] * 2,
         "CVE_MUN": ["015"] * 2, "CVE_LOC": ["0001"] * 2, "CVE_AGEB": ["0771", "0999"]},
        geometry=geometries, crs="EPSG:6372",
    )
    directory = raw / "marco_geo_2020_09" / "conjunto_de_datos"
    directory.mkdir(parents=True)
    frame.to_file(directory / "09a.shp")
    for stem, key in [("09l", "090150001"), ("09mun", "09015")]:
        layer = gpd.GeoDataFrame(
            {"CVEGEO": [key], "CVE_ENT": ["09"], "CVE_MUN": ["015"], "NOMGEO": ["Fixture"]},
            geometry=[box(2800000, 800000, 2800200, 800100)], crs="EPSG:6372",
        )
        layer.to_file(directory / f"{stem}.shp")
    for key in ("census_ageb_2020_09", "denue_09"):
        member = provenance.ARCHIVE_MEMBERS[key][0]
        path = raw / key / member
        path.parent.mkdir(parents=True)
        path.write_text("fixture_column\nfixture_value\n", encoding="utf-8")
    for key in provenance.ARCHIVE_MEMBERS:
        with zipfile.ZipFile(raw / f"{key}.zip", "w") as archive:
            for path in sorted((raw / key).rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(raw / key).as_posix())
        monkeypatch.setitem(provenance.PINNED_MANIFEST_DIGESTS, key, provenance._hash_file(raw / f"{key}.zip"))
    crime = b"fixture_column\nnot_an_analytical_incident\n"
    (raw / "crime_fgj_2024.csv").write_bytes(crime)
    (raw / "crime_fgj_2024").mkdir()
    (raw / "crime_fgj_2024" / "crime_fgj_2024.csv").write_bytes(crime)
    digest = hashlib.sha256(crime).hexdigest()
    monkeypatch.setattr(provenance, "PINNED_CRIME_SHA256", digest)
    monkeypatch.setitem(provenance.PINNED_MANIFEST_DIGESTS, "crime_fgj_2024", digest)
    result = gpd.GeoDataFrame(
        {"cvegeo": frame["CVEGEO"], "cve_ent": frame["CVE_ENT"], "cve_mun": frame["CVE_MUN"],
         "cve_loc": frame["CVE_LOC"], "cve_ageb": frame["CVE_AGEB"], "mun_name": ["Fixture"] * 2,
         "loc_name": ["Fixture"] * 2, "is_city_core": [True] * 2},
        geometry=[MultiPolygon([geom]) for geom in geometries], crs=frame.crs,
    )
    result["area_km2"] = result.geometry.area / 1_000_000
    result[AGEB_COLUMNS].to_parquet(processed / "ageb.parquet", index=False)
    return raw, processed


def _input_bytes(raw, processed):
    return {str(path): path.read_bytes() for root in (raw, processed) for path in root.rglob("*") if path.is_file()}


def test_preflight_checks_consumed_inputs_without_writing(pinned_inputs):
    raw, processed = pinned_inputs
    before = _input_bytes(raw, processed)
    verified = provenance.verify_input_provenance(raw, processed)
    assert verified == provenance.PINNED_MANIFEST_DIGESTS
    assert _input_bytes(raw, processed) == before
    assert provenance.verify_input_provenance(raw, processed) == verified


@pytest.mark.parametrize("key,member", [
    ("census_ageb_2020_09", provenance.ARCHIVE_MEMBERS["census_ageb_2020_09"][0]),
    ("denue_09", provenance.ARCHIVE_MEMBERS["denue_09"][0]),
    ("marco_geo_2020_09", "conjunto_de_datos/09a.dbf"),
    ("marco_geo_2020_09", "conjunto_de_datos/09l.cpg"),
])
def test_stale_extraction_fails_with_unchanged_pinned_archive(pinned_inputs, key, member):
    raw, processed = pinned_inputs
    path = raw / key / member
    path.write_bytes(path.read_bytes() + b"stale_fixture")
    before = _input_bytes(raw, processed)
    with pytest.raises(ValueError, match="extracted bytes differ"):
        provenance.verify_input_provenance(raw, processed)
    assert _input_bytes(raw, processed) == before


@pytest.mark.parametrize("relative", [
    "census_ageb_2020_09.zip", "denue_09.zip", "marco_geo_2020_09.zip", "crime_fgj_2024.csv",
    "crime_fgj_2024/crime_fgj_2024.csv", "marco_geo_2020_09/conjunto_de_datos/09a.prj",
    "marco_geo_2020_09/conjunto_de_datos/09mun.cpg",
    "denue_09/conjunto_de_datos/denue_inegi_09_.csv",
])
def test_missing_required_source_fails(pinned_inputs, relative):
    raw, processed = pinned_inputs
    (raw / relative).unlink()
    with pytest.raises(ValueError, match="missing"):
        provenance.verify_input_provenance(raw, processed)


def test_missing_processed_polygons_fails(pinned_inputs):
    raw, processed = pinned_inputs
    (processed / "ageb.parquet").unlink()
    with pytest.raises(ValueError, match="processed polygons are missing"):
        provenance.verify_input_provenance(raw, processed)


def test_empty_prerequisites_fail(tmp_path):
    with pytest.raises(ValueError, match="required archive is missing"):
        provenance.verify_input_provenance(tmp_path / "raw", tmp_path / "processed")


@pytest.mark.parametrize("target", ["denue_09.zip", "crime_fgj_2024.csv", "crime_fgj_2024/crime_fgj_2024.csv"])
def test_unexpected_raw_version_fails(pinned_inputs, target):
    raw, processed = pinned_inputs
    path = raw / target
    path.write_bytes(path.read_bytes() + b"different_fixture_version")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        provenance.verify_input_provenance(raw, processed)


def test_unverified_extra_shapefile_index_fails(pinned_inputs):
    raw, processed = pinned_inputs
    (raw / "marco_geo_2020_09/conjunto_de_datos/09a.qix").write_bytes(b"extra_fixture_index")
    with pytest.raises(ValueError, match="unverified extra shapefile sidecar"):
        provenance.verify_input_provenance(raw, processed)


@pytest.mark.parametrize("change", ["geometry", "area_km2", "loc_name", "cvegeo", "crs"])
def test_altered_processed_polygons_fail(pinned_inputs, change):
    raw, processed = pinned_inputs
    path = processed / "ageb.parquet"
    frame = gpd.read_parquet(path)
    if change == "geometry":
        frame.loc[0, "geometry"] = affinity.translate(frame.geometry.iloc[0], xoff=1)
        assert frame.geometry.is_valid.all()  # Same count, valid polygons, same CRS/area.
    elif change == "crs":
        frame = frame.set_crs("EPSG:3857", allow_override=True)
    elif change == "area_km2":
        frame.loc[0, change] *= 2
    else:
        frame.loc[0, change] = "altered_fixture"
    frame.to_parquet(path, index=False)
    before = path.read_bytes()
    with pytest.raises(ValueError, match="ageb.parquet"):
        provenance.verify_input_provenance(raw, processed)
    assert path.read_bytes() == before


def _census_frame(populations):
    n = len(populations)
    return pd.DataFrame({"ENTIDAD": ["09"] * n, "MUN": ["015"] * n, "LOC": ["0001"] * n,
                         "AGEB": ["0771", "0999", "0888"][:n], "MZA": ["000"] * n,
                         "NOM_MUN": ["Fixture"] * n, "POBTOT": populations})


@pytest.mark.parametrize("suppressed", ["*", "N/D"])
def test_matched_population_must_be_known(suppressed):
    with pytest.raises(ValueError, match="Matched AGEB POBTOT must not be missing"):
        census_polygon_compatibility(_census_frame([suppressed, "10"]), {"0901500010771"})


@pytest.mark.parametrize("values", [["100", "*"], ["100", "N/D"], ["100", "*", "N/D"]])
def test_entirely_suppressed_orphan_population_stays_missing(values):
    result = census_polygon_compatibility(_census_frame(values), {"0901500010771"})
    assert pd.isna(result["orphan_population"])
    assert result["orphan_summary"]["pop_total"].isna().all()
    assert result["orphan_population_observed_count"] == 0
    assert result["orphan_population_missing_count"] == len(values) - 1
    assert result["orphan_population_complete"] is False


def test_partial_orphan_population_discloses_missing_coverage():
    result = census_polygon_compatibility(_census_frame(["100", "5", "*"]), {"0901500010771"})
    assert result["orphan_population"] == 5
    assert result["orphan_population_observed_count"] == 1
    assert result["orphan_population_missing_count"] == 1
    assert result["orphan_population_complete"] is False


def test_observed_zero_population_is_zero():
    result = census_polygon_compatibility(_census_frame(["0", "0"]), {"0901500010771"})
    assert result["matched_population"] == result["orphan_population"] == 0
    assert result["matched_population_missing_count"] == result["orphan_population_missing_count"] == 0
    assert result["orphan_population_complete"] is True


def test_empty_orphan_group_is_not_suppressed():
    result = census_polygon_compatibility(_census_frame(["100"]), {"0901500010771"})
    assert result["orphan_count"] == result["orphan_population"] == 0
    assert result["orphan_population_observed_count"] == result["orphan_population_missing_count"] == 0
    assert result["orphan_population_complete"] is True


@pytest.mark.parametrize("values", [["bad", "10"], ["100", "12a"]])
def test_malformed_population_rejected_at_aggregation(values):
    with pytest.raises(ValueError, match="Unexpected non-numeric census values in POBTOT"):
        census_polygon_compatibility(_census_frame(values), {"0901500010771"})
