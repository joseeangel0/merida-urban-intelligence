"""Bivariate Moran analysis of warehouse KPIs using the shared spatial weights."""

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from esda import Moran_BV
from libpysal.weights import lag_spatial

from src.analysis.spatial_weights import build_weights
from src.config import SOURCES


def bivariate_results(
    sample: gpd.GeoDataFrame,
    x_column: str = "business_density_km2",
    y_column: str = "crime_rate_per_1k",
    permutations: int = 999,
    seed: int = 42,
) -> tuple[pd.DataFrame, dict]:
    """Test x at each AGEB against the spatial lag of y on the same ordered sample.

    The caller selects warehouse rows before building weights. Raw values are the
    primary result; log1p is a separate sensitivity analysis for skewed indicators.
    PySAL's p_sim is its smaller-tail permutation pseudo p-value, not a two-sided
    normal-test p-value. Preserve the caller's NumPy random state.
    """
    if len(sample) < 7 or not sample.index.is_unique:
        raise ValueError("Sample must have at least seven AGEBs with unique indices")
    if not isinstance(permutations, (int, np.integer)) or isinstance(permutations, bool) or permutations < 1:
        raise ValueError("permutations must be a positive integer")
    values = sample[[x_column, y_column]].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("The density/rate pair must have finite, non-negative values")
    if (values.std(axis=0) == 0).any():
        raise ValueError("Both indicators must vary across AGEBs")

    rows, statistics = [], {}
    for kind in ["queen", "knn"]:
        weights = build_weights(sample, kind=kind, k=6)
        if list(weights.id_order) != sample.index.tolist():
            raise ValueError("Spatial weights do not match the ordered sample")
        for scale in ["raw", "log1p"]:
            transformed = values if scale == "raw" else np.log1p(values)
            random_state = np.random.get_state()
            try:
                np.random.seed(seed)
                statistic = Moran_BV(
                    transformed[:, 0], transformed[:, 1], weights,
                    transformation="r", permutations=permutations,
                )
            finally:
                np.random.set_state(random_state)
            statistics[(kind, scale)] = statistic
            rows.append({
                "x": x_column, "spatial_lag_of": y_column,
                "weights": "Queen" if kind == "queen" else "KNN-6",
                "scale": scale, "n": len(sample), "I": statistic.I,
                "p_sim": statistic.p_sim, "z_sim": statistic.z_sim,
                "permutations": permutations, "seed": seed,
                "components": weights.n_components, "islands_after_attachment": len(weights.islands),
                "mean_neighbours": weights.mean_neighbors,
            })
    return pd.DataFrame(rows), statistics


def save_bivariate_figure(
    statistics: dict, output_dir: Path, seed: int = 42, period_label: str = "2024 snapshot",
) -> Path:
    """Plot the same pair under both weight rules and scales, without clipping outliers."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    fig.suptitle(f"Business density and neighbouring crime rate | CDMX\n{period_label}", fontsize=16)
    for row, kind in enumerate(["queen", "knn"]):
        for column, scale in enumerate(["raw", "log1p"]):
            statistic = statistics[(kind, scale)]
            ax = axes[row, column]
            lag = lag_spatial(statistic.w, statistic.zy)
            ax.scatter(statistic.zx, lag, s=12, alpha=0.4, color="#287b8e", edgecolors="none")
            xline = np.array([statistic.zx.min(), statistic.zx.max()])
            ax.plot(xline, statistic.I * xline + lag.mean(), color="#ba4a45", linewidth=1.6)
            ax.axhline(0, color="#b0b5bb", linewidth=0.7)
            ax.axvline(0, color="#b0b5bb", linewidth=0.7)
            ax.set_title(
                f"{'Queen' if kind == 'queen' else 'KNN-6'} | {scale}\n"
                f"I = {statistic.I:.4f}; p_sim = {statistic.p_sim:.3f}; n = {len(statistic.zx):,}"
            )
            ax.set_xlabel("Standardised business density\n(establishments / km²)" if scale == "raw"
                          else "Standardised log1p(business density)")
            ax.set_ylabel("Spatial lag of standardised\ncrime rate (files / 1,000 residents)" if scale == "raw"
                          else "Spatial lag of standardised\nlog1p(crime rate)")
            ax.spines[["top", "right"]].set_visible(False)
    permutations = len(next(iter(statistics.values())).sim)
    fig.text(0.02, 0.018,
             f"Source: dw.v_kpi_ageb. {SOURCES['census_ageb_2020_09']['version_label']}; "
             f"{SOURCES['denue_09']['version_label']}; FGJ {period_label}.\n"
             "City core; population >= 100; row-standardised weights; "
             f"{permutations} permutations, seed {seed}. Association does not establish causation.", fontsize=8)
    fig.tight_layout(rect=(0, 0.045, 1, 0.94))
    path = output_dir / "bivariate_moran_business_crime.png"
    fig.savefig(path, dpi=180, facecolor="white")
    plt.close(fig)
    return path
