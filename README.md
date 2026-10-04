# Automated Data Health & Profiling Dashboard

A tool that reads an arbitrary CSV file, reports its statistical health, and
flags multivariate outliers using two unsupervised machine learning
methods - **Isolation Forest** and **KNN (k-nearest neighbours)** - then
compares what each one found. Available as both a command-line tool and a
browser-based UI.

## What it does

1. Reads a CSV and automatically splits columns into numeric vs. non-numeric
   (no manual schema needed).
2. Reports descriptive statistics per numeric column: mean, median, mode,
   variance, standard deviation, kurtosis, and a five-point summary, plus the
   covariance matrix across all numeric columns - computed on the raw,
   un-modified data.
3. Fills missing numeric values with each column's median in a *separate
   working copy* used only for scoring (`--no-impute` to disable).
4. Scores every row with Isolation Forest and/or KNN, flags the most unusual
   rows, and explains *why* each one was flagged (which column(s) deviated
   most, and by how many standard deviations).
5. Compares the two methods: rows both flag are high-confidence outliers;
   rows only one flags are worth a second look.

## Project structure

```
cli.py              entry point for the command-line tool
stats.py             descriptive statistics (Phase 1)
preprocessing.py     median imputation
ml_processing.py      Isolation Forest + KNN outlier detection and comparison
app.py               Flask web app - imports the same three modules above,
                     so the browser UI and the CLI always produce identical
                     results
static/              browser frontend (plain HTML/CSS/JS, no build step)
sample_*.csv         test fixtures (clean, messy, edge case, 200-row with
                     planted outliers)
```

The web app does not duplicate any logic - `app.py` calls the exact same
`stats.py`, `preprocessing.py`, and `ml_processing.py` functions the CLI
uses.

## Running the CLI

```bash
pip install -r requirements.txt
python cli.py sample_200.csv                              # both methods + comparison
python cli.py sample_200.csv --method knn --k 7
python cli.py sample_200.csv --method isolation_forest
python cli.py sample_200.csv --contamination 0.1
python cli.py sample_200.csv --no-impute
```

## Running the web UI locally

```bash
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000, upload a CSV (or click one of the sample
buttons), choose options, and click **Analyze**.

## Deploying to Vercel

This repo is set up for Vercel's Python runtime with zero extra config:

1. Push this repo to GitHub (already done if you're reading this on GitHub).
2. In the [Vercel dashboard](https://vercel.com/new), import the repo.
   Vercel detects Flask from `requirements.txt` + `app.py` automatically.
3. Deploy. No environment variables are required.

**One thing to know:** `pandas` + `numpy` + `scikit-learn` together are large
(around 400 MB installed), close to Vercel's 500 MB Python function limit.
`vercel.json` already excludes non-runtime files to help. If a deploy ever
fails on bundle size, Vercel's [Large Functions
beta](https://vercel.com/docs/functions/limitations#large-functions-beta)
(`VERCEL_SUPPORT_LARGE_FUNCTIONS=1`) raises the cap to 5 GB.

The demo caps uploads at 1 GB in `app.py` (`MAX_CONTENT_LENGTH`). Note that
this only governs the local/self-hosted server: Vercel enforces its own
request body size limit on Functions, well under 1 GB, so an upload that
large would be rejected by the platform before it ever reached this code
when deployed there. Locally, a file anywhere near that size could also take
a very long time to score - `IsolationForest` and the KNN detector's nearest-
neighbour search both get significantly slower as row count grows into the
millions.

## How well does it work?

Isolation Forest and KNN were checked against a 200-row synthetic dataset
(`sample_200.csv`) with 8 outliers deliberately planted and recorded
separately, at the default contamination of 0.05 (10 rows flagged each):

| Method | Rows flagged | Planted outliers found |
|---|---|---|
| Isolation Forest | 10 | 7 / 8 (87.5%) |
| KNN | 10 | 8 / 8 (100%) |
| Flagged by both | 8 | 7 planted + 1 naturally extreme row |

Isolation Forest missed one planted outlier because the dataset's random
missing-value step happened to blank out the two columns that made that row
unusual, and median imputation then made it look ordinary; KNN still caught
it through its other columns. At contamination 0.10, both methods find all
8 (with more rows flagged overall). This is a controlled test on synthetic
data with known answers - on real, unlabeled data there is no ground truth
to check a flag against, which is exactly why the tool reports both methods
and where they agree rather than a single verdict.

## What's not built yet

- Categorical encoding and feature scaling ahead of Isolation Forest (KNN
  already standardises its own features).
- Exporting results to a file (PDF/HTML/CSV) - both the CLI and the web UI
  are display-only right now.
- A formal automated test suite (current testing is manual, via the sample
  CSVs and a one-off recall check against `sample_200.csv`'s planted
  outliers).
- Chunked reading for very large files.

## References

- Liu, F. T., Ting, K. M., & Zhou, Z.-H. (2008). Isolation Forest. *IEEE
  ICDM*, 413-422.
- Ramaswamy, S., Rastogi, R., & Shim, K. (2000). Efficient algorithms for
  mining outliers from large data sets. *ACM SIGMOD*, 427-438.
- Pedregosa, F. et al. (2011). Scikit-learn: Machine Learning in Python.
  *JMLR*, 12, 2825-2830.
