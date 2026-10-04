"""Phase 2 ML integration: Isolation Forest and KNN multivariate outlier detection."""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from preprocessing import compare_imputations, impute_numeric_knn, impute_numeric_median


def get_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.select_dtypes(include="number")


def _explain_row(scoring_df: pd.DataFrame, means: pd.Series, stds: pd.Series, row_index, top_n: int = 2) -> str:
    """Describe which column(s) pushed a row's anomaly score, in plain terms.

    Neither Isolation Forest nor KNN gives per-feature reasoning, so this
    approximates one: the columns where the row sits furthest (in standard
    deviations) from that column's own average are the most likely drivers.
    """
    row = scoring_df.loc[row_index]
    z_scores = ((row - means) / stds).dropna()
    if z_scores.empty:
        return "n/a"
    top = z_scores.abs().sort_values(ascending=False).head(top_n).index
    parts = []
    for col in top:
        z = z_scores[col]
        direction = "above" if z > 0 else "below"
        parts.append(f"{col} ({abs(z):.1f} SD {direction} avg)")
    return ", ".join(parts)


def _empty_result(total_rows: int, impute: bool, dropped_columns: list = None) -> dict:
    return {
        "total_rows": total_rows,
        "scored_rows": 0,
        "skipped_rows": total_rows,
        "imputed": impute,
        "impute_method": None,
        "imputed_row_count": 0,
        "dropped_columns": dropped_columns or [],
        "imputation_comparison": pd.DataFrame(),
        "flagged_count": 0,
        "flagged": pd.DataFrame(),
        "scores": pd.Series(dtype=float),
        "model_settings": None,
    }


def _prepare_scoring_data(df: pd.DataFrame, impute: bool, impute_method: str = "median", impute_k: int = 5):
    """Build the complete numeric matrix both detectors score.

    When impute=True, both median and KNN imputation are computed regardless
    of impute_method - the one that's not used for scoring still feeds the
    imputation_comparison table, so you can see what each method would have
    filled in for every originally-missing cell.

    Returns (scoring_df, info). scoring_df is None when there is nothing to
    score, in which case info is a ready-made empty result.
    """
    numeric_df = get_numeric_columns(df)
    total_rows = len(df)

    if numeric_df.shape[1] == 0:
        return None, _empty_result(total_rows, impute)

    dropped_columns = []
    imputed_row_count = 0
    imputation_comparison = pd.DataFrame()

    if impute:
        median_imputation = impute_numeric_median(numeric_df)
        knn_imputation = impute_numeric_knn(numeric_df, k=impute_k)
        chosen = knn_imputation if impute_method == "knn" else median_imputation

        scoring_df = chosen["imputed_df"]
        dropped_columns = chosen["dropped_columns"]
        imputed_row_count = chosen["imputed_row_count"]

        if numeric_df.isna().any().any():
            imputation_comparison = compare_imputations(
                numeric_df, median_imputation["imputed_df"], knn_imputation["imputed_df"]
            )
    else:
        scoring_df = numeric_df.dropna()

    if scoring_df.shape[1] == 0 or len(scoring_df) == 0:
        return None, _empty_result(total_rows, impute, dropped_columns)

    scored_rows = len(scoring_df)
    return scoring_df, {
        "total_rows": total_rows,
        "scored_rows": scored_rows,
        "skipped_rows": total_rows - scored_rows,
        "imputed": impute,
        "impute_method": impute_method if impute else None,
        "imputed_row_count": imputed_row_count,
        "dropped_columns": dropped_columns,
        "imputation_comparison": imputation_comparison,
    }


def _finish_result(df, scoring_df, info, flagged_mask, scores, score_column, ascending, model_settings) -> dict:
    """Attach scores and explanations to the flagged rows and package the result."""
    flagged = df.loc[scoring_df.index[flagged_mask]].copy()
    flagged[score_column] = scores[flagged_mask]

    means = scoring_df.mean()
    stds = scoring_df.std().replace(0, pd.NA)
    flagged["why_flagged"] = [
        _explain_row(scoring_df, means, stds, idx) for idx in flagged.index
    ]
    flagged = flagged.sort_values(score_column, ascending=ascending)

    return {
        **info,
        "flagged_count": int(flagged_mask.sum()),
        "flagged": flagged,
        "scores": pd.Series(scores, index=scoring_df.index),
        "model_settings": model_settings,
    }


