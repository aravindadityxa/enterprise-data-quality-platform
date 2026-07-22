"""
Forecasting engine using multiple ML algorithms.

Implements Linear Regression, Random Forest, and basic time-series forecasting.
"""

from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_percentage_error
from datetime import datetime, timedelta
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


class Forecaster:
    """Engine for multi-method forecasting."""

    @staticmethod
    def linear_regression_forecast(
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        periods: int = 12,
    ) -> Dict[str, Any]:
        """
        Forecast using Linear Regression.

        Args:
            df: Historical data
            date_col: Date column name
            value_col: Value column name
            periods: Number of periods to forecast

        Returns:
            dict: Forecast results with metrics
        """
        try:
            df_temp = df.copy()
            df_temp[date_col] = pd.to_datetime(df_temp[date_col])
            df_temp = df_temp.sort_values(date_col).dropna(subset=[value_col])

            # Create time-based features
            df_temp["time_index"] = np.arange(len(df_temp))
            X = df_temp[["time_index"]].values
            y = df_temp[value_col].values

            # Split data
            train_size = int(len(df_temp) * 0.8)
            X_train, X_test = X[:train_size], X[train_size:]
            y_train, y_test = y[:train_size], y[train_size:]

            # Train model
            model = LinearRegression()
            model.fit(X_train, y_train)

            # Evaluate
            y_pred_train = model.predict(X_train)
            y_pred_test = model.predict(X_test)

            rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
            r2 = r2_score(y_test, y_pred_test)

            # Forecast
            last_time = df_temp["time_index"].iloc[-1]
            future_indices = np.arange(last_time + 1, last_time + periods + 1).reshape(-1, 1)
            forecast_values = model.predict(future_indices)

            last_date = df_temp[date_col].iloc[-1]
            forecast_dates = [str((last_date + timedelta(days=i)).date()) for i in range(1, periods + 1)]

            logger.info(f"Linear Regression forecast: R²={r2:.3f}, RMSE={rmse:.2f}")

            return {
                "method": "linear_regression",
                "forecast_values": forecast_values.tolist(),
                "forecast_dates": forecast_dates,
                "r_squared": float(r2),
                "rmse": float(rmse),
                "mape": float(np.mean(np.abs((y_test - y_pred_test) / y_test))) if np.any(y_test != 0) else None,
                "trend": float(model.coef_[0]),
            }

        except Exception as e:
            logger.error(f"Linear Regression forecast error: {e}")
            return {"error": str(e)}

    @staticmethod
    def random_forest_forecast(
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        periods: int = 12,
        lags: int = 7,
    ) -> Dict[str, Any]:
        """
        Forecast using Random Forest with lag features.

        Args:
            df: Historical data
            date_col: Date column name
            value_col: Value column name
            periods: Number of periods to forecast
            lags: Number of lag features

        Returns:
            dict: Forecast results with metrics
        """
        try:
            df_temp = df.copy()
            df_temp[date_col] = pd.to_datetime(df_temp[date_col])
            df_temp = df_temp.sort_values(date_col).dropna(subset=[value_col])

            # Create lag features
            for i in range(1, lags + 1):
                df_temp[f"lag_{i}"] = df_temp[value_col].shift(i)

            df_temp = df_temp.dropna()

            if len(df_temp) < 10:
                return {"error": "Insufficient data for Random Forest"}

            # Prepare data
            feature_cols = [f"lag_{i}" for i in range(1, lags + 1)]
            X = df_temp[feature_cols].values
            y = df_temp[value_col].values

            # Split data
            train_size = int(len(df_temp) * 0.8)
            X_train, X_test = X[:train_size], X[train_size:]
            y_train, y_test = y[:train_size], y[train_size:]

            # Train model
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X_train, y_train)

            # Evaluate
            y_pred_test = model.predict(X_test)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
            r2 = r2_score(y_test, y_pred_test)

            # Forecast
            forecast_values = []
            last_values = df_temp[value_col].iloc[-lags:].values[::-1]

            for _ in range(periods):
                next_value = model.predict([last_values])[0]
                forecast_values.append(next_value)
                last_values = np.roll(last_values, 1)
                last_values[0] = next_value

            last_date = df_temp[date_col].iloc[-1]
            forecast_dates = [str((last_date + timedelta(days=i)).date()) for i in range(1, periods + 1)]

            logger.info(f"Random Forest forecast: R²={r2:.3f}, RMSE={rmse:.2f}")

            return {
                "method": "random_forest",
                "forecast_values": forecast_values,
                "forecast_dates": forecast_dates,
                "r_squared": float(r2),
                "rmse": float(rmse),
                "feature_importance": {f"lag_{i}": float(imp) for i, imp in enumerate(model.feature_importances_)},
            }

        except Exception as e:
            logger.error(f"Random Forest forecast error: {e}")
            return {"error": str(e)}

    @staticmethod
    def exponential_smoothing_forecast(
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        periods: int = 12,
        alpha: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Forecast using Exponential Smoothing.

        Args:
            df: Historical data
            date_col: Date column name
            value_col: Value column name
            periods: Number of periods to forecast
            alpha: Smoothing factor

        Returns:
            dict: Forecast results
        """
        try:
            df_temp = df.copy()
            df_temp[date_col] = pd.to_datetime(df_temp[date_col])
            df_temp = df_temp.sort_values(date_col).dropna(subset=[value_col])

            values = df_temp[value_col].values

            # Apply exponential smoothing
            result = [values[0]]
            for i in range(1, len(values)):
                result.append(alpha * values[i] + (1 - alpha) * result[-1])

            # Forecast
            forecast_values = []
            last_smoothed = result[-1]

            for _ in range(periods):
                forecast_values.append(last_smoothed)

            last_date = df_temp[date_col].iloc[-1]
            forecast_dates = [str((last_date + timedelta(days=i)).date()) for i in range(1, periods + 1)]

            logger.info("Exponential Smoothing forecast completed")

            return {
                "method": "exponential_smoothing",
                "forecast_values": forecast_values,
                "forecast_dates": forecast_dates,
                "alpha": alpha,
            }

        except Exception as e:
            logger.error(f"Exponential Smoothing error: {e}")
            return {"error": str(e)}

    @staticmethod
    def combined_forecast(
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        periods: int = 12,
    ) -> Dict[str, Any]:
        """
        Generate forecasts using all methods.

        Args:
            df: Historical data
            date_col: Date column name
            value_col: Value column name
            periods: Number of periods to forecast

        Returns:
            dict: Combined forecast results
        """
        try:
            lr_forecast = Forecaster.linear_regression_forecast(df, date_col, value_col, periods)
            rf_forecast = Forecaster.random_forest_forecast(df, date_col, value_col, periods)
            es_forecast = Forecaster.exponential_smoothing_forecast(df, date_col, value_col, periods)

            # Ensemble forecast (average)
            forecasts = []
            if "error" not in lr_forecast:
                forecasts.append(np.array(lr_forecast["forecast_values"]))
            if "error" not in rf_forecast:
                forecasts.append(np.array(rf_forecast["forecast_values"]))
            if "error" not in es_forecast:
                forecasts.append(np.array(es_forecast["forecast_values"]))

            ensemble_forecast = np.mean(forecasts, axis=0).tolist() if forecasts else []

            df_temp = df.copy()
            df_temp[date_col] = pd.to_datetime(df_temp[date_col])
            df_temp = df_temp.sort_values(date_col)
            last_date = df_temp[date_col].iloc[-1]
            forecast_dates = [str((last_date + timedelta(days=i)).date()) for i in range(1, periods + 1)]

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "forecast_dates": forecast_dates,
                "linear_regression": lr_forecast,
                "random_forest": rf_forecast,
                "exponential_smoothing": es_forecast,
                "ensemble_forecast": ensemble_forecast,
            }

        except Exception as e:
            logger.error(f"Combined forecast error: {e}")
            return {"error": str(e)}
