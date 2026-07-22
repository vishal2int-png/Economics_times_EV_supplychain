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


# Candidate recency weightings tried during model selection. None means an
# unweighted fit; an integer d weights observations by exp(-age / (n/d)), so
# larger d discounts older cycles harder.
WEIGHTING_CANDIDATES = [None, 2, 3, 5]


def fit_coefficients(
    months: List[float], soh: List[float], weight_divisor: Optional[int] = None
) -> Dict[str, float]:
    """
    Least-squares fit of [a, b] in SOH = 100 - a*sqrt(t) - b*t.

    Coefficients are clamped non-negative: battery capacity does not recover,
    so an upward-sloping fit would be physically meaningless.

    `weight_divisor` optionally applies exponential recency weighting. Cells
    that enter the capacity "knee" — accelerated non-linear fade near end of
    life — are poorly described by their own early history, and weighting
    recent cycles more heavily tracks the current degradation regime.
    """
    t = np.asarray(months, dtype=float)
    y = 100.0 - np.asarray(soh, dtype=float)  # cumulative capacity fade
    design = np.column_stack([np.sqrt(t), t])

    if weight_divisor:
        tau = max(len(t) / weight_divisor, 1e-6)
        age = len(t) - 1 - np.arange(len(t))
        w = np.sqrt(np.exp(-age / tau))
        coeffs, *_ = np.linalg.lstsq(design * w[:, None], y * w, rcond=None)
    else:
        coeffs, *_ = np.linalg.lstsq(design, y, rcond=None)

    return {"a_calendar": max(float(coeffs[0]), 0.0), "b_cycling": max(float(coeffs[1]), 0.0)}


def select_and_fit(t: List[float], soh: List[float]) -> Dict:
    """
    Choose a weighting on an inner split of the training data, then refit on
    all of it.

    The selection split is carved out of the training data only — the held-out
    test data is never consulted, so the reported accuracy stays honest.
    """
    if len(t) < 8:
        return {"coefficients": fit_coefficients(t, soh), "weighting": None}

    inner = int(len(t) * 0.75)
    best, best_err = None, float("inf")
    for cand in WEIGHTING_CANDIDATES:
        coeffs = fit_coefficients(t[:inner], soh[:inner], cand)
        err = _rmse(soh[inner:], predict(t[inner:], coeffs))
        if err < best_err:
            best_err, best = err, cand

    return {"coefficients": fit_coefficients(t, soh, best), "weighting": best}


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

    selection = select_and_fit(train_m, train_s)
    coeffs = selection["coefficients"]
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
        "weighting_selected": selection["weighting"],
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


