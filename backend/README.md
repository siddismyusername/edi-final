# ETA-Sync Backend

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