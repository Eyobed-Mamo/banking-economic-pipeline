# Explain the project in an interview

## A 60-second introduction

I built a pipeline and Power BI report to analyze U.S. economic conditions relevant to banking. Python retrieves seven FRED series, pandas validates the observations, and PostgreSQL stores the data with a unique series-and-date key. SQL views calculate measures such as the Treasury yield spread and year-over-year inflation. Power BI organizes the results into executive, rates, inflation, credit, and data-health pages.

The pipeline supports safe reruns, recent-data overlap, periodic full-history refreshes, and per-series failure isolation. Tests cover revisions, missing values, mixed reporting frequencies, and database behavior.

Only claim live automation or a published interactive dashboard after you have enabled and verified those steps yourself.

## Decisions worth explaining

**Why PostgreSQL instead of only CSV?** A database supports primary keys, transactions, repeatable queries, and a shared BI data source.

**Why upsert?** New observations insert; revised values update; rerunning does not duplicate rows.

**Why revisit historical data?** Economic data can be revised. The 90-day overlap handles recent changes, while a full refresh every 30 days revisits older history.

**Why separate quarterly data?** Repeating a quarterly delinquency number across months could imply measurements that do not exist. The credit page uses the quarterly grain.

**Why calculate inflation with a date join?** A 12-row lag is not necessarily 12 months when observations are missing. An exact prior-year-month join preserves the definition.

**How do you know a job worked?** Exit code, run status, per-series outcomes, freshness checks, and the data-health page.

## First real-data analysis

After obtaining a FRED key and refreshing the report, write three findings using this structure:

1. Indicator and exact observation period.
2. Comparison period and quantified change, with correct units.
3. A cautious explanation of why the change matters to banking.

For example, describe a mortgage-rate change in percentage points, then explain its relevance to borrowing costs. Do not turn that into a claim about an individual bank's profits or customer behavior.

Include your selected date range and the refresh date. Explain that historical values reflect the latest retrieved revisions.
