CREATE TABLE IF NOT EXISTS dim_series (
    series_id text PRIMARY KEY,
    title text NOT NULL,
    units text NOT NULL,
    frequency text NOT NULL,
    category text NOT NULL,
    stale_after_days integer NOT NULL CHECK (stale_after_days > 0),
    source_url text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS fact_observations (
    series_id text NOT NULL REFERENCES dim_series(series_id),
    observation_date date NOT NULL,
    value double precision,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (series_id, observation_date)
);
CREATE INDEX IF NOT EXISTS ix_observation_date ON fact_observations(observation_date);

CREATE TABLE IF NOT EXISTS etl_run_log (
    run_id uuid PRIMARY KEY,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    status text NOT NULL CHECK (status IN ('running','success','partial','failed','interrupted')),
    series_succeeded integer NOT NULL DEFAULT 0,
    series_failed integer NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS etl_series_log (
    run_id uuid NOT NULL REFERENCES etl_run_log(run_id),
    -- No dimension FK: log failures even before metadata is successfully loaded.
    series_id text NOT NULL,
    status text NOT NULL CHECK (status IN ('success','failed')),
    requested_start date NOT NULL,
    is_full_refresh boolean NOT NULL,
    rows_processed integer NOT NULL DEFAULT 0,
    missing_values integer NOT NULL DEFAULT 0,
    latest_observation date,
    is_stale boolean,
    error_type text,
    finished_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, series_id)
);
