"""Deterministic SYNTHETIC observations for a separate demo database; no API key."""
import argparse
from datetime import date
import math
import psycopg
from psycopg.conninfo import conninfo_to_dict
from .config import SERIES, Settings
from .pipeline import run


class DemoClient:
    def metadata(self, series_id):
        return {}

    def observations(self, series_id, start, end):
        import pandas as pd
        frequency = next(s.frequency for s in SERIES if s.id == series_id)
        rule = {"Monthly":"MS", "Quarterly":"QS", "Weekly":"W-THU", "Daily":"B"}[frequency]
        base = {"FEDFUNDS":3.5,"DGS2":3.8,"DGS10":4.1,"MORTGAGE30US":6.4,
                "DRCCLACBS":2.6,"CPIAUCSL":240,"UNRATE":4.8}[series_id]
        rows = []
        for ts in pd.date_range(max(start,date(2015,1,1)), min(end,date(2025,12,31)),freq=rule):
            t = (ts.date()-date(2015,1,1)).days/365.25
            value = base*(1.025**t) if series_id=="CPIAUCSL" else base+0.7*math.sin(t/1.8)+0.2*math.cos(t*3)
            if series_id=="DGS2":
                value += 0.55*math.sin(t)
            rows.append({"date":ts.date().isoformat(),"value":str(round(value,4))})
        return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    settings = Settings.from_env()
    dbname = conninfo_to_dict(settings.database_url).get("dbname", "")
    if not dbname.endswith("_demo"):
        raise SystemExit("Demo requires a separate database whose name ends in _demo. See README.")
    with psycopg.connect(settings.database_url, autocommit=True) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS demo_marker (label text PRIMARY KEY)")
        conn.execute("INSERT INTO demo_marker VALUES ('SYNTHETIC DEMO - NOT REAL ECONOMIC DATA') ON CONFLICT DO NOTHING")
    code = run(settings, full_refresh=True, today=date(2025,12,31), client=DemoClient())
    print("SYNTHETIC demo loaded (2015-2025). This database must never be used to claim real economic findings.")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