def evaluate_nasa() -> Dict:
    """
    Validate the same model against real measured cells from the NASA PCoE
    ageing dataset.

    This is the honest accuracy number: the synthetic fleet is generated by a
    process we wrote, so fitting it well is partly circular. These are lab
    cells cycled to failure, and the model has never seen them.

    Two things are scored:
      1. Capacity-fade forecasting on a held-out tail, vs a persistence baseline.
      2. Remaining-useful-life error, in cycles, against the measured cycle at
         which each cell actually crossed the end-of-life threshold.
    """
    from services import nasa_data

    cells = nasa_data.load_cells()
    per_cell: List[Dict] = []

    for name, df in sorted(cells.items()):
        cycles = df["cycle"].astype(float).tolist()
        soh = df["soh_pct"].astype(float).tolist()

        split = int(len(cycles) * TRAIN_FRACTION)
        if split < 5 or len(cycles) - split < 3:
            continue

        train_c, train_s = cycles[:split], soh[:split]
        test_c, test_s = cycles[split:], soh[split:]

        selection = select_and_fit(train_c, train_s)
        coeffs = selection["coefficients"]
        model_pred = predict(test_c, coeffs)
        baseline_pred = [train_s[-1]] * len(test_s)

        model_rmse = _rmse(test_s, model_pred)
        baseline_rmse = _rmse(test_s, baseline_pred)

        # Ground-truth EOL: first measured cycle at or below the threshold.
        true_eol_cycle = next(
            (int(c) for c, s in zip(cycles, soh) if s <= nasa_data.EOL_SOH_PCT), None
        )

        # RUL is forecast from half-life, not from the 70% training split.
        # At 70% the cell is nearly dead, leaving only a handful of cycles of
        # true runway, so percentage error explodes on a tiny denominator and
        # says more about the denominator than the model. Half-life is also
        # the operationally useful question: "how long have I got?"
        rul_entry = None
        rul_origin = int(len(cycles) * 0.5)
        if true_eol_cycle is None:
            rul_status = "never_reaches_eol"
        elif true_eol_cycle <= cycles[rul_origin]:
            rul_status = "eol_before_forecast_origin"
        else:
            rul_status = "evaluated"
            origin_cycle = cycles[rul_origin]
            rul_coeffs = select_and_fit(cycles[:rul_origin], soh[:rul_origin])["coefficients"]
            true_rul = true_eol_cycle - origin_cycle
            predicted_rul = forecast_rul_months(origin_cycle, rul_coeffs)  # cycles here
            if predicted_rul is None:
                rul_status = "no_degradation_trend"
            else:
                rul_entry = {
                    "forecast_from_cycle": int(origin_cycle),
                    "true_eol_cycle": true_eol_cycle,
                    "true_rul_cycles": int(true_rul),
                    "predicted_rul_cycles": int(predicted_rul),
                    "error_cycles": int(predicted_rul - true_rul),
                    # Normalised against total cell life, which is a stable
                    # denominator, unlike the few cycles left near EOL.
                    "error_pct_of_cell_life": round(
                        abs(predicted_rul - true_rul) / len(cycles) * 100, 1
                    ),
                }

        per_cell.append({
            "cell": name,
            "cycles": len(cycles),
            "train_cycles": len(train_c),
            "test_cycles": len(test_c),
            "coefficients": {
                "a_calendar_sei": round(coeffs["a_calendar"], 4),
                "b_cycling": round(coeffs["b_cycling"], 4),
            },
            "weighting_selected": selection["weighting"],
            "model_rmse": round(model_rmse, 3),
            "model_mae": round(_mae(test_s, model_pred), 3),
            "baseline_rmse": round(baseline_rmse, 3),
            "baseline_mae": round(_mae(test_s, baseline_pred), 3),
            "rmse_improvement_pct": round(
                (baseline_rmse - model_rmse) / baseline_rmse * 100, 1
            ) if baseline_rmse > 0 else 0.0,
            "reaches_eol": true_eol_cycle is not None,
            "rul_status": rul_status,
            "rul": rul_entry,
        })

    if not per_cell:
        return {"summary": {"evaluated_cells": 0}, "per_cell": []}

    model_rmse = float(np.mean([c["model_rmse"] for c in per_cell]))
    baseline_rmse = float(np.mean([c["baseline_rmse"] for c in per_cell]))
    beat = len([c for c in per_cell if c["model_rmse"] < c["baseline_rmse"]])
    rul_cells = [c["rul"] for c in per_cell if c["rul"]]

    summary = {
        "dataset": "NASA PCoE Li-ion Battery Aging Dataset (community mirror)",
        "data_type": "real measured cells",
        "evaluated_cells": len(per_cell),
        "total_cycles": int(sum(c["cycles"] for c in per_cell)),
        "validation": "hold-out (last 30% of each cell's cycle history)",
        "model": "SOH(t) = 100 - a*sqrt(t) - b*t  [SEI calendar + cycling]",
        "baseline": "persistence (last observed SoH carried forward)",
        "model_rmse_pct_soh": round(model_rmse, 3),
        "baseline_rmse_pct_soh": round(baseline_rmse, 3),
        "model_mae_pct_soh": round(float(np.mean([c["model_mae"] for c in per_cell])), 3),
        "baseline_mae_pct_soh": round(float(np.mean([c["baseline_mae"] for c in per_cell])), 3),
        "rmse_improvement_pct": round(
            (baseline_rmse - model_rmse) / baseline_rmse * 100, 1
        ) if baseline_rmse > 0 else 0.0,
        "cells_beating_baseline": beat,
    }

    if rul_cells:
        summary["rul_cells_evaluated"] = len(rul_cells)
        summary["rul_forecast_origin"] = "half of each cell's cycle life"
        summary["rul_mean_abs_error_cycles"] = round(
            float(np.mean([abs(r["error_cycles"]) for r in rul_cells])), 1
        )
        summary["rul_mean_error_pct_of_cell_life"] = round(
            float(np.mean([r["error_pct_of_cell_life"] for r in rul_cells])), 1
        )

    return {"summary": summary, "per_cell": per_cell}


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
    selection = select_and_fit(months, soh)
    coeffs = selection["coefficients"]

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
        "weighting_selected": selection["weighting"],
        "eol_threshold": EOL_THRESHOLD,
        "forecast_rul_months": forecast_rul_months(last, coeffs),
        "observed": observed,
        "forecast": forecast,
    }
