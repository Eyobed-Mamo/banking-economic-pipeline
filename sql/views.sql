-- Daily/weekly rates use the arithmetic average of available observations.
-- No interpolation. Quarterly series are deliberately excluded from monthly views.
CREATE OR REPLACE VIEW vw_monthly_indicators AS
SELECT o.series_id, date_trunc('month',o.observation_date)::date AS month,
       avg(o.value) AS value, count(o.value)::integer AS observation_count,
       max(o.observation_date) FILTER (WHERE o.value IS NOT NULL) AS latest_observation,
       d.title, d.units, d.category,
       date_trunc('month',o.observation_date)::date = date_trunc('month',current_date)::date AS is_current_month
FROM fact_observations o JOIN dim_series d USING(series_id)
WHERE d.frequency <> 'Quarterly'
GROUP BY o.series_id, date_trunc('month',o.observation_date)::date, d.title,d.units,d.category;

CREATE OR REPLACE VIEW vw_yield_curve AS
SELECT a.observation_date, a.value AS yield_10y, b.value AS yield_2y,
       a.value-b.value AS spread_pp, (a.value-b.value)*100 AS spread_bps,
       a.value < b.value AS is_inverted
FROM fact_observations a JOIN fact_observations b ON a.observation_date=b.observation_date
WHERE a.series_id='DGS10' AND b.series_id='DGS2' AND a.value IS NOT NULL AND b.value IS NOT NULL;

-- Join exactly 12 calendar months earlier: LAG(12) alone silently breaks with gaps.
CREATE OR REPLACE VIEW vw_cpi_yoy AS
SELECT a.month, a.value AS cpi_index, b.value AS cpi_index_prior_year,
       100.0*(a.value/NULLIF(b.value,0)-1) AS inflation_yoy_pct
FROM vw_monthly_indicators a LEFT JOIN vw_monthly_indicators b
ON b.series_id='CPIAUCSL' AND b.month=(a.month-interval '1 year')::date
WHERE a.series_id='CPIAUCSL';

CREATE OR REPLACE VIEW vw_latest_snapshot AS
SELECT d.series_id,d.title,d.units,d.frequency,d.category,d.source_url,
       x.observation_date,x.value,
       current_date-x.observation_date AS age_days,
       x.observation_date IS NULL OR current_date-x.observation_date>d.stale_after_days AS is_stale
FROM dim_series d LEFT JOIN LATERAL (
    SELECT observation_date,value FROM fact_observations o
    WHERE o.series_id=d.series_id AND value IS NOT NULL ORDER BY observation_date DESC LIMIT 1
) x ON true;

CREATE OR REPLACE VIEW vw_credit_quarterly AS
SELECT o.observation_date AS quarter_start, o.value AS delinquency_pct,
       f.fed_funds_pct, u.unemployment_pct
FROM fact_observations o
LEFT JOIN LATERAL (
    SELECT avg(value) AS fed_funds_pct FROM fact_observations
    WHERE series_id='FEDFUNDS' AND observation_date>=o.observation_date
      AND observation_date<o.observation_date+interval '3 months'
) f ON true
LEFT JOIN LATERAL (
    SELECT avg(value) AS unemployment_pct FROM fact_observations
    WHERE series_id='UNRATE' AND observation_date>=o.observation_date
      AND observation_date<o.observation_date+interval '3 months'
) u ON true
WHERE o.series_id='DRCCLACBS';

-- Weekly mortgage observations compared with the same calendar week's Treasury mean.
CREATE OR REPLACE VIEW vw_mortgage_spread AS
WITH treasury AS (
    SELECT date_trunc('week',observation_date)::date AS week_start, avg(value) AS treasury_10y_pct
    FROM fact_observations WHERE series_id='DGS10' GROUP BY 1
)
SELECT m.observation_date,t.week_start,m.value AS mortgage_pct,t.treasury_10y_pct,
       m.value-t.treasury_10y_pct AS spread_pp
FROM fact_observations m JOIN treasury t ON t.week_start=date_trunc('week',m.observation_date)::date
WHERE m.series_id='MORTGAGE30US' AND m.value IS NOT NULL AND t.treasury_10y_pct IS NOT NULL;

CREATE OR REPLACE VIEW vw_pipeline_health AS
SELECT r.run_id::text, r.started_at,r.finished_at,r.status AS run_status,
       s.series_id,s.status AS series_status,s.rows_processed,s.missing_values,s.is_stale,s.error_type
FROM etl_run_log r LEFT JOIN etl_series_log s USING(run_id);
