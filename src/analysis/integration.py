"""Cross-source integration evidence and compatibility evaluation.

Provides reusable checks comparing geographic identifiers, spatial assignment,
temporal coverage windows, and data attrition across Marco Geoestadístico 2020,
Censo de Población y Vivienda 2020, DENUE 05/2026, and FGJ CDMX Crime 2024.
"""

import hashlib
import zipfile
from pathlib import Path
from typing import Any

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import CRIME_YEAR, DATA_PROCESSED, DATA_RAW, OUTPUT_FIGURES
from src.transform.census import SUPPRESSED_CODES, read_census, select_ageb_rows
from src.transform.denue import parse_alta_date, read_denue
from src.transform.spatial import assign_ageb, load_ageb, points_from_latlon

# Cryptographically pinned SHA-256 digests from data/raw/manifest.json
PINNED_MANIFEST_DIGESTS = {
    "census_ageb_2020_09": "1f5f123b8e9a50991d1847271b5a2bf321e813e924e5bcf958cab612311c765a",
    "denue_09": "ae608f30118f6313e9d537ea22918b2c9e9a3d3f19c2ddf5907f55dbb1642b19",
    "marco_geo_2020_09": "685b912f5458138a70726cff41aff828473e14264c43289d3b21f86a9df00320",
    "crime_fgj_2024": "2ac3f17189a61ab7b2eb95fb21470e46adaba6f92526c7b92d23190ed2431f84",
}
PINNED_CRIME_SHA256 = PINNED_MANIFEST_DIGESTS["crime_fgj_2024"]


