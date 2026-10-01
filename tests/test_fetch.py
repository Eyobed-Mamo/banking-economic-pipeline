from datetime import date
from unittest.mock import Mock
import requests
import pytest
from etl.fetch import FredClient, FredError


def response(payload):
    r = Mock()
    r.json.return_value = payload
    return r


def test_pagination_and_request_parameters():
    session = Mock()
    session.get.side_effect = [response({"count":2,"observations":[{"date":"2024-01-01","value":"1"}]}),
                               response({"count":2,"observations":[{"date":"2024-01-02","value":"2"}]})]
    client = FredClient("private-test-key", session)
    assert len(client.observations("DGS10",date(2024,1,1),date(2024,1,2))) == 2
    assert session.get.call_args.kwargs["params"]["offset"] == 1
    assert session.get.call_args.kwargs["params"]["observation_start"] == "2024-01-01"
    retry = session.mount.call_args.args[1].max_retries
    assert 429 in retry.status_forcelist and retry.total == 4


def test_http_error_does_not_leak_key():
    session = Mock()
    session.get.side_effect = requests.RequestException("https://example/?api_key=SECRET")
    with pytest.raises(FredError) as exc:
        FredClient("SECRET",session).metadata("DGS10")
    assert "SECRET" not in str(exc.value)


def test_incomplete_pagination_rejected():
    session = Mock()
    session.get.return_value = response({"count":2,"observations":[]})
    with pytest.raises(FredError):
        FredClient("key",session).observations("DGS10",date(2024,1,1),date(2024,1,2))
