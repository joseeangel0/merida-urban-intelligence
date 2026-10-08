"""Temporal summaries and figures from ``dw.v_crime_by_type_time`` only."""

from pathlib import Path
import textwrap

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
from matplotlib.ticker import StrMethodFormatter

from src.config import CRIME_YEAR

TIME_BANDS = [
    "Night (00-05)", "Morning (06-11)", "Afternoon (12-17)",
    "Evening (18-23)", "Unknown",
]
CRIME_CATEGORIES = ["Property", "Violent", "Sexual", "Other"]
REQUIRED_COLUMNS = {
    "year", "month", "day_of_week", "time_band", "crime_type",
    "crime_category", "incidents",
}
# English labels as in dw.dim_date; calendar.* names would follow the process locale.
MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
# Filing window (fecha_inicio) profiled for the pinned FGJ CSV with this SHA-256.
# Re-profile both values if the warehouse is built from another file version.
CRIME_COVERAGE = ("2024-01-01", "2024-07-31")
CRIME_COVERAGE_SHA256 = "2ac3f17189a61ab7b2eb95fb21470e46adaba6f92526c7b92d23190ed2431f84"
SOURCE_NOTE = "Source: FGJ CDMX investigation files / dw.v_crime_by_type_time. Offence date; urban AGEBs only."


