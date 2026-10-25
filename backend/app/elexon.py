"""Read-through Elexon data with a bounded, per-instance cache and honest fallback."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import threading
import time
from types import MappingProxyType
from typing import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
API = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
FORECAST_URL = f"{API}/WINDFOR/stream?" + urlencode({"publishDateTimeFrom": "2025-12-30T00:00:00Z", "publishDateTimeTo": "2026-02-01T00:00:00Z"})
ACTUAL_URL = f"{API}/FUELHH/stream?" + urlencode({"settlementDateFrom": "2026-01-02", "settlementDateTo": "2026-02-01", "fuelType": "WIND"})
SOURCE_URLS = {"forecasts": FORECAST_URL, "actuals": ACTUAL_URL, "coverage": "https://bmrs.elexon.co.uk/wind-generation"}
FIRST_TARGET = "2026-01-02T00:00:00Z"
AFTER_TARGET = "2026-02-02T00:00:00Z"
FETCH_DEADLINE_SECONDS = 42.0


class DataUnavailable(RuntimeError):
    """No usable upstream data, previous cache, or fallback is available."""


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonical_time(value) -> str:
    if not isinstance(value, str):
        raise ValueError("Elexon returned a missing timestamp.")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Elexon returned a timestamp without a timezone.")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def generation(value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Elexon returned an invalid generation value.")
    return float(value)


@dataclass(frozen=True)
class Dataset:
    forecasts_by_day: Mapping
    actuals: Mapping
    metadata: Mapping
    epoch: str
    origin: str


@dataclass(frozen=True)
class DatasetResult:
    dataset: Dataset
    status: dict


def normalize(forecasts, actuals, retrieved_at: str, *, origin="live_api", snapshot_metadata=None) -> Dataset:
    if not isinstance(forecasts, list) or not isinstance(actuals, list) or not forecasts or not actuals:
        raise ValueError("Elexon returned an empty or malformed dataset for the January window.")
    revisions = {}
    halfhours = {}
    for row in forecasts:
        if not isinstance(row, dict):
            raise ValueError("Elexon returned a malformed forecast record.")
        target, published = canonical_time(row.get("startTime")), canonical_time(row.get("publishTime"))
        value = generation(row.get("generation"))
        if not FIRST_TARGET <= target < AFTER_TARGET:
            continue
        if target[14:19] != "00:00":
            raise ValueError("The forecast target resolution changed; hourly alignment needs review.")
        key = (target, published)
        if key in revisions and revisions[key] != value:
            raise ValueError("Elexon returned conflicting forecast revisions.")
        revisions[key] = value
    for row in actuals:
        if not isinstance(row, dict):
            raise ValueError("Elexon returned a malformed actual record.")
        if row.get("fuelType") != "WIND":
            continue
        target, published = canonical_time(row.get("startTime")), canonical_time(row.get("publishTime"))
        value = generation(row.get("generation"))
        if not FIRST_TARGET <= target < AFTER_TARGET:
            continue
        if target[14:19] not in ("00:00", "30:00"):
            raise ValueError("The actual generation resolution changed; half-hour alignment needs review.")
        previous = halfhours.get(target)
        if previous is not None and published == previous[0] and value != previous[1]:
            raise ValueError("Elexon returned conflicting actual records.")
        if previous is None or published > previous[0]:
            halfhours[target] = (published, value)
    if not revisions or not halfhours:
        raise ValueError("Elexon returned no usable wind observations in the January delivery window.")
    hourly, missing = {}, []
    start = datetime(2026, 1, 2, tzinfo=timezone.utc)
    for hour in range(744):
        first = (start + timedelta(hours=hour)).isoformat(timespec="seconds").replace("+00:00", "Z")
        second = (start + timedelta(hours=hour, minutes=30)).isoformat(timespec="seconds").replace("+00:00", "Z")
        if first in halfhours and second in halfhours:
            hourly[first] = (halfhours[first][1] + halfhours[second][1]) / 2
        else:
            missing.append(first)
    indexed = {}
    for (target, published), value in sorted(revisions.items()):
        indexed.setdefault(target[:10], []).append(MappingProxyType({"target_time": target, "publish_time": published, "generation": value}))
    digest = hashlib.sha256(json.dumps({"forecasts": [(t, p, v) for (t, p), v in sorted(revisions.items())], "actuals": [(t, p, v) for t, (p, v) in sorted(halfhours.items())]}, separators=(",", ":")).encode()).hexdigest()
    source = dict(snapshot_metadata or {})
    source.update({
        "retrieved_at": retrieved_at, "source_urls": MappingProxyType(dict(SOURCE_URLS)),
        "forecast_records": len(revisions), "halfhour_actual_records": len(halfhours),
        "hourly_actual_records": len(hourly), "incomplete_actual_hours": tuple(missing),
        "dataset_sha256": digest,
        "notes": (
            "Elexon API data for January 2026 decisions; next-day delivery runs from 2 January through 1 February.",
            "GB metered wind coverage does not include every UK wind installation.",
            "Hourly actual MW requires two complete half-hour observations; missing values remain unavailable.",
            "Forecast selection uses publishTime as an availability proxy, with the chosen London cutoff.",
            "09:00 Europe/London is a configurable demonstration assumption, not a universal market deadline.",
            "Actuals and accuracy are available immediately. MWh describes wind forecast mismatch, not procurement volume or financial loss.",
        ),
    })
    return Dataset(MappingProxyType({day: tuple(rows) for day, rows in indexed.items()}), MappingProxyType(hourly), MappingProxyType(source), digest, origin)


def load_snapshot(data_dir: Path | None = None) -> Dataset:
    directory = data_dir or ROOT / "data"
    metadata = json.loads((directory / "metadata.json").read_text())
    path = directory / "wind.sqlite"
    if not path.is_file():
        raise FileNotFoundError("The bundled historical fallback is unavailable.")
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        forecasts = [{"startTime": row["target_time"], "publishTime": row["publish_time"], "generation": row["generation"]} for row in connection.execute("SELECT * FROM forecasts")]
        actuals = [{"startTime": row["target_time"], "publishTime": row["publish_time"], "generation": row["generation"], "fuelType": "WIND"} for row in connection.execute("SELECT * FROM actual_halfhour")]
    finally:
        connection.close()
    return normalize(forecasts, actuals, metadata["retrieved_at"], origin="snapshot_fallback", snapshot_metadata=metadata)


def fetch_json(url: str, timeout: float = 18):
    if url not in (FORECAST_URL, ACTUAL_URL):
        raise ValueError("Only the two fixed Elexon dataset requests are allowed.")
    for attempt in range(2):
        try:
            request = urllib.request.Request(url, headers={"Accept": "application/json", "Cache-Control": "no-cache", "User-Agent": "WindDecisionReplay/2.0"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
            return json.loads(body)
        except (HTTPError, URLError, TimeoutError) as error:
            transient = not isinstance(error, HTTPError) or error.code in (429, 500, 502, 503, 504)
            if not transient or attempt == 1:
                raise
            time.sleep(0.25)


class ElexonProvider:
    """Fetch once per instance/TTL; concurrent readers share one immutable epoch."""
    def __init__(self, *, loader: Callable | None = None, fallback_loader: Callable | None = None, clock: Callable | None = None, ttl: int = 300):
        self.loader = loader or self._upstream
        self.fallback_loader = fallback_loader or load_snapshot
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.ttl = ttl
        self._condition = threading.Condition()
        self._dataset = None
        self._fetched_at = None
        self._last_attempt = None
        self._last_error = None
        self._refreshing = False

    def _upstream(self):
        pool = ThreadPoolExecutor(max_workers=2)
        deadline = time.monotonic() + FETCH_DEADLINE_SECONDS
        forecast_future = pool.submit(fetch_json, FORECAST_URL)
        actual_future = pool.submit(fetch_json, ACTUAL_URL)
        try:
            forecasts = forecast_future.result(timeout=max(0.001, deadline - time.monotonic()))
            actuals = actual_future.result(timeout=max(0.001, deadline - time.monotonic()))
        except FutureTimeout as exc:
            raise TimeoutError("The Elexon request exceeded its overall deadline.") from exc
        finally:
            # Do not hold the request open past its deadline. A timed-out worker
            # cannot mutate the cache; only the completed pair is normalized.
            pool.shutdown(wait=False, cancel_futures=True)
        return normalize(forecasts, actuals, iso(self.clock()))

    def peek_status(self):
        """Report current state without starting any network request."""
        with self._condition:
            return self._result("cached_api").status if self._dataset is not None else None

    def _result(self, mode: str) -> DatasetResult:
        now = self.clock()
        fallback = self._dataset.origin == "snapshot_fallback"
        expired = self._fetched_at is None or (now - self._fetched_at).total_seconds() >= self.ttl
        stale = fallback or expired or self._last_error is not None
        if fallback:
            mode = "snapshot_fallback"
            message = "Elexon is unavailable. Showing the bundled historical fallback; Refresh will retry the API."
        elif self._last_error:
            message = "Elexon refresh failed. The last successful API data is still visible; its retrieval time has not changed."
        elif mode == "live_api":
            message = "Fetched January wind forecasts and actuals from the Elexon API."
        else:
            message = "Using recently fetched Elexon API data. Refresh requests both datasets again."
        status = {"mode": mode, "retrieved_at": self._dataset.metadata["retrieved_at"], "last_refresh_attempt": iso(self._last_attempt) if self._last_attempt else None, "cache_expires_at": iso(self._fetched_at + timedelta(seconds=self.ttl)) if self._fetched_at else None, "stale": stale, "message": message, "refresh_error": self._last_error, "source_urls": dict(SOURCE_URLS), "data_epoch": self._dataset.epoch}
        return DatasetResult(self._dataset, status)

    def get_dataset(self, force=False) -> DatasetResult:
        with self._condition:
            if self._refreshing:
                while self._refreshing:
                    self._condition.wait()
                if self._dataset is None:
                    raise DataUnavailable(self._last_error or "Elexon data is unavailable.")
                return self._result("cached_api")
            now = self.clock()
            if not force and self._dataset is not None:
                if self._fetched_at and (now - self._fetched_at).total_seconds() < self.ttl:
                    return self._result("cached_api")
                # Avoid repeated automatic failures across legacy endpoints. Manual Refresh always retries.
                if self._last_error and self._last_attempt and (now - self._last_attempt).total_seconds() < 30:
                    return self._result("cached_api")
            self._refreshing = True
            self._last_attempt = now
        candidate = None
        error = None
        try:
            candidate = self.loader()
            if not isinstance(candidate, Dataset) or candidate.origin != "live_api":
                raise ValueError("The upstream loader did not provide a valid Elexon dataset.")
        except Exception as exc:
            error = f"Elexon API request failed: {type(exc).__name__}: {exc}"
            if self._dataset is None:
                try:
                    candidate = self.fallback_loader()
                except Exception:
                    candidate = None
        with self._condition:
            if error is None:
                self._dataset = candidate
                self._fetched_at = self.clock()
                self._last_error = None
            else:
                self._last_error = error
                if self._dataset is None and candidate is not None:
                    self._dataset = candidate
            self._refreshing = False
            self._condition.notify_all()
            if self._dataset is None:
                raise DataUnavailable(error or "Elexon data is unavailable.")
            return self._result("live_api" if error is None else "cached_api")
