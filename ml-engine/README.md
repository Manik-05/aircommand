# ml-engine (Developer A)

Pure Python package. No server/networking code lives here — that's
`backend`'s job. This package owns MediaPipe capture, feature extraction,
model training, and real-time inference.

## Public interface

`engine.py::GestureEngine` is the ONLY class the backend imports. Keep its
method signatures stable — see the docstring at the top of that file.

## Test headlessly (no server, no dashboard needed)

```bash
conda activate aircommand
python -m ml_engine.demo   # TODO(Dev A): add a small CLI harness here
```

## Module layout

- `capture/` — webcam + MediaPipe hand landmark extraction
- `features/` — static pose normalization, dynamic trajectory/resampling features
- `models/` — static classifier (MLP/k-NN) + dynamic matcher (DTW)
- `training/` — fit + persist model artifacts
- `inference/` — real-time loop, sliding window, cooldown, smoothing
- `tests/` — unit tests, no webcam required (use recorded fixture sequences)
