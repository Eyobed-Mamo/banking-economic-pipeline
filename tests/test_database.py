"""Real PostgreSQL tests in a unique schema, never drop existing user tables."""
from datetime import date
import os
from uuid import uuid4
import psycopg
from psycopg import sql
import pytest
from etl.config import SERIES, Settings
from etl.load import initialize, upsert_series, upsert_observations
from etl.transform import clean_observations
from etl.pipeline import run

pytestmark = pytest.mark.integration


@pytest.fixture
def db():
    dsn = os.getenv("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("Set TEST_DATABASE_URL to run real PostgreSQL tests")
    schema = "test_" + uuid4().hex
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        initialize(conn)
        for s in SERIES:
            upsert_series(conn,s,{})
        isolated = psycopg.conninfo.make_conninfo(dsn, options=f"-c search_path={schema}")
        yield conn, isolated
        conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def put(conn, series, rows):
    frame = clean_observations([{"date":d,"value":v} for d,v in rows],series,date(2000,1,1),date(2030,1,1))
    upsert_observations(conn,frame)


def test_idempotency_and_revisions(db):
    conn,_ = db
    put(conn,"DGS10",[("2024-01-01","4.0")])
    put(conn,"DGS10",[("2024-01-01","4.0")])
    assert conn.execute("SELECT count(*) FROM fact_observations").fetchone()[0] == 1
    put(conn,"DGS10",[("2024-01-01","4.3")])
    assert conn.execute("SELECT value FROM fact_observations").fetchone()[0] == 4.3
    put(conn,"DGS10",[("2024-01-01","."),("2024-01-02","4.2")])
    assert conn.execute("SELECT value FROM fact_observations WHERE observation_date='2024-01-01'").fetchone()[0] is None


def test_cpi_calendar_join_handles_missing_months(db):
    conn,_ = db
    put(conn,"CPIAUCSL",[("2023-01-01","100"),("2024-01-01","110"),("2024-03-01","120")])
    rows = conn.execute("SELECT month,inflation_yoy_pct FROM vw_cpi_yoy ORDER BY month").fetchall()
    assert rows[1][1] == pytest.approx(10)
    assert rows[2][1] is None


def test_yield_curve_matching_and_basis_points(db):
    conn,_ = db
    put(conn,"DGS10",[("2024-01-01","4.0"),("2024-01-02","4.1")])
    put(conn,"DGS2",[("2024-01-01","4.5"),("2024-01-02",".")])
    rows = conn.execute("SELECT spread_bps,is_inverted FROM vw_yield_curve").fetchall()
    assert rows == [(-50.0, True)]


def test_quarterly_data_not_misrepresented_as_monthly(db):
    conn,_ = db
    put(conn,"DRCCLACBS",[("2024-01-01","3.2")])
    put(conn,"FEDFUNDS",[("2024-01-01","5"),("2024-02-01","4"),("2024-03-01","3")])
    assert conn.execute("SELECT count(*) FROM vw_monthly_indicators WHERE series_id='DRCCLACBS'").fetchone()[0] == 0
    assert conn.execute("SELECT fed_funds_pct FROM vw_credit_quarterly").fetchone()[0] == 4


def test_pipeline_failure_isolation_and_run_status(db):
    conn,dsn = db
    class Fake:
        def metadata(self,s): return {}
        def observations(self,s,start,end):
            if s == "DGS2": raise RuntimeError("sensitive text should not appear")
            return [{"date":"2024-01-01","value":"4.0"}]
    settings = Settings(dsn,"not-used")
    code = run(settings, today=date(2024,2,1),client=Fake(),series_list=SERIES[:3])
    assert code == 1
    assert conn.execute("SELECT status,series_succeeded,series_failed FROM etl_run_log").fetchone() == ("partial",2,1)
    assert conn.execute("SELECT error_type FROM etl_series_log WHERE status='failed'").fetchone()[0] == "RuntimeError"
    assert conn.execute("SELECT count(*) FROM fact_observations").fetchone()[0] == 2


def test_latest_snapshot_does_not_use_missing_observation(db):
    conn,_ = db
    put(conn,"DGS10",[("2024-01-01","4"),("2024-01-02",".")])
    row = conn.execute("SELECT observation_date,value FROM vw_latest_snapshot WHERE series_id='DGS10'").fetchone()
    assert row == (date(2024,1,1),4.0)
