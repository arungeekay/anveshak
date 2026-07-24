"""forecast tool (contracts.md §7): weekly SARIMA per district x sub-head.

Backtests against a held-out tail and reports MAE vs a seasonal-naive baseline
(value from 52 weeks earlier). Refuses when history is too thin.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from ..db import get_connection

MIN_WEEKS = 80


def _weekly_series(con, district: str, sub_head: str) -> pd.Series:
    rows = con.execute("""
        SELECT CAST(date_trunc('week', CrimeRegisteredDate) AS DATE) wk, COUNT(*) n
        FROM vw_case_360 WHERE district = ? AND crime_sub_head = ?
        GROUP BY wk ORDER BY wk
    """, [district, sub_head]).fetchall()
    if not rows:
        return pd.Series(dtype=float)
    s = pd.Series({pd.Timestamp(r[0]): r[1] for r in rows})
    idx = pd.date_range(s.index.min(), s.index.max(), freq="W-MON")
    return s.reindex(idx, fill_value=0).astype(float)


def _seasonal_naive_mae(series: pd.Series, holdout: int, period: int = 52) -> float:
    if len(series) <= holdout + period:
        return float("nan")
    test = series.iloc[-holdout:]
    pred = series.shift(period).iloc[-holdout:]
    return float(np.mean(np.abs(test.values - pred.values)))


def forecast(district: str, crime_sub_head: str, horizon_weeks: int = 8, con=None) -> dict:
    con = con or get_connection()
    series = _weekly_series(con, district, crime_sub_head)
    if len(series) < MIN_WEEKS or series.sum() < 30:
        return {"error": "insufficient history to forecast",
                "weeks": int(len(series)), "total": int(series.sum())}

    from statsmodels.tsa.statespace.sarimax import SARIMAX

    def _fit(endog):
        # method='nm' avoids the scipy>=1.15 / statsmodels lbfgs `disp` incompatibility.
        return SARIMAX(endog, order=(1, 1, 1), seasonal_order=(1, 0, 1, 52),
                       enforce_stationarity=False, enforce_invertibility=False
                       ).fit(method="nm", maxiter=400, disp=False)

    holdout = horizon_weeks
    train, test = series.iloc[:-holdout], series.iloc[-holdout:]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            pred = _fit(train).forecast(holdout)
            backtest_mae = float(np.mean(np.abs(test.values - np.asarray(pred))))
            fc = _fit(series).get_forecast(horizon_weeks)
            mean = np.asarray(fc.predicted_mean)
            ci = np.asarray(fc.conf_int(alpha=0.2))
        except Exception as exc:  # pragma: no cover - model instability
            return {"error": f"model fit failed: {exc}", "weeks": int(len(series))}

    baseline_mae = _seasonal_naive_mae(series, holdout)
    future_idx = pd.date_range(series.index.max(), periods=horizon_weeks + 1, freq="W-MON")[1:]
    return {
        "history": [{"week": str(w.date()), "count": int(v)} for w, v in series.items()],
        "forecast": [{"week": str(w.date()), "mean": round(float(m), 2),
                      "lo": round(float(max(0, lo)), 2), "hi": round(float(hi), 2)}
                     for w, m, (lo, hi) in zip(future_idx, mean, ci, strict=True)],
        "backtest_mae": round(backtest_mae, 3),
        "baseline_mae": round(baseline_mae, 3) if baseline_mae == baseline_mae else None,
    }
