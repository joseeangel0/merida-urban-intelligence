"""Check Moran direction, sample alignment and permutation reproducibility."""

import geopandas as gpd
import numpy as np
import pytest
from libpysal.weights import lag_spatial
from shapely.geometry import box

from src.analysis.crime_bivariate import bivariate_results


@pytest.fixture
def sample():
    return gpd.GeoDataFrame(
        {"business_density_km2": [1, 3, 9, 2, 4, 10, 5, 8, 20],
         "crime_rate_per_1k": [8, 1, 4, 5, 3, 9, 2, 10, 12]},
        geometry=[box(x, y, x + 1, y + 1) for y in range(3) for x in range(3)],
        crs="EPSG:6372", index=[f"unit-{i}" for i in range(9)],
    )


def test_moran_uses_x_at_ageb_against_spatial_lag_of_y(sample):
    table, statistics = bivariate_results(sample, permutations=19)
    statistic = statistics[("queen", "raw")]
    x = sample.business_density_km2.to_numpy(dtype=float)
    y = sample.crime_rate_per_1k.to_numpy(dtype=float)
    zx = (x - x.mean()) / x.std(ddof=1)
    zy = (y - y.mean()) / y.std(ddof=1)
    expected = zx @ lag_spatial(statistic.w, zy) / (len(sample) - 1)
    assert statistic.I == pytest.approx(expected)
    assert table.iloc[0]["z_sim"] == pytest.approx(statistic.z_sim)
    assert len(table) == 4 and table.n.eq(9).all()
    assert table.permutations.eq(19).all()
    assert table.islands_after_attachment.eq(0).all()
    assert statistic.w.id_order == sample.index.tolist()
    assert np.asarray(statistic.w.sparse.sum(axis=1)).ravel() == pytest.approx(np.ones(9))


def test_permutations_reproduce_and_preserve_callers_random_state(sample):
    np.random.seed(7)
    expected_next = np.random.random()
    np.random.seed(7)
    _, first = bivariate_results(sample, permutations=19)
    assert np.random.random() == expected_next
    _, second = bivariate_results(sample, permutations=19)
    for key in first:
        np.testing.assert_array_equal(first[key].sim, second[key].sim)


@pytest.mark.parametrize("bad_value", [np.nan, np.inf, -1])
def test_rejects_non_finite_or_negative_rates(sample, bad_value):
    sample["crime_rate_per_1k"] = sample["crime_rate_per_1k"].astype(float)
    sample.iloc[0, sample.columns.get_loc("crime_rate_per_1k")] = bad_value
    with pytest.raises(ValueError, match="finite, non-negative"):
        bivariate_results(sample)


def test_rejects_constant_indicators(sample):
    sample["crime_rate_per_1k"] = 1
    with pytest.raises(ValueError, match="vary"):
        bivariate_results(sample)


def test_rejects_too_few_rows_or_duplicate_indices(sample):
    with pytest.raises(ValueError, match="seven"):
        bivariate_results(sample.iloc[:6])
    sample.index = ["same"] * len(sample)
    with pytest.raises(ValueError, match="unique"):
        bivariate_results(sample)
