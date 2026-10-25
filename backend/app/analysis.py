"""Pure, auditable forecast selection and error calculations."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import math
import re
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def decision_timestamp(decision_date: str, cutoff: str) -> tuple[date, datetime]:
    try:
        day = date.fromisoformat(decision_date)
    except (TypeError, ValueError) as exc:
        raise ValueError("Choose a valid January 2026 decision date (YYYY-MM-DD).") from exc
    if day.year != 2026 or day.month != 1:
        raise ValueError("Decision dates must be between 1 and 31 January 2026.")
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", cutoff or ""):
        raise ValueError("Cutoff must be a 24-hour time in HH:MM format.")
    clock = time.fromisoformat(cutoff)
    return day, datetime.combine(day, clock, LONDON).astimezone(timezone.utc)


def parse_publication(value: str | None, cutoff: datetime) -> datetime:
    if value is None:
        return cutoff
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timezone required")
        parsed = parsed.astimezone(timezone.utc)
    except (TypeError, ValueError) as exc:
        raise ValueError("Publication must be an ISO timestamp with a timezone.") from exc
    if parsed > cutoff:
        raise ValueError("A publication checkpoint cannot be later than the decision cutoff.")
    return parsed


def error_metrics(errors: list[float]) -> dict:
    if not errors:
        return {"mae": None, "rmse": None, "bias": None, "positive_error_mwh": None, "net_error_mwh": None, "n": 0}
    count = len(errors)
    return {
        "mae": sum(abs(error) for error in errors) / count,
        "rmse": math.sqrt(sum(error * error for error in errors) / count),
        "bias": sum(errors) / count,
        # Each point is one complete hour: MW multiplied by one hour gives MWh.
        "positive_error_mwh": sum(max(error, 0) for error in errors),
        "net_error_mwh": sum(errors),
        "n": count,
    }


def align_actuals(halfhours: dict[str, float], targets: list[str]) -> dict[str, float]:
    result = {}
    for target in targets:
        start = datetime.fromisoformat(target.replace("Z", "+00:00"))
        second = iso(start + timedelta(minutes=30))
        if target in halfhours and second in halfhours:
            result[target] = (halfhours[target] + halfhours[second]) / 2
    return result


def assemble_replay(decision_date: str, cutoff: str, forecast_rows: list[dict], actuals: dict[str, float], publication: str | None = None) -> dict:
    day, decision_at = decision_timestamp(decision_date, cutoff)
    checkpoint = parse_publication(publication, decision_at)
    delivery = day + timedelta(days=1)
    delivery_at = datetime.combine(delivery, time.min, LONDON).astimezone(timezone.utc)
    targets = [iso(delivery_at + timedelta(hours=hour)) for hour in range(24)]
    target_set = set(targets)
    # Native SQLite columns and API-source columns are both accepted by this pure function.
    eligible = []
    seen = {}
    for raw in forecast_rows:
        target = raw.get("target_time", raw.get("startTime"))
        published = raw.get("publish_time", raw.get("publishTime"))
        if target not in target_set:
            continue
        published_at = datetime.fromisoformat(published.replace("Z", "+00:00"))
        if published_at > decision_at:
            continue
        key = (target, iso(published_at))
        value = float(raw["generation"])
        if key in seen and seen[key] != value:
            raise ValueError("Conflicting forecast records found for the same target and publication.")
        seen[key] = value
    for (target, published), value in seen.items():
        eligible.append({"target_time": target, "publish_time": published, "generation": value})

    by_target = {target: [] for target in targets}
    publication_counts = {}
    for row in eligible:
        publication_counts[row["publish_time"]] = publication_counts.get(row["publish_time"], 0) + 1
        if row["publish_time"] <= iso(checkpoint):
            by_target[row["target_time"]].append(row)
    selected_publications = [published for published in publication_counts if published <= iso(checkpoint)]
    selected_publication = max(selected_publications, default=None)
    publications = [
        {"publish_time": published, "label": datetime.fromisoformat(published.replace("Z", "+00:00")).astimezone(LONDON).strftime("%d %b · %H:%M"), "hours_covered": publication_counts[published], "selected": published == selected_publication}
        for published in sorted(publication_counts)
    ]
    series = []
    for hour, target in enumerate(targets):
        revisions = sorted(by_target[target], key=lambda row: row["publish_time"], reverse=True)
        latest = revisions[0] if revisions else None
        previous = revisions[1] if len(revisions) > 1 else None
        actual = actuals.get(target)
        latest_value = latest["generation"] if latest else None
        series.append({
            "start_time": target, "hour": hour,
            "latest": latest_value, "previous": previous["generation"] if previous else None,
            "actual": actual,
            "latest_publish_time": latest["publish_time"] if latest else None,
            "previous_publish_time": previous["publish_time"] if previous else None,
            "error": latest_value - actual if latest_value is not None and actual is not None else None,
        })
    matched = [row for row in series if row["latest"] is not None and row["actual"] is not None]
    paired = [row for row in matched if row["previous"] is not None]
    # Headline accuracy uses all matches; revision comparisons use identical target hours.
    latest_metrics = error_metrics([row["latest"] - row["actual"] for row in matched])
    paired_latest_metrics = error_metrics([row["latest"] - row["actual"] for row in paired])
    previous_metrics = error_metrics([row["previous"] - row["actual"] for row in paired])
    previous_mae = previous_metrics["mae"]
    change = ((paired_latest_metrics["mae"] / previous_mae) - 1) * 100 if previous_mae is not None and previous_mae > 0 else None
    improved = sum(abs(row["latest"] - row["actual"]) < abs(row["previous"] - row["actual"]) for row in paired)
    worsened = sum(abs(row["latest"] - row["actual"]) > abs(row["previous"] - row["actual"]) for row in paired)
    if change is not None and change > 0:
        insight = {"title": "Newer did not mean more accurate", "body": f"The latest eligible update increased mean absolute error by {change:.1f}% across {len(paired)} identical delivery hours. It improved {improved} hours and worsened {worsened}. This is a retrospective result, not a rule for choosing an older forecast.", "tone": "warning"}
    elif change is not None and change < 0:
        insight = {"title": "This update improved accuracy", "body": f"The latest eligible update reduced mean absolute error by {abs(change):.1f}% across {len(paired)} identical delivery hours. It improved {improved} hours and worsened {worsened}. This is a retrospective comparison.", "tone": "positive"}
    elif matched:
        insight = {"title": "A traceable view of the decision", "body": "Every displayed forecast was published by the selected checkpoint. Actuals are retrospective and are used only to evaluate the forecast.", "tone": "neutral"}
    else:
        insight = {"title": "No complete comparison is available", "body": "No eligible forecast and complete actual hour overlap at this checkpoint. Missing observations are kept missing, never replaced with zero.", "tone": "neutral"}
    return {
        "decision": {"date": day.isoformat(), "cutoff": cutoff, "at": iso(decision_at), "delivery_date": delivery.isoformat(), "timezone": "Europe/London", "as_of": iso(checkpoint)},
        "coverage": {"expected_hours": len(targets), "forecast_hours": sum(row["latest"] is not None for row in series), "actual_hours": sum(row["actual"] is not None for row in series), "matched_hours": len(matched), "paired_hours": len(paired)},
        "publications": publications,
        "series": series,
        "metrics": {"latest": latest_metrics, "previous": previous_metrics, "mae_change_pct": change, "improved_hours": improved, "worsened_hours": worsened, "comparison_hours": len(paired), "comparison": {"latest_mae": paired_latest_metrics["mae"], "previous_mae": previous_mae, "n": len(paired)}},
        "insight": insight,
    }