def temporal_tables(
    frame: pd.DataFrame, year: int = CRIME_YEAR,
    coverage_start: str | None = CRIME_COVERAGE[0], coverage_end: str | None = CRIME_COVERAGE[1],
) -> dict[str, pd.DataFrame]:
    """Sum incident weights, including absent periods and unknown hours.

    The view is already aggregated by AGEB/type/time. Counting its rows would
    undercount the incidents. Calendar-day denominators correct for month length
    and unequal weekday frequency in the study year; they are not population
    rates or an adjustment for reporting/coordinate availability. The window
    defaults to the profiled coverage of the pinned source; None means the
    whole study year. Months outside the window are unavailable (NULL), not
    observed zero-crime months. The month holding the window end is flagged
    ``right_censored``: offences near the filing cutoff whose files were opened
    later are missing.
    """
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing temporal-view columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("Crime view is empty; load the crime layer before analysis")
    data = frame.copy()
    for column in ["year", "month", "day_of_week", "incidents"]:
        data[column] = pd.to_numeric(data[column], errors="raise")
        if data[column].isna().any() or not data[column].mod(1).eq(0).all():
            raise ValueError(f"{column} must contain non-null integers")
        data[column] = data[column].astype("int64")
    if not data["year"].eq(year).all():
        raise ValueError(f"The temporal sample must contain only offences from {year}")
    if not data["month"].between(1, 12).all() or not data["day_of_week"].between(1, 7).all():
        raise ValueError("Invalid month or ISO weekday in temporal view")
    if not data["incidents"].gt(0).all():
        raise ValueError("View incident counts must be positive")
    if not data["time_band"].isin(TIME_BANDS).all():
        raise ValueError("Unexpected or missing time band in temporal view")
    if data[["crime_type", "crime_category"]].isna().any().any():
        raise ValueError("Crime labels and categories must not be missing")
    if not data["crime_category"].isin(CRIME_CATEGORIES).all():
        raise ValueError("Unexpected crime category in temporal view")
    if not data.groupby("crime_type")["crime_category"].nunique().eq(1).all():
        raise ValueError("Each crime type must have exactly one category")

    total = int(data["incidents"].sum())
    start = pd.Timestamp(coverage_start or f"{year}-01-01")
    end = pd.Timestamp(coverage_end or f"{year}-12-31")
    if start.year != year or end.year != year or start > end:
        raise ValueError("Coverage must be an ordered interval within the study year")
    calendar_dates = pd.date_range(start, end)
    if not data["month"].isin(calendar_dates.month.unique()).all():
        raise ValueError("View contains months outside the profiled coverage window")
    months = pd.Index(range(1, 13), name="month")
    monthly = data.groupby("month")["incidents"].sum().reindex(months, fill_value=0).to_frame()
    monthly["incidents"] = monthly["incidents"].astype("Int64")
    monthly["month_name"] = MONTH_ABBR
    monthly["calendar_days"] = pd.Series(calendar_dates.month).value_counts().reindex(months, fill_value=0).to_numpy()
    monthly.loc[monthly["calendar_days"].eq(0), "incidents"] = pd.NA
    monthly["incidents_per_day"] = monthly["incidents"] / monthly["calendar_days"].replace(0, np.nan)
    monthly["right_censored"] = monthly.index == end.month
    monthly.attrs["coverage"] = f"{start.date()} to {end.date()}"

    weekdays = pd.Index(range(1, 8), name="day_of_week")
    daily = data.groupby("day_of_week")["incidents"].sum().reindex(weekdays, fill_value=0).to_frame()
    daily["day_name"] = DAY_NAMES
    exposures = pd.Series(calendar_dates.dayofweek + 1).value_counts().reindex(weekdays, fill_value=0)
    daily["calendar_days"] = exposures.to_numpy()
    daily["incidents_per_day"] = daily["incidents"] / daily["calendar_days"].replace(0, np.nan)

    bands = data.groupby("time_band")["incidents"].sum().reindex(TIME_BANDS, fill_value=0).to_frame()
    types = data.groupby(["crime_type", "crime_category"], as_index=False)["incidents"].sum()
    types = types.sort_values(["incidents", "crime_type"], ascending=[False, True]).reset_index(drop=True)
    for table in [monthly, daily, bands, types]:
        table["share_pct"] = 100 * table["incidents"] / total
        if int(table["incidents"].sum()) != total:
            raise ValueError("Temporal summaries must reconcile to the same incident total")

    heatmap = data.groupby(["day_of_week", "time_band"])["incidents"].sum().unstack(fill_value=0)
    heatmap = heatmap.reindex(index=weekdays, columns=TIME_BANDS, fill_value=0)
    if int(heatmap.to_numpy().sum()) != total:
        raise ValueError("Weekday/time-band totals do not reconcile")
    heatmap = heatmap.div(daily["calendar_days"].replace(0, np.nan), axis=0)
    category_tables = {}
    for column, index in [("month", months), ("day_of_week", weekdays), ("time_band", TIME_BANDS)]:
        category_table = data.groupby([column, "crime_category"])["incidents"].sum().unstack(fill_value=0)
        category_table = category_table.reindex(index=index, columns=CRIME_CATEGORIES, fill_value=0).astype("Int64")
        if column == "month":
            category_table.loc[monthly["calendar_days"].eq(0)] = pd.NA
        if int(category_table.sum().sum()) != total:
            raise ValueError("Category summaries must reconcile to the incident total")
        category_tables[f"{column}_by_category"] = category_table
    return {"monthly": monthly, "weekday": daily, "time_band": bands,
            "crime_type": types, "weekday_time_band_per_day": heatmap, **category_tables}


def censoring_sensitivity(
    frame: pd.DataFrame, sensitivity_end: str, year: int = CRIME_YEAR,
    coverage_start: str | None = CRIME_COVERAGE[0], coverage_end: str | None = CRIME_COVERAGE[1],
) -> pd.DataFrame:
    """Weekday averages on the full window and on complete months only.

    Dropping the months after ``sensitivity_end`` removes the right-censored tail
    of the filing window. It shows whether the weekday pattern depends on that
    tail; it is a sensitivity check, not a reporting-lag correction.
    """
    end = pd.Timestamp(sensitivity_end)
    if end != end + pd.offsets.MonthEnd(0):
        raise ValueError("sensitivity_end must be the last day of a month")
    if end >= pd.Timestamp(coverage_end or f"{year}-12-31"):
        raise ValueError("sensitivity_end must fall before the end of the coverage window")
    primary = temporal_tables(frame, year, coverage_start, coverage_end)["weekday"]
    complete_months = frame[pd.to_numeric(frame["month"], errors="raise") <= end.month]
    complete = temporal_tables(complete_months, year, coverage_start, sensitivity_end)["weekday"]
    comparison = pd.DataFrame({
        "day_name": primary["day_name"],
        "full_window_per_day": primary["incidents_per_day"],
        "complete_months_per_day": complete["incidents_per_day"],
    })
    comparison["change_pct"] = 100 * (comparison["complete_months_per_day"] / comparison["full_window_per_day"] - 1)
    for column in ["full_window_per_day", "complete_months_per_day"]:
        comparison[column.replace("per_day", "rank")] = comparison[column].rank(ascending=False, method="min").astype(int)
    return comparison


