# Power BI report guide

Open `powerbi/Banking.pbip`; keep the adjacent `.Report` and `.SemanticModel` folders together. Microsoft documents [PBIP projects](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview) and the [editable report format](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report).

The report source was generated and schema-validated. It has not been opened/rendered in Power BI Desktop in the build environment. There is no cached data or fabricated report screenshot in this repository.

## Connect and refresh

1. Load your database using the README instructions.
2. Open the project in a current Power BI Desktop release.
3. Edit `Server` and `Database` in Power Query parameters. Defaults: `localhost:5433`, `fred_pipeline`.
4. Enter PostgreSQL credentials through Data source settings. The Power BI project contains no password.
5. Refresh; save. For synthetic demo data, use `fred_pipeline_demo` and label the report explicitly as a demo before sharing screenshots.

All tables use Import mode. A Calendar table relates to each historical view. Series relates to the monthly and snapshot tables. Snapshot cards deliberately show latest available values and are not connected to the historical date filter. Pages use their appropriate view rather than combining measurements with incompatible units.

## Pages

| Page | What to review |
|---|---|
| Executive overview | Four latest-rate cards; a table with dates, units, frequency, and stale flags; reading guidance |
| Rates & yield curve | Year filter; 10Y and 2Y yields with year/quarter/month drill; spread in basis points |
| Inflation & labor | Year filter; CPI year-over-year inflation; policy rate and unemployment |
| Credit & lending | Year filter; quarterly delinquency and policy rates; mortgage–Treasury spread |
| Data & pipeline health | Observation freshness; per-series run outcomes and processed/missing counts |

The overview includes a prompt to record three dated findings after real-data loading. It does not pretend that synthetic or unobserved data supports an executive conclusion.

## Metric rules

- A percent-valued rate is stored as `5.25`, not `0.0525`. Card formats append the percent symbol without multiplying by 100.
- One percentage point equals 100 basis points.
- CPI index values are not inflation rates; the report uses the SQL year-over-year calculation.
- Line charts average values at the displayed grain. The Treasury chart starts yearly; drill to quarter/month for more detail. At coarse grains, spread lines show averages, not the count of inverted days.
- Latest observations may refer to different periods; read the date beside the value.
- Missing values are not zero, and quarterly values are not fabricated into monthly observations.

## Public portfolio publishing

GitHub makes the project source and instructions public. It does **not** host an interactive Power BI report automatically.

After checking the report in Desktop with real data:

1. Capture clear screenshots or export a PDF and add it to your portfolio.
2. Publish to your Power BI workspace if your account supports it.
3. Use Microsoft's public-sharing option only if it is available and allowed by your tenant; it makes the report's data public. Account/tenant eligibility varies.
4. If interactive public sharing is unavailable, publish screenshots, a PDF, and a short walkthrough video alongside the PBIP source.

For automated Power BI Service refresh against a local database, configure the [on-premises gateway and refresh schedule](https://learn.microsoft.com/en-us/power-bi/connect-data/refresh-scheduled-refresh). The gateway machine and PostgreSQL must be online. Set the report refresh after the ETL's usual completion time and check run status on the health page.

## Rebuild the source

`python scripts/build_powerbi.py` regenerates the project files. It overwrites generated definitions, so do not run it over manual report edits you want to keep. Normal report editing should happen in Power BI Desktop.
