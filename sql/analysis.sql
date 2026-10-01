-- 1. Yield-curve inversion by calendar year. Denominator is matched valid trading days.
SELECT extract(year FROM observation_date)::integer AS year,
       count(*) AS matched_days, count(*) FILTER(WHERE is_inverted) AS inverted_days,
       round((100.0*count(*) FILTER(WHERE is_inverted)/NULLIF(count(*),0))::numeric,2) AS inverted_pct,
       round(min(spread_bps)::numeric,1) AS lowest_spread_bps
FROM vw_yield_curve GROUP BY 1 ORDER BY 1;

-- 2. Mortgage spread by month; a contextual proxy, NOT a bank's lending margin.
SELECT date_trunc('month',observation_date)::date AS month,
       avg(mortgage_pct) AS mortgage_pct,avg(treasury_10y_pct) AS treasury_pct,
       avg(spread_pp) AS spread_pp
FROM vw_mortgage_spread GROUP BY 1 ORDER BY 1;

-- 3. Quarterly credit pressure with the previous quarter's policy rate.
SELECT a.quarter_start,a.delinquency_pct,a.fed_funds_pct,
       b.fed_funds_pct AS previous_quarter_fed_funds_pct,
       a.delinquency_pct-b.delinquency_pct AS delinquency_change_pp
FROM vw_credit_quarterly a LEFT JOIN vw_credit_quarterly b
ON b.quarter_start=(a.quarter_start-interval '3 months')::date ORDER BY 1;

-- 4. Pairwise monthly correlation. Association does not establish causation.
SELECT count(*) AS paired_months, min(a.month) AS first_month,max(a.month) AS last_month,
       corr(a.value,b.value) AS fed_funds_unemployment_correlation
FROM vw_monthly_indicators a JOIN vw_monthly_indicators b USING(month)
WHERE a.series_id='FEDFUNDS' AND b.series_id='UNRATE' AND a.value IS NOT NULL AND b.value IS NOT NULL;

-- 5. Data quality and operational health.
SELECT * FROM vw_latest_snapshot WHERE is_stale ORDER BY age_days DESC NULLS FIRST;
SELECT * FROM etl_run_log ORDER BY started_at DESC LIMIT 20;
SELECT * FROM etl_series_log WHERE status='failed' ORDER BY finished_at DESC LIMIT 20;