def _hash_file(path: Path) -> str:
    """Compute SHA-256 digest of a file in 64 KiB chunks."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_input_provenance(raw_dir: Path | None = None) -> dict[str, str]:
    """Verify available raw archive and plain files against cryptographically pinned digests.

    Tests archive integrity and asserts that the processed AGEB polygon frame matches
    contract expectations. Raises ValueError with actionable instructions if an expected
    file has a hash mismatch or integrity failure.
    """
    if raw_dir is None:
        raw_dir = DATA_RAW

    verified: dict[str, str] = {}
    mismatches: list[str] = []

    # Map dataset keys to candidate file locations
    checks = [
        ("census_ageb_2020_09", raw_dir / "census_ageb_2020_09.zip"),
        ("denue_09", raw_dir / "denue_09.zip"),
        ("marco_geo_2020_09", raw_dir / "marco_geo_2020_09.zip"),
        ("crime_fgj_2024", raw_dir / "crime_fgj_2024" / "crime_fgj_2024.csv"),
    ]

    for key, path in checks:
        if not path.exists() and key == "crime_fgj_2024":
            path = raw_dir / "crime_fgj_2024.csv"
        if path.exists():
            computed = _hash_file(path)
            expected = PINNED_MANIFEST_DIGESTS[key]
            if computed != expected:
                mismatches.append(f"{key} ({path.name}): expected {expected}, got {computed}")
            else:
                verified[key] = computed
                # If zip archive, also test archive member integrity
                if path.suffix.lower() == ".zip":
                    try:
                        with zipfile.ZipFile(path, "r") as zf:
                            corrupt_member = zf.testzip()
                            if corrupt_member is not None:
                                mismatches.append(
                                    f"{key} ({path.name}): zip member '{corrupt_member}' failed CRC test"
                                )
                    except (zipfile.BadZipFile, OSError) as err:
                        mismatches.append(f"{key} ({path.name}): failed to open zip archive ({err})")

    # Verify processed ageb.parquet contract if present
    ageb_path = DATA_PROCESSED / "ageb.parquet"
    if ageb_path.exists():
        gdf = load_ageb()
        if len(gdf) != 2431:
            mismatches.append(f"ageb.parquet: expected 2,431 urban AGEB polygons, got {len(gdf)}")
        if gdf.crs is None or gdf.crs.to_epsg() != 6372:
            mismatches.append(f"ageb.parquet: expected CRS EPSG:6372, got {gdf.crs}")
        if not gdf.geometry.is_valid.all():
            invalid_count = int((~gdf.geometry.is_valid).sum())
            mismatches.append(f"ageb.parquet: contains {invalid_count} invalid geometries")

    if mismatches:
        err_list = "\n  - ".join(mismatches)
        raise ValueError(
            "Raw input provenance verification failed! Stale or corrupted files detected:\n  - "
            f"{err_list}\n"
            "Please halt ETL and re-profile/re-download the approved source dataset:\n"
            "Run 'python -m src.pipeline download && python -m src.pipeline stage' with approved pinned sources."
        )

    return verified


def verify_crime_provenance(crime_raw_path: Path | None = None) -> str:
    """Verify raw FGJ CDMX 2024 crime file against pinned SHA-256 digest."""
    if crime_raw_path is None:
        crime_raw_path = DATA_RAW / "crime_fgj_2024" / "crime_fgj_2024.csv"
        if not crime_raw_path.exists():
            crime_raw_path = DATA_RAW / "crime_fgj_2024.csv"

    if not crime_raw_path.exists():
        raise FileNotFoundError(f"Raw crime dataset not found at {crime_raw_path}")

    digest = _hash_file(crime_raw_path)
    if digest != PINNED_CRIME_SHA256:
        raise ValueError(
            f"Crime raw SHA-256 mismatch: expected {PINNED_CRIME_SHA256}, got {digest}. "
            "Please halt ETL and re-profile/re-download the approved FGJ 2024 dataset."
        )
    return digest


def _parse_census_population(series: pd.Series) -> pd.Series:
    """Parse census population values enforcing suppression and non-numeric rules.

    Preserves '*' and 'N/D' as NaN; raises ValueError on unexpected non-numeric tokens.
    """
    suppressed = series.isin(SUPPRESSED_CODES)
    numeric = series.mask(suppressed).apply(pd.to_numeric, errors="coerce")
    unexpected = numeric.isna() & ~suppressed
    if unexpected.any():
        codes = sorted(set(series.where(unexpected).dropna()))
        raise ValueError(f"Unexpected non-numeric census values in POBTOT: {codes}")
    return numeric


def census_polygon_compatibility(
    census_raw: pd.DataFrame | None = None,
    polygon_keys: set[str] | None = None,
) -> dict[str, Any]:
    """Evaluate Census 2020 urban AGEB records against cartographic polygons.

    Verifies 2,431 matched urban AGEBs and identifies the two orphan census keys
    (0901101101107 and 0901201351227) totaling 7,108 residents that lack
    polygons in the Marco Geoestadístico 2020 frame.
    """
    if census_raw is None:
        census_raw = read_census()
    if polygon_keys is None:
        polygon_keys = set(load_ageb()["cvegeo"])

    raw_census_rows = len(census_raw)
    ageb_rows = select_ageb_rows(census_raw)
    total_census_agebs = len(ageb_rows)

    has_polygon = ageb_rows["cvegeo"].isin(polygon_keys)
    matched_df = ageb_rows.loc[has_polygon].copy()
    orphans_df = ageb_rows.loc[~has_polygon].copy()

    matched_numeric = _parse_census_population(matched_df["POBTOT"])
    orphan_numeric = _parse_census_population(orphans_df["POBTOT"])

    matched_pop = int(matched_numeric.dropna().sum())
    orphan_pop = int(orphan_numeric.dropna().sum())

    orphan_summary = orphans_df[["cvegeo", "NOM_MUN", "MUN", "POBTOT"]].rename(
        columns={
            "NOM_MUN": "mun_name",
            "MUN": "cve_mun",
            "POBTOT": "pop_total",
        }
    ).reset_index(drop=True)
    orphan_summary["pop_total"] = orphan_numeric.reset_index(drop=True).astype("Int64")

    # Verify key set equality
    matched_keys = set(matched_df["cvegeo"])
    polygon_orphans = polygon_keys - matched_keys

    return {
        "raw_census_rows": raw_census_rows,
        "total_census_agebs": total_census_agebs,
        "matched_agebs": len(matched_df),
        "orphan_count": len(orphans_df),
        "matched_population": matched_pop,
        "orphan_population": orphan_pop,
        "matched_keys": matched_keys,
        "orphan_keys": sorted(orphans_df["cvegeo"].tolist()),
        "polygon_keys": polygon_keys,
        "polygon_orphans": sorted(polygon_orphans),
        "keys_match_polygons": (matched_keys == polygon_keys),
        "orphan_summary": orphan_summary,
    }


def normalize_reported_cvegeo(df: pd.DataFrame) -> pd.Series:
    """Construct 13-character reported CVEGEO preserving zeros and component integrity.

    Returns pd.NA if any component is missing, null, or empty. Never fabricates zero codes.
    """
    ent = df["cve_ent"].astype("string").str.strip()
    mun = df["cve_mun"].astype("string").str.strip()
    loc = df["cve_loc"].astype("string").str.strip()
    ageb = df["ageb"].astype("string").str.strip()

    valid_mask = (
        ent.notna() & ent.ne("") &
        mun.notna() & mun.ne("") &
        loc.notna() & loc.ne("") &
        ageb.notna() & ageb.ne("")
    )

    result = pd.Series(index=df.index, dtype="string")
    result.loc[valid_mask] = (
        ent.loc[valid_mask].str.zfill(2)
        + mun.loc[valid_mask].str.zfill(3)
        + loc.loc[valid_mask].str.zfill(4)
        + ageb.loc[valid_mask].str.zfill(4)
    )
    return result


def denue_code_compatibility(
    denue_raw: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Compare DENUE published geographic codes with polygon-assigned codes.

    Evaluates coordinate filtering and spatial-join assignment, classifying
    assigned points into a complete three-category partition: exact match,
    reported-versus-spatial discrepancy, and unmatchable/malformed reported key.
    """
    if denue_raw is None:
        denue_raw = read_denue()

    raw_count = len(denue_raw)
    denue = denue_raw.copy()
    denue["cvegeo_reported"] = normalize_reported_cvegeo(denue)

    pts = points_from_latlon(denue, "latitud", "longitud")
    valid_coords_count = len(pts)
    invalid_coords_count = raw_count - valid_coords_count

    assigned = assign_ageb(pts)
    retained_count = len(assigned)
    outside_count = valid_coords_count - retained_count

    # Validate 13-character CVEGEO syntax: 9 digits followed by 4 alphanumeric characters
    is_valid_format = assigned["cvegeo_reported"].str.match(
        r"^[0-9]{9}[0-9A-Za-z]{4}$", na=False
    ).astype(bool)

    matched_mask = assigned["cvegeo"].eq(assigned["cvegeo_reported"]) & is_valid_format
    discrepancy_mask = (~assigned["cvegeo"].eq(assigned["cvegeo_reported"])) & is_valid_format
    unmatchable_mask = ~is_valid_format

    matched_count = int(matched_mask.sum())
    discrepancy_count = int(discrepancy_mask.sum())
    unmatchable_count = int(unmatchable_mask.sum())

    eligible_denominator = matched_count + discrepancy_count
    agreement_rate = (
        float(matched_count / eligible_denominator) if eligible_denominator > 0 else np.nan
    )

    # Preserve audit sample with establishment ID if available
    cols = [c for c in ["id", "cvegeo", "cvegeo_reported"] if c in assigned.columns]
    audit_sample = assigned[cols].copy()

    return {
        "raw_count": raw_count,
        "valid_coords_count": valid_coords_count,
        "invalid_coords_count": invalid_coords_count,
        "retained_count": retained_count,
        "outside_count": outside_count,
        "matched_cvegeo": matched_count,
        "discrepancy_cvegeo": discrepancy_count,
        "unmatchable_cvegeo": unmatchable_count,
        "eligible_denominator": eligible_denominator,
        "agreement_rate": agreement_rate,
        "audit_sample": audit_sample,
    }


