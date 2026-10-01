"""Preserve missing observations as NULL; reject malformed dates/numbers."""
from datetime import date
import numpy as np
import pandas as pd


def clean_observations(records, series_id, start: date, end: date):
    if not records:
        raise ValueError("Unexpected empty observation response")
    frame = pd.DataFrame(records)
    if not {"date", "value"}.issubset(frame.columns):
        raise ValueError("Observations require date and value")
    dates = pd.to_datetime(frame["date"], format="%Y-%m-%d", errors="coerce")
    raw = frame["value"].astype("string").str.strip()
    missing = raw.isna() | raw.isin([".", ""])
    values = pd.to_numeric(raw.mask(missing), errors="coerce")
    if dates.isna().any():
        raise ValueError("Invalid observation date")
    if ((~missing) & values.isna()).any() or np.isinf(values.dropna().astype(float)).any():
        raise ValueError("Invalid numeric observation")
    result = pd.DataFrame({"series_id": series_id, "observation_date": dates.dt.date,
                           "value": values.astype(float)})
    if ((result.observation_date < start) | (result.observation_date > end)).any():
        raise ValueError("Observation outside requested interval")
    # FRED should be unique. Identical duplicates are harmless; conflicting ones are not.
    if (result.groupby("observation_date").value.nunique(dropna=False) > 1).any():
        raise ValueError("Conflicting duplicate observations")
    result = result.drop_duplicates(["series_id", "observation_date"]).sort_values("observation_date")
    if result.value.notna().sum() == 0:
        raise ValueError("Response contains no numeric observations")
    return result.reset_index(drop=True)
