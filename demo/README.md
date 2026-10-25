# Local narrated application walkthrough

The current version is `../deliverables/wind-decision-replay-demo-v2.mp4`. It describes immediate actuals and accuracy, real Elexon API retrieval, a 300-second instance cache, manual Refresh, one dataset epoch, and explicit stale/fallback status. The earlier MP4 is preserved as an obsolete version.

The video stays local at the candidate's request. No YouTube upload or submission is performed by this pipeline. It uses screenshots captured from the running application and excerpts from the actual source; it is not a continuous screen recording. The macOS Daniel synthetic narration is disclosed and does not impersonate the candidate.

## Build version two

Use a Python environment with Pillow, imageio-ffmpeg, and the backend requirements installed. Install frontend dependencies first. macOS `say` supplies the narration.

```sh
python demo/build_video.py --screenshots ../deliverables/screenshots-v2 --output ../deliverables/wind-decision-replay-demo-v2.mp4
```

Required new captures are `01-overview.png`, `02-outcome.png`, `03-explain.png`, `04-month.png`, `05-partial.png`, `06-chart.png`, and `07-metrics.png`. The builder never falls back to the previous capture directory. It stops if any required capture is missing.

Chapter text is read from `chapters.json`; generated narration and audio live in the version-specific build directory under deliverables. Changed text generates new audio. Architecture panels describe real API retrieval as the normal path and SQLite as an explicit upstream-failure fallback. Code panels read the provider, analysis, and Docker source. The verification panel executes both backend and frontend checks and preserves their output.

## Local outputs

- `wind-decision-replay-demo-v2.mp4`: H.264 1080p video with AAC narration, chapter metadata, and selectable captions.
- `wind-decision-replay-demo-v2.srt`: sidecar captions.
- `wind-decision-replay-demo-v2-manifest.json`: measured chapter and part durations.
- `wind-decision-replay-demo-v2-description.txt`: local description and chapter timestamps.
- `video-qa-v2/`: decode report, sampled frames, embedded caption extraction, and inspection notes.

Both parts must remain below five minutes, and the total below ten minutes. The current narration and scenes total approximately eight minutes and two seconds: about three minutes forty-eight seconds for the customer presentation and four minutes fourteen seconds for the technical review. Check the final encoded duration in the QA report. The generated video, raw captures, and intermediate audio stay outside the public source repository.
