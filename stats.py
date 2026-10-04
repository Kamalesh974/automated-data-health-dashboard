"""Phase 1 descriptive statistics for the data profiling CLI."""

import pandas as pd


def dataset_overview(df: pd.DataFrame) -> dict:
    """Row/column counts plus per-column dtype and missing-value info."""
    columns_info = pd.DataFrame({
        "dtype": df.dtypes.astype(str),
        "missing": df.isna().sum(),
    })
    return {
        "rows": len(df),
        "columns": df.shape[1],
        "columns_info": columns_info,
    }


def numeric_summary(numeric_df: pd.DataFrame) -> pd.DataFrame:
    """Mean, median, mode, variance, std dev, kurtosis per numeric column."""
    rows = {}
    for col in numeric_df.columns:
        series = numeric_df[col].dropna()
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
    """Min, Q1, median, Q3, max per numeric column."""
    rows = {}
    for col in numeric_df.columns:
        series = numeric_df[col].dropna()
        rows[col] = {
            "min": series.min(),
            "Q1": series.quantile(0.25),
            "median": series.median(),
            "Q3": series.quantile(0.75),
            "max": series.max(),
        }
    return pd.DataFrame(rows).T


def covariance_matrix(numeric_df: pd.DataFrame) -> pd.DataFrame:
    return numeric_df.cov()
