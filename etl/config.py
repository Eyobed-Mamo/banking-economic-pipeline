from dataclasses import dataclass
from datetime import date
import os
from pathlib import Path

from dotenv import load_dotenv
from psycopg.conninfo import make_conninfo

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Series:
    id: str
    title: str
    units: str
    frequency: str
    category: str
    stale_after_days: int


SERIES = (
    Series("FEDFUNDS", "Federal funds effective rate", "Percent", "Monthly", "Policy", 75),
    Series("DGS2", "2-year Treasury yield", "Percent", "Daily", "Treasuries", 10),
    Series("DGS10", "10-year Treasury yield", "Percent", "Daily", "Treasuries", 10),
    Series("MORTGAGE30US", "30-year fixed mortgage rate", "Percent", "Weekly", "Lending", 21),
    Series("DRCCLACBS", "Credit card loan delinquency rate", "Percent", "Quarterly", "Credit", 200),
    Series("CPIAUCSL", "Consumer price index (seasonally adjusted)", "Index 1982-1984=100", "Monthly", "Inflation", 75),
    Series("UNRATE", "Unemployment rate", "Percent", "Monthly", "Labor", 75),
)


@dataclass(frozen=True)
class Settings:
    database_url: str
    api_key: str
    start_date: date = date(2000, 1, 1)
    overlap_days: int = 90
    full_refresh_days: int = 30

    @classmethod
    def from_env(cls):
        load_dotenv(ROOT / ".env")
        # libpq fields let Docker accept passwords containing URL-special characters.
        dsn = os.getenv("DATABASE_URL", "")
        if os.getenv("PGHOST"):
            dsn = make_conninfo(host=os.environ["PGHOST"], port=os.getenv("PGPORT", "5432"),
                                dbname=os.getenv("PGDATABASE", "fred_pipeline"),
                                user=os.getenv("PGUSER", "fred"), password=os.getenv("PGPASSWORD", ""))
        if not dsn:
            raise ValueError("Set DATABASE_URL in .env; see README.md")
        overlap = int(os.getenv("OVERLAP_DAYS", "90"))
        full = int(os.getenv("FULL_REFRESH_DAYS", "30"))
        if overlap < 1 or full < 1:
            raise ValueError("OVERLAP_DAYS and FULL_REFRESH_DAYS must be positive")
        return cls(dsn, os.getenv("FRED_API_KEY", ""), date.fromisoformat(os.getenv("START_DATE", "2000-01-01")), overlap, full)
