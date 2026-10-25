"""January analysis, calculated from one immutable Elexon data epoch."""
from __future__ import annotations

from datetime import timedelta
import os
from pathlib import Path

from .analysis import assemble_replay, decision_timestamp, error_metrics, parse_publication
from .elexon import Dataset, ElexonProvider, load_snapshot

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("WIND_DATA_DIR", ROOT / "data"))
provider = ElexonProvider(fallback_loader=lambda: load_snapshot(DATA_DIR))


def provenance(dataset: Dataset) -> dict:
    metadata = dataset.metadata
    return {
        "source": "Elexon Insights · WINDFOR + FUELHH" + (" · bundled fallback" if dataset.origin == "snapshot_fallback" else " · API data"),
        "description": "GB metered wind generation. This pilot covers wind forecast mismatch, not customer demand, procurement volume or financial loss.",
        "retrieved_at": metadata["retrieved_at"],
        "alignment": "Hourly forecasts are compared with the average of two complete half-hour actual MW observations. Each complete comparison represents one hour.",
        "availability_note": "Forecasts are eligible only when publishTime is at or before the decision checkpoint. Publication time is an availability proxy; recipient-specific network latency is unknown.",
        "source_urls": dict(metadata["source_urls"]),
        "snapshot_sha256": metadata.get("sqlite_sha256") if dataset.origin == "snapshot_fallback" else None,
        "dataset_sha256": dataset.epoch,
        "source_mode": dataset.origin,
        "units": {"generation": "MW", "mae": "MW", "rmse": "MW", "bias": "MW", "positive_error_mwh": "MWh", "net_error_mwh": "MWh"},
        "error_definition": "forecast minus actual; positive means wind was overforecast",
        "comparison_cohort": "Latest headline metrics use every complete latest/actual match. Revision changes use only hours with both forecasts and actuals; their paired MAEs and sample size are provided separately.",
    }


def _replay(dataset: Dataset, decision_date: str, cutoff: str = "09:00", publication: str | None = None) -> dict:
    day, _ = decision_timestamp(decision_date, cutoff)
    delivery = day + timedelta(days=1)
    forecasts = dataset.forecasts_by_day.get(delivery.isoformat(), ())
    result = assemble_replay(decision_date, cutoff, forecasts, dataset.actuals, publication)
    result["provenance"] = provenance(dataset)
    return result


def _accuracy(dataset: Dataset, cutoff: str = "09:00") -> dict:
    decision_timestamp("2026-01-01", cutoff)
    days = []
    errors = []
    previous_errors = []
    revision_improved = 0
    revision_compared = 0
    for day_number in range(1, 32):
        result = _replay(dataset, f"2026-01-{day_number:02d}", cutoff)
        latest = result["metrics"]["latest"]
        previous = result["metrics"]["previous"]
        paired = [row for row in result["series"] if row["latest"] is not None and row["previous"] is not None and row["actual"] is not None]
        cohort = [row for row in result["series"] if row["latest"] is not None and row["actual"] is not None]
        errors.extend(row["latest"] - row["actual"] for row in cohort)
        previous_errors.extend(row["previous"] - row["actual"] for row in paired)
        if paired:
            revision_compared += 1
            revision_improved += result["metrics"]["comparison"]["latest_mae"] < previous["mae"]
        days.append({"decision_date": result["decision"]["date"], "delivery_date": result["decision"]["delivery_date"], **latest, "matched_hours": result["coverage"]["matched_hours"], "paired_hours": result["coverage"]["paired_hours"], "comparison_latest_mae": result["metrics"]["comparison"]["latest_mae"], "previous_mae": previous["mae"], "mae_change_pct": result["metrics"]["mae_change_pct"]})
    aggregate = {**error_metrics(errors), "total_expected_hours": 31 * 24, "coverage_pct": len(errors) / (31 * 24) * 100, "revision_improved_days": revision_improved, "revision_compared_days": revision_compared, "previous": error_metrics(previous_errors)}
    positive_bias = aggregate["bias"] is not None and aggregate["bias"] >= 0
    insights = [
        {"title": "A fair test of every update", "body": f"The latest eligible revision had lower daily MAE on {revision_improved} of {revision_compared} comparable January decision days. Every revision comparison uses identical target hours.", "tone": "neutral"},
        {"title": "Wind overforecast" if positive_bias else "Wind underforecast", "body": f"Mean signed forecast error was {aggregate['bias']:,.0f} MW across {len(errors)} complete hourly comparisons. This describes wind forecast mismatch, not a purchasing recommendation." if errors else "No complete comparisons are available at this cutoff.", "tone": "neutral"},
    ]
    return {"cutoff": cutoff, "days": days, "aggregate": aggregate, "insights": insights, "provenance": provenance(dataset)}


def _metadata(dataset: Dataset, month: dict | None = None) -> dict:
    stored = dataset.metadata
    month = month or _accuracy(dataset, "09:00")
    covered_days = [day for day in month["days"] if day["matched_hours"]]
    worst = max(covered_days, key=lambda item: item["mae"], default=None)
    return {
        "decision_dates": [f"2026-01-{day:02d}" for day in range(1, 32)],
        "min_date": "2026-01-01", "max_date": "2026-01-31",
        "default_date": "2026-01-15", "default_cutoff": "09:00",
        "retrieved_at": stored["retrieved_at"], "source_urls": dict(stored["source_urls"]),
        "coverage": {"expected_hours": 31 * 24, "actual_hours": stored["hourly_actual_records"], "matched_hours": month["aggregate"]["n"], "coverage_pct": month["aggregate"]["coverage_pct"], "forecast_records": stored["forecast_records"], "missing_actual_hours": list(stored["incomplete_actual_hours"])},
        "notes": list(stored["notes"]),
        "case_studies": [
            {"decision_date": "2026-01-15", "title": "When newer was less accurate", "description": "Compare the 15 January forecasts with next-day actuals, including MAE and overforecast energy."},
            *([{"decision_date": worst["decision_date"], "title": "The largest daily error", "description": "Inspect the January decision day with the greatest latest-forecast MAE at the selected cutoff."}] if worst else []),
        ],
        "snapshot_sha256": stored.get("sqlite_sha256") if dataset.origin == "snapshot_fallback" else None,
        "dataset_sha256": dataset.epoch,
    }


def validate_selection(decision_date: str, cutoff: str, publication: str | None = None):
    _, at = decision_timestamp(decision_date, cutoff)
    parse_publication(publication, at)


def dashboard(decision_date="2026-01-15", cutoff="09:00", publication=None, force=False):
    validate_selection(decision_date, cutoff, publication)
    result = provider.get_dataset(force=force)
    day = _replay(result.dataset, decision_date, cutoff, publication)
    month = _accuracy(result.dataset, cutoff)
    return {"replay": day, "accuracy": month, "metadata": _metadata(result.dataset, month), "data_status": result.status}


def replay(decision_date: str, cutoff="09:00", publication=None):
    validate_selection(decision_date, cutoff, publication)
    result = provider.get_dataset()
    value = _replay(result.dataset, decision_date, cutoff, publication)
    value["data_status"] = result.status
    return value


def accuracy(cutoff="09:00"):
    decision_timestamp("2026-01-01", cutoff)
    result = provider.get_dataset()
    value = _accuracy(result.dataset, cutoff)
    value["data_status"] = result.status
    return value


def metadata():
    result = provider.get_dataset()
    value = _metadata(result.dataset)
    value["data_status"] = result.status
    return value
