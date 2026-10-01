"""Bounded HTTP retries; paginate observations; never log key-bearing URLs."""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://api.stlouisfed.org/fred"


class FredError(RuntimeError):
    pass


class FredClient:
    def __init__(self, api_key, session=None):
        if not api_key:
            raise ValueError("FRED_API_KEY is missing; add it locally to .env")
        self.api_key = api_key
        self.session = session or requests.Session()
        retry = Retry(total=4, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504],
                      allowed_methods=["GET"], respect_retry_after_header=True)
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def _get(self, endpoint, **params):
        try:
            response = self.session.get(f"{BASE_URL}/{endpoint}",
                params={**params, "api_key": self.api_key, "file_type": "json"}, timeout=(10, 60))
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            # requests errors may contain the URL and API key. Do not propagate them.
            raise FredError(f"FRED {endpoint} request failed; check key, connectivity and service status") from None
        if not isinstance(payload, dict) or "error_code" in payload:
            raise FredError("FRED returned an invalid/error response")
        return payload

    def metadata(self, series_id):
        rows = self._get("series", series_id=series_id).get("seriess", [])
        if len(rows) != 1 or rows[0].get("id") != series_id:
            raise FredError(f"Unexpected metadata for {series_id}")
        return rows[0]

    def observations(self, series_id, start, end):
        records, offset = [], 0
        while True:
            payload = self._get("series/observations", series_id=series_id,
                observation_start=start.isoformat(), observation_end=end.isoformat(),
                sort_order="asc", limit=10000, offset=offset)
            page = payload.get("observations")
            if not isinstance(page, list):
                raise FredError("FRED response has no observations list")
            count = int(payload.get("count", len(page)))
            records.extend(page)
            offset += len(page)
            if offset >= count:
                return records
            if not page:
                raise FredError("FRED pagination stopped before all observations were received")

    def close(self):
        self.session.close()
