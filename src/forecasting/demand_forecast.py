"""
SupplyVision – Demand Forecasting Module
Implements:
  1. Linear Regression baseline
  2. SARIMA time-series model (via statsmodels)
  3. Inventory requirement projection
  4. Forecast accuracy evaluation
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

try:
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    logger.warning("statsmodels not available – SARIMA disabled.")

PROCESSED_DIR = Path("data/processed")
EXPORT_DIR = Path("data/exports")
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


# ─── Helper: aggregate monthly demand ────────────────────────────────────────
def build_monthly_demand(orders: pd.DataFrame) -> pd.DataFrame:
    o = orders[orders["Order_Status"] != "Cancelled"].copy()
    o["Order_Date"] = pd.to_datetime(o["Order_Date"])
    monthly = (
        o.resample("ME", on="Order_Date")
        .agg(Total_Quantity=("Quantity", "sum"), Total_Revenue=("Revenue", "sum"))
        .reset_index()
        .rename(columns={"Order_Date": "Month"})
    )
    monthly["Month_Num"] = range(len(monthly))
    return monthly


def build_product_monthly(orders: pd.DataFrame, product_id: str) -> pd.DataFrame:
    o = orders[(orders["Order_Status"] != "Cancelled") & (orders["Product_ID"] == product_id)].copy()
    o["Order_Date"] = pd.to_datetime(o["Order_Date"])
    monthly = (
        o.resample("ME", on="Order_Date")
        .agg(Total_Quantity=("Quantity", "sum"))
        .reset_index()
        .rename(columns={"Order_Date": "Month"})
    )
    return monthly


# ─── 1. Linear Regression Forecast ───────────────────────────────────────────
class LinearDemandForecaster:
    """
    Univariate linear regression on monthly demand (time index as feature).
    Extended with lag and rolling-mean features for better accuracy.
    """

    def __init__(self, horizon_months: int = 6):
        self.horizon = horizon_months
        self.model = LinearRegression()
        self.scaler = StandardScaler()
        self._trained = False
        self.metrics: dict[str, float] = {}

    def _build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy().reset_index(drop=True)
        df["t"] = range(len(df))
        df["lag_1"] = df["Total_Quantity"].shift(1)
        df["lag_2"] = df["Total_Quantity"].shift(2)
        df["rolling_3"] = df["Total_Quantity"].rolling(3).mean()
        df["month_sin"] = np.sin(2 * np.pi * df["Month"].dt.month / 12)
        df["month_cos"] = np.cos(2 * np.pi * df["Month"].dt.month / 12)
        df.dropna(inplace=True)
        return df

    def fit(self, df: pd.DataFrame) -> "LinearDemandForecaster":
        df = self._build_features(df)
        feature_cols = ["t", "lag_1", "lag_2", "rolling_3", "month_sin", "month_cos"]
        X = df[feature_cols].values
        y = df["Total_Quantity"].values

        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        X_train_s = self.scaler.fit_transform(X_train)
        X_test_s = self.scaler.transform(X_test)

        self.model.fit(X_train_s, y_train)
        self._trained = True
        self._last_df = df
        self._feature_cols = feature_cols

        if len(y_test) > 0:
            y_pred = self.model.predict(X_test_s)
            self.metrics = {
                "MAE": round(float(mean_absolute_error(y_test, y_pred)), 2),
                "RMSE": round(float(np.sqrt(mean_squared_error(y_test, y_pred))), 2),
                "R2": round(float(r2_score(y_test, y_pred)), 4),
                "MAPE": round(
                    float(np.mean(np.abs((y_test - y_pred) / np.maximum(y_test, 1))) * 100), 2
                ),
            }
            logger.info(f"Linear model metrics: {self.metrics}")
        return self

    def predict(self) -> pd.DataFrame:
        if not self._trained:
            raise RuntimeError("Call fit() before predict()")

        last_row = self._last_df.iloc[-1]
        last_month = self._last_df["Month"].max()
        history = list(self._last_df["Total_Quantity"].values)

        rows = []
        for i in range(self.horizon):
            next_month = last_month + pd.DateOffset(months=i + 1)
            t = int(last_row["t"]) + i + 1
            lag1 = history[-1]
            lag2 = history[-2] if len(history) >= 2 else lag1
            roll3 = np.mean(history[-3:]) if len(history) >= 3 else lag1
            msin = np.sin(2 * np.pi * next_month.month / 12)
            mcos = np.cos(2 * np.pi * next_month.month / 12)
            X = np.array([[t, lag1, lag2, roll3, msin, mcos]])
            X_s = self.scaler.transform(X)
            pred = max(0, float(self.model.predict(X_s)[0]))
            history.append(pred)
            rows.append({"Month": next_month, "Forecast_Quantity": round(pred, 0), "Model": "Linear Regression"})

        return pd.DataFrame(rows)


# ─── 2. Exponential Smoothing / SARIMA ────────────────────────────────────────
class TimeSeriesForecaster:
    """
    Holt-Winters Exponential Smoothing with seasonal decomposition.
    Falls back gracefully when series is too short.
    """

    def __init__(self, horizon_months: int = 6, seasonal_periods: int = 12):
        self.horizon = horizon_months
        self.seasonal_periods = seasonal_periods
        self.model = None
        self.metrics: dict[str, float] = {}

    def fit(self, df: pd.DataFrame) -> "TimeSeriesForecaster":
        if not STATSMODELS_AVAILABLE:
            logger.warning("statsmodels not available; TimeSeriesForecaster skipped.")
            return self

        ts = df.set_index("Month")["Total_Quantity"].astype(float)
        seasonal = "add" if len(ts) >= self.seasonal_periods * 2 else None

        try:
            self.model = ExponentialSmoothing(
                ts,
                trend="add",
                seasonal=seasonal,
                seasonal_periods=self.seasonal_periods if seasonal else None,
                initialization_method="estimated",
            ).fit(optimized=True)
        except Exception as exc:
            logger.warning(f"ExponentialSmoothing failed ({exc}); using SARIMA.")
            self._fit_sarima(ts)

        # Evaluate on hold-out
        split = int(len(ts) * 0.8)
        if split > 0 and self.model is not None:
            y_true = ts.iloc[split:].values
            fitted = self.model.fittedvalues.iloc[split:].values
            if len(y_true) > 0:
                mae = mean_absolute_error(y_true, fitted)
                rmse = np.sqrt(mean_squared_error(y_true, fitted))
                self.metrics = {"MAE": round(mae, 2), "RMSE": round(rmse, 2)}
                logger.info(f"TS model metrics: {self.metrics}")

        self._last_month = ts.index[-1]
        return self

    def _fit_sarima(self, ts: pd.Series) -> None:
        self.model = SARIMAX(ts, order=(1, 1, 1), seasonal_order=(0, 1, 1, 12)).fit(disp=False)

    def predict(self) -> pd.DataFrame:
        if self.model is None:
            return pd.DataFrame(columns=["Month", "Forecast_Quantity", "Model"])

        forecast = self.model.forecast(self.horizon)
        rows = []
        for i, val in enumerate(forecast):
            month = self._last_month + pd.DateOffset(months=i + 1)
            rows.append({
                "Month": month,
                "Forecast_Quantity": max(0, round(float(val), 0)),
                "Model": "Exp. Smoothing",
            })
        return pd.DataFrame(rows)


# ─── 3. Inventory Requirement Projection ─────────────────────────────────────
def project_inventory_requirements(
    forecast_df: pd.DataFrame,
    avg_lead_time_days: float = 14,
    safety_stock_factor: float = 1.5,
) -> pd.DataFrame:
    """
    From monthly demand forecast, derive recommended order quantities
    and reorder timing based on lead time.
    """
    df = forecast_df.copy()
    daily_demand = df["Forecast_Quantity"] / 30
    df["Safety_Stock_Required"] = (daily_demand * avg_lead_time_days * safety_stock_factor).round(0)
    df["Reorder_Quantity"] = (df["Forecast_Quantity"] + df["Safety_Stock_Required"]).round(0)
    df["Reorder_Date"] = df["Month"] - pd.to_timedelta(avg_lead_time_days, unit="D")
    return df


# ─── 4. Forecast Accuracy KPI ─────────────────────────────────────────────────
def forecast_accuracy(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    mape = np.mean(np.abs((actual - predicted) / np.maximum(actual, 1))) * 100
    accuracy = max(0, 100 - mape)
    return {
        "MAPE": round(float(mape), 2),
        "Forecast_Accuracy_Pct": round(float(accuracy), 2),
        "MAE": round(float(mean_absolute_error(actual, predicted)), 2),
        "RMSE": round(float(np.sqrt(mean_squared_error(actual, predicted))), 2),
    }


# ─── 5. Full Forecasting Pipeline ─────────────────────────────────────────────
def run_forecasting(orders: pd.DataFrame, horizon_months: int = 6) -> dict[str, Any]:
    logger.info("═══ SupplyVision Forecasting Pipeline ═══")

    monthly = build_monthly_demand(orders)
    logger.info(f"Monthly demand series: {len(monthly)} periods")

    # Linear Regression
    lr = LinearDemandForecaster(horizon_months=horizon_months)
    lr.fit(monthly)
    lr_forecast = lr.predict()

    # Time Series
    ts = TimeSeriesForecaster(horizon_months=horizon_months)
    ts.fit(monthly)
    ts_forecast = ts.predict()

    # Inventory projection from linear forecast
    inv_req = project_inventory_requirements(lr_forecast)

    # Ensemble: average of both forecasts where available
    if len(ts_forecast) > 0:
        ensemble = lr_forecast.copy()
        ensemble["Forecast_Quantity"] = (
            (lr_forecast["Forecast_Quantity"] + ts_forecast["Forecast_Quantity"]) / 2
        ).round(0)
        ensemble["Model"] = "Ensemble"
    else:
        ensemble = lr_forecast.copy()

    # Save outputs
    lr_forecast.to_csv(EXPORT_DIR / "forecast_linear.csv", index=False)
    if len(ts_forecast) > 0:
        ts_forecast.to_csv(EXPORT_DIR / "forecast_ts.csv", index=False)
    ensemble.to_csv(EXPORT_DIR / "forecast_ensemble.csv", index=False)
    inv_req.to_csv(EXPORT_DIR / "inventory_requirements.csv", index=False)

    logger.success("Forecasting pipeline complete. Outputs saved to data/exports/")

    return {
        "monthly_historical": monthly,
        "lr_forecast": lr_forecast,
        "ts_forecast": ts_forecast,
        "ensemble_forecast": ensemble,
        "inventory_requirements": inv_req,
        "lr_metrics": lr.metrics,
        "ts_metrics": ts.metrics,
    }


if __name__ == "__main__":
    orders = pd.read_parquet(PROCESSED_DIR / "orders_clean.parquet")
    results = run_forecasting(orders, horizon_months=6)
    print("\nEnsemble Forecast:")
    print(results["ensemble_forecast"].to_string(index=False))
    print("\nLR Metrics:", results["lr_metrics"])