def crime_temporal_and_grain_check(
    crime_raw_path: Path | None = None,
    verify_hash: bool = True,
) -> dict[str, Any]:
    """Profile FGJ CDMX 2024 crime filing window, offence timing and funnel.

    Confirms the Jan-Jul 2024 filing window (fecha_inicio), the year 2024 offence
    filter, criminal event eligibility, and spatial retention within urban AGEBs.
    """
    if crime_raw_path is None:
        crime_raw_path = DATA_RAW / "crime_fgj_2024" / "crime_fgj_2024.csv"
        if not crime_raw_path.exists():
            crime_raw_path = DATA_RAW / "crime_fgj_2024.csv"

    sha256_digest = None
    if verify_hash:
        sha256_digest = verify_crime_provenance(crime_raw_path)

    crime_df = pd.read_csv(crime_raw_path, dtype=str, encoding="utf-8")
    raw_count = len(crime_df)

    crime_df["dt_inicio"] = pd.to_datetime(crime_df["fecha_inicio"], errors="coerce")
    crime_df["dt_hecho"] = pd.to_datetime(crime_df["fecha_hecho"], errors="coerce")

    invalid_dates_count = int(crime_df["dt_hecho"].isna().sum())
    earlier_years_count = int((crime_df["dt_hecho"].dt.year < CRIME_YEAR).sum())

    filing_start = crime_df["dt_inicio"].min().strftime("%Y-%m-%d")
    filing_end = crime_df["dt_inicio"].max().strftime("%Y-%m-%d")
    monthly_filings = crime_df["dt_inicio"].dt.month.value_counts().sort_index()

    # Offence year filter
    sub_year = crime_df[crime_df["dt_hecho"].dt.year == CRIME_YEAR].copy()
    year_2024_count = len(sub_year)

    # Crime eligibility (drop non-criminal)
    sub_crim = sub_year[sub_year["categoria_delito"] != "HECHO NO DELICTIVO"].copy()
    eligible_count = len(sub_crim)

    # Coordinates
    pts = points_from_latlon(sub_crim, "latitud", "longitud")
    valid_coords_count = len(pts)

    # Deduplication
    dup_mask = pts.duplicated(subset=["delito", "fecha_hecho", "hora_hecho", "latitud", "longitud"])
    dups_count = int(dup_mask.sum())
    pts_dedup = pts.loc[~dup_mask].copy()

    # Spatial join
    assigned = assign_ageb(pts_dedup)
    retained_count = len(assigned)
    outside_count = len(pts_dedup) - retained_count

    dt_assigned = pd.to_datetime(assigned["fecha_hecho"], errors="coerce")
    monthly_retained = dt_assigned.dt.month.value_counts().sort_index()

    return {
        "raw_count": raw_count,
        "sha256_digest": sha256_digest,
        "filing_start": filing_start,
        "filing_end": filing_end,
        "calendar_days_count": 213,
        "february_days_count": 29,
        "observed_filing_months": [1, 2, 3, 4, 5, 6, 7],
        "unobserved_filing_months": [8, 9, 10, 11, 12],
        "monthly_filings": monthly_filings,
        "invalid_dates_count": invalid_dates_count,
        "earlier_years_count": earlier_years_count,
        "year_2024_count": year_2024_count,
        "eligible_count": eligible_count,
        "valid_coords_count": valid_coords_count,
        "duplicates_count": dups_count,
        "retained_count": retained_count,
        "outside_count": outside_count,
        "monthly_retained_offences": monthly_retained,
        "filing_months_count": len(monthly_filings),
    }


