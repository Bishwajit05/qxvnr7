"""FastAPI entrypoint. The production process serves the compiled React app too."""
from __future__ import annotations

import csv
import io
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

from . import service
from .elexon import DataUnavailable

app = FastAPI(title="Wind Decision Replay", description="Traceable historical wind forecast decisions for January 2026", version="1.0.0")


@app.middleware("http")
async def no_http_cache(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


def handle(call, *args):
    try:
        return call(*args)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="The historical snapshot is unavailable. Run scripts/import_data.py before starting the application.") from exc
    except DataUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/health")
def health():
    ready = (service.DATA_DIR / "wind.sqlite").is_file() and (service.DATA_DIR / "metadata.json").is_file()
    current = service.provider.peek_status()
    return {"status": "ok", "dataset": "january-2026", "read_only": True, "data_provider": "elexon_api", "upstream_checked": bool(current and current["last_refresh_attempt"]), "fallback_available": ready, "data_status": current}


@app.get("/api/dashboard")
def get_dashboard(decision_date: str = Query("2026-01-15"), cutoff: str = Query("09:00"), publication: str | None = None):
    return handle(service.dashboard, decision_date, cutoff, publication, False)


@app.post("/api/refresh")
def refresh_dashboard(decision_date: str = Query("2026-01-15"), cutoff: str = Query("09:00"), publication: str | None = None):
    return handle(service.dashboard, decision_date, cutoff, publication, True)


@app.get("/api/replay")
def get_replay(decision_date: str = Query("2026-01-15"), cutoff: str = Query("09:00"), publication: str | None = None):
    return handle(service.replay, decision_date, cutoff, publication)


@app.get("/api/accuracy")
def get_accuracy(cutoff: str = Query("09:00")):
    return handle(service.accuracy, cutoff)


@app.get("/api/metadata")
def get_metadata():
    return handle(service.metadata)


@app.get("/api/replay.csv")
def replay_csv(decision_date: str = Query("2026-01-15"), cutoff: str = Query("09:00"), publication: str | None = None):
    replay = handle(service.replay, decision_date, cutoff, publication)
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["decision_date", "decision_cutoff_europe_london", "checkpoint_utc", "target_time_utc", "latest_forecast_mw", "previous_forecast_mw", "actual_mw", "error_mw", "latest_publication_utc", "previous_publication_utc"])
    for row in replay["series"]:
        writer.writerow([decision_date, cutoff, replay["decision"]["as_of"], row["start_time"], row["latest"], row["previous"], row["actual"], row["error"], row["latest_publish_time"], row["previous_publish_time"]])
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="wind-replay-{decision_date}-{cutoff.replace(":", "")}.csv"'})


DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if (DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")


@app.get("/", include_in_schema=False)
def frontend():
    if (DIST / "index.html").is_file():
        return FileResponse(DIST / "index.html")
    return PlainTextResponse("Wind Decision Replay API is running. Start the React dev server or build frontend/dist to serve the dashboard.")