def detect_outliers_isolation_forest(
    df: pd.DataFrame, contamination: float = 0.05, impute: bool = True,
    impute_method: str = "median", impute_k: int = 5,
) -> dict:
    """Run Isolation Forest on the numeric columns of df.

    By default, missing numeric values are filled per-column with the median
    (see preprocessing.impute_numeric_median) so every row can be scored.
    Pass impute_method="knn" to fill with K-Nearest Neighbors imputation
    instead (preprocessing.impute_numeric_knn, using impute_k neighbours).
    Either way, the result's imputation_comparison table shows what both
    methods would have filled in for every originally-missing cell. Columns
    that are entirely missing can't be imputed and are excluded from
    scoring. Pass impute=False to instead drop any row with a missing numeric
    value (old behavior) and report it as skipped.

    Returns counts plus the flagged rows (original columns + anomaly_score
    and why_flagged), sorted from most to least anomalous.
    """
    scoring_df, info = _prepare_scoring_data(df, impute, impute_method, impute_k)
    if scoring_df is None:
        return info

    model = IsolationForest(contamination=contamination, random_state=42)
    predictions = model.fit_predict(scoring_df)
    scores = model.score_samples(scoring_df)

    return _finish_result(
        df, scoring_df, info,
        flagged_mask=predictions == -1,
        scores=scores,
        score_column="anomaly_score",
        ascending=True,
        model_settings={
            "method": "isolation_forest",
            "n_estimators": model.n_estimators,
            "contamination": contamination,
            "score_threshold": float(model.offset_),
        },
    )


def detect_outliers_knn(
    df: pd.DataFrame, contamination: float = 0.05, k: int = 5, impute: bool = True,
    impute_method: str = "median", impute_k: int = 5,
) -> dict:
    """Flag outliers by distance to the k-th nearest neighbour.

    A row's score is its distance to its k-th nearest neighbour: rows in sparse
    regions sit far from their neighbours and score high. The top
    `contamination` fraction of scores is flagged. Distances are only
    meaningful when every column is on the same scale, so features are
    standardised first (unlike Isolation Forest, which does not need this).
    Missing-value handling is identical to detect_outliers_isolation_forest,
    including the impute_method/impute_k options - note impute_k here is the
    KNN *imputer's* neighbour count, independent of k, the outlier-detection
    neighbour count.

    Returns counts plus the flagged rows (original columns + knn_distance and
    why_flagged), sorted from most to least anomalous.
    """
    scoring_df, info = _prepare_scoring_data(df, impute, impute_method, impute_k)
    if scoring_df is None:
        return info

    scored_rows = info["scored_rows"]
    if scored_rows < 2:
        return {
            **info,
            "flagged_count": 0,
            "flagged": pd.DataFrame(),
            "scores": pd.Series(dtype=float),
            "model_settings": None,
        }

    k = max(1, min(k, scored_rows - 1))
    X = StandardScaler().fit_transform(scoring_df)

    # each row is its own nearest neighbour (distance 0), so ask for k + 1
    distances, _ = NearestNeighbors(n_neighbors=k + 1).fit(X).kneighbors(X)
    scores = distances[:, k]

    threshold = float(np.quantile(scores, 1 - contamination))

    return _finish_result(
        df, scoring_df, info,
        flagged_mask=scores > threshold,
        scores=scores,
        score_column="knn_distance",
        ascending=False,
        model_settings={
            "method": "knn",
            "k": k,
            "contamination": contamination,
            "score_threshold": threshold,
        },
    )


def compare_outlier_methods(df: pd.DataFrame, if_result: dict, knn_result: dict) -> dict:
    """Compare what the two detectors flagged.

    Rows flagged by both methods are the high-confidence outliers; rows flagged
    by only one are worth a closer look but are less certain.
    """
    if_idx = set(if_result["flagged"].index)
    knn_idx = set(knn_result["flagged"].index)
    both = if_idx & knn_idx
    union = if_idx | knn_idx

    shared = if_result["scores"].index.intersection(knn_result["scores"].index)
    rank_correlation = float("nan")
    if len(shared) >= 3:
        # isolation forest: lower = more anomalous; knn: higher = more anomalous
        rank_correlation = float(
            (-if_result["scores"].loc[shared]).corr(knn_result["scores"].loc[shared], method="spearman")
        )

    consensus = pd.DataFrame()
    if union:
        order = {"both": 0, "IF only": 1, "KNN only": 1}
        consensus = df.loc[sorted(union)].copy()
        consensus["flagged_by"] = [
            "both" if i in both else ("IF only" if i in if_idx else "KNN only")
            for i in consensus.index
        ]
        consensus["anomaly_score"] = if_result["scores"].reindex(consensus.index)
        consensus["knn_distance"] = knn_result["scores"].reindex(consensus.index)
        explanations = [
            r["flagged"]["why_flagged"] if "why_flagged" in r["flagged"].columns else pd.Series(dtype=object)
            for r in (if_result, knn_result)
        ]
        consensus["why_flagged"] = (
            explanations[0].reindex(consensus.index).combine_first(explanations[1].reindex(consensus.index))
        )
        consensus["_rank"] = consensus["flagged_by"].map(order)
        consensus = consensus.sort_values(["_rank", "knn_distance"], ascending=[True, False]).drop(columns="_rank")

    return {
        "isolation_forest_count": len(if_idx),
        "knn_count": len(knn_idx),
        "both_count": len(both),
        "union_count": len(union),
        "agreement": len(both) / len(union) if union else float("nan"),
        "rank_correlation": rank_correlation,
        "consensus": consensus,
    }
