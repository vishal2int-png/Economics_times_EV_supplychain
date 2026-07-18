"""Net Zero & Carbon Intelligence API Router"""

from fastapi import APIRouter
from data.seed_data import store

router = APIRouter(prefix="/api/carbon", tags=["Net Zero"])


@router.get("/summary")
def get_carbon_summary():
    """Get overall carbon emissions summary."""
    return store.carbon_data["summary"]


@router.get("/emissions")
def get_monthly_emissions():
    """Get monthly emissions breakdown with counterfactual comparison."""
    return {
        "monthly": store.carbon_data["monthly_emissions"],
        "counterfactual": store.carbon_data["counterfactual"],
    }


@router.get("/scope-breakdown")
def get_scope_breakdown():
    """Get Scope 1/2/3 breakdown."""
    data = store.carbon_data["monthly_emissions"]
    return {
        "monthly": data,
        "totals": {
            "scope1_tons": round(sum(m["scope1_kg"] for m in data) / 1000, 2),
            "scope2_tons": round(sum(m["scope2_kg"] for m in data) / 1000, 2),
            "scope3_tons": round(sum(m["scope3_kg"] for m in data) / 1000, 2),
            "total_tons": round(sum(m["total_kg"] for m in data) / 1000, 2),
        },
    }


@router.get("/route-intensity")
def get_route_intensity():
    """Get per-route carbon intensity."""
    return {
        "routes": store.carbon_data["route_emissions"],
    }


@router.get("/next-best-action")
def get_next_best_action():
    """Get AI-prioritized next electrification actions for maximum carbon impact."""
    # Combine fleet readiness with carbon data
    actions = []
    route_emissions = {r["route_id"]: r for r in store.carbon_data["route_emissions"]}

    for v in store.fleet_readiness[:10]:  # Top 10 by ERI
        route = route_emissions.get(v["route_id"], {})
        monthly_diesel = v.get("monthly_cost_inr", 0) / 95 * 2.68  # Approx kg CO2/month
        annual_co2_saved = monthly_diesel * 12 / 1000  # tons

        actions.append({
            "rank": len(actions) + 1,
            "vehicle_id": v["id"],
            "registration": v["registration"],
            "model": v["model"],
            "city": v["city"],
            "route_name": v["route_name"],
            "eri_score": v["readiness"]["eri_score"],
            "estimated_annual_co2_saved_tons": round(annual_co2_saved, 1),
            "recommended_ev": v["readiness"]["recommended_ev"],
            "investment_lakh": v["readiness"]["tco_comparison"]["ev_tco_lakh"],
            "carbon_roi": f"₹{round(v['readiness']['tco_comparison']['ev_tco_lakh'] * 100000 / max(annual_co2_saved, 0.1), 0):,.0f}/ton CO₂ saved",
        })

    # Sort by carbon impact
    actions.sort(key=lambda x: x["estimated_annual_co2_saved_tons"], reverse=True)
    for i, a in enumerate(actions):
        a["rank"] = i + 1

    return {
        "actions": actions,
        "total_potential_savings_tons": round(sum(a["estimated_annual_co2_saved_tons"] for a in actions), 1),
    }


@router.get("/progress")
def get_electrification_progress():
    """Get electrification progress vs targets."""
    summary = store.carbon_data["summary"]
    ev_count = len(store.ev_vehicles)
    total = len(store.vehicles)
    target_pct = summary["target_electrification_pct"]
    current_pct = summary["electrification_pct"]

    # Project trajectory
    trajectory = []
    for year in range(2026, 2036):
        if year == 2026:
            pct = current_pct
        else:
            # Assume 8% annual growth
            pct = min(100, current_pct + (year - 2026) * 8)
        trajectory.append({"year": year, "electrification_pct": round(pct, 1)})

    return {
        "current": {
            "ev_count": ev_count,
            "total_vehicles": total,
            "electrification_pct": current_pct,
            "target_pct": target_pct,
            "gap_pct": round(target_pct - current_pct, 1),
        },
        "net_zero_target_year": summary["net_zero_target_year"],
        "on_track": summary["on_track"],
        "trajectory": trajectory,
        "carbon_savings": {
            "annual_tons_saved": summary["carbon_savings_tons"],
            "savings_pct": summary["carbon_savings_pct"],
        },
    }
