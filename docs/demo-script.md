# Local demo script for the API refresh workflow

Prepare a two-part local video, targeting eight to nine minutes in total and keeping each overview below five minutes. The candidate has requested that the video stay local. Do not upload it or submit the form as part of regeneration.

The existing 8:42 MP4 demonstrates the earlier workflow and is obsolete for this revision. This script and `demo/chapters.json` describe the revised application. Record new captures only after real API retrieval, source status, immediate results, cache reuse, and manual refresh have been verified. The old screenshots and hardcoded technical panels in the video builder also need replacement or revision before rendering.

## Part one Customer presentation 0:00 to 4:15

| Time | Screen action | Narration focus |
| --- | --- | --- |
| 0:00–0:45 | Open the dashboard at 15 January 2026, 09:00 London time. | Explain the buying team's two questions: what wind forecast was available, and how accurate was it? Point out that forecast, actuals, and accuracy are already visible after loading. |
| 0:45–1:25 | Inspect the selected publication and move to an earlier eligible checkpoint. | The latest publication at or before the historical cutoff is chosen for each target hour. Freshly retrieving data today never permits later publications into an earlier decision. The default cutoff is a demonstration assumption. |
| 1:25–2:15 | Hover an hourly comparison and show the metric explanations. | Explain forecast minus actual, MAE, RMSE, bias, complete half-hour alignment, and MW versus MWh. The analysis concerns wind mismatch rather than a utility's exact procurement volume. |
| 2:15–3:00 | Inspect the revision comparison and its paired sample size. | Compare selected and previous forecasts on identical hours. Use the verified displayed values; do not assume a newer revision improves every measure. |
| 3:00–3:40 | Click Refresh and show the resulting source status and retrieval time. | A manual refresh attempts real Elexon requests. Distinguish successful API retrieval, cached API data, and an explicitly labelled fallback. Explain a stale/error state if it actually occurs. |
| 3:40–4:15 | Open January review and inspect an early cutoff with partial coverage. | The month retains January decision dates with next-day delivery through 1 February. Missing hours stay missing, and revision charts compare the common cohort. |

## Part two Technical review 4:15 to 8:45

| Time | Screen action | Narration focus |
| --- | --- | --- |
| 4:15–5:00 | Show the revised architecture and dashboard API response. | React renders one FastAPI response containing the selected decision, January metrics, metadata, and source status from one dataset epoch. Python owns calculations. |
| 5:00–5:50 | Show the API provider and a real request's provenance. | Retrieve only the two permitted Elexon datasets, with historical publication and delivery bounds. A successful normalized dataset is cached in memory for 300 seconds per instance. |
| 5:50–6:35 | Show refresh and failure-handling tests. | Forced refresh bypasses the cache interval. A failed refresh preserves the last-good dataset and original retrieval time, marks it stale, and records the failure. With no successful API data, fallback is explicit and retains its original provenance. |
| 6:35–7:20 | Show cutoff, alignment, and cohort logic plus their tests. | Exclude future publications; require two actual half-hours; distinguish missing from zero; compute revision changes from the same hours; preserve the January-to-February boundary. |
| 7:20–8:05 | Show frontend interaction tests and CI results. | Verify immediate actuals and metrics, no reveal workflow, refresh loading/error state, Python tests, frontend tests, TypeScript, and production build. Mention only checks that have executed successfully. |
| 8:05–8:45 | Show Docker, Vercel configuration, and the deployed app. | Docker runs the complete local application. Vercel serves the frontend and the same ASGI app, with a 60-second configured function duration. Its cache is instance-local and disposable. Explain the January scope, source limits, AI disclosure, and local-only video status. |

## Numerical reference case

The bundled reference snapshot contains this example: 15 January at 09:00 London time for 16 January delivery. At midnight, selected forecast is 7,398 MW, hourly actual is 7,335.5 MW, and signed error is +62.5 MW. The 24-hour selected MAE is 782.75 MW, compared with 736.29 MW for previous revisions, or 6.3% higher. Eight hours improve and sixteen worsen. Positive-error energy is nevertheless lower: 13,616.5 MWh versus 14,548 MWh.

These are reference-snapshot values, not a guarantee about a new API retrieval. Recheck every narrated number against the response used for the final captures, because upstream historical records may have been revised.

## Recording checks

- Use real captures of the revised running application, including a completed manual refresh and its source status.
- Capture the provider and unified endpoint rather than presenting the offline fallback importer as the normal runtime architecture.
- Replace the builder's obsolete architecture and delivery panels before generating a new video.
- Do not simulate an upstream failure without clearly labelling it as a controlled demonstration.
- Keep source labels, retrieval times, stale/error states, units, and cohort sizes readable.
- Watch the complete regenerated MP4 and verify its actual total and part durations.
- Keep the MP4, captions, and personal submission details local. No upload or form submission is requested.
