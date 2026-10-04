"""Entry point: reads a CSV and prints a full statistical + outlier profile."""

import argparse
import sys

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from stats import covariance_matrix, dataset_overview, five_point_summary, numeric_summary
from ml_processing import (
    compare_outlier_methods,
    detect_outliers_isolation_forest,
    detect_outliers_knn,
    get_numeric_columns,
)

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False


def print_table(df: pd.DataFrame, title: str = None) -> None:
    if title:
        print(f"\n{title}")
        print("-" * len(title))
    if df is None or df.empty:
        print("(none)")
        return
    if HAS_TABULATE:
        print(tabulate(df, headers="keys", tablefmt="psql", showindex=True))
    else:
        print(df.to_string())


def print_section(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def load_csv(path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except pd.errors.EmptyDataError:
        print(f"Error: file is empty: {path}", file=sys.stderr)
        sys.exit(1)
    except pd.errors.ParserError as e:
        print(f"Error: could not parse CSV: {e}", file=sys.stderr)
        sys.exit(1)


def describe_model(settings: dict) -> str:
    if settings["method"] == "knn":
        return (
            f"KNN (k={settings['k']}) - distance to the k-th nearest neighbour, on standardised features. "
            f"Rows with a distance above {settings['score_threshold']:.4f} are flagged as outliers."
        )
    return (
        f"IsolationForest with {settings['n_estimators']} trees. "
        f"Rows scoring below {settings['score_threshold']:.4f} are flagged as outliers."
    )


def print_detector_report(result: dict, contamination: float) -> None:
    print(f"Contamination: {contamination}")
    if result["model_settings"]:
        print(f"Model: {describe_model(result['model_settings'])}")
    if result["dropped_columns"]:
        print(
            "Excluded column(s) with no numeric data at all (nothing to "
            f"impute from): {', '.join(result['dropped_columns'])}"
        )
    print(f"Scored {result['scored_rows']} of {result['total_rows']} rows.")
    if result["imputed"]:
        if result["imputed_row_count"] > 0:
            method_label = "each column's median" if result["impute_method"] == "median" else "KNN imputation"
            print(
                f"Filled missing numeric values in {result['imputed_row_count']} "
                f"row(s) using {method_label} before scoring "
                "(use --no-impute to disable and skip those rows instead)."
            )
    elif result["skipped_rows"] > 0:
        print(
            f"Skipped {result['skipped_rows']} row(s) with missing values in "
            "numeric columns (these models can't score incomplete rows). "
            "Drop --no-impute to fill them with the column median instead."
        )
    print(f"\nFlagged {result['flagged_count']} outlier row(s):")
    print_table(result["flagged"])


def print_imputation_comparison(comparison_df: pd.DataFrame, impute_method: str) -> None:
    print(f"Active imputation method for scoring: {impute_method}")
    other = "KNN" if impute_method == "median" else "median"
    print(
        f"{len(comparison_df)} originally-missing cell(s) - what {impute_method} filled in "
        f"vs what {other} would have filled in instead:"
    )
    print_table(comparison_df)


def print_comparison(comparison: dict) -> None:
    print(
        f"Isolation Forest flagged {comparison['isolation_forest_count']} row(s); "
        f"KNN flagged {comparison['knn_count']} row(s)."
    )
    print(
        f"Both agree on {comparison['both_count']} row(s) - the high-confidence outliers "
        f"({comparison['union_count']} distinct rows flagged in total)."
    )
    if comparison["union_count"]:
        print(f"Agreement (flagged by both / flagged by either): {comparison['agreement']:.0%}")
    if comparison["rank_correlation"] == comparison["rank_correlation"]:
        print(
            "Rank correlation of the two methods' scores across all rows "
            f"(Spearman): {comparison['rank_correlation']:.3f}"
        )
    print("\nRows flagged by both methods are listed first; 'IF only' / 'KNN only' rows deserve a closer look.")
    print_table(comparison["consensus"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Data health & profiling CLI")
    parser.add_argument("csv_path", help="Path to the CSV file to profile")
    parser.add_argument(
        "--method",
        choices=["isolation_forest", "knn", "both"],
        default="both",
        help="Outlier detection method to run (default: both, followed by a comparison)",
    )
    parser.add_argument(
        "--contamination",
        type=float,
        default=0.05,
        help="Expected proportion of outliers, used by both methods (default: 0.05)",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Number of neighbours for the KNN method (default: 5)",
    )
    parser.add_argument(
        "--no-impute",
        dest="impute",
        action="store_false",
        default=True,
        help=(
            "Disable imputation before scoring; rows "
            "with missing numeric values are skipped instead (old behavior)."
        ),
    )
    parser.add_argument(
        "--impute-method",
        choices=["median", "knn"],
        default="median",
        help="How to fill missing numeric values before scoring (default: median).",
    )
    parser.add_argument(
        "--impute-k",
        type=int,
        default=5,
        help="Neighbours used by KNN imputation (default: 5; only relevant with --impute-method knn).",
    )
    args = parser.parse_args()

    if not 0 < args.contamination <= 0.5:
        parser.error("--contamination must be greater than 0 and at most 0.5")
    if args.k < 1:
        parser.error("--k must be at least 1")
    if args.impute_k < 1:
        parser.error("--impute-k must be at least 1")

    df = load_csv(args.csv_path)
    if df.empty:
        print("The CSV has no rows to profile.")
        sys.exit(0)

    numeric_df = get_numeric_columns(df)

    print_section("DATASET OVERVIEW")
    overview = dataset_overview(df)
    print(f"Rows: {overview['rows']}")
    print(f"Columns: {overview['columns']}")
    print_table(overview["columns_info"], "Column dtypes & missing values")

    if numeric_df.shape[1] == 0:
        print("\nNo numeric columns found - skipping numeric statistics.")
    else:
        print_section("NUMERIC COLUMN STATISTICS")
        print_table(numeric_summary(numeric_df), "Central tendency, spread & kurtosis")
        print_table(five_point_summary(numeric_df), "Five-point summary")

        print_section("COVARIANCE MATRIX")
        print_table(covariance_matrix(numeric_df))

    if numeric_df.shape[1] == 0:
        print_section("OUTLIER DETECTION")
        print("No numeric columns available - skipping outlier detection.")
        return

    if_result = knn_result = None

    if args.method in ("isolation_forest", "both"):
        if_result = detect_outliers_isolation_forest(
            df, contamination=args.contamination, impute=args.impute,
            impute_method=args.impute_method, impute_k=args.impute_k,
        )

    if args.method in ("knn", "both"):
        knn_result = detect_outliers_knn(
            df, contamination=args.contamination, k=args.k, impute=args.impute,
            impute_method=args.impute_method, impute_k=args.impute_k,
        )

    comparison_source = if_result or knn_result
    if args.impute and comparison_source is not None and not comparison_source["imputation_comparison"].empty:
        print_section("IMPUTATION COMPARISON - MEDIAN vs KNN")
        print_imputation_comparison(comparison_source["imputation_comparison"], args.impute_method)

    if if_result is not None:
        print_section("ISOLATION FOREST - MULTIVARIATE OUTLIER DETECTION")
        print_detector_report(if_result, args.contamination)

    if knn_result is not None:
        print_section("KNN - DISTANCE-BASED OUTLIER DETECTION")
        print_detector_report(knn_result, args.contamination)

    if if_result is not None and knn_result is not None:
        print_section("COMPARISON - ISOLATION FOREST vs KNN")
        print_comparison(compare_outlier_methods(df, if_result, knn_result))


if __name__ == "__main__":
    main()
