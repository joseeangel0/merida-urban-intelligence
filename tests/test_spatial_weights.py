import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from src.analysis.spatial_weights import build_weights, local_clusters


@pytest.fixture
def gdf() -> gpd.GeoDataFrame:
    """Three contiguous squares plus one island (D)."""
    return gpd.GeoDataFrame(
        {"cvegeo": ["A", "B", "C", "D"]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1), box(0, 1, 1, 2), box(10, 10, 11, 11)],
        crs="EPSG:6372",
    ).set_index("cvegeo")


def test_queen_attaches_island_and_row_standardizes(gdf):
    weights = build_weights(gdf, kind="queen")

    assert weights.id_order == ["A", "B", "C", "D"]
    assert weights.islands == []
    for observation in weights.id_order:
        assert sum(weights.weights[observation]) == pytest.approx(1.0)


def test_knn_uses_requested_neighbor_count_and_row_standardizes(gdf):
    weights = build_weights(gdf, kind="knn", k=2)

    assert all(len(neighbors) == 2 for neighbors in weights.neighbors.values())
    for observation in weights.id_order:
        assert sum(weights.weights[observation]) == pytest.approx(1.0)


def test_rejects_unsupported_kind_and_invalid_k(gdf):
    with pytest.raises(ValueError, match="kind"):
        build_weights(gdf, kind="rook")
    with pytest.raises(ValueError, match="k"):
        build_weights(gdf, kind="knn", k=0)


@pytest.fixture
def grid() -> gpd.GeoDataFrame:
    """5 x 5 grid of squares with a block of high values in the lower-left 3 x 3 corner."""
    cells = [(x, y) for y in range(5) for x in range(5)]
    return gpd.GeoDataFrame(
        {
            "cvegeo": [f"{x}{y}" for x, y in cells],
            "value": [10.0 if x < 3 and y < 3 else 0.0 for x, y in cells],
        },
        geometry=[box(x, y, x + 1, y + 1) for x, y in cells],
        crs="EPSG:6372",
    ).set_index("cvegeo")


def test_local_clusters_labels_rows_and_keeps_index(grid):
    result = local_clusters(grid, "value", build_weights(grid))

    assert result.index.equals(grid.index)
    assert result.columns.tolist() == ["cluster", "p_sim"]
    assert set(result["cluster"]) <= {"HH", "LL", "HL", "LH", "ns"}
    assert result.loc["11", "cluster"] == "HH"
    assert result.loc[result["p_sim"] >= 0.05, "cluster"].eq("ns").all()


def test_local_clusters_is_reproducible_with_the_same_seed(grid):
    weights = build_weights(grid)

    first = local_clusters(grid, "value", weights, seed=7)
    second = local_clusters(grid, "value", weights, seed=7)

    pd.testing.assert_frame_equal(first, second)


def test_local_clusters_rejects_misaligned_weights_and_missing_values(grid):
    with pytest.raises(ValueError, match="same ids"):
        local_clusters(grid.iloc[::-1], "value", build_weights(grid))

    grid.loc["00", "value"] = None
    with pytest.raises(ValueError, match="missing values"):
        local_clusters(grid, "value", build_weights(grid))
