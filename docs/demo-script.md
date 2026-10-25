# Nine minute demo script

Record one unlisted YouTube video with a customer presentation followed by a technical review. Target nine minutes so pauses and transitions remain inside the ten-minute assignment limit. Keep each part below five minutes. This is a prepared script; recording and upload are still required.

Before recording, run the app, select a date with complete source coverage, and inspect the actual results. Replace bracketed prompts below with verified numbers shown by the dashboard. Do not invent performance figures or procurement savings.

The packaged snapshot provides a useful example: **15 January at 09:00 London time, for 16 January delivery**. At midnight delivery, the selected forecast is 7,398 MW, the recorded hourly actual is 7,335.5 MW, and the error is +62.5 MW. Across all 24 delivery hours, selected MAE is 782.75 MW versus 736.29 MW for the previous revisions: the latest revision has **6.3% higher MAE**, improving eight hours and worsening sixteen. Its positive-error energy is nevertheless lower, 13,616.5 MWh versus 14,548 MWh. This illustrates that different error measures answer different questions. These values were checked against the packaged snapshot; confirm them again if the data is refreshed.

## Part one Customer presentation 0:00 to 4:30

| Time | Screen action | Narration |
| --- | --- | --- |
| 0:00–0:40 | Show the dashboard and January decision controls. | “This pilot helps your day-ahead buying team answer two questions: what wind forecast was available when you had to decide, and how reliable was it? We use Elexon's wind forecasts and recorded generation to replay those decisions.” |
| 0:40–1:30 | Select the chosen January decision date and 09:00 London time. Point out the next-day delivery date and publication information. | “This is a historical decision on [date]. The forecast covers tomorrow's delivery. Only publications available by this selected time qualify. The default time is a demonstration assumption that your team's operating process can configure.” |
| 1:30–2:20 | Explain the forecast and actual lines, then inspect an hour with a visible error. | “The forecast showed [verified MW] and the later recorded value was [verified MW]. The signed error tells us whether wind was over- or underforecast. This gives a concrete view of the uncertainty that a buying team faces.” |
| 2:20–3:10 | Show MAE, RMSE, bias, and coverage. | “Average absolute error describes a typical miss, while RMSE makes large misses more visible. Bias shows the direction of errors. Coverage tells us how much data supports these statistics; missing observations never become zeroes.” |
| 3:10–4:00 | Open the forecast revision comparison and point out its common matched hours. | “Here we compare the latest eligible forecast with the previous eligible revision for each delivery hour. Both are evaluated on the same hours, so a change in coverage cannot masquerade as an improvement. On this example, the measured change is [verified result]. We can also replay earlier publication checkpoints.” |
| 4:00–4:30 | Return to the overall dashboard or methodology information. | “The result is an auditable view of wind expectations and uncertainty. This pilot uses GB metered wind data. Adding your demand and contracted positions would be a separate next step before calculating your own procurement volume.” |

## Part two Technical review 4:30 to 9:00

| Time | Screen action | Narration |
| --- | --- | --- |
| 4:30–5:10 | Show the README architecture diagram. | “The app has a React and TypeScript frontend, a Python FastAPI backend, and a read-only SQLite snapshot. An offline importer retrieves the two allowed Elexon datasets. A single Docker command runs the complete local application.” |
| 5:10–5:55 | Show the importer and `data/metadata.json`. | “Forecast queries use publication windows. We retain revisions and separately filter delivery times. Metadata preserves the source requests, retrieval timestamps, record counts, and checksums. January decision dates produce next-day delivery from 2 January through 1 February.” |
| 5:55–6:45 | Show the forecast-selection function and its cutoff test. | “The backend selects the latest publication at or before the decision timestamp for each target hour. This test prevents future information from leaking into an earlier decision. UTC timestamps are stored consistently, and the interface labels the London decision time.” |
| 6:45–7:30 | Show alignment and metric logic, then related tests. | “Forecasts are hourly. We require two half-hour actuals and average their MW values for comparison. Missing hours stay unavailable. Error is forecast minus actual, and revision scores use a shared cohort. The tests cover those definitions and boundary conditions.” |
| 7:30–8:15 | Show frontend components, API contract, and CI checks. | “The frontend requests selected results and renders charts, metrics, and coverage. Calculations stay in Python. The build checks TypeScript, while CI also runs backend tests. Loading and error states explain problems without fabricating data.” |
| 8:15–9:00 | Show Docker, Vercel configuration, and live application. | “Docker builds the frontend and runs the Python app. Vercel hosts the built frontend and the same ASGI app as a Python function, with the snapshot included. The public links have been checked while signed out [say this only after verification]. AI assistance is disclosed in the README. The main tradeoff is a fixed historical snapshot, appropriate to this pilot's scope and time limit.” |

## Recording checks

- Close private tabs and notifications before screen recording.
- Use a readable zoom level and a microphone with clear audio.
- Keep narration grounded in results actually visible in this build.
- Do not expose account credentials or deployment tokens.
- Upload as **Unlisted**, then open the YouTube link in an incognito window.
- Add the verified video URL to the README and submission checklist.
