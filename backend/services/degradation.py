"""
Battery degradation forecasting with held-out validation.

Model form is physics-informed rather than a black box:

    SOH(t) = 100 - a*sqrt(t) - b*t

  * the sqrt(t) term captures calendar ageing driven by solid-electrolyte
    interphase (SEI) layer growth, which follows a square-root-of-time law
  * the linear t term captures cycling ageing (loss of active material),
    which is approximately linear in throughput

Constraining the functional form this way means we fit only two coefficients,
so the model stays stable on the short, noisy histories available per vehicle
and degrades gracefully out-of-distribution — the failure mode that sinks
unconstrained regressors on battery data.

Accuracy is reported against a persistence baseline (carry the last observed
SoH forward), which is the standard naive forecaster for monotonic series.
"""

import math
from typing import Dict, List, Optional

import numpy as np

EOL_THRESHOLD = 70.0
MIN_HISTORY_POINTS = 6
TRAIN_FRACTION = 0.7


def fit_coefficients(months: List[float], soh: List[float]) -> Dict[str, float]:
    """
    Least-squares fit of [a, b] in SOH = 100 - a*sqrt(t) - b*t.

    Coefficients are clamped non-negative: battery capacity does not recover,
    so an upward-sloping fit would be physically meaningless.
    """
    t = np.asarray(months, dtype=float)
    y = 100.0 - np.asarray(soh, dtype=float)  # cumulative capacity fade

    design = np.column_stack([np.sqrt(t), t])
    coeffs, *_ = np.linalg.lstsq(design, y, rcond=None)
    a, b = float(coeffs[0]), float(coeffs[1])
    return {"a_calendar": max(a, 0.0), "b_cycling": max(b, 0.0)}


def predict(months: List[float], coeffs: Dict[str, float]) -> List[float]:
    """Predicted SoH at each month offset."""
    a, b = coeffs["a_calendar"], coeffs["b_cycling"]
    return [100.0 - a * math.sqrt(t) - b * t for t in months]


def forecast_rul_months(current_month: float, coeffs: Dict[str, float]) -> Optional[int]:
    """
    Months from now until SoH crosses the automotive EOL threshold.
    Solved by forward search (the curve is monotonic, so this is exact
    to the month without needing a closed-form inverse).
    """
    a, b = coeffs["a_calendar"], coeffs["b_cycling"]
    if a <= 0 and b <= 0:
        return None  # no measurable degradation trend
    for step in range(0, 241):
        t = current_month + step
        if 100.0 - a * math.sqrt(t) - b * t <= EOL_THRESHOLD:
            return step
    return None  # beyond a 20-year horizon


def _rmse(actual: List[float], pred: List[float]) -> float:
    a, p = np.asarray(actual), np.asarray(pred)
    return float(np.sqrt(np.mean((a - p) ** 2)))


def _mae(actual: List[float], pred: List[float]) -> float:
    a, p = np.asarray(actual), np.asarray(pred)
    return float(np.mean(np.abs(a - p)))


def evaluate_vehicle(vehicle: Dict) -> Optional[Dict]:
    """
    Fit on the earlier portion of a vehicle's history and score on the
    held-out tail against a persistence baseline.
    """
    history = vehicle["battery"]["degradation_history"]
    if len(history) < MIN_HISTORY_POINTS:
        return None

    months = [float(i + 1) for i in range(len(history))]
    soh = [float(h["soh"]) for h in history]

    split = int(len(history) * TRAIN_FRACTION)
    if split < 3 or len(history) - split < 2:
        return None

    train_m, train_s = months[:split], soh[:split]
    test_m, test_s = months[split:], soh[split:]

    coeffs = fit_coefficients(train_m, train_s)
    model_pred = predict(test_m, coeffs)

    # Persistence baseline: last observed training value, carried forward.
    baseline_pred = [train_s[-1]] * len(test_s)

    model_rmse = _rmse(test_s, model_pred)
    baseline_rmse = _rmse(test_s, baseline_pred)

    return {
        "vehicle_id": vehicle["id"],
        "model": vehicle["model"],
        "chemistry_capacity_kwh": vehicle["battery_kwh"],
        "history_points": len(history),
        "train_points": len(train_m),
        "test_points": len(test_m),
        "coefficients": {
            "a_calendar_sei": round(coeffs["a_calendar"], 4),
            "b_cycling": round(coeffs["b_cycling"], 4),
        },
        "model_rmse": round(model_rmse, 3),
        "model_mae": round(_mae(test_s, model_pred), 3),
        "baseline_rmse": round(baseline_rmse, 3),
        "baseline_mae": round(_mae(test_s, baseline_pred), 3),
        "rmse_improvement_pct": round(
            (baseline_rmse - model_rmse) / baseline_rmse * 100, 1
        ) if baseline_rmse > 0 else 0.0,
        "current_soh": vehicle["battery"]["soh_pct"],
        "forecast_rul_months": forecast_rul_months(months[-1], coeffs),
    }


