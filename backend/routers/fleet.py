"""Fleet Electrification Readiness API Router"""

from fastapi import APIRouter, HTTPException
from data.seed_data import store

router = APIRouter(prefix="/api/fleet", tags=["Fleet Readiness"])


@router.get("/readiness-scores")
def get_readiness_scores():
    """Get ERI scores for all diesel vehicles."""
    results = store.fleet_readiness
    grades = {"A": 0, "B": 0, "C": 0, "D": 0}
    for r in results:
        grades[r["readiness"]["eri_grade"]] = grades.get(r["readiness"]["eri_grade"], 0) + 1

    return {
        "summary": {
            "total_diesel_vehicles": len(results),
            "avg_eri_score": round(sum(r["readiness"]["eri_score"] for r in results) / max(len(results), 1), 1),
            "ready_now": len([r for r in results if r["readiness"]["eri_score"] >= 80]),
            "ready_next_quarter": len([r for r in results if 65 <= r["readiness"]["eri_score"] < 80]),
            "needs_evaluation": len([r for r in results if r["readiness"]["eri_score"] < 50]),
            "grade_distribution": grades,
            "total_potential_savings_lakh": round(sum(
                r["readiness"]["tco_comparison"]["savings_lakh"] for r in results
                if (r["readiness"]["tco_comparison"]["savings_lakh"] or 0) > 0
            ), 2),
            "awaiting_ev_technology": len([
                r for r in results if not r["readiness"]["tco_comparison"]["ev_available"]
            ]),
        },
        "vehicles": [
            {
                "id": r["id"],
                "registration": r["registration"],
                "model": r["model"],
                "vehicle_type": r["vehicle_type"],
                "city": r["city"],
                "route_name": r["route_name"],
                "daily_km": r["daily_km"],
                "age_months": r["age_months"],
                "eri_score": r["readiness"]["eri_score"],
                "eri_grade": r["readiness"]["eri_grade"],
                "breakdown": r["readiness"]["breakdown"],
                "recommended_ev": r["readiness"]["recommended_ev"],
                "recommended_ev_oem": r["readiness"]["recommended_ev_oem"],
                "tco_savings_lakh": r["readiness"]["tco_comparison"]["savings_lakh"],
                "breakeven_months": r["readiness"]["tco_comparison"]["breakeven_months"],
                "ev_available": r["readiness"]["tco_comparison"]["ev_available"],
                "transition_priority": r["readiness"]["transition_priority"],
            }
            for r in results
        ],
    }


@router.get("/vehicle/{vehicle_id}/tco")
def get_vehicle_tco(vehicle_id: str):
    """Get detailed TCO comparison for a specific diesel vehicle."""
    vehicle_data = store.get_fleet_readiness_for_vehicle(vehicle_id)
    if not vehicle_data:
        raise HTTPException(status_code=404, detail="Diesel vehicle not found in readiness data")

    return {
        "vehicle_id": vehicle_id,
        "registration": vehicle_data["registration"],
        "model": vehicle_data["model"],
        "city": vehicle_data["city"],
        "route_name": vehicle_data["route_name"],
        "daily_km": vehicle_data["daily_km"],
        "eri_score": vehicle_data["readiness"]["eri_score"],
        "eri_grade": vehicle_data["readiness"]["eri_grade"],
        "breakdown": vehicle_data["readiness"]["breakdown"],
        "recommended_ev": vehicle_data["readiness"]["recommended_ev"],
        "tco_comparison": vehicle_data["readiness"]["tco_comparison"],
    }


