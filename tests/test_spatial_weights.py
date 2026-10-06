import unittest

import geopandas as gpd
from shapely.geometry import box

from src.analysis.spatial_weights import build_weights


class SpatialWeightsTests(unittest.TestCase):
    def setUp(self):
        self.gdf = gpd.GeoDataFrame(
            {"cvegeo": ["A", "B", "C", "D"]},
            geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1), box(0, 1, 1, 2), box(10, 10, 11, 11)],
            crs="EPSG:6372",
        ).set_index("cvegeo")

    def test_queen_attaches_island_and_row_standardizes(self):
        weights = build_weights(self.gdf, kind="queen")

        self.assertEqual(weights.id_order, ["A", "B", "C", "D"])
        self.assertEqual(weights.islands, [])
        for observation in weights.id_order:
            self.assertAlmostEqual(sum(weights.weights[observation]), 1.0)

    def test_knn_uses_requested_neighbor_count_and_row_standardizes(self):
        weights = build_weights(self.gdf, kind="knn", k=2)

        self.assertTrue(all(len(neighbors) == 2 for neighbors in weights.neighbors.values()))
        for observation in weights.id_order:
            self.assertAlmostEqual(sum(weights.weights[observation]), 1.0)

    def test_rejects_unsupported_kind_and_invalid_k(self):
        with self.assertRaisesRegex(ValueError, "kind"):
            build_weights(self.gdf, kind="rook")
        with self.assertRaisesRegex(ValueError, "k"):
            build_weights(self.gdf, kind="knn", k=0)


if __name__ == "__main__":
    unittest.main()
