"""Spatial weights shared by the Moran and bivariate analyses."""

import geopandas as gpd
from libpysal.weights import KNN, Queen, attach_islands


def build_weights(gdf: gpd.GeoDataFrame, kind: str = "queen", k: int = 6):
    """Build row-standardized Queen or K-nearest-neighbor weights."""
    if kind not in {"queen", "knn"}:
        raise ValueError("kind must be 'queen' or 'knn'")
    if kind == "knn" and (k < 1 or k >= len(gdf)):
        raise ValueError(f"k must be between 1 and {len(gdf) - 1}")
    if gdf.empty or gdf.geometry.isna().any() or gdf.geometry.is_empty.any():
        raise ValueError("gdf must contain non-empty geometries")

    ids = gdf.index.tolist()
    if kind == "knn":
        weights = KNN.from_dataframe(gdf, ids=ids, k=k, silence_warnings=True)
    else:
        weights = Queen.from_dataframe(gdf, ids=ids, silence_warnings=True)
        if weights.islands:
            nearest = KNN.from_dataframe(gdf, ids=ids, k=1, silence_warnings=True)
            weights = attach_islands(weights, nearest, silence_warnings=True)

    weights.transform = "R"
    return weights
