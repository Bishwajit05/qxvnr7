"""Public dashboard/refresh contract, with only the upstream HTTP boundary replaced."""
import json
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import threading
import time
from urllib.error import URLError
import urllib.request
import pytest

from fastapi.testclient import TestClient

from app.main import app
from app import service
from app.elexon import ElexonProvider, normalize
from app import elexon


def source_rows(offset=0):
    forecasts = []
    actuals = []
    for hour, base in [(0, 100), (1, 200)]:
        target = f"2026-01-16T{hour:02d}:00:00Z"
        for published, value in [("04:30", base + 20), ("07:30", base), ("09:30", 9999)]:
            forecasts.append({"startTime": target, "publishTime": f"2026-01-15T{published}:00Z", "generation": value + offset})
        for minute, value in [(0, base - 20), (30, base)]:
            actuals.append({"startTime": f"2026-01-16T{hour:02d}:{minute:02d}:00Z", "publishTime": "2026-01-17T00:00:00Z", "fuelType": "WIND", "generation": value})
    return forecasts, actuals


class Response:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.rows).encode()


def test_initial_dashboard_fetches_real_provider_then_uses_its_cache(monkeypatch):
    calls = []
    forecasts, actuals = source_rows()

    def upstream(request, timeout):
        calls.append(request.full_url)
        return Response(forecasts if "/WINDFOR/" in request.full_url else actuals)

    monkeypatch.setattr(urllib.request, "urlopen", upstream)
    client = TestClient(app)
    first = client.get("/api/dashboard", params={"decision_date": "2026-01-15", "cutoff": "09:00"})
    assert first.status_code == 200
    payload = first.json()
    assert payload["data_status"]["mode"] == "live_api"
    assert len(calls) == 2
    assert payload["replay"]["metrics"]["latest"]["mae"] == 10
    assert payload["accuracy"]["aggregate"]["mae"] == 10
    assert payload["metadata"]["retrieved_at"] == payload["data_status"]["retrieved_at"]
    second = client.get("/api/dashboard", params={"decision_date": "2026-01-15", "cutoff": "09:00"})
    assert second.json()["data_status"]["mode"] == "cached_api"
    assert len(calls) == 2


def test_refresh_bypasses_ttl_and_updates_every_view_atomically(monkeypatch):
    calls = []
    state = {"offset": 0}

    def upstream(request, timeout):
        calls.append(request.full_url)
        forecasts, actuals = source_rows(state["offset"])
        return Response(forecasts if "/WINDFOR/" in request.full_url else actuals)

    monkeypatch.setattr(urllib.request, "urlopen", upstream)
    client = TestClient(app)
    before = client.get("/api/dashboard").json()
    state["offset"] = 30
    response = client.post("/api/refresh")
    assert response.status_code == 200
    after = response.json()
    assert len(calls) == 4
    assert after["data_status"]["mode"] == "live_api"
    assert after["data_status"]["retrieved_at"] != before["data_status"]["retrieved_at"]
    assert after["replay"]["metrics"]["latest"]["mae"] == 40
    assert after["accuracy"]["aggregate"]["mae"] == 40
    assert after["metadata"]["retrieved_at"] == after["replay"]["provenance"]["retrieved_at"] == after["accuracy"]["provenance"]["retrieved_at"] == after["data_status"]["retrieved_at"]
    assert after["replay"]["provenance"]["dataset_sha256"] == after["accuracy"]["provenance"]["dataset_sha256"] == after["data_status"]["data_epoch"]
    assert after["replay"]["provenance"]["snapshot_sha256"] is None
    assert response.headers["cache-control"].startswith("no-store")


def test_ttl_expiry_fetches_again_without_manual_refresh(monkeypatch):
    now = [datetime(2026, 10, 25, tzinfo=timezone.utc)]
    calls = []
    forecasts, actuals = source_rows()

    def upstream(request, timeout):
        calls.append(request.full_url)
        return Response(forecasts if "/WINDFOR/" in request.full_url else actuals)

    monkeypatch.setattr(urllib.request, "urlopen", upstream)
    monkeypatch.setattr(service, "provider", ElexonProvider(clock=lambda: now[0]))
    client = TestClient(app)
    first = client.get("/api/dashboard").json()
    now[0] += timedelta(seconds=299)
    assert client.get("/api/dashboard").json()["data_status"]["mode"] == "cached_api"
    assert len(calls) == 2
    now[0] += timedelta(seconds=2)
    third = client.get("/api/dashboard").json()
    assert third["data_status"]["mode"] == "live_api"
    assert len(calls) == 4
    assert third["data_status"]["retrieved_at"] != first["data_status"]["retrieved_at"]


def test_failed_refresh_preserves_last_good_epoch_and_retrieval_time(monkeypatch):
    forecasts, actuals = source_rows()

    def upstream(request, timeout):
        return Response(forecasts if "/WINDFOR/" in request.full_url else actuals)

    monkeypatch.setattr(urllib.request, "urlopen", upstream)
    client = TestClient(app)
    first = client.get("/api/dashboard").json()

    def failure(request, timeout):
        raise URLError("upstream temporarily unavailable")

    monkeypatch.setattr(urllib.request, "urlopen", failure)
    after = client.post("/api/refresh").json()
    assert after["data_status"]["mode"] == "cached_api"
    assert after["data_status"]["stale"] is True
    assert after["data_status"]["refresh_error"]
    assert after["data_status"]["retrieved_at"] == first["data_status"]["retrieved_at"]
    assert after["data_status"]["cache_expires_at"] == first["data_status"]["cache_expires_at"]
    assert after["data_status"]["data_epoch"] == first["data_status"]["data_epoch"]
    assert after["replay"]["metrics"] == first["replay"]["metrics"]


