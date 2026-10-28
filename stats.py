"""Phase 1 descriptive statistics for the data profiling CLI."""

import pandas as pd
import numpy as np


def dataset_overview(df: pd.DataFrame) -> dict:
    """Row/column counts plus per-column dtype and missing-value info (treating 0 as missing)."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    
    missing_counts = df.isna().sum()
    for col in numeric_cols:
        if col in missing_counts:
            missing_counts[col] += (df[col] == 0).sum()

    columns_info = pd.DataFrame({
        "dtype": df.dtypes.astype(str),
        "missing": missing_counts,
    })
    return {
        "rows": len(df),
        "columns": df.shape[1],
        "columns_info": columns_info,
    }


def numeric_summary(numeric_df: pd.DataFrame) -> pd.DataFrame:
    """Mean, median, mode, variance, std dev, kurtosis per numeric column (excluding 0s)."""
    rows = {}
    for col in numeric_df.columns:
        series = numeric_df[col].replace(0, np.nan).dropna()
        if series.empty:
            rows[col] = {"mean": float("nan"), "median": float("nan"), "mode": float("nan"), "variance": float("nan"), "std_dev": float("nan"), "kurtosis": float("nan")}
            continue

        mode = series.mode()
        rows[col] = {
            "mean": series.mean(),
            "median": series.median(),
            "mode": mode.iloc[0] if not mode.empty else float("nan"),
            "variance": series.var(),
            "std_dev": series.std(),
            "kurtosis": series.kurt(),
        }
    return pd.DataFrame(rows).T


def five_point_summary(numeric_df: pd.DataFrame) -> pd.DataFrame:
    """Min, Q1, median, Q3, max per numeric column (excluding 0s)."""
    rows = {}
    for col in numeric_df.columns:
        series = numeric_df[col].replace(0, np.nan).dropna()
        if series.empty:
            rows[col] = {"min": float("nan"), "Q1": float("nan"), "median": float("nan"), "Q3": float("nan"), "max": float("nan")}
            continue

        rows[col] = {
            "min": series.min(),
            "Q1": series.quantile(0.25),
            "median": series.median(),
            "Q3": series.quantile(0.75),
            "max": series.max(),
        }
    return pd.DataFrame(rows).T


def covariance_matrix(numeric_df: pd.DataFrame) -> pd.DataFrame:
    return numeric_df.replace(0, np.nan).cov()