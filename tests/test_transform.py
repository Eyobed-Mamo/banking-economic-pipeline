from datetime import date
import pandas as pd
import pytest
from etl.transform import clean_observations

START, END = date(2024,1,1), date(2024,12,31)


def clean(rows):
    return clean_observations(rows,"DGS10",START,END)


def test_missing_values_and_duplicate_removal():
    df = clean([{"date":"2024-01-02","value":"."},{"date":"2024-01-01","value":"4.2"},
                {"date":"2024-01-01","value":"4.2"}])
    assert len(df) == 2
    assert df.iloc[0].value == 4.2
    assert pd.isna(df.iloc[1].value)


@pytest.mark.parametrize("rows", [[],[{"date":"bad","value":"1"}],
    [{"date":"2024-01-01","value":"bad"}], [{"date":"2024-01-01","value":"inf"}],
    [{"date":"2024-01-01","value":"."}], [{"date":"2025-01-01","value":"1"}],
    [{"date":"2024-01-01","value":"1"},{"date":"2024-01-01","value":"2"}]])
def test_reject_bad_responses(rows):
    with pytest.raises(ValueError):
        clean(rows)


def test_negative_rates_are_valid():
    assert clean([{"date":"2024-01-01","value":"-0.5"}]).iloc[0].value == -0.5
