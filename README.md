# Banking Economic Conditions & Automated ETL

A Python, SQL, PostgreSQL, and Power BI portfolio project for understanding the economic environment around U.S. banking and lending.

**Business question:** How are borrowing costs, the yield curve, inflation, employment, and credit-card delinquencies changing together?

This analyzes national economic conditions. It does not measure individual banks' profits, customers, deposits, or churn.

```mermaid
flowchart LR
    A[FRED API: 7 series] --> B[Python requests: retry + pagination]
    B --> C[pandas: validate and clean]
    C --> D[(PostgreSQL: dimensions + observations)]
    D --> E[SQL reporting views]
    E --> F[Power BI: 5 report pages]
    C --> G[Run and series logs]
    H[Daily scheduler] --> B
```

## What is included

- Seven economic series with metadata and a unique `(series_id, observation_date)` key.
- Bounded retries for transient HTTP failures, timeouts, and paginated API responses.
- Incremental loads with a 90-day overlap based on the latest stored valid observation.
- Automatic full-history refresh every 30 days, plus `--full-refresh` on demand.
- Transactional per-series upserts, failure isolation, run logs, and a concurrent-run lock.
- Missing-value, invalid-value, duplicate, empty-response, and freshness checks.
- Seven SQL views and five annotated SQL analyses.
- Editable **Power BI project (`.pbip`)** with five pages, nine model tables, measures, filters, and a drillable date axis.
- A synthetic demo that requires no API key and uses a separate database.
- Unit tests, real PostgreSQL integration tests, and GitHub Actions CI.
- Windows and Linux/macOS daily-run scripts.

## Validation status

The Python/SQL implementation was tested against PostgreSQL 18 with Python 3.12. All **23 tests passed**. All **40 Power BI definition files** passed validation against Microsoft's published JSON schemas. See [validation details](docs/VALIDATION.md).

**Power BI Desktop rendering and a live FRED API run have not been verified in the build environment.** The included report is editable source, not a screenshot or a pre-refreshed `.pbix`. It opens without cached data and needs a database refresh. A FRED API key is required only for real-data ingestion.

## Quick start: real data

### 1. Prerequisites

