import math

import pytest

from app.analysis import align_actuals, assemble_replay, error_metrics
from app import service

TARGET = "2026-01-16T00:00:00Z"


def forecast(value, publication, target=TARGET):
    return {"startTime": target, "publishTime": f"2026-01-15T{publication}:00Z", "generation": value}


def test_future_publication_is_excluded_and_exact_cutoff_is_included():
    rows = [forecast(100, "07:30"), forecast(120, "09:00"), forecast(9000, "09:01")]
    result = assemble_replay("2026-01-15", "09:00", rows, {TARGET: 110})
    assert result["series"][0]["latest"] == 120
    assert result["series"][0]["previous"] == 100
    assert len(result["publications"]) == 2
    assert result["metrics"]["latest"]["mae"] == 10


def test_checkpoint_rewinds_selection_without_changing_decision_time():
    rows = [forecast(100, "04:30"), forecast(120, "07:30")]
    result = assemble_replay("2026-01-15", "09:00", rows, {TARGET: 110}, "2026-01-15T04:30:00Z")
    assert result["series"][0]["latest"] == 100
    assert result["series"][0]["previous"] is None
    assert result["decision"]["at"] == "2026-01-15T09:00:00Z"
    assert result["decision"]["as_of"] == "2026-01-15T04:30:00Z"
    assert sum(item["selected"] for item in result["publications"]) == 1


def test_latest_and_previous_are_selected_independently_per_target():
    second = "2026-01-16T01:00:00Z"
    rows = [forecast(10, "04:30"), forecast(20, "07:30"), forecast(30, "04:30", second)]
    result = assemble_replay("2026-01-15", "09:00", rows, {TARGET: 0, second: 0})
    assert result["series"][0]["previous"] == 10
    assert result["series"][1]["latest"] == 30
    assert result["series"][1]["previous"] is None


def test_zero_is_observed_but_missing_is_not_zero():
    result = assemble_replay("2026-01-15", "09:00", [forecast(0, "07:30")], {TARGET: 0})
    assert result["coverage"]["matched_hours"] == 1
    assert result["metrics"]["latest"]["mae"] == 0
    assert result["series"][1]["actual"] is None
    assert result["series"][1]["latest"] is None


def test_hourly_actual_needs_both_half_hours():
    second = "2026-01-16T01:00:00Z"
    actuals = {TARGET: 10, "2026-01-16T00:30:00Z": 30, second: 100}
    assert align_actuals(actuals, [TARGET, second]) == {TARGET: 20}


def test_hand_calculated_metrics_preserve_sign_and_units():
    metrics = error_metrics([10, -20, 0])
    assert metrics["mae"] == 10
    assert metrics["rmse"] == pytest.approx(math.sqrt(500 / 3))
    assert metrics["bias"] == pytest.approx(-10 / 3)
    assert metrics["positive_error_mwh"] == 10
    assert metrics["net_error_mwh"] == -10
    assert error_metrics([])["mae"] is None


def test_revision_change_uses_common_cohort_not_different_headline_samples():
    second = "2026-01-16T01:00:00Z"
    rows = [forecast(10, "04:30"), forecast(50, "07:30"), forecast(1000, "07:30", second)]
    result = assemble_replay("2026-01-15", "09:00", rows, {TARGET: 0, second: 0})
    assert result["metrics"]["latest"]["mae"] == 525
    assert result["metrics"]["comparison"] == {"latest_mae": 50, "previous_mae": 10, "n": 1}
    assert result["metrics"]["mae_change_pct"] == 400


def test_identical_duplicate_does_not_create_a_previous_revision():
    row = forecast(10, "07:30")
    result = assemble_replay("2026-01-15", "09:00", [row, row], {TARGET: 20})
    assert result["series"][0]["previous"] is None
    assert result["coverage"]["paired_hours"] == 0


def test_january_last_decision_delivers_on_february_first():
    result = assemble_replay("2026-01-31", "09:00", [], {})
    assert result["decision"]["delivery_date"] == "2026-02-01"
    assert result["series"][0]["start_time"] == "2026-02-01T00:00:00Z"
    assert result["series"][-1]["start_time"] == "2026-02-01T23:00:00Z"


@pytest.mark.parametrize("day,cutoff,publication", [("2026-02-01", "09:00", None), ("2026-01-15", "25:00", None), ("2026-01-15", "09:00", "2026-01-15T09:01:00Z"), ("2026-01-15", "09:00", "2026-01-15T07:30:00")])
def test_invalid_decisions_and_future_or_naive_checkpoints_are_rejected(day, cutoff, publication):
    with pytest.raises(ValueError):
        assemble_replay(day, cutoff, [], {}, publication)


def test_verified_historical_case_and_complete_snapshot():
    result = service.replay("2026-01-15", "09:00")
    assert result["coverage"]["matched_hours"] == 24
    assert result["metrics"]["latest"]["mae"] == 782.75
    assert result["metrics"]["previous"]["mae"] == pytest.approx(736.2916666667)
    assert result["metrics"]["mae_change_pct"] == pytest.approx(6.3097730745)
    assert result["metrics"]["improved_hours"] == 8
    assert result["metrics"]["worsened_hours"] == 16
    assert result["metrics"]["latest"]["positive_error_mwh"] == 13616.5
    assert service.metadata()["coverage"]["actual_hours"] == 744


def test_month_aggregate_is_calculated_from_individual_errors():
    month = service.accuracy("09:00")
    errors = [row["error"] for day in range(1, 32) for row in service.replay(f"2026-01-{day:02d}", "09:00")["series"] if row["error"] is not None]
    assert month["aggregate"]["n"] == len(errors) == 744
    assert month["aggregate"]["mae"] == pytest.approx(sum(abs(e) for e in errors) / len(errors))
    assert month["aggregate"]["rmse"] == pytest.approx(math.sqrt(sum(e * e for e in errors) / len(errors)))
    assert month["aggregate"]["revision_improved_days"] == 16


def test_month_revision_comparison_preserves_common_cohort_at_early_cutoff():
    # The 02:30 update introduces two additional target hours. Scoring those only
    # for the new forecast would reverse the apparent direction of the update.
    day = service.accuracy("03:00")["days"][0]
    assert day["matched_hours"] == 24
    assert day["paired_hours"] == 22
    assert day["mae"] == pytest.approx(3113.9583333333335)
    assert day["comparison_latest_mae"] == pytest.approx(3018.7272727272725)
    assert day["previous_mae"] == pytest.approx(3065.6363636363635)
    assert day["comparison_latest_mae"] < day["previous_mae"] < day["mae"]
    assert day["mae_change_pct"] == pytest.approx(-1.5301583535970664)
