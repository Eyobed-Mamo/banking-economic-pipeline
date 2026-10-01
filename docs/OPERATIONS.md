# Operations and recovery

## Run lifecycle

The process takes a PostgreSQL advisory lock, creates tables/views if needed, records a run, and processes each series in turn. Each successful series commits metadata, observations, and its success log in one transaction. An error rolls back that series' changes and records a failure separately. The run is `success`, `partial`, or `failed`; the exit code is nonzero for partial failure so schedulers can detect problems.

If a process is terminated, PostgreSQL releases its session lock. The next run marks any old `running` log as `interrupted`. API requests use connect/read timeouts, exponential backoff, four retries, and Retry-After handling for transient failures. No raw HTTP errors or key-bearing URLs are logged.

## Incremental and revision policy

For each series, start at the latest stored non-null observation minus 90 days, bounded by START_DATE. This catches recent revisions and works even if the pipeline was offline for a while. The first load, a forced full load, or 30 days since the last successful full load triggers history retrieval from START_DATE. Full-refresh due dates are tracked separately for each series so one failing series cannot defer its own recovery indefinitely.

This is a current-revision store, not a complete audit of vintages. Extend the model with retrieval/vintage dates if you later need point-in-time analysis.

## Daily checks

```sql
SELECT * FROM etl_run_log ORDER BY started_at DESC LIMIT 10;
SELECT * FROM etl_series_log WHERE status = 'failed' ORDER BY finished_at DESC;
SELECT * FROM vw_latest_snapshot WHERE is_stale;
```

Freshness warnings are recorded but do not fail an otherwise valid retrieval. Holidays, delayed releases, and period labels affect age. Treat stale flags as prompts to investigate.

Logs contain safe exception classes. For `FredError`, verify key/network/service availability. For `ValueError`, inspect the series' source data or configured dates. For database errors, check permissions, free space, and schema compatibility. Do not add raw request URLs to public troubleshooting logs.

## Recovery

Correct the root cause and rerun. The primary key and upsert prevent duplicates. To revisit old revisions, run `python -m etl.pipeline --full-refresh`. Never load demo values into the live database. The live loader checks the demo marker and refuses that combination.

Back up PostgreSQL separately if your copy of the historical revisions matters. Docker's named volume persists between ordinary container restarts. Removing a database or its volume destroys stored observations and run history.

## Scheduling

Use `scripts/run_daily.ps1` in Windows Task Scheduler or `scripts/run_daily.sh` in cron. The intended time is 7 a.m. **America/New_York** for Charlotte. Configure the host/scheduler timezone rather than hard-coding a fixed UTC offset, because daylight saving changes the offset.

Docker Compose starts the database and offers an ETL job; it does not provide a daily scheduler. The repository's GitHub Actions workflow runs tests only. It cannot refresh a PostgreSQL instance on your laptop.

## Security

`.env`, logs, cached Power BI data, and virtual environments are ignored by Git. Database port publishing binds to 127.0.0.1. Development passwords in `.env.example` are examples, not production credentials. Use a dedicated read-only database account for a deployed BI service and store production secrets in the relevant scheduler/hosting secret store.
