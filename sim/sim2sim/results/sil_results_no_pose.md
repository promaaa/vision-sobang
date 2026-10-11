Detector: `baseline_detector.py`. Pose on UDP 5605: no. Frame messages: interface v2.

| Scenario | Mode | Result | First SPRAY (s) | Fire out (s) | Mean landing error (m) | Stray spray samples | Fall (s) | End (s) |
|---|---|---|---|---|---|---|---|---|
| two_fires | in-process | PASS | 7.0 | 10.0, 38.3 | 0.096 | 0 | - | 63.4 |
| two_fires | SIL 1 no pose | PASS | 5.1 | 8.6, 35.2 | 0.12 | 0 | - | 59.7 |

| Scenario | Run | Frame messages sent | Rejected by run.py | run.py ticks while the camera sends | ... with no new frame | ... with 2 frames | Largest command gap (s) | Walk timeouts | Largest feedback gap (s) | Largest simulator lag (s) | run.py dead-reckoning messages (1 = only at the start, before the first pose) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| two_fires | SIL 1 no pose | 598 | 0 | 643 | 103 | 45 | 0.108 | 0 | 0.331 | 6.686 | 1 |
