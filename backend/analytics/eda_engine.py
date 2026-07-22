"""
Exploratory Data Analysis (EDA) engine.

Performs comprehensive statistical analysis, correlation analysis, and generates automated insights.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


class EDAEngine:
    """Engine for exploratory data analysis."""

    @staticmethod
    def calculate_summary_statistics(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate summary statistics for all numeric columns.

        Args:
            df: DataFrame to analyze

        Returns:
            dict: Summary statistics
        """
        numeric_df = df.select_dtypes(include=[np.number])
        summary = {}

        for col in numeric_df.columns:
            summary[col] = {
                "count": int(numeric_df[col].count()),
                "mean": float(numeric_df[col].mean()),
                "median": float(numeric_df[col].median()),
                "std": float(numeric_df[col].std()),
                "min": float(numeric_df[col].min()),
                "max": float(numeric_df[col].max()),
                "q25": float(numeric_df[col].quantile(0.25)),
                "q50": float(numeric_df[col].quantile(0.50)),
                "q75": float(numeric_df[col].quantile(0.75)),
                "skewness": float(stats.skew(numeric_df[col].dropna())),
                "kurtosis": float(stats.kurtosis(numeric_df[col].dropna())),
            }

        logger.info(f"Calculated summary statistics for {len(summary)} columns")
        return summary

    @staticmethod
    def calculate_correlation_matrix(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """
        Calculate correlation matrix for numeric columns.

        Args:
            df: DataFrame to analyze

        Returns:
            dict: Correlation matrix
        """
        numeric_df = df.select_dtypes(include=[np.number])
        
        if numeric_df.empty:
            return {}

        corr_matrix = numeric_df.corr().round(4)
        
        # Convert to dictionary
        correlation_dict = {}
        for col1 in corr_matrix.columns:
            correlation_dict[col1] = {}
            for col2 in corr_matrix.columns:
                correlation_dict[col1][col2] = float(corr_matrix.loc[col1, col2])

        logger.info(f"Calculated correlation matrix for {len(numeric_df.columns)} columns")
        return correlation_dict

    @staticmethod
    def analyze_distributions(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze distribution of columns.

        Args:
            df: DataFrame to analyze

        Returns:
            dict: Distribution analysis
        """
        distributions = {}
        numeric_df = df.select_dtypes(include=[np.number])

        for col in numeric_df.columns:
            data = numeric_df[col].dropna()
            
            if len(data) == 0:
                continue

            # Check for normality
            _, normality_pvalue = stats.normaltest(data)

            distributions[col] = {
                "distribution_type": "normal" if normality_pvalue > 0.05 else "non-normal",
                "normality_pvalue": float(normality_pvalue),
                "bins": list(pd.cut(data, bins=10).value_counts().sort_index().values),
                "histogram_edges": list(pd.cut(data, bins=10).cat.categories.astype(str)),
            }

        logger.info(f"Analyzed distributions for {len(distributions)} columns")
        return distributions

    @staticmethod
    def analyze_categorical_distributions(df: pd.DataFrame, top_n: int = 10) -> Dict[str, Any]:
        """
        Analyze distribution of categorical columns.

        Args:
            df: DataFrame to analyze
            top_n: Top N categories to include

        Returns:
            dict: Categorical distribution analysis
        """
        categorical_dist = {}
        categorical_cols = df.select_dtypes(include=["object"]).columns

        for col in categorical_cols:
            value_counts = df[col].value_counts()
            
            categorical_dist[col] = {
                "total_unique": int(df[col].nunique()),
                "missing_count": int(df[col].isnull().sum()),
                "top_categories": value_counts.head(top_n).to_dict(),
                "top_categories_percentage": {
                    k: float(v / len(df) * 100)
                    for k, v in value_counts.head(top_n).items()
                },
            }

        logger.info(f"Analyzed {len(categorical_dist)} categorical columns")
        return categorical_dist

    @staticmethod
    def calculate_top_categories(df: pd.DataFrame, top_n: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get top categories from categorical columns.

        Args:
            df: DataFrame to analyze
            top_n: Number of top categories to return

        Returns:
            dict: Top categories per column
        """
        top_categories = {}
        categorical_cols = df.select_dtypes(include=["object"]).columns

        for col in categorical_cols:
            value_counts = df[col].value_counts().head(top_n)
            top_categories[col] = [
                {
                    "category": str(k),
                    "count": int(v),
                    "percentage": float(v / len(df) * 100),
                }
                for k, v in value_counts.items()
            ]

        logger.info(f"Extracted top categories from {len(top_categories)} columns")
        return top_categories

    @staticmethod
    def analyze_growth_trends(
        df: pd.DataFrame,
        date_column: Optional[str] = None,
        value_column: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze growth trends over time.

        Args:
            df: DataFrame to analyze
            date_column: Name of date column
            value_column: Name of value column

        Returns:
            dict: Growth trend analysis
        """
        trends = {}

        # Auto-detect date and value columns if not provided
        if not date_column:
            date_cols = [col for col in df.columns if "date" in col.lower() or "time" in col.lower()]
            if date_cols:
                date_column = date_cols[0]

        if not value_column:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_cols:
                value_column = numeric_cols[0]

        if date_column and value_column:
            try:
                df_temp = df.copy()
                df_temp[date_column] = pd.to_datetime(df_temp[date_column], errors="coerce")
                df_temp = df_temp.sort_values(date_column)

                # Monthly analysis
                df_temp["month"] = df_temp[date_column].dt.to_period("M")
                monthly = df_temp.groupby("month")[value_column].agg(["sum", "mean", "count"])

                trends["monthly"] = {
                    "periods": [str(idx) for idx in monthly.index],
                    "values": monthly["sum"].tolist(),
                    "averages": monthly["mean"].tolist(),
                    "counts": monthly["count"].astype(int).tolist(),
                }

                # Yearly analysis
                df_temp["year"] = df_temp[date_column].dt.year
                yearly = df_temp.groupby("year")[value_column].agg(["sum", "mean", "count"])

                trends["yearly"] = {
                    "years": yearly.index.astype(int).tolist(),
                    "values": yearly["sum"].tolist(),
                    "averages": yearly["mean"].tolist(),
                    "counts": yearly["count"].astype(int).tolist(),
                }

                logger.info("Analyzed growth trends")

            except Exception as e:
                logger.warning(f"Could not analyze growth trends: {e}")

        return trends

    @staticmethod
    def generate_insights(
        df: pd.DataFrame,
        summary_stats: Dict[str, Any],
        correlations: Dict[str, Dict[str, float]],
    ) -> List[str]:
        """
        Generate automated insights from data analysis.

        Args:
            df: DataFrame being analyzed
            summary_stats: Summary statistics
            correlations: Correlation matrix

        Returns:
            list: List of insights
        """
        insights = []

        # Data shape insights
        insights.append(f"Dataset contains {len(df)} rows and {len(df.columns)} columns")

        # Missing data insights
        missing_pct = (df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100
        if missing_pct > 10:
            insights.append(f"Dataset has {missing_pct:.1f}% missing values - consider imputation")
        elif missing_pct > 0:
            insights.append(f"Dataset has {missing_pct:.1f}% missing values - relatively clean")

        # Numeric column insights
        for col, stats_dict in summary_stats.items():
            # High skewness
            if abs(stats_dict["skewness"]) > 1:
                insights.append(f"{col} shows {'right' if stats_dict['skewness'] > 0 else 'left'} skewness - consider transformation")

            # Outliers
            iqr = stats_dict["q75"] - stats_dict["q25"]
            lower_bound = stats_dict["q25"] - 1.5 * iqr
            upper_bound = stats_dict["q75"] + 1.5 * iqr
            
            outlier_count = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
            if outlier_count > 0:
                outlier_pct = (outlier_count / len(df)) * 100
                if outlier_pct > 5:
                    insights.append(f"{col} contains {outlier_pct:.1f}% outliers - review data quality")

        # Correlation insights
        strong_correlations = []
        for col1 in correlations:
            for col2 in correlations[col1]:
                if col1 < col2:  # Avoid duplicates
                    corr_value = correlations[col1][col2]
                    if abs(corr_value) > 0.7:
                        strong_correlations.append((col1, col2, corr_value))

        if strong_correlations:
            insights.append(f"Found {len(strong_correlations)} strong correlations between variables")
            for col1, col2, corr_value in strong_correlations[:3]:
                insights.append(f"  - {col1} and {col2}: {corr_value:.3f}")

        # Categorical insights
        categorical_cols = df.select_dtypes(include=["object"]).columns
        if len(categorical_cols) > 0:
            insights.append(f"Dataset contains {len(categorical_cols)} categorical columns")

        logger.info(f"Generated {len(insights)} insights")
        return insights

    @staticmethod
    def generate_eda_report(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate comprehensive EDA report.

        Args:
            df: DataFrame to analyze

        Returns:
            dict: Complete EDA report
        """
        logger.info(f"Starting EDA for dataset with {len(df)} rows, {len(df.columns)} columns")

        # Calculate all analyses
        summary_stats = EDAEngine.calculate_summary_statistics(df)
        correlations = EDAEngine.calculate_correlation_matrix(df)
        distributions = EDAEngine.analyze_distributions(df)
        categorical_dist = EDAEngine.analyze_categorical_distributions(df)
        top_categories = EDAEngine.calculate_top_categories(df)
        growth_trends = EDAEngine.analyze_growth_trends(df)
        insights = EDAEngine.generate_insights(df, summary_stats, correlations)

        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "dataset_shape": {
                "rows": len(df),
                "columns": len(df.columns),
                "numeric_columns": len(df.select_dtypes(include=[np.number]).columns),
                "categorical_columns": len(df.select_dtypes(include=["object"]).columns),
            },
            "summary_statistics": summary_stats,
            "correlation_matrix": correlations,
            "distributions": distributions,
            "categorical_distributions": categorical_dist,
            "top_categories": top_categories,
            "growth_trends": growth_trends,
            "generated_insights": insights,
        }

        logger.info("EDA report generation complete")
        return report
