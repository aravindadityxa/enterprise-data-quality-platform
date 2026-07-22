"""
Anomaly detection engine using multiple algorithms.

Implements Isolation Forest, Z-score, and IQR methods for detecting anomalies.
"""

from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from scipy import stats
from datetime import datetime
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


class AnomalyDetector:
    """Engine for multi-method anomaly detection."""

    @staticmethod
    def isolation_forest(
        df: pd.DataFrame,
        contamination: float = 0.05,
        columns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Detect anomalies using Isolation Forest.

        Args:
            df: DataFrame to analyze
            contamination: Expected proportion of anomalies
            columns: Columns to analyze (default: all numeric)

        Returns:
            dict: Anomaly detection results
        """
        try:
            numeric_df = df.select_dtypes(include=[np.number])

            if numeric_df.empty:
                return {"method": "isolation_forest", "anomalies": [], "scores": {}}

            if columns:
                numeric_df = numeric_df[[c for c in columns if c in numeric_df.columns]]

            # Train model
            model = IsolationForest(contamination=contamination, random_state=42)
            predictions = model.fit_predict(numeric_df)
            scores = model.score_samples(numeric_df)

            # Extract anomalies
            anomalies = []
            for idx, (pred, score) in enumerate(zip(predictions, scores)):
                if pred == -1:
                    anomalies.append({
                        "row_index": int(idx),
                        "anomaly_score": float(score),
                        "values": {col: numeric_df.iloc[idx][col] for col in numeric_df.columns},
                    })

            logger.info(f"Isolation Forest: Found {len(anomalies)} anomalies")

            return {
                "method": "isolation_forest",
                "anomalies": sorted(anomalies, key=lambda x: x["anomaly_score"])[:100],
                "total_anomalies": len(anomalies),
                "contamination": contamination,
            }

        except Exception as e:
            logger.error(f"Isolation Forest error: {e}")
            return {"method": "isolation_forest", "error": str(e), "anomalies": []}

    @staticmethod
    def z_score_method(
        df: pd.DataFrame,
        threshold: float = 3.0,
        columns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Detect anomalies using Z-score method.

        Args:
            df: DataFrame to analyze
            threshold: Z-score threshold (typically 2-3)
            columns: Columns to analyze (default: all numeric)

        Returns:
            dict: Anomaly detection results
        """
        try:
            numeric_df = df.select_dtypes(include=[np.number])

            if numeric_df.empty:
                return {"method": "z_score", "anomalies": [], "threshold": threshold}

            if columns:
                numeric_df = numeric_df[[c for c in columns if c in numeric_df.columns]]

            anomalies = []

            for col in numeric_df.columns:
                z_scores = np.abs(stats.zscore(numeric_df[col].dropna()))
                anomaly_mask = z_scores > threshold

                for idx, is_anomaly in enumerate(anomaly_mask):
                    if is_anomaly:
                        original_idx = numeric_df[col].dropna().index[idx]
                        anomalies.append({
                            "row_index": int(original_idx),
                            "column": col,
                            "value": float(numeric_df.loc[original_idx, col]),
                            "z_score": float(z_scores[idx]),
                            "mean": float(numeric_df[col].mean()),
                            "std": float(numeric_df[col].std()),
                        })

            logger.info(f"Z-score: Found {len(anomalies)} anomalies")

            return {
                "method": "z_score",
                "anomalies": sorted(anomalies, key=lambda x: abs(x["z_score"]), reverse=True)[:100],
                "total_anomalies": len(anomalies),
                "threshold": threshold,
            }

        except Exception as e:
            logger.error(f"Z-score error: {e}")
            return {"method": "z_score", "error": str(e), "anomalies": []}

    @staticmethod
    def iqr_method(
        df: pd.DataFrame,
        multiplier: float = 1.5,
        columns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Detect anomalies using IQR (Interquartile Range) method.

        Args:
            df: DataFrame to analyze
            multiplier: IQR multiplier (typically 1.5)
            columns: Columns to analyze (default: all numeric)

        Returns:
            dict: Anomaly detection results
        """
        try:
            numeric_df = df.select_dtypes(include=[np.number])

            if numeric_df.empty:
                return {"method": "iqr", "anomalies": [], "multiplier": multiplier}

            if columns:
                numeric_df = numeric_df[[c for c in columns if c in numeric_df.columns]]

            anomalies = []

            for col in numeric_df.columns:
                Q1 = numeric_df[col].quantile(0.25)
                Q3 = numeric_df[col].quantile(0.75)
                IQR = Q3 - Q1

                lower_bound = Q1 - multiplier * IQR
                upper_bound = Q3 + multiplier * IQR

                for idx, value in enumerate(numeric_df[col]):
                    if pd.isna(value):
                        continue

                    if value < lower_bound or value > upper_bound:
                        anomalies.append({
                            "row_index": int(idx),
                            "column": col,
                            "value": float(value),
                            "lower_bound": float(lower_bound),
                            "upper_bound": float(upper_bound),
                            "distance_from_bounds": float(min(
                                abs(value - lower_bound),
                                abs(value - upper_bound)
                            )),
                        })

            logger.info(f"IQR: Found {len(anomalies)} anomalies")

            return {
                "method": "iqr",
                "anomalies": sorted(anomalies, key=lambda x: x["distance_from_bounds"], reverse=True)[:100],
                "total_anomalies": len(anomalies),
                "multiplier": multiplier,
            }

        except Exception as e:
            logger.error(f"IQR error: {e}")
            return {"method": "iqr", "error": str(e), "anomalies": []}

    @staticmethod
    def combined_detection(
        df: pd.DataFrame,
        z_threshold: float = 3.0,
        if_contamination: float = 0.05,
        iqr_multiplier: float = 1.5,
    ) -> Dict[str, Any]:
        """
        Run all three methods and combine results.

        Args:
            df: DataFrame to analyze
            z_threshold: Z-score threshold
            if_contamination: Isolation Forest contamination
            iqr_multiplier: IQR multiplier

        Returns:
            dict: Combined anomaly detection results
        """
        try:
            z_results = AnomalyDetector.z_score_method(df, z_threshold)
            if_results = AnomalyDetector.isolation_forest(df, if_contamination)
            iqr_results = AnomalyDetector.iqr_method(df, iqr_multiplier)

            # Combine results
            anomaly_indices = set()

            for anomaly in z_results.get("anomalies", []):
                anomaly_indices.add(anomaly["row_index"])

            for anomaly in if_results.get("anomalies", []):
                anomaly_indices.add(anomaly["row_index"])

            for anomaly in iqr_results.get("anomalies", []):
                anomaly_indices.add(anomaly["row_index"])

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "z_score": z_results,
                "isolation_forest": if_results,
                "iqr": iqr_results,
                "unique_anomalies": len(anomaly_indices),
                "anomalous_rows": sorted(list(anomaly_indices)),
            }

        except Exception as e:
            logger.error(f"Combined detection error: {e}")
            return {"error": str(e)}

    @staticmethod
    def detect_sales_spikes(
        df: pd.DataFrame,
        date_col: Optional[str] = None,
        amount_col: Optional[str] = None,
        threshold: float = 2.0,
    ) -> Dict[str, Any]:
        """
        Detect sales spikes using time-series analysis.

        Args:
            df: DataFrame with time-series data
            date_col: Date column name
            amount_col: Amount column name
            threshold: Standard deviation threshold

        Returns:
            dict: Detected spikes
        """
        try:
            if not date_col or not amount_col:
                return {"error": "Date and amount columns required"}

            df_temp = df.copy()
            df_temp[date_col] = pd.to_datetime(df_temp[date_col], errors="coerce")
            df_temp = df_temp.sort_values(date_col)

            # Calculate rolling statistics
            df_temp["ma"] = df_temp[amount_col].rolling(window=7, min_periods=1).mean()
            df_temp["std"] = df_temp[amount_col].rolling(window=7, min_periods=1).std()

            spikes = []
            for idx, row in df_temp.iterrows():
                if pd.isna(row["std"]) or row["std"] == 0:
                    continue

                z_score = (row[amount_col] - row["ma"]) / row["std"]

                if abs(z_score) > threshold:
                    spikes.append({
                        "date": str(row[date_col]),
                        "amount": float(row[amount_col]),
                        "moving_average": float(row["ma"]),
                        "z_score": float(z_score),
                        "spike_type": "spike" if z_score > 0 else "dip",
                    })

            logger.info(f"Detected {len(spikes)} sales spikes")

            return {
                "method": "sales_spike_detection",
                "total_spikes": len(spikes),
                "spikes": spikes,
            }

        except Exception as e:
            logger.error(f"Sales spike detection error: {e}")
            return {"error": str(e)}
