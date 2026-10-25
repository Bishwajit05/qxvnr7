# Submission checklist

The application and public repository must be accessible to a reviewer without account access. The assignment ultimately requires an unlisted YouTube video, but the candidate has requested that the video remain local and that the form not be submitted for now.

## Submission links

| Item | Status or link |
| --- | --- |
| Public GitHub repository with an anonymous random name | [Bishwajit05/qxvnr7](https://github.com/Bishwajit05/qxvnr7) |
| Deployed Vercel application | [Wind Decision Replay](https://wind-decision-replay.vercel.app); updated API-refresh release requires production verification |
| Local demonstration under ten minutes | Prior 8:42 video shows the old workflow; regenerate only after fresh captures and verification |
| Unlisted YouTube demonstration | Deferred at candidate request; no upload performed |
| Submission form | [Full Stack SWE challenge submission v4](https://forms.cloud.microsoft/r/Ljmf1aWESK) |

If the candidate later requests submission, the current local video must first be uploaded as unlisted and its playback verified. LinkedIn, resume links, and contact details remain outside this public repository.

## Before recording

- [ ] Rebuild Docker and verify the revised frontend, Python API, real upstream access, and labelled fallback.
- [ ] Run the current backend tests, frontend interaction tests, TypeScript checks, and production build.
- [ ] Actuals, accuracy cards, comparisons, and CSV export are immediately accessible without reveal controls.
- [ ] A cold request calls the real Elexon APIs and reports `live_api` only after successful retrieval.
- [ ] A repeated request reports `cached_api` and retains its original retrieval timestamp.
- [ ] Manual refresh performs a real upstream request and updates every view from one dataset epoch.
- [ ] An upstream failure preserves last-good API data, marks it stale, and records the refresh error.
- [ ] With no last-good API data, upstream failure uses the bundled snapshot with `snapshot_fallback` status.
- [x] January decision dates are distinguished from next-day delivery dates.
- [x] The default decision cutoff is labelled as an assumption.
- [x] A forecast published after a decision cannot enter that decision's result.
- [x] Incomplete actual hours are reported and excluded from error metrics.
- [x] Forecast revisions are compared using the same eligible delivery hours.
- [x] Source coverage, units, signs, and provenance are explained.
- [x] The README contains project structure, run instructions, deployed link, API-cache/fallback definitions, and AI disclosure.
- [ ] Capture the revised interface and source panels, regenerate the local video, and inspect the complete output.

## Public access checks

Use an incognito/private browser window with no GitHub, hosting, or YouTube login.

- [ ] Open the public repository URL and read its README and source files.
- [ ] Open the updated deployment without credentials and confirm no hosting login is required.
- [ ] Change the date and cutoff, inspect the immediately visible actuals and accuracy, and confirm the Python API responds.
- [ ] Use Refresh and inspect successful API retrieval, cache reuse, dataset consistency, and error/fallback labels.
- [ ] Open the unlisted YouTube URL and play both the customer and technical sections.
- [ ] Confirm the regenerated local video is at most ten minutes and each overview is at most five minutes. The old 8:42 timing does not verify the new video.
- [ ] Put the final verified application and video links in the README and in the table above.

## Submit only if later requested

- [ ] Open the submission form and enter the real repository, application, and video URLs.
- [ ] Recheck every URL copied into the form in incognito mode.
- [ ] Review the form before final submission and record confirmation after submitting.
- [ ] Record the actual work duration honestly; do not exceed the assignment's sixteen-hour limit.
