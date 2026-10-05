"""Single entry point for the reproducible pipeline.

    python -m src.pipeline all          # everything, in order
    python -m src.pipeline <step> ...   # one or more steps

Steps (in order):
    download   original INEGI files -> data/raw/ (+ manifest.json)
    transform  raw -> clean -> spatial join -> data/processed/*.parquet
    schema     sql/01_schema.sql (drop + create stg/dw schemas)
    stage      data/processed/*.parquet -> stg.* tables
    load       sql/02_load.sql (stg.* -> dw dimensions and facts)
    views      sql/03_views.sql (KPI views)
    validate   sql/04_validation.sql (counts, keys, KPI checks)
"""
import importlib
import sys

from src.config import SQL_DIR

# Transform modules, in dependency order. Each exposes run() and writes one
# file in data/processed/ following the contract in docs/team/TEAM_PLAN.md.
TRANSFORM_MODULES = [
    "src.transform.geography",  # ageb.parquet      (Lorena)
    "src.transform.census",     # census_ageb.parquet (Julio)
    "src.transform.denue",      # business.parquet  (Ricardo)
    "src.transform.crime",      # crime.parquet     (Valeria)
]


def _run_module(name: str) -> None:
    try:
        module = importlib.import_module(name)
    except ModuleNotFoundError as e:
        if e.name == name:
            print(f"[pipeline] SKIP {name}: not implemented yet")
            return
        raise
    print(f"[pipeline] running {name}")
    module.run()


def _run_sql(filename: str) -> None:
    from src.db import run_sql_file

    path = SQL_DIR / filename
    if not path.exists():
        print(f"[pipeline] SKIP {filename}: not written yet")
        return
    run_sql_file(path)


def step_download():
    from src.extract.download_sources import main

    main()


def step_transform():
    for name in TRANSFORM_MODULES:
        _run_module(name)


STEPS = {
    "download": step_download,
    "transform": step_transform,
    "schema": lambda: _run_sql("01_schema.sql"),
    "stage": lambda: _run_module("src.load.load_staging"),
    "load": lambda: _run_sql("02_load.sql"),
    "views": lambda: _run_sql("03_views.sql"),
    "validate": lambda: _run_sql("04_validation.sql"),
}


def main(argv: list[str]) -> None:
    steps = list(STEPS) if argv in ([], ["all"]) else argv
    unknown = [s for s in steps if s not in STEPS]
    if unknown:
        sys.exit(f"Unknown step(s): {unknown}. Valid: {list(STEPS)} or 'all'")
    for s in steps:
        print(f"\n=== {s} ===")
        STEPS[s]()


if __name__ == "__main__":
    main(sys.argv[1:])
