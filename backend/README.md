# ETA-Sync Backend

## Development Setup

Use Python 3.12 for the backend environment. Python 3.14 is not currently a
safe target for the pinned Torch/FastAPI stack.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests -q
```

## Evaluation Reports

Run the evaluation script to generate the confusion matrix and performance report for the current checkpoint.

```bash
python evaluate.py
```

Outputs are written to `backend/reports/`:

- `confusion_matrix.json`
- `classification_report.json`
- `classification_report.txt`
- `evaluation_summary.json`

The script evaluates the trained checkpoint on a synthetic validation set using the same DTW-guided fusion pipeline as training.

## Running the API

To make the backend reachable from your phone on the same Wi-Fi network, bind Uvicorn to all interfaces:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Then point the mobile app at your computer's LAN IP, for example `http://192.168.1.23:8000/health`.