def evaluate_fleet(ev_vehicles: List[Dict]) -> Dict:
    """Fleet-wide held-out accuracy of the degradation model vs baseline."""
    results = [r for r in (evaluate_vehicle(v) for v in ev_vehicles) if r]
    if not results:
        return {"summary": {"evaluated_vehicles": 0}, "per_vehicle": []}

    model_rmse = float(np.mean([r["model_rmse"] for r in results]))
    baseline_rmse = float(np.mean([r["baseline_rmse"] for r in results]))
    model_mae = float(np.mean([r["model_mae"] for r in results]))
    baseline_mae = float(np.mean([r["baseline_mae"] for r in results]))
    beat_baseline = len([r for r in results if r["model_rmse"] < r["baseline_rmse"]])

    return {
        "summary": {
            "evaluated_vehicles": len(results),
            "validation": "hold-out (last 30% of each vehicle's history)",
            "model": "SOH(t) = 100 - a*sqrt(t) - b*t  [SEI calendar + cycling]",
            "baseline": "persistence (last observed SoH carried forward)",
            "model_rmse_pct_soh": round(model_rmse, 3),
            "baseline_rmse_pct_soh": round(baseline_rmse, 3),
            "model_mae_pct_soh": round(model_mae, 3),
            "baseline_mae_pct_soh": round(baseline_mae, 3),
            "rmse_improvement_pct": round(
                (baseline_rmse - model_rmse) / baseline_rmse * 100, 1
            ) if baseline_rmse > 0 else 0.0,
            "vehicles_beating_baseline": beat_baseline,
            "beat_baseline_pct": round(beat_baseline / len(results) * 100, 1),
        },
        "per_vehicle": sorted(results, key=lambda r: r["model_rmse"]),
    }


def forecast_curve(vehicle: Dict, horizon_months: int = 36) -> Dict:
    """
    Fit on a vehicle's full history and project forward — used to draw the
    observed-vs-predicted degradation curve in the UI.
    """
    history = vehicle["battery"]["degradation_history"]
    if len(history) < 3:
        return {"vehicle_id": vehicle["id"], "observed": [], "forecast": []}

    months = [float(i + 1) for i in range(len(history))]
    soh = [float(h["soh"]) for h in history]
    coeffs = fit_coefficients(months, soh)

    observed = [
        {"month_index": int(m), "label": h["month"], "soh": s, "fitted": round(p, 2)}
        for m, h, s, p in zip(months, history, soh, predict(months, coeffs))
    ]

    last = months[-1]
    future_m = [last + i for i in range(1, horizon_months + 1)]
    forecast = [
        {"month_index": int(m), "soh": round(p, 2)}
        for m, p in zip(future_m, predict(future_m, coeffs))
    ]

    return {
        "vehicle_id": vehicle["id"],
        "coefficients": {
            "a_calendar_sei": round(coeffs["a_calendar"], 4),
            "b_cycling": round(coeffs["b_cycling"], 4),
        },
        "eol_threshold": EOL_THRESHOLD,
        "forecast_rul_months": forecast_rul_months(last, coeffs),
        "observed": observed,
        "forecast": forecast,
    }
