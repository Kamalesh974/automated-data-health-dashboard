"""Web UI backend: a thin Flask wrapper around the existing CLI modules.

This intentionally reuses stats.py, preprocessing.py, and ml_processing.py
unchanged, so the web results match `python cli.py` exactly - no logic is
duplicated or re-implemented for the browser.
"""

import io
import math

import numpy as np
import pandas as pd
from flask import Flask, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge

from stats import covariance_matrix, dataset_overview, five_point_summary, numeric_summary
from ml_processing import (
    compare_outlier_methods,
    detect_outliers_isolation_forest,
    detect_outliers_knn,
    get_numeric_columns,
)

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024  # 1 GB upload cap

MAX_CHART_ROWS = 3000  # cap raw points sent for client-side charting


def _clean(value):
    """Make a single value JSON-safe: NaN/inf -> None, numpy scalars -> plain Python."""
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def df_to_table(df: pd.DataFrame) -> dict:
    """Turn a DataFrame into {columns, rows} the frontend can render as a table."""
    if df is None or df.empty:
        return {"columns": [] if df is None else [str(c) for c in df.columns], "rows": []}
    rows = []
    for idx, row in df.iterrows():
        record = {"_index": _clean(idx)}
        for col, val in row.items():
            record[str(col)] = _clean(val)
        rows.append(record)
    return {"columns": [str(c) for c in df.columns], "rows": rows}


def detector_payload(result: dict) -> dict:
    return {
        "total_rows": result["total_rows"],
        "scored_rows": result["scored_rows"],
        "skipped_rows": result["skipped_rows"],
        "imputed": result["imputed"],
        "impute_method": result["impute_method"],
        "imputed_row_count": result["imputed_row_count"],
        "dropped_columns": result["dropped_columns"],
        "flagged_count": result["flagged_count"],
        "flagged": df_to_table(result["flagged"]),
        "model_settings": result["model_settings"],
    }


@app.errorhandler(RequestEntityTooLarge)
def too_large(_e):
    return jsonify({"error": "File is too large. This demo accepts CSVs up to 1 GB."}), 413


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/analyze")
def analyze():
    file = request.files.get("file")
    if file is None or file.filename == "":
        return jsonify({"error": "No file uploaded. Attach a CSV as 'file'."}), 400

    method = request.form.get("method", "both")
    if method not in ("isolation_forest", "knn", "both"):
        return jsonify({"error": "method must be isolation_forest, knn, or both."}), 400

    try:
        contamination = float(request.form.get("contamination", 0.05))
    except ValueError:
        return jsonify({"error": "contamination must be a number."}), 400
    if not (0 < contamination <= 0.5):
        return jsonify({"error": "contamination must be greater than 0 and at most 0.5."}), 400

    try:
        k = int(request.form.get("k", 5))
    except ValueError:
        return jsonify({"error": "k must be an integer."}), 400
    if k < 1:
        return jsonify({"error": "k must be at least 1."}), 400

    impute = request.form.get("impute", "true").lower() != "false"

    impute_method = request.form.get("impute_method", "median")
    if impute_method not in ("median", "knn"):
        return jsonify({"error": "impute_method must be median or knn."}), 400

    try:
        impute_k = int(request.form.get("impute_k", 5))
    except ValueError:
        return jsonify({"error": "impute_k must be an integer."}), 400
    if impute_k < 1:
        return jsonify({"error": "impute_k must be at least 1."}), 400

    try:
        df = pd.read_csv(io.BytesIO(file.read()))
    except pd.errors.EmptyDataError:
        return jsonify({"error": "The uploaded file is empty."}), 400
    except pd.errors.ParserError as e:
        return jsonify({"error": f"Could not parse CSV: {e}"}), 400
    except UnicodeDecodeError:
        return jsonify({"error": "Could not decode file - is it a valid CSV (UTF-8)?"}), 400

    if df.empty:
        return jsonify({"error": "The CSV has no rows to profile."}), 400

    numeric_df = get_numeric_columns(df)
    overview = dataset_overview(df)

    response = {
        "rows": overview["rows"],
        "columns": overview["columns"],
        "columns_info": df_to_table(overview["columns_info"]),
        "has_numeric": numeric_df.shape[1] > 0,
    }

    if numeric_df.shape[1] > 0:
        response["numeric_summary"] = df_to_table(numeric_summary(numeric_df))
        response["five_point_summary"] = df_to_table(five_point_summary(numeric_df))
        response["covariance_matrix"] = df_to_table(covariance_matrix(numeric_df))

        # Raw (un-imputed) numeric columns, for client-side scatter plots / histograms.
        # Capped so a large upload can't blow up the response payload.
        response["raw_numeric"] = df_to_table(numeric_df.head(MAX_CHART_ROWS))
        response["raw_numeric_truncated"] = len(numeric_df) > MAX_CHART_ROWS

        results = {}
        if method in ("isolation_forest", "both"):
            results["isolation_forest"] = detect_outliers_isolation_forest(
                df, contamination=contamination, impute=impute,
                impute_method=impute_method, impute_k=impute_k,
            )
        if method in ("knn", "both"):
            results["knn"] = detect_outliers_knn(
                df, contamination=contamination, k=k, impute=impute,
                impute_method=impute_method, impute_k=impute_k,
            )

        response["results"] = {name: detector_payload(res) for name, res in results.items()}

        comparison_source = next(iter(results.values()))
        if impute and not comparison_source["imputation_comparison"].empty:
            response["imputation_comparison"] = {
                "active_method": impute_method,
                "table": df_to_table(comparison_source["imputation_comparison"]),
            }

        # index -> "both" | "isolation_forest" | "knn", for coloring chart points
        flagged_index_sets = {name: {str(i) for i in res["flagged"].index} for name, res in results.items()}
        flagged_by = {}
        if len(flagged_index_sets) == 2:
            if_idx, knn_idx = flagged_index_sets["isolation_forest"], flagged_index_sets["knn"]
            for key in if_idx & knn_idx:
                flagged_by[key] = "both"
            for key in if_idx - knn_idx:
                flagged_by[key] = "isolation_forest"
            for key in knn_idx - if_idx:
                flagged_by[key] = "knn"
        else:
            ((name, idx_set),) = flagged_index_sets.items()
            flagged_by = {key: name for key in idx_set}
        response["flagged_by"] = flagged_by

        if "isolation_forest" in results and "knn" in results:
            comparison = compare_outlier_methods(df, results["isolation_forest"], results["knn"])
            response["comparison"] = {
                "isolation_forest_count": comparison["isolation_forest_count"],
                "knn_count": comparison["knn_count"],
                "both_count": comparison["both_count"],
                "union_count": comparison["union_count"],
                "agreement": _clean(comparison["agreement"]),
                "rank_correlation": _clean(comparison["rank_correlation"]),
                "consensus": df_to_table(comparison["consensus"]),
            }

    return jsonify(response)


@app.get("/")
def index():
    return app.send_static_file("index.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
