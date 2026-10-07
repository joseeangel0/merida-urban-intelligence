import geopandas as gpd
import pytest
from shapely.geometry import box

from src.analysis.spatial_weights import build_weights


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
