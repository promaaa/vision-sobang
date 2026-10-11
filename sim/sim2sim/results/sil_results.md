Detector: `baseline_detector.py`. Pose on UDP 5605: yes. Frame messages: interface v2.

| Scenario | Mode | Result | First SPRAY (s) | Fire out (s) | Mean landing error (m) | Stray spray samples | Fall (s) | End (s) |
|---|---|---|---|---|---|---|---|---|
| two_fires | in-process | PASS | 7.0 | 10.0, 37.9 | 0.094 | 0 | - | 63.0 |
| two_fires | SIL 1 | PASS | 7.4 | 10.4, 39.4 | 0.055 | 0 | - | 64.7 |
| two_fires | SIL 2 | PASS | 6.0 | 9.0, 35.7 | 0.057 | 0 | - | 61.0 |
| two_fires | SIL 3 | PASS | 5.4 | 8.4, 34.2 | 0.04 | 0 | - | 59.5 |
| two_fires | SIL 4 | PASS | 7.5 | 10.5, 36.7 | 0.052 | 0 | - | 62.1 |
| two_fires | SIL 5 | PASS | 5.6 | 8.9, 34.7 | 0.052 | 0 | - | 60.1 |
| ahead | in-process | PASS | 4.3 | 7.3 | 0.089 | 0 | - | 32.5 |
| ahead | SIL 1 | PASS | 4.4 | 7.4 | 0.051 | 0 | - | 32.8 |
| ahead | SIL 2 | PASS | 4.4 | 7.4 | 0.062 | 0 | - | 32.6 |
| ahead | SIL 3 | PASS | 4.4 | 7.4 | 0.051 | 0 | - | 32.7 |

| Scenario | Run | Frame messages sent | Rejected by run.py | run.py ticks while the camera sends | ... with no new frame | ... with 2 frames | Largest command gap (s) | Walk timeouts | Largest feedback gap (s) | Largest simulator lag (s) | run.py dead-reckoning messages (1 = only at the start, before the first pose) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| two_fires | SIL 1 | 648 | 0 | 636 | 52 | 53 | 0.104 | 0 | 0.158 | 0.075 | 1 |
| two_fires | SIL 2 | 611 | 0 | 599 | 40 | 41 | 0.105 | 0 | 0.17 | 0.08 | 1 |
| two_fires | SIL 3 | 596 | 0 | 585 | 113 | 113 | 0.104 | 0 | 0.194 | 0.087 | 1 |
| two_fires | SIL 4 | 622 | 0 | 611 | 109 | 109 | 0.107 | 0 | 0.157 | 0.066 | 1 |
| two_fires | SIL 5 | 602 | 0 | 590 | 81 | 82 | 0.105 | 0 | 0.167 | 0.086 | 1 |
| ahead | SIL 1 | 329 | 0 | 318 | 2 | 2 | 0.106 | 0 | 0.158 | 0.06 | 1 |
| ahead | SIL 2 | 327 | 0 | 316 | 92 | 92 | 0.104 | 0 | 0.153 | 0.073 | 1 |
| ahead | SIL 3 | 328 | 0 | 317 | 74 | 74 | 0.104 | 0 | 0.189 | 0.091 | 1 |