def export_temporal_tables(tables: dict[str, pd.DataFrame], output_dir: Path) -> dict[str, Path]:
    """Export reproducible summary tables alongside figures."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, table in tables.items():
        path = output_dir / f"crime_{name}.csv"
        table.to_csv(path, index=name != "crime_type")
        paths[name] = path
    return paths


def save_temporal_figures(
    tables: dict[str, pd.DataFrame], output_dir: Path, year: int = CRIME_YEAR,
) -> dict[str, Path]:
    """Save temporal figures, including the category comparison required by the plan."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    colors = {"Property": "#287b8e", "Violent": "#ba4a45",
              "Sexual": "#8056a6", "Other": "#73808d"}

    def save(fig, name):
        fig.text(0.015, 0.017, SOURCE_NOTE + "\nProfiled filing window: "
                 + tables["monthly"].attrs["coverage"] + "; its final month is right-censored (later reports missing)."
                 " No annualisation or reporting-lag adjustment.",
                 fontsize=8, color="#4b5563")
        fig.tight_layout(rect=(0, 0.055, 1, 0.95))
        filename = "crime_temporal_patterns.png" if name == "temporal_patterns" else f"crime_{name}_{year}.png"
        path = output_dir / filename
        fig.savefig(path, dpi=180, facecolor="white")
        plt.close(fig)
        paths[name] = path

    def style(ax):
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.18)
        ax.set_axisbelow(True)
        ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))

    monthly = tables["monthly"]
    month_note = "shaded: outside the source window; hatched: partial, later reports missing"

    def mark_months(ax):
        for position in np.flatnonzero(monthly["calendar_days"].eq(0)):
            ax.axvspan(position - 0.45, position + 0.45, color="#eef0f2", zorder=0)
        for position in np.flatnonzero(monthly["right_censored"] & monthly["calendar_days"].gt(0)):
            ax.axvspan(position - 0.35, position + 0.35, facecolor="none", edgecolor="#9aa3ab",
                       hatch="///", linewidth=0, zorder=3)
            ax.text(position, 0.98, "Partial", transform=ax.get_xaxis_transform(), ha="center", va="top",
                    fontsize=8, color="#4b5563", zorder=4,
                    bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.5})

    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    fig.suptitle(f"Recorded crime by offence month | CDMX {year}", fontsize=16)
    axes[0].bar(monthly["month_name"], monthly["incidents"].to_numpy(dtype=float, na_value=np.nan),
                color="#287b8e", width=0.65)
    axes[0].set_ylabel("Investigation files")
    axes[1].plot(monthly["month_name"], monthly["incidents_per_day"].to_numpy(dtype=float, na_value=np.nan),
                 color="#ba4a45", marker="o")
    axes[1].set_ylabel("Files per calendar day")
    axes[1].set_ylim(bottom=0)
    axes[1].set_xlabel(f"Offence month ({month_note})")
    for ax in axes:
        mark_months(ax)
        style(ax)
    save(fig, "monthly")

    weekdays = tables["weekday"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(f"Recorded crime by offence weekday | CDMX {year}", fontsize=16)
    labels = [day[:3] for day in weekdays["day_name"]]
    axes[0].bar(labels, weekdays["incidents"], color="#287b8e")
    axes[0].set_ylabel("Investigation files")
    axes[0].set_title("Observed-window totals")
    axes[1].bar(labels, weekdays["incidents_per_day"], color="#ba4a45")
    axes[1].set_ylabel("Files per occurrence of weekday")
    axes[1].set_title("Calendar-adjusted average")
    for ax in axes:
        style(ax)
    save(fig, "weekday")

    bands = tables["time_band"]
    fig, ax = plt.subplots(figsize=(11, 5))
    fig.suptitle(f"Recorded crime by offence time band | CDMX {year}", fontsize=16)
    ax.barh(bands.index, bands["incidents"], color=["#287b8e"] * 4 + ["#a1a9b1"])
    for i, row in enumerate(bands.itertuples()):
        ax.text(row.incidents + bands["incidents"].max() * 0.02, i,
                f"{row.incidents:,} ({row.share_pct:.1f}%)", va="center", fontsize=10)
    ax.set_xlim(0, max(bands["incidents"].max() * 1.35, 1))
    ax.invert_yaxis()
    ax.set_xlabel("Investigation files (unknown hours retained separately)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.xaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    save(fig, "time_band")

    types = tables["crime_type"].head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(13, 9))
    fig.suptitle(f"Top 15 recorded crime types | CDMX {year}", fontsize=16)
    ax.barh(range(len(types)), types["incidents"], color=types["crime_category"].map(colors))
    ax.set_yticks(range(len(types)), [textwrap.fill(label, 46) for label in types["crime_type"]])
    for i, count in enumerate(types["incidents"]):
        ax.text(count + types["incidents"].max() * 0.015, i, f"{count:,}", va="center", fontsize=9)
    ax.set_xlim(0, types["incidents"].max() * 1.15)
    ax.set_xlabel(f"Investigation files | Top 15 cover {types['share_pct'].sum():.1f}% of the retained sample")
    ax.spines[["top", "right"]].set_visible(False)
    ax.xaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    ax.legend(handles=[Patch(color=color, label=label) for label, color in colors.items()],
              title="Analytical category", loc="lower right")
    save(fig, "top_types")

    heatmap = tables["weekday_time_band_per_day"]
    fig, ax = plt.subplots(figsize=(11, 6))
    fig.suptitle(f"Weekday and time band | CDMX {year}", fontsize=16)
    values = heatmap.to_numpy()
    mesh = ax.imshow(values, cmap="YlOrRd", aspect="auto", vmin=0)
    ax.set_xticks(range(5), ["Night\n00-05", "Morning\n06-11", "Afternoon\n12-17", "Evening\n18-23", "Unknown\nhour"])
    ax.set_yticks(range(7), weekdays["day_name"])
    for (row, column), value in np.ndenumerate(values):
        ax.text(column, row, f"{value:.1f}", ha="center", va="center",
                color="white" if value > values.max() * 0.55 else "#263238")
    fig.colorbar(mesh, ax=ax, label="Average files per occurrence of weekday")
    ax.set_xlabel("Offence time band (unknown hours retained)")
    save(fig, "weekday_time_band")

    fig, axes = plt.subplots(3, 1, figsize=(12, 11))
    fig.suptitle(f"Recorded crime by analytical category | CDMX {year}", fontsize=16)
    panels = [
        ("month_by_category", monthly["month_name"].tolist(), f"Offence month ({month_note})"),
        ("day_of_week_by_category", [day[:3] for day in weekdays["day_name"]], "Offence weekday"),
        ("time_band_by_category", TIME_BANDS, "Offence time band (unknown hours retained)"),
    ]
    for ax, (name, labels, xlabel) in zip(axes, panels):
        category_table = tables[name]
        positions = np.arange(len(labels))
        bottom = np.zeros(len(labels))
        for category in CRIME_CATEGORIES:
            values = category_table[category].to_numpy(dtype=float, na_value=np.nan)
            ax.bar(positions, values, bottom=bottom, color=colors[category], label=category, width=0.7)
            bottom += values
        if name == "month_by_category":
            mark_months(ax)
        ax.set_xticks(positions, labels)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Investigation files")
        style(ax)
    axes[0].legend(title="Analytical category", ncol=4, loc="upper right")
    save(fig, "temporal_patterns")
    return paths