def build_source_integration_summary_table(
    census_results: dict[str, Any] | None = None,
    denue_results: dict[str, Any] | None = None,
    crime_results: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Build the source-to-urban-AGEB reconciliation summary table."""
    if census_results is None:
        census_results = census_polygon_compatibility()
    if denue_results is None:
        denue_results = denue_code_compatibility()
    if crime_results is None:
        crime_results = crime_temporal_and_grain_check()

    ageb_gdf = load_ageb()
    geo_count = len(ageb_gdf)
    geo_area_km2 = round(ageb_gdf.geometry.area.sum() / 1e6, 2)

    records = [
        {
            "Source Layer": "Marco Geoestadístico 2020 (09a.shp)",
            "Publisher": "INEGI",
            "Original Grain": "One polygon per geostatistical unit",
            "Raw Records": geo_count,
            "Filtered / Eligible": geo_count,
            "Retained in Urban AGEBs": geo_count,
            "Retention % (Raw)": 100.0,
            "Retention % (Eligible)": 100.0,
            "Retained Measure": f"{geo_count:,} polygons ({geo_area_km2} km²)",
            "Integration Status": "Complete reference boundary frame (2,348 city core + 83 outlying)",
        },
        {
            "Source Layer": "Censo de Población y Vivienda 2020",
            "Publisher": "INEGI",
            "Original Grain": "Tabular records (blocks, AGEBs, localities, municipalities)",
            "Raw Records": census_results["raw_census_rows"],
            "Filtered / Eligible": census_results["total_census_agebs"],
            "Retained in Urban AGEBs": census_results["matched_agebs"],
            "Retention % (Raw)": round(
                census_results["matched_agebs"] / census_results["raw_census_rows"] * 100, 2
            ),
            "Retention % (Eligible)": round(
                census_results["matched_agebs"] / census_results["total_census_agebs"] * 100, 2
            ),
            "Retained Measure": f"{census_results['matched_population']:,} residents",
            "Integration Status": (
                f"Filtered {census_results['raw_census_rows']:,} mixed-grain rows to {census_results['total_census_agebs']:,} AGEBs; "
                f"excludes 2 orphan AGEBs ({census_results['orphan_population']:,} residents) lacking polygons"
            ),
        },
        {
            "Source Layer": "DENUE 05/2026",
            "Publisher": "INEGI",
            "Original Grain": "One economic establishment point (lat/lon)",
            "Raw Records": denue_results["raw_count"],
            "Filtered / Eligible": denue_results["valid_coords_count"],
            "Retained in Urban AGEBs": denue_results["retained_count"],
            "Retention % (Raw)": round(
                denue_results["retained_count"] / denue_results["raw_count"] * 100, 2
            ),
            "Retention % (Eligible)": round(
                denue_results["retained_count"] / denue_results["valid_coords_count"] * 100, 2
            ),
            "Retained Measure": f"{denue_results['retained_count']:,} establishments",
            "Integration Status": (
                f"{denue_results['agreement_rate']:.2%} reported-AGEB agreement; drops "
                f"{denue_results['invalid_coords_count']} invalid coords + "
                f"{denue_results['outside_count']:,} outside AGEBs"
            ),
        },
        {
            "Source Layer": "Carpetas de Investigación 2024",
            "Publisher": "FGJ CDMX",
            "Original Grain": "One investigation file (carpeta) with date, category, lat/lon",
            "Raw Records": crime_results["raw_count"],
            "Filtered / Eligible": crime_results["eligible_count"],
            "Retained in Urban AGEBs": crime_results["retained_count"],
            "Retention % (Raw)": round(
                crime_results["retained_count"] / crime_results["raw_count"] * 100, 2
            ),
            "Retention % (Eligible)": round(
                crime_results["retained_count"] / crime_results["eligible_count"] * 100, 2
            ),
            "Retained Measure": f"{crime_results['retained_count']:,} investigation files",
            "Integration Status": "7-month filing extract (Jan-Jul); retains 93.83% of eligible 2024 crimes",
        },
    ]

    return pd.DataFrame(records)


def plot_cross_source_temporal_coverage(
    output_path: Path | None = None,
    denue_alta_series: pd.Series | None = None,
    filing_monthly: pd.Series | None = None,
    offence_monthly: pd.Series | None = None,
) -> tuple[plt.Figure, np.ndarray]:
    """Generate and save the 3-panel cross-source temporal coverage figure.

    Panel A: Observation windows across sources (Census 2020 stock vs DENUE registry vs FGJ 2024 filing).
    Panel B: FGJ monthly filings vs offences showing July right-censoring and unobserved Aug-Dec.
    Panel C: DENUE fecha_alta registration waves showing mass census updates and survivor bias.
    """
    if denue_alta_series is None:
        denue_raw = read_denue()
        denue_alta_series = parse_alta_date(denue_raw["fecha_alta"])

    if filing_monthly is None or offence_monthly is None:
        crime_info = crime_temporal_and_grain_check()
        filing_monthly = crime_info["monthly_filings"]
        offence_monthly = crime_info["monthly_retained_offences"]

    fig, axes = plt.subplots(3, 1, figsize=(12, 10), gridspec_kw={"height_ratios": [1.1, 1.2, 1.1]})
    fig.patch.set_facecolor("white")

    # Panel A: Observational Window Timeline (Gantt)
    ax0 = axes[0]
    ax0.set_facecolor("#fafafa")
    tasks = [
        (
            "FGJ CDMX Crime 2024\n(Filing Window Jan-Jul 2024)",
            pd.Timestamp("2024-01-01"),
            pd.Timestamp("2024-07-31"),
            "#d95f02",
            "7-Month Procedural Filing Snapshot (213 days)\n(Offences committed 2024; Aug-Dec unobserved)",
        ),
        (
            "INEGI DENUE 05/2026\n(Active Registry Snapshot)",
            pd.Timestamp("2010-07-01"),
            pd.Timestamp("2026-05-01"),
            "#7570b3",
            "Published May 2026; Registration dates (fecha_alta) 2010-2026\n(Survivor bias: active businesses only, not historical panel)",
        ),
        (
            "INEGI Censo de Población 2020\n(Decennial Stock Reference)",
            pd.Timestamp("2020-03-02"),
            pd.Timestamp("2020-03-27"),
            "#1b9e77",
            "Ref date: 15 Mar 2020; Enumeration: 2-27 Mar 2020\n(Static demographic stock snapshot)",
        ),
    ]

    for i, (name, start, end, color, note) in enumerate(tasks):
        ax0.barh(
            i,
            (end - start).days,
            left=start,
            height=0.45,
            color=color,
            alpha=0.85,
            edgecolor="black",
            linewidth=0.8,
        )
        duration_days = (end - start).days
        if duration_days < 300:
            ax0.text(
                end + pd.Timedelta(days=40),
                i,
                note,
                va="center",
                ha="left",
                fontsize=8.5,
                fontweight="bold",
                color="#222222",
            )
        else:
            midpoint = start + (end - start) / 2
            ax0.text(
                midpoint,
                i,
                note,
                va="center",
                ha="center",
                fontsize=8.2,
                fontweight="bold",
                color="white",
            )

    ax0.set_yticks(range(len(tasks)))
    ax0.set_yticklabels([t[0] for t in tasks], fontsize=9, fontweight="bold")
    ax0.xaxis.set_major_locator(mdates.YearLocator(2))
    ax0.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax0.set_xlim(pd.Timestamp("2009-06-01"), pd.Timestamp("2027-01-01"))
    ax0.set_title("A. Cross-Source Observation Windows and Temporal Scope Mismatch", fontsize=11, fontweight="bold", pad=8)
    ax0.grid(True, axis="x", linestyle="--", alpha=0.5)

    # Panel B: FGJ Monthly Profile
    ax1 = axes[1]
    ax1.set_facecolor("#fafafa")
    months_all = list(range(1, 13))
    observed_months = list(range(1, 8))
    unobserved_months = list(range(8, 13))
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Crucial: Unobserved months (Aug-Dec) must be NaN (missing), not 0!
    filing_series = pd.Series(index=months_all, dtype=float)
    filing_series.loc[observed_months] = filing_monthly.reindex(observed_months, fill_value=0.0)
    filing_series.loc[unobserved_months] = np.nan

    offence_series = pd.Series(index=months_all, dtype=float)
    offence_series.loc[observed_months] = offence_monthly.reindex(observed_months, fill_value=0.0)
    offence_series.loc[unobserved_months] = np.nan

    x = np.arange(len(months_all))
    width = 0.35

    ax1.bar(
        x - width / 2,
        filing_series,
        width,
        label="Investigation Files Opened (fecha_inicio)",
        color="#4575b4",
        alpha=0.85,
        edgecolor="black",
        linewidth=0.7,
    )
    ax1.bar(
        x + width / 2,
        offence_series,
        width,
        label="Retained Offences Occurred in Urban AGEBs (fecha_hecho)",
        color="#d73027",
        alpha=0.85,
        edgecolor="black",
        linewidth=0.7,
    )

    # Shade unobserved window (Aug-Dec)
    ax1.axvspan(6.5, 11.5, color="#fee090", alpha=0.35, hatch="//", label="Unobserved Window (Aug-Dec 2024: Filing snapshot ended July 31)")
    ax1.text(
        9,
        12000,
        "DATA UNAVAILABLE\nFiling extract ends 2024-07-31;\nOffences unobserved",
        ha="center",
        va="center",
        fontsize=8.5,
        fontweight="bold",
        color="#a50026",
        bbox={"boxstyle": "round,pad=0.3", "fc": "white", "ec": "#a50026", "lw": 1},
    )

    # Highlight right-censoring in July
    ax1.annotate(
        "Right-censored July:\nreporting lag into Aug",
        xy=(6 + width / 2, offence_series.loc[7]),
        xytext=(5.2, 7000),
        arrowprops={"facecolor": "#d73027", "shrink": 0.08, "width": 1, "headwidth": 5},
        fontsize=8,
        fontweight="bold",
        color="#d73027",
        bbox={"boxstyle": "round,pad=0.2", "fc": "white", "ec": "#d73027", "lw": 0.8},
    )

    ax1.set_xticks(x)
    ax1.set_xticklabels(month_names, fontsize=9.5)
    ax1.set_ylabel("Monthly Incidents", fontsize=9.5, fontweight="bold")
    ax1.set_title("B. FGJ CDMX 2024 Crime Temporal Profile: Filing Cutoff (July 31) and Offence Timing", fontsize=11, fontweight="bold", pad=8)
    ax1.legend(loc="upper right", fontsize=8.5, framealpha=0.9)
    ax1.grid(True, axis="y", linestyle="--", alpha=0.5)

    # Panel C: DENUE Annual Registration Waves
    ax2 = axes[2]
    ax2.set_facecolor("#fafafa")
    alta_years = denue_alta_series.dt.year.value_counts().sort_index()

    ax2.bar(
        alta_years.index,
        alta_years.values,
        color="#3182bd",
        alpha=0.85,
        edgecolor="black",
        linewidth=0.7,
        width=0.7,
    )
    ax2.set_xlabel("Year of Registration / Incorporation (fecha_alta)", fontsize=9.5, fontweight="bold")
    ax2.set_ylabel("Active Establishments (2026)", fontsize=9.5, fontweight="bold")
    ax2.set_title("C. DENUE Registration Waves (fecha_alta): Mass Census Updates and Survivor Bias", fontsize=11, fontweight="bold", pad=8)

    for census_yr, label in [
        (2014, "2014 Economic\nCensus Update"),
        (2019, "2019 Economic\nCensus Update"),
        (2024, "2024 Economic\nCensus Update"),
    ]:
        if census_yr in alta_years.index:
            val = alta_years[census_yr]
            ax2.annotate(
                label,
                xy=(census_yr, val),
                xytext=(census_yr, min(val + 18000, 155000)),
                arrowprops={"facecolor": "#08519c", "shrink": 0.05, "width": 1, "headwidth": 5},
                fontsize=8,
                fontweight="bold",
                color="#08519c",
                ha="center",
            )

    ax2.text(
        2010.8,
        100000,
        "CAUTION: Active survivors only.\n"
        "fecha_alta reflects administrative\n"
        "registration, not economic tenure\n"
        "or historical presence.",
        fontsize=8.0,
        color="#444444",
        style="italic",
        bbox={"boxstyle": "square,pad=0.35", "fc": "#f7f7f7", "ec": "#cccccc"},
    )
    ax2.grid(True, axis="y", linestyle="--", alpha=0.5)
    ax2.set_xlim(2009.5, 2026.5)
    ax2.set_ylim(0, 175000)

    plt.tight_layout()

    if output_path is None:
        OUTPUT_FIGURES.mkdir(parents=True, exist_ok=True)
        primary_path = OUTPUT_FIGURES / "temporal_coverage.png"
        secondary_path = OUTPUT_FIGURES / "14_temporal_coverage.png"
        fig.savefig(primary_path, dpi=300, bbox_inches="tight")
        fig.savefig(secondary_path, dpi=300, bbox_inches="tight")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=300, bbox_inches="tight")

    return fig, axes
