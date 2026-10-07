"""Load processed Parquet files and source metadata into the staging schema."""
import json
import re

import geopandas as gpd
import pandas as pd
import pyarrow.parquet as parquet

from src.config import DATA_PROCESSED, DATA_RAW, SCHEMA_STAGING, SOURCES
from src.db import get_engine


def _load_processed_file(path, engine) -> None:
    """Write one Parquet file to a staging table, preserving GeoParquet geometry."""
    table_name = path.stem
    if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", table_name):
        raise ValueError(f"Unsafe staging table name derived from {path.name!r}")

    metadata = parquet.read_metadata(path).metadata or {}
    if b"geo" in metadata:
        frame = gpd.read_parquet(path)
        if frame.crs is None:
            raise ValueError(f"GeoParquet file has no CRS: {path}")
        frame.to_postgis(
            table_name,
            engine,
            schema=SCHEMA_STAGING,
            if_exists="replace",
            index=False,
        )
    else:
        pd.read_parquet(path).to_sql(
            table_name,
            engine,
            schema=SCHEMA_STAGING,
            if_exists="replace",
            index=False,
        )
    print(f"[stage] wrote {path.name} to {SCHEMA_STAGING}.{table_name}")


def _load_sources(engine) -> None:
    manifest_path = DATA_RAW / "manifest.json"
    if manifest_path.exists():
        try:
            manifest_text = manifest_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            manifest_text = manifest_path.read_text(encoding="cp1252")
        manifest = json.loads(manifest_text)
    else:
        manifest = {}
    rows = []
    for source_code, source in SOURCES.items():
        entry = manifest.get(source_code, {})
        rows.append(
            {
                "source_code": source_code,
                "source_name": source["name"],
                "publisher": source["publisher"],
                "url": source.get("url"),
                "version_label": entry.get("version_label", source.get("version_label")),
                "original_grain": source["original_grain"],
                "sha256": entry.get("sha256"),
            }
        )

    pd.DataFrame(rows).to_sql(
        "source",
        engine,
        schema=SCHEMA_STAGING,
        if_exists="replace",
        index=False,
    )
    print(f"[stage] wrote {len(rows)} sources to {SCHEMA_STAGING}.source")


def run() -> None:
    """Replace staging tables from available processed files and source metadata."""
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    engine = get_engine()
    try:
        for path in sorted(DATA_PROCESSED.glob("*.parquet")):
            _load_processed_file(path, engine)
        _load_sources(engine)
    finally:
        engine.dispose()
