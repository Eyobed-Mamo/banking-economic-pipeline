"""Run with python -m etl.pipeline. Each series commits atomically."""
import argparse
from datetime import date, timedelta
import logging
import sys
from uuid import uuid4
import psycopg
from .config import SERIES, Settings
from .fetch import FredClient
from .load import initialize, upsert_series, upsert_observations
from .transform import clean_observations

LOG = logging.getLogger(__name__)
LOCK_ID = 749210035


def choose_start(latest, last_full, today, settings, force_full=False):
    full = force_full or latest is None or last_full is None or (today - last_full).days >= settings.full_refresh_days
    start = settings.start_date if full else max(settings.start_date, latest - timedelta(days=settings.overlap_days))
    return start, full


def run(settings, *, full_refresh=False, today=None, client=None, series_list=SERIES):
    today = today or date.today()
    if settings.start_date > today:
        raise ValueError("START_DATE cannot be in the future")
    own_client = client is None
    client = client or FredClient(settings.api_key)
    run_id, failures = uuid4(), 0
    try:
        with psycopg.connect(settings.database_url, autocommit=True, connect_timeout=10) as conn:
            if own_client and conn.execute("SELECT to_regclass('demo_marker')").fetchone()[0]:
                raise ValueError("Live FRED loads are forbidden in a synthetic demo database")
            if not conn.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_ID,)).fetchone()[0]:
                raise RuntimeError("Another pipeline run is active; try again later")
            initialize(conn)
            # A prior process may have been killed before it could finalize its run.
            conn.execute("UPDATE etl_run_log SET status='interrupted', finished_at=now() WHERE status='running'")
            conn.execute("INSERT INTO etl_run_log (run_id,status) VALUES (%s,'running')", (run_id,))
            try:
                for series in series_list:
                    latest = conn.execute("SELECT max(observation_date) FROM fact_observations WHERE series_id=%s AND value IS NOT NULL", (series.id,)).fetchone()[0]
                    last_full = conn.execute("""SELECT max(finished_at)::date FROM etl_series_log
                        WHERE series_id=%s AND is_full_refresh AND status='success'""", (series.id,)).fetchone()[0]
                    start, full = choose_start(latest, last_full, today, settings, full_refresh)
                    try:
                        metadata = client.metadata(series.id)
                        frame = clean_observations(client.observations(series.id, start, today), series.id, start, today)
                        latest_valid = frame.loc[frame.value.notna(), "observation_date"].max()
                        stale = (today - latest_valid).days > series.stale_after_days
                        missing = int(frame.value.isna().sum())
                        with conn.transaction():
                            upsert_series(conn, series, metadata)
                            count = upsert_observations(conn, frame)
                            conn.execute("""INSERT INTO etl_series_log
                                (run_id,series_id,status,requested_start,is_full_refresh,rows_processed,missing_values,latest_observation,is_stale)
                                VALUES (%s,%s,'success',%s,%s,%s,%s,%s,%s)""",
                                (run_id, series.id, start, full, count, missing, latest_valid, stale))
                        LOG.info("%s: %s observations processed%s", series.id, count, " [STALE]" if stale else "")
                    except Exception as exc:
                        failures += 1
                        # Only record the class; arbitrary exception messages can contain credentials.
                        code = type(exc).__name__
                        conn.execute("""INSERT INTO etl_series_log
                            (run_id,series_id,status,requested_start,is_full_refresh,error_type)
                            VALUES (%s,%s,'failed',%s,%s,%s)""", (run_id, series.id, start, full, code))
                        LOG.error("%s failed (%s); remaining series will continue", series.id, code)
                status = "success" if not failures else "failed" if failures == len(series_list) else "partial"
                conn.execute("UPDATE etl_run_log SET status=%s, finished_at=now(), series_succeeded=%s, series_failed=%s WHERE run_id=%s",
                             (status, len(series_list)-failures, failures, run_id))
            except BaseException:
                conn.execute("UPDATE etl_run_log SET status='failed', finished_at=now() WHERE run_id=%s", (run_id,))
                raise
    finally:
        if own_client:
            client.close()
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-refresh", action="store_true", help="Re-fetch all observations since START_DATE")
    parser.add_argument("--init-db", action="store_true", help="Create/update tables and views without a FRED key")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        settings = Settings.from_env()
        if args.init_db:
            with psycopg.connect(settings.database_url, autocommit=True, connect_timeout=10) as conn:
                initialize(conn)
            LOG.info("Database schema and views ready")
            return 0
        return run(settings, full_refresh=args.full_refresh)
    except Exception as exc:
        LOG.error("Pipeline could not complete (%s). Check .env, database availability, and README troubleshooting.", type(exc).__name__)
        return 2


if __name__ == "__main__":
    sys.exit(main())
