"""Spatial weights and local clusters shared by the Moran, LISA and bivariate analyses."""

import geopandas as gpd
import pandas as pd
from esda import Moran_Local
from libpysal.weights import KNN, Queen, W, attach_islands

# Moran_Local quadrants: 1 = HH, 2 = LH, 3 = LL, 4 = HL
CLUSTER_LABELS = {1: "HH", 2: "LH", 3: "LL", 4: "HL"}
NOT_SIGNIFICANT = "ns"


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


def local_clusters(
    gdf: gpd.GeoDataFrame,
    column: str,
    w: W,
    permutations: int = 999,
    alpha: float = 0.05,
    seed: int = 42,
) -> pd.DataFrame:
    """Local Moran's I cluster per row of gdf: HH, LL, HL, LH, or ns when p_sim >= alpha.

    w must be built on the same rows (build_weights(gdf)); the result has gdf's index and
    the columns `cluster` and `p_sim`. The seed makes the permutation p-values reproducible.
    """
    if list(w.id_order) != gdf.index.tolist():
        raise ValueError("w must be built on gdf: same ids in the same order (use build_weights(gdf))")
    values = gdf[column]
    if values.isna().any():
        raise ValueError(f"{column} has missing values; drop them before building the weights")

    local = Moran_Local(values.to_numpy(dtype=float), w, permutations=permutations, seed=seed)
    labels = [
        CLUSTER_LABELS[quadrant] if p_value < alpha else NOT_SIGNIFICANT
        for quadrant, p_value in zip(local.q, local.p_sim)
    ]
    return pd.DataFrame({"cluster": labels, "p_sim": local.p_sim}, index=gdf.index)
