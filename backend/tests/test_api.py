import csv
import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_replay_and_snapshot_provenance_are_available():
    response = client.get("/api/replay", params={"decision_date": "2026-01-15", "cutoff": "09:00"})
    assert response.status_code == 200
    data = response.json()
    assert data["metrics"]["latest"]["mae"] == 782.75
    assert data["provenance"]["snapshot_sha256"]
    assert "availability proxy" in data["provenance"]["availability_note"]
    assert client.get("/health").json()["read_only"] is True


def test_api_rejects_out_of_scope_decisions_and_future_publications():
    assert client.get("/api/replay", params={"decision_date": "2026-02-01"}).status_code == 422
    assert client.get("/api/replay", params={"publication": "2026-01-15T10:00:00Z"}).status_code == 422
    assert client.get("/api/accuracy", params={"cutoff": "abc"}).status_code == 422


def test_csv_matches_selected_checkpoint_and_has_complete_source_timestamps():
    response = client.get("/api/replay.csv", params={"decision_date": "2026-01-15", "cutoff": "09:00", "publication": "2026-01-15T04:30:00Z"})
    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 24
    assert rows[0]["latest_publication_utc"] == "2026-01-15T04:30:00Z"
    assert float(rows[0]["latest_forecast_mw"]) == 7848
    assert rows[0]["checkpoint_utc"] == "2026-01-15T04:30:00Z"


def test_month_and_metadata_cover_all_january_decision_dates():
    month = client.get("/api/accuracy").json()
    assert len(month["days"]) == 31
    assert month["days"][-1]["delivery_date"] == "2026-02-01"
    assert month["aggregate"]["coverage_pct"] == 100
    assert client.get("/api/metadata").json()["default_date"] == "2026-01-15"
