"""Preprocessing used ahead of outlier scoring (Isolation Forest and KNN):
median imputation and KNN imputation, plus a way to compare the two."""

import pandas as pd
import numpy as np
from sklearn.impute import KNNImputer


def impute_numeric_median(numeric_df: pd.DataFrame) -> dict:
    """Fill missing values (and zeros) in each numeric column with that column's median.

    Columns that are entirely missing have no median to impute with, so they
    are dropped from the returned frame rather than left as NaN.
    """
    numeric_df = numeric_df.copy()
    
    # Treat explicit 0s as missing data as requested
    numeric_df.replace(0, np.nan, inplace=True)

    fully_missing = numeric_df.columns[numeric_df.isna().all()]
    if len(fully_missing) > 0:
        numeric_df = numeric_df.drop(columns=fully_missing)

    imputed_mask = numeric_df.isna()
    imputed_df = numeric_df.fillna(numeric_df.median())

    return {
        "imputed_df": imputed_df,
        "dropped_columns": list(fully_missing),
        "imputed_row_count": int(imputed_mask.any(axis=1).sum()),
    }


def impute_numeric_knn(numeric_df: pd.DataFrame, k: int = 5) -> dict:
    """Fill missing values (and zeros) using K-Nearest Neighbors imputation.

    Each missing value is filled with the (uniformly weighted) average of
    that column's value across the k rows most similar to it, using
    whichever other numeric columns both rows actually have.
    """
    numeric_df = numeric_df.copy()
    
    # Treat explicit 0s as missing data as requested
    numeric_df.replace(0, np.nan, inplace=True)

    fully_missing = numeric_df.columns[numeric_df.isna().all()]
    if len(fully_missing) > 0:
        numeric_df = numeric_df.drop(columns=fully_missing)

    if numeric_df.shape[1] == 0 or len(numeric_df) == 0:
        return {"imputed_df": numeric_df, "dropped_columns": list(fully_missing), "imputed_row_count": 0}

    imputed_mask = numeric_df.isna()
    k = max(1, min(k, len(numeric_df) - 1)) if len(numeric_df) > 1 else 1
    values = KNNImputer(n_neighbors=k).fit_transform(numeric_df)
    imputed_df = pd.DataFrame(values, columns=numeric_df.columns, index=numeric_df.index)

    return {
        "imputed_df": imputed_df,
        "dropped_columns": list(fully_missing),
        "imputed_row_count": int(imputed_mask.any(axis=1).sum()),
    }


def compare_imputations(numeric_df: pd.DataFrame, median_df: pd.DataFrame, knn_df: pd.DataFrame) -> pd.DataFrame:
    """For every originally-missing cell (including zeros), show the median fill next to the KNN fill."""
    numeric_df = numeric_df.copy()
    numeric_df.replace(0, np.nan, inplace=True)  # Treat 0 as missing for comparison mask
    
    mask = numeric_df.isna()
    common_cols = [c for c in numeric_df.columns if c in median_df.columns and c in knn_df.columns]

    rows = []
    for col in common_cols:
        for idx in numeric_df.index[mask[col]]:
            median_val = float(median_df.loc[idx, col])
            knn_val = float(knn_df.loc[idx, col])
            rows.append({
                "row": idx,
                "column": col,
                "median_fill": median_val,
                "knn_fill": knn_val,
                "difference": knn_val - median_val,
            })

    if not rows:
        return pd.DataFrame(columns=["row", "column", "median_fill", "knn_fill", "difference"]).set_index("row")

    return pd.DataFrame(rows).set_index("row")