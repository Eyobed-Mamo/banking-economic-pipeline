# Data dictionary and metric definitions

## Tables

| Table | Grain / key | Purpose |
|---|---|---|
| dim_series | One row per FRED series; `series_id` | Title, units, frequency, category, source URL, freshness allowance |
| fact_observations | One row per series and observation date | Latest retrieved numeric value (nullable) and last change timestamp |
| etl_run_log | One row per pipeline attempt; UUID `run_id` | Start/end, overall status, success/failure counts |
| etl_series_log | One row per run and series | Requested start, full/incremental flag, processed rows, missing count, freshness, error class |

`rows_processed` counts validated input rows offered to the upsert, not newly inserted rows. Repeated input may therefore produce a positive count with no changed database rows.

`fact_observations.updated_at` changes only when a value is inserted or revised. `etl_series_log.finished_at` identifies successful retrieval even when all values were unchanged. Timestamps use PostgreSQL `timestamptz`.

## Reporting views

| View | Grain | Semantics |
|---|---|---|
| vw_monthly_indicators | Series/month, non-quarterly series | Arithmetic mean of available values; count; latest date; current-month flag |
| vw_yield_curve | Matching valid trading date | 10Y, 2Y, spread in percentage points and basis points, inversion flag |
| vw_cpi_yoy | CPI month | Index and exact same-month-prior-year percentage change |
| vw_latest_snapshot | Series | Most recent non-null observation, period, value, age and stale flag |
| vw_credit_quarterly | Quarterly delinquency period | Delinquency plus policy and unemployment means within that quarter |
| vw_mortgage_spread | Mortgage observation date | Mortgage rate minus mean Treasury yield in the same Monday-starting calendar week |
| vw_pipeline_health | Run/series | Operational history for the report |

## Original data providers

| Series | Original provider | Source |
|---|---|---|
| FEDFUNDS | Board of Governors of the Federal Reserve System | [FRED](https://fred.stlouisfed.org/series/FEDFUNDS) |
| DGS2 | Board of Governors of the Federal Reserve System | [FRED](https://fred.stlouisfed.org/series/DGS2) |
| DGS10 | Board of Governors of the Federal Reserve System | [FRED](https://fred.stlouisfed.org/series/DGS10) |
| MORTGAGE30US | Freddie Mac | [FRED](https://fred.stlouisfed.org/series/MORTGAGE30US) |
| DRCCLACBS | Board of Governors of the Federal Reserve System | [FRED](https://fred.stlouisfed.org/series/DRCCLACBS) |
| CPIAUCSL | U.S. Bureau of Labor Statistics | [FRED](https://fred.stlouisfed.org/series/CPIAUCSL) |
| UNRATE | U.S. Bureau of Labor Statistics | [FRED](https://fred.stlouisfed.org/series/UNRATE) |

Metadata titles, units, and frequency are refreshed from FRED; analytical categories and freshness allowances are project configuration.

## Freshness

Daily Treasury series: 10 calendar days; weekly mortgage: 21 days; monthly indicators: 75 days; quarterly credit: 200 days. Age is measured from the observation-period date, so the longer allowances account approximately for publication lag and period-start labels. These are monitoring heuristics, not an official release calendar or a guarantee of completeness.

Freshness in imported Power BI data is evaluated when the SQL view is refreshed. It does not update just because someone opens the report.

## Data limitations

The initial history begins in 2000 by default. Source revisions overwrite current values; previous vintages are not retained. Upserts do not delete dates removed entirely by a provider. A supplied missing value does overwrite the previous value with NULL. Partial months/quarters may have fewer observations, and comparisons should use complete periods when appropriate. The demo is entirely synthetic.