def test_initial_failure_labels_bundled_fallback_and_keeps_original_retrieval(monkeypatch):
    def failure(request, timeout):
        raise URLError("Elexon unavailable")

    monkeypatch.setattr(urllib.request, "urlopen", failure)
    result = TestClient(app).get("/api/dashboard").json()
    status = result["data_status"]
    assert status["mode"] == "snapshot_fallback"
    assert status["stale"] is True and status["refresh_error"]
    assert status["cache_expires_at"] is None
    assert "bundled" in status["message"]
    assert status["retrieved_at"] == result["metadata"]["retrieved_at"]
    assert status["retrieved_at"] != status["last_refresh_attempt"]
    assert result["replay"]["metrics"]["latest"]["mae"] == 782.75


def test_no_upstream_and_no_fallback_returns_service_unavailable(monkeypatch):
    def failure(*args):
        raise RuntimeError("Unavailable")

    monkeypatch.setattr(service, "provider", ElexonProvider(loader=failure, fallback_loader=failure))
    response = TestClient(app).post("/api/refresh")
    assert response.status_code == 503
    assert "Elexon" in response.json()["detail"]


@pytest.mark.parametrize("query", [{"decision_date": "2026-02-01"}, {"cutoff": "25:00"}, {"publication": "2026-01-15T10:00:00Z"}])
def test_invalid_request_is_rejected_before_any_upstream_network(monkeypatch, query):
    calls = []
    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: calls.append(args))
    client = TestClient(app)
    assert client.get("/api/dashboard", params=query).status_code == 422
    assert client.post("/api/refresh", params=query).status_code == 422
    assert calls == []


def test_partial_actuals_remain_missing_and_latest_actual_revision_wins(monkeypatch):
    forecasts, actuals = source_rows()
    actuals = actuals[:3]  # No 01:30 actual: the whole second hour stays missing.
    actuals[0]["generation"] = 0
    actuals[1]["generation"] = 0
    actuals.append({**actuals[0], "publishTime": "2026-01-16T00:30:00Z", "generation": 5000})

    def upstream(request, timeout):
        return Response(forecasts if "/WINDFOR/" in request.full_url else actuals)

    monkeypatch.setattr(urllib.request, "urlopen", upstream)
    result = TestClient(app).get("/api/dashboard").json()
    assert result["data_status"]["mode"] == "live_api"
    assert result["replay"]["coverage"]["forecast_hours"] == 2
    assert result["replay"]["coverage"]["actual_hours"] == 1
    assert result["replay"]["series"][0]["actual"] == 0
    assert result["replay"]["series"][1]["actual"] is None
    assert result["accuracy"]["aggregate"]["n"] == 1


@pytest.mark.parametrize("broken", [[], {"data": []}, [{"startTime": "bad"}], [{"startTime": "2026-01-16T00:00:00Z", "publishTime": "2026-01-15T07:30:00Z", "generation": None}]])
def test_malformed_upstream_data_is_never_labelled_live(monkeypatch, broken):
    _, actuals = source_rows()
    monkeypatch.setattr(urllib.request, "urlopen", lambda request, timeout: Response(broken if "/WINDFOR/" in request.full_url else actuals))
    result = TestClient(app).get("/api/dashboard").json()
    assert result["data_status"]["mode"] == "snapshot_fallback"
    assert result["data_status"]["refresh_error"]


def test_concurrent_forced_requests_share_one_inflight_fetch():
    entered, release = threading.Event(), threading.Event()
    calls = []
    forecasts, actuals = source_rows()

    def slow_upstream():
        calls.append("fetch")
        entered.set()
        assert release.wait(2)
        return normalize(forecasts, actuals, "2026-10-25T10:00:00Z")

    provider = ElexonProvider(loader=slow_upstream)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(provider.get_dataset, True)
        assert entered.wait(1)
        second = pool.submit(provider.get_dataset, True)
        time.sleep(0.05)
        release.set()
        first, second = first.result(timeout=2), second.result(timeout=2)
    assert calls == ["fetch"]
    assert first.dataset is second.dataset
    assert first.status["mode"] == "live_api"
    assert second.status["mode"] == "cached_api"


def test_health_reports_provider_without_triggering_upstream_or_requiring_fallback(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: calls.append(args))
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["data_provider"] == "elexon_api"
    assert response.json()["upstream_checked"] is False
    assert response.json()["fallback_available"] is False
    assert calls == []


def test_overall_upstream_deadline_returns_explicit_fallback(monkeypatch):
    forecasts, actuals = source_rows()
    release = threading.Event()

    def slow(request, timeout):
        release.wait(1)
        return Response(forecasts if "/WINDFOR/" in request.full_url else actuals)

    monkeypatch.setattr(urllib.request, "urlopen", slow)
    monkeypatch.setattr(elexon, "FETCH_DEADLINE_SECONDS", 0.02, raising=False)
    started = time.monotonic()
    try:
        result = TestClient(app).get("/api/dashboard").json()
        assert result["data_status"]["mode"] == "snapshot_fallback"
        assert "deadline" in result["data_status"]["refresh_error"].lower()
        assert time.monotonic() - started < 0.5
    finally:
        release.set()
