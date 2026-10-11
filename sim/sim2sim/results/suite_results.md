Detector: `baseline_detector.py`

| Scenario | Result | First SPRAY (s) | Fire out (s) | Mean landing error (m) | Stray spray samples | Detections on fires | False detections | Fall (s) | End (s) |
|---|---|---|---|---|---|---|---|---|---|
| ahead | **PASS** | 4.3 | 7.3 | 0.089 | 0 | 74 | 61 | - | 32.5 |
| behind_right | **PASS** | 15.9 | 18.9 | 0.084 | 0 | 106 | 56 | - | 44.2 |
| two_fires | **PASS** | 7.0 | 10.0, 37.9 | 0.094 | 0 | 258 | 80 | - | 63.0 |
| lamp_only | **PASS** | - | no fire | - | 0 | 0 | 53 | - | 21.2 |
| too_close | **PASS** | 4.0 | 7.0 | 0.062 | 0 | 68 | 70 | - | 32.2 |
| far | **PASS** | 35.6 | 38.7 | 0.089 | 0 | 267 | 152 | - | 63.8 |