@router.get("/procurement-recommendations")
def get_procurement_recommendations():
    """Get EV procurement recommendations based on fleet analysis."""
    ready_vehicles = [r for r in store.fleet_readiness if r["readiness"]["eri_score"] >= 65]

    # Group by recommended EV
    ev_demand = {}
    for v in ready_vehicles:
        ev_model = v["readiness"]["recommended_ev"]
        if ev_model not in ev_demand:
            ev_demand[ev_model] = {"count": 0, "vehicles": [], "oem": v["readiness"]["recommended_ev_oem"]}
        ev_demand[ev_model]["count"] += 1
        ev_demand[ev_model]["vehicles"].append(v["id"])

    recommendations = []
    for model, data in sorted(ev_demand.items(), key=lambda x: x[1]["count"], reverse=True):
        from data.seed_data import EV_MODELS
        model_info = next((m for m in EV_MODELS if m["model"] == model), None)
        recommendations.append({
            "ev_model": model,
            "oem": data["oem"],
            "quantity_needed": data["count"],
            "vehicle_ids": data["vehicles"],
            "unit_price_lakh": model_info["price_lakh"] if model_info else 0,
            "fame_subsidy_pct": 15,
            "total_investment_lakh": round(data["count"] * (model_info["price_lakh"] * 0.85 if model_info else 0), 2),
            "estimated_delivery_weeks": 12 + data["count"] * 2,
            "specs": {
                "range_km": model_info["range_km"] if model_info else 0,
                "battery_kwh": model_info["battery_kwh"] if model_info else 0,
                "payload_kg": model_info["payload_kg"] if model_info else 0,
            } if model_info else {},
        })

    return {
        "total_vehicles_ready": len(ready_vehicles),
        "total_investment_lakh": round(sum(r["total_investment_lakh"] for r in recommendations), 2),
        "recommendations": recommendations,
    }


@router.get("/transition-roadmap")
def get_transition_roadmap():
    """Get phased electrification transition roadmap."""
    phases = [
        {
            "phase": 1,
            "name": "Quick Wins",
            "timeline": "Q3 2026",
            "criteria": "ERI ≥ 80 (Grade A)",
            "vehicles": [
                {"id": r["id"], "registration": r["registration"], "model": r["model"],
                 "eri_score": r["readiness"]["eri_score"], "city": r["city"],
                 "recommended_ev": r["readiness"]["recommended_ev"]}
                for r in store.fleet_readiness if r["readiness"]["eri_score"] >= 80
            ],
        },
        {
            "phase": 2,
            "name": "Strategic Transition",
            "timeline": "Q1 2027",
            "criteria": "ERI 65-79 (Grade B)",
            "vehicles": [
                {"id": r["id"], "registration": r["registration"], "model": r["model"],
                 "eri_score": r["readiness"]["eri_score"], "city": r["city"],
                 "recommended_ev": r["readiness"]["recommended_ev"]}
                for r in store.fleet_readiness if 65 <= r["readiness"]["eri_score"] < 80
            ],
        },
        {
            "phase": 3,
            "name": "Infrastructure Build-out",
            "timeline": "2027-2028",
            "criteria": "ERI 50-64 (Grade C) — needs infra investment",
            "vehicles": [
                {"id": r["id"], "registration": r["registration"], "model": r["model"],
                 "eri_score": r["readiness"]["eri_score"], "city": r["city"],
                 "recommended_ev": r["readiness"]["recommended_ev"]}
                for r in store.fleet_readiness if 50 <= r["readiness"]["eri_score"] < 65
            ],
        },
        {
            "phase": 4,
            "name": "Long-range EV Adoption",
            "timeline": "2028-2030",
            "criteria": "ERI < 50 (Grade D) — awaiting long-range EV options",
            "vehicles": [
                {"id": r["id"], "registration": r["registration"], "model": r["model"],
                 "eri_score": r["readiness"]["eri_score"], "city": r["city"],
                 "recommended_ev": r["readiness"]["recommended_ev"]}
                for r in store.fleet_readiness if r["readiness"]["eri_score"] < 50
            ],
        },
    ]

    for p in phases:
        p["vehicle_count"] = len(p["vehicles"])

    return {"phases": phases, "total_vehicles": len(store.fleet_readiness)}
