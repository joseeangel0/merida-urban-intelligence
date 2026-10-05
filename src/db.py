"""Database helpers shared by ETL and analysis code."""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.config import ROOT

load_dotenv(ROOT / ".env")


def get_engine() -> Engine:
    url = (
        f"postgresql+psycopg://{os.getenv('POSTGRES_USER', 'merida')}:{os.getenv('POSTGRES_PASSWORD', 'merida')}"
        f"@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5433')}"
        f"/{os.getenv('POSTGRES_DB', 'merida_dw')}"
    )
    return create_engine(url)


def run_sql_file(path: Path, engine: Engine | None = None) -> None:
    """Execute a whole .sql file in a single transaction."""
    engine = engine or get_engine()
    sql = Path(path).read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.exec_driver_sql(sql)
    print(f"[sql] executed {Path(path).name}")


def query_scalar(sql: str, engine: Engine | None = None):
    engine = engine or get_engine()
    with engine.connect() as conn:
        return conn.execute(text(sql)).scalar()
