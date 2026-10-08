"""Shared-helper regression evidence for issue #26; fixtures are not source data."""
import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point, box

from src.analysis.integration import denue_code_compatibility, normalize_reported_cvegeo
from src.transform import spatial


def test_coordinate_validation_preserves_ids_and_projects_longitude_first():
    frame = pd.DataFrame({"id": range(8),
                          "latitud": [19.4326, -99.1332, None, "bad", 0, 20, 19.4326, 19.4326],
                          "longitud": [-99.1332, 19.4326, -99.1332, -99.1332, -99.1332, -99.1332, 0, -100]})
    result = spatial.points_from_latlon(frame, "latitud", "longitud")
    expected = gpd.GeoSeries([Point(-99.1332, 19.4326)], crs="EPSG:4326").to_crs("EPSG:6372")
    assert result["id"].tolist() == [0]
    assert result.crs.to_epsg() == 6372
    assert result.geometry.iloc[0].equals(expected.iloc[0])


def test_within_excludes_boundary_and_outside_points(monkeypatch):
    polygons = gpd.GeoDataFrame({"cvegeo": ["0901500010771"]}, geometry=[box(-1, -1, 1, 1)], crs=6372)
    monkeypatch.setattr(spatial, "load_ageb", lambda: polygons)
    points = gpd.GeoDataFrame({"id": [1, 2, 3]}, geometry=[Point(0, 0), Point(1, 0), Point(2, 0)], crs=6372)
    result = spatial.assign_ageb(points)
    assert result["id"].tolist() == [1]
    assert result["cvegeo"].tolist() == ["0901500010771"]


def test_ambiguous_polygon_assignment_fails(monkeypatch):
    polygons = gpd.GeoDataFrame({"cvegeo": ["0901500010771", "0901500010999"]},
                                geometry=[box(-1, -1, 1, 1), box(-2, -2, 2, 2)], crs=6372)
    monkeypatch.setattr(spatial, "load_ageb", lambda: polygons)
    points = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(0, 0)], crs=6372)
    with pytest.raises(ValueError, match="assignment is ambiguous"):
        spatial.assign_ageb(points)


@pytest.mark.parametrize("crs", [None, 3857])
def test_assignment_rejects_missing_or_incompatible_crs(crs):
    points = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(0, 0)], crs=crs)
    with pytest.raises(ValueError, match="Expected input points in EPSG:6372"):
        spatial.assign_ageb(points)


def test_duplicate_processed_polygon_keys_fail(tmp_path, monkeypatch):
    path = tmp_path / "ageb.parquet"
    polygons = gpd.GeoDataFrame({"cvegeo": ["0901500010771"] * 2},
                                geometry=[box(-1, -1, 1, 1), box(2, 2, 3, 3)], crs=6372)
    polygons.to_parquet(path)
    monkeypatch.setattr(spatial, "AGEB_FILE", path)
    with pytest.raises(ValueError, match="cvegeo values must be unique"):
        spatial.load_ageb()


@pytest.mark.parametrize("missing_field", ["cve_ent", "cve_mun", "cve_loc", "ageb"])
def test_key_normalization_preserves_alpha_and_missing_components(missing_field):
    frame = pd.DataFrame({"cve_ent": ["9"] * 3, "cve_mun": ["15"] * 3,
                          "cve_loc": ["1"] * 3, "ageb": ["77A"] * 3})
    frame.loc[1, missing_field] = None
    frame.loc[2, missing_field] = ""
    result = normalize_reported_cvegeo(frame)
    assert result.iloc[0] == "090150001077A"
    assert result.iloc[1:].isna().all()


def test_partition_handles_malformed_keys_and_zero_eligible_comparisons(monkeypatch):
    sample = spatial.points_from_latlon(pd.DataFrame({"latitud": [19.4326], "longitud": [-99.1332]}),
                                       "latitud", "longitud")
    x, y = sample.geometry.iloc[0].coords[0]
    polygons = gpd.GeoDataFrame({"cvegeo": ["0901500010771"]}, geometry=[box(x-10, y-10, x+10, y+10)], crs=6372)
    monkeypatch.setattr(spatial, "load_ageb", lambda: polygons)
    frame = pd.DataFrame({"id": range(5), "latitud": [19.4326] * 5, "longitud": [-99.1332] * 5,
                          "cve_ent": ["09", "09", "09", "009", "09"], "cve_mun": ["015"] * 5,
                          "cve_loc": ["0001"] * 5, "ageb": ["0771", "0999", "", "0771", "077A"]})
    result = denue_code_compatibility(frame)
    assert (result["matched_cvegeo"], result["discrepancy_cvegeo"], result["unmatchable_cvegeo"]) == (1, 2, 2)
    assert result["retained_count"] == 5
    assert result["agreement_rate"] == 1 / 3
    assert result["audit_sample"]["id"].tolist() == list(range(5))
    unavailable = denue_code_compatibility(frame.iloc[[2, 3]])
    assert unavailable["retained_count"] == unavailable["unmatchable_cvegeo"] == 2
    assert unavailable["eligible_denominator"] == 0
    assert np.isnan(unavailable["agreement_rate"])
