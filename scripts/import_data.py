#!/usr/bin/env python3
"""Download the two Elexon datasets and build the reproducible read-only pilot snapshot."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
API = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
FIRST_DELIVERY = date(2026, 1, 2)
LAST_DELIVERY = date(2026, 2, 1)


def dates(first: date, last: date):
    current = first
    while current <= last:
        yield current
        current += timedelta(days=1)


def timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def fetch_job(kind: str, day: date, cache: Path, refresh: bool):
    cache_path = cache / f"{kind}-{day.isoformat()}.json"
    if cache_path.exists() and not refresh:
        envelope = json.loads(cache_path.read_text())
        return kind, envelope
    if kind == "WINDFOR":
        start = datetime.combine(day, datetime.min.time(), timezone.utc)
        params = {"publishDateTimeFrom": timestamp(start), "publishDateTimeTo": timestamp(start + timedelta(days=1))}
    else:
        params = {"settlementDateFrom": day.isoformat(), "settlementDateTo": day.isoformat(), "fuelType": "WIND"}
    url = f"{API}/{kind}/stream?{urlencode(params)}"
    for attempt in range(5):
        try:
            request = Request(url, headers={"Accept": "application/json", "User-Agent": "WindDecisionReplay/1.0 (historical pilot)"})
            with urlopen(request, timeout=45) as response:
                body = response.read()
            rows = json.loads(body)
            if not isinstance(rows, list):
                raise ValueError(f"Unexpected {kind} response: expected an array")
            envelope = {"url": url, "retrieved_at": timestamp(datetime.now(timezone.utc)), "sha256": hashlib.sha256(body).hexdigest(), "row_count": len(rows), "data": rows}
            cache_path.write_text(json.dumps(envelope, separators=(",", ":")))
            print(f"Fetched {kind} {day}: {len(rows)} records", flush=True)
            return kind, envelope
        except (HTTPError, URLError, TimeoutError) as error:
            retryable = not isinstance(error, HTTPError) or error.code in (429, 500, 502, 503, 504)
            if not retryable or attempt == 4:
                raise RuntimeError(f"Could not retrieve {url}: {error}") from error
            time.sleep(min(2 ** attempt, 12))
    raise RuntimeError("Unreachable")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Re-download cached source windows")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "raw")
    args = parser.parse_args()
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    jobs = [("WINDFOR", d) for d in dates(date(2025, 12, 30), date(2026, 1, 31))]
    jobs += [("FUELHH", d) for d in dates(FIRST_DELIVERY, LAST_DELIVERY)]
    envelopes = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(fetch_job, kind, day, args.cache_dir, args.refresh) for kind, day in jobs]
        for future in as_completed(futures):
            envelopes.append(future.result())

    forecast_rows = {}
    halfhour_rows = {}
    for kind, envelope in envelopes:
        for row in envelope["data"]:
            target = row["startTime"]
            target_date = date.fromisoformat(target[:10])
            if target_date < FIRST_DELIVERY or target_date > LAST_DELIVERY:
                continue
            if kind == "WINDFOR":
                key = (target, row["publishTime"])
                value = float(row["generation"])
                if key in forecast_rows and forecast_rows[key] != value:
                    raise ValueError(f"Conflicting duplicate forecast {key}")
                forecast_rows[key] = value
            elif row.get("fuelType") == "WIND":
                # Prefer the most recently published actual if the source contains revisions.
                previous = halfhour_rows.get(target)
                if previous is None or row["publishTime"] > previous[0]:
                    halfhour_rows[target] = (row["publishTime"], float(row["generation"]))

    output = ROOT / "data"
    temporary = output / "wind.build.sqlite"
    temporary.unlink(missing_ok=True)
    connection = sqlite3.connect(temporary)
    connection.executescript("""
        CREATE TABLE forecasts (target_time TEXT NOT NULL, publish_time TEXT NOT NULL, generation REAL NOT NULL, PRIMARY KEY(target_time,publish_time));
        CREATE INDEX forecasts_publication ON forecasts(publish_time);
        CREATE TABLE actual_halfhour (target_time TEXT PRIMARY KEY, publish_time TEXT NOT NULL, generation REAL NOT NULL);
        CREATE TABLE actuals (target_time TEXT PRIMARY KEY, generation REAL NOT NULL, half_hours INTEGER NOT NULL CHECK(half_hours=2));
    """)
    connection.executemany("INSERT INTO forecasts VALUES (?,?,?)", [(target, published, value) for (target, published), value in sorted(forecast_rows.items())])
    connection.executemany("INSERT INTO actual_halfhour VALUES (?,?,?)", [(target, published, value) for target, (published, value) in sorted(halfhour_rows.items())])
    hours = []
    incomplete = []
    for day in dates(FIRST_DELIVERY, LAST_DELIVERY):
        for hour in range(24):
            start = datetime(day.year, day.month, day.day, hour, tzinfo=timezone.utc)
            first, second = timestamp(start), timestamp(start + timedelta(minutes=30))
            if first in halfhour_rows and second in halfhour_rows:
                hours.append((first, (halfhour_rows[first][1] + halfhour_rows[second][1]) / 2, 2))
            else:
                incomplete.append(first)
    connection.executemany("INSERT INTO actuals VALUES (?,?,?)", hours)
    connection.commit()
    connection.execute("VACUUM")
    connection.close()
    destination = output / "wind.sqlite"
    temporary.replace(destination)
    retrieved_at = max(envelope["retrieved_at"] for _, envelope in envelopes)
    metadata = {
        "dataset_version": "january-2026-v1",
        "retrieved_at": retrieved_at,
        "decision_start": "2026-01-01", "decision_end": "2026-01-31",
        "delivery_start": FIRST_DELIVERY.isoformat(), "delivery_end": LAST_DELIVERY.isoformat(),
        "forecast_records": len(forecast_rows), "halfhour_actual_records": len(halfhour_rows),
        "hourly_actual_records": len(hours), "expected_delivery_hours": 31 * 24,
        "incomplete_actual_hours": incomplete,
        "sqlite_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "source_urls": {"forecasts": "https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream", "actuals": "https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream", "coverage": "https://bmrs.elexon.co.uk/wind-generation"},
        "source_requests": [{"dataset": kind, **{key: envelope[key] for key in ("url", "retrieved_at", "sha256", "row_count")}} for kind, envelope in sorted(envelopes, key=lambda x: x[1]["url"])],
        "notes": [
            "Historical pilot covering January 2026 decisions and next-day delivery from 2 January to 1 February.",
            "Elexon GB metered wind coverage; this is not a model of all UK wind installations.",
            "Actual MW is averaged from two complete half-hours to align with hourly forecasts.",
            "publishTime is used as an availability proxy; recipient-specific delivery latency is unknown.",
            "09:00 Europe/London is a configurable demonstration cutoff, not a universal market deadline.",
            "MWh represents wind forecast mismatch, not the utility's procurement requirement or financial loss."
        ]
    }
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps({key: metadata[key] for key in ("forecast_records", "halfhour_actual_records", "hourly_actual_records", "expected_delivery_hours", "incomplete_actual_hours", "sqlite_sha256")}, indent=2))


if __name__ == "__main__":
    main()