- Python 3.11 or newer (3.12 recommended).
- Docker Desktop with Compose, **or** an existing PostgreSQL 15+ installation.
- Power BI Desktop for the report (Windows).
- A free FRED API key: [request one here](https://fred.stlouisfed.org/docs/api/api_key.html).

Create a FRED account, follow its API-key instructions, and keep the key private. Do not put it in GitHub, screenshots, issues, or chat messages.

### 2. Get the project and install dependencies

```powershell
git clone https://github.com/Eyobed-Mamo/banking-economic-pipeline.git
cd banking-economic-pipeline
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

On Linux/macOS, use `python3 -m venv .venv`, `.venv/bin/python -m pip install -r requirements-dev.txt`, and `cp .env.example .env`.

Edit `.env` in your text editor. Paste your key after `FRED_API_KEY=`. The supplied database credentials are for local development only. If you change them, update both the PostgreSQL fields and `DATABASE_URL`; URL-encode any special characters in the URL password.

### 3. Start the database

```powershell
docker compose up -d db
docker compose ps
```

Wait until the database is healthy. This project uses **localhost:5433**, avoiding the usual 5432 port used by an existing PostgreSQL installation.

Already have PostgreSQL? Create a database named `fred_pipeline` in pgAdmin, set `DATABASE_URL` to its credentials and port, and skip Docker. The pipeline creates its own tables and views; it does not create the database. Use a dedicated project database, not an existing application database.

### 4. Run the pipeline

```powershell
.\.venv\Scripts\python.exe -m etl.pipeline
```

The first run loads history from January 2000. Later runs use incremental loading unless a full refresh is due.

```powershell
# Re-fetch all history to capture older revisions
.\.venv\Scripts\python.exe -m etl.pipeline --full-refresh

# Create the schema without requesting FRED data
.\.venv\Scripts\python.exe -m etl.pipeline --init-db
```

Alternatively run the ETL inside Docker:

```powershell
docker compose --profile pipeline run --rm --build etl
```

### 5. Open Power BI

1. Open `powerbi/Banking.pbip` in a recent Power BI Desktop release.
2. If your release requires it, enable Power BI Project/PBIR support in Preview features and restart Desktop.
3. In **Transform data → Edit parameters**, set `Server` to `localhost:5433` and `Database` to `fred_pipeline` (or your existing database settings).
4. Select **Refresh**. Choose database authentication and enter your PostgreSQL username/password locally. No credentials are included in the project.
5. Browse the five pages. Use the year slicers and the Treasury chart's drill controls.
6. Save the report; you can also save a local `.pbix` for personal use.

See [Power BI guide](docs/POWER_BI.md) for metrics, filters, refresh, and public sharing.

## Try it without a FRED key

The demo uses deterministic **synthetic values, not real FRED observations**. It is for learning the workflow and testing the report. It cannot support economic conclusions.

After installing dependencies and starting the Docker database:

```powershell
# Run once to create a separate demo database
docker compose exec db createdb -U fred fred_pipeline_demo

# Override the connection for this terminal session only
$env:DATABASE_URL = 'postgresql://fred:local_dev_change_me@localhost:5433/fred_pipeline_demo'
.\.venv\Scripts\python.exe -m etl.demo
Remove-Item Env:DATABASE_URL
```

Adapt the username/password if you changed them. In Power BI, set the `Database` parameter to `fred_pipeline_demo` and refresh. **Keep a visible SYNTHETIC DEMO label on any screenshots you share.** The demo covers 2015–2025; it will intentionally appear stale later.

On Linux/macOS, use:

```bash
DATABASE_URL='postgresql://fred:local_dev_change_me@localhost:5433/fred_pipeline_demo' .venv/bin/python -m etl.demo
```

The demo loader refuses database names that do not end in `_demo`. The live loader refuses databases marked as demo. Use `fred_pipeline` when you obtain your real FRED key.

## Run the SQL analyses

In pgAdmin, open Query Tool for your project database and open `sql/analysis.sql`. Execute individual queries to inspect:

1. Annual yield-curve inversion days and shares.
2. Monthly mortgage spreads over Treasuries.
3. Delinquency and prior-quarter policy rates.
4. Monthly policy-rate/unemployment correlation.
5. Stale series and failed pipeline runs.

Or use the command line with Docker:

```powershell
Get-Content sql/analysis.sql | docker compose exec -T db psql -U fred -d fred_pipeline
```

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Without `TEST_DATABASE_URL`, the database tests are explicitly skipped. To run the full suite:

```powershell
docker compose exec db createdb -U fred fred_pipeline_test
$env:TEST_DATABASE_URL = 'postgresql://fred:local_dev_change_me@localhost:5433/fred_pipeline_test'
.\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:TEST_DATABASE_URL
```

Tests create and remove a unique schema inside this dedicated test database. GitHub Actions provides its own temporary PostgreSQL service and runs the full suite without a FRED key.

## Daily automation: 7 a.m. Charlotte time

Windows Task Scheduler uses the computer's local timezone. For Charlotte, use **Eastern Time**, which handles daylight saving automatically.

Create a daily task at 7:00 a.m.:

- **Program:** `powershell.exe`
- **Arguments:** `-NoProfile -File "C:\path\to\banking-economic-pipeline\scripts\run_daily.ps1"`
- **Start in:** `C:\path\to\banking-economic-pipeline`
- Set **If the task is already running: Do not start a new instance**.
- Enable **Run task as soon as possible after a scheduled start is missed**.

The script uses `.venv`, writes a timestamped log in `logs/`, and preserves the exit code. The computer and database must be running. No scheduled task is installed automatically.

Linux/macOS: configure the machine/scheduler timezone as `America/New_York`, then add:

```cron
0 7 * * * /bin/sh /absolute/path/banking-economic-pipeline/scripts/run_daily.sh
```

Python ingestion and Power BI refresh are separate jobs. A published Power BI report connecting to local PostgreSQL needs a running on-premises data gateway and its own refresh schedule. See [operations](docs/OPERATIONS.md).

## Series

| ID | Indicator | Frequency | Units |
|---|---|---|---|
| FEDFUNDS | Effective federal funds rate | Monthly | Percent |
| DGS2 | 2-year Treasury yield | Daily | Percent |
| DGS10 | 10-year Treasury yield | Daily | Percent |
| MORTGAGE30US | 30-year fixed mortgage rate | Weekly | Percent |
| DRCCLACBS | Credit card loan delinquency rate, all commercial banks | Quarterly | Percent |
| CPIAUCSL | Seasonally adjusted consumer price index | Monthly | Index, 1982–1984=100 |
| UNRATE | Unemployment rate | Monthly | Percent |

## Important analytical choices

- Preserve FRED `.` observations as SQL `NULL`; never replace missing rates with zero.
- Daily and weekly rates become monthly averages of available observations. Current-month averages can be incomplete.
- Keep delinquency quarterly. Its FRED date labels the observation period, not the date the public learned the value.
- CPI year-over-year inflation joins the exact prior-year month; a missing month yields a missing comparison.
- Yield spread = 10Y minus 2Y. Multiply percentage points by 100 for basis points.
- Mortgage spread compares a weekly mortgage observation with that week's mean 10Y yield. It is not a bank's net interest margin, and it is not a point-in-time trading signal.
- Historical observations reflect the latest retrieved revisions. This is not a vintage-aware backtest dataset.
- Correlations are descriptive and can depend strongly on the selected period. They do not demonstrate causality.

## Project map

```text
etl/          API client, cleaning, upserts, orchestration, demo
sql/          Schema, seven reporting views, analyses
powerbi/      Editable report and semantic-model source
scripts/      Scheduling wrappers and Power BI source generator
tests/        Unit and PostgreSQL integration tests
docs/         Data dictionary, operations, report guide, walkthrough
.github/      CI tests with a temporary PostgreSQL service
```

## Troubleshooting

| Symptom | Check |
|---|---|
| `python` is not recognized | Install Python; reopen your terminal. On Windows, `py -3.12` may be available instead. |
| Cannot connect to database | Check `docker compose ps`, the port, database name, and credentials in `.env`. |
| All FRED series fail | Check that your key is present and valid, and that the network can reach FRED. |
| One series fails | Inspect `etl_series_log.error_type`; the other series still load. A rerun is safe. |
| Stale flag | Check the source's publication schedule and the pipeline logs. Quarterly series use a longer allowance. |
| Empty Power BI visuals | Run ETL, set the two parameters, provide database credentials, and refresh. |
| PBIP will not open | Update Power BI Desktop; check project/PBIR support. Report files have schema validation, but Desktop rendering remains unverified. |
| Exit code 1 | At least one series failed; inspect logs. |
| Exit code 2 | Startup/database/configuration problem or a concurrent active run. |

## Sources and documentation

- [FRED observations API](https://fred.stlouisfed.org/docs/api/fred/series_observations.html)
- [FRED real-time periods and revisions](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html)
- [FRED series and original-provider citations](docs/DATA_DICTIONARY.md)
- [Microsoft Power BI projects](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview)
- [Power BI scheduled refresh](https://learn.microsoft.com/en-us/power-bi/connect-data/refresh-scheduled-refresh)

Economic data remains subject to its original provider's terms. Review individual series notes before redistributing data. This repository includes source code and synthetic demo generation, not a republished real-data dump.
