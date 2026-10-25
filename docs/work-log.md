# Development work log

Date: 25 October 2026. AI assistance: OpenAI Codex with parallel implementation and review.

The project directory was created at 14:49 IST. This checkpoint was recorded at 15:44 IST, approximately 0.93 hours later. Document reading, domain research, and product planning occurred earlier in the same afternoon and are additional to that filesystem-based interval. No manual stopwatch was used.

## Earlier release completed

- Researched source fields, historical publication filtering, units, wind coverage, and hourly alignment.
- Validated a real January case before implementation, then imported all January decision dates with next-day delivery through 1 February.
- Implemented the React dashboard, forecast replay, outcome reveal, publication checkpoints, metric explanations, CSV export, and January review.
- Implemented the Python API, immutable SQLite snapshot, provenance and reproducible importer.
- Checked 20 backend tests, frontend TypeScript/build and dependency audit; corrected paired-cohort and timezone presentation defects found during review.
- Built and ran Docker; checked the packaged frontend, API, CSV, and static assets.
- Deployed on Vercel under the approved bishwajit05 account and checked the production page, assets, and Python API without credentials.
- Produced an 8:42 narrated demo with captions, real app captures, source excerpts, and executed test evidence. The customer and technical parts are each shorter than five minutes.

## Requested revision

The candidate requested immediate access to actuals and accuracy, real Elexon API retrieval with a manual refresh, and retention of the January 2026 historical scope. The earlier reveal workflow and fixed-snapshot-only architecture no longer describe the requested application.

- The revised contract uses one `/api/dashboard` response for the selected decision, January analysis, metadata, and retrieval status from one dataset epoch.
- The API provider makes real upstream requests, uses a 300-second cache per Python instance, and supports forced refresh through `POST /api/refresh`.
- Successful API retrieval, cached data, stale last-good data after failure, and bundled snapshot fallback must be distinguishable. A failed refresh must not claim a new successful retrieval time.
- Vercel's configured function maximum duration is now 60 seconds. CI includes the frontend interaction test command in addition to Python tests and the production build.
- Updated README, source preview, narration, architecture panels, and local version 2 video for the new workflow; the earlier video is preserved separately.

Revision verified on 25 October 2026 at 16:38 IST:

- 37 backend tests and 8 frontend interaction tests pass. The Linux Docker backend checks and GitHub CI also pass.
- Initial requests call the two official Elexon APIs. The local initial fetch took 1.88 seconds; a cached request took 0.02 seconds; forced refresh took 1.91 seconds.
- The public production refresh returned live_api, advanced the successful retrieval timestamp, and provided daily, monthly, and metadata results from the same immutable dataset. Both API datasets supplied all 744 complete delivery hours at the default cutoff.
- Actuals, all accuracy cards, revision comparisons, and CSV are immediately visible. Browser checks confirmed zero reveal controls and successful Refresh on the live site.
- Mobile and tablet layouts were inspected at 390 and 768 pixels with no page overflow.
- The regenerated local version 2 demo is 8:02; customer and technical parts are 3:48 and 4:14. Full audio/video decoding and caption/frame checks passed. No upload was performed.

## Remaining submission items

- The candidate requested that the video stay local for now. No YouTube upload is authorized by this revision; an upload and public playback check would be needed before eventual assignment submission.
- The candidate will supply LinkedIn and public Google Drive resume URLs. Contact details are stored outside this public repository.
- The submission form has not been submitted.

The application is a historical pilot. Its forecast mismatch measures do not estimate actual portfolio purchases or financial loss.
