from dataclasses import asdict
import math
from .config import ROOT


def initialize(conn):
    with conn.transaction():
        conn.execute((ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))
        conn.execute((ROOT / "sql" / "views.sql").read_text(encoding="utf-8"))


def upsert_series(conn, series, metadata):
    values = asdict(series)
    for name in ("title", "units", "frequency"):
        values[name] = metadata.get(name, values[name])
    conn.execute("""
        INSERT INTO dim_series (series_id, title, units, frequency, category, stale_after_days, source_url)
        VALUES (%(id)s, %(title)s, %(units)s, %(frequency)s, %(category)s, %(stale_after_days)s,
                'https://fred.stlouisfed.org/series/' || %(id)s)
        ON CONFLICT (series_id) DO UPDATE SET title=EXCLUDED.title, units=EXCLUDED.units,
          frequency=EXCLUDED.frequency, category=EXCLUDED.category, stale_after_days=EXCLUDED.stale_after_days,
          updated_at=now()
    """, values)


def upsert_observations(conn, frame):
    rows = [(row.series_id, row.observation_date, None if math.isnan(row.value) else row.value)
            for row in frame.itertuples(index=False)]
    with conn.cursor() as cur:
        cur.executemany("""
            INSERT INTO fact_observations (series_id, observation_date, value) VALUES (%s,%s,%s)
            ON CONFLICT (series_id, observation_date) DO UPDATE SET value=EXCLUDED.value,
              updated_at=now()
            WHERE fact_observations.value IS DISTINCT FROM EXCLUDED.value
        """, rows)
    return len(rows)
