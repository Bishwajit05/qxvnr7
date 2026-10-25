# Narrated application walkthrough

This pipeline creates a maximum ten-minute, two-part MP4 using screenshots of the running application and excerpts from the actual repository. The narration uses the macOS Daniel synthetic voice; it does not impersonate the candidate. The customer and technical parts must each remain below five minutes.

The narration text is in `chapters.json` and generated chapter files under `narration/`. Review the text against the current snapshot before publishing. This is a narrated walkthrough of captured application states, rather than a continuous live screen recording.

## Build

Install Pillow and imageio-ffmpeg in the Python environment. On macOS, run:

```sh
python demo/build_video.py --screenshots ../deliverables/screenshots
```

Required actual application captures are `01-overview.png`, `02-outcome.png`, `03-explain.png`, `04-month.png`, `05-partial.png`, `06-chart.png`, and `07-metrics.png`. The partial capture shows a midnight decision cutoff with incomplete forecast coverage; the chart capture shows the publication timeline before revealing actuals. A viewport near 1920 by 1080 is recommended. The builder stops rather than fabricating missing screenshots.

The output is `../deliverables/wind-decision-replay-demo.mp4`, with an SRT caption file and a manifest containing chapter timestamps and part durations. MP4 captions are selectable. Intermediate chapter audio, frames, and segments are under `../deliverables/video-build/` and should not be committed to the public repository.

The technical test panel runs the backend tests during the build and preserves the executed output. Source panels read the current importer, analysis code, and Dockerfile. The final MP4 should be watched before uploading to YouTube as unlisted. Upload and public access verification are separate steps.
