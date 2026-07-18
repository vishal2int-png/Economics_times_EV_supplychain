"""AI Copilot API Router"""

from fastapi import APIRouter
from pydantic import BaseModel
from services.gemini_agent import agent
from data.seed_data import store

router = APIRouter(prefix="/api/ai", tags=["AI Copilot"])


class ChatRequest(BaseModel):
    message: str
    module: str | None = None  # battery, fleet, supply-chain, carbon


@router.post("/chat")
async def chat(request: ChatRequest):
    """Chat with VoltEdge AI Copilot."""
    # Build context based on active module
    context = {}
    if request.module == "battery":
        evs = store.ev_vehicles
        context = {
            "module": "Battery APM",
            "fleet_avg_soh": round(sum(v["battery"]["soh_pct"] for v in evs) / len(evs), 1),
            "critical_vehicles": [v["id"] for v in evs if v["battery"]["soh_pct"] < 80],
            "total_evs": len(evs),
        }
    elif request.module == "fleet":
        context = {
            "module": "Fleet Readiness",
            "total_diesel": len(store.diesel_vehicles),
            "ready_for_ev": len([r for r in store.fleet_readiness if r["readiness"]["eri_score"] >= 80]),
            "avg_eri": round(sum(r["readiness"]["eri_score"] for r in store.fleet_readiness) / len(store.fleet_readiness), 1),
        }
    elif request.module == "supply-chain":
        sc = store.supply_chain
        context = {
            "module": "Supply Chain",
            "total_suppliers": sc["summary"]["total_suppliers"],
            "critical_risks": sc["summary"]["critical_risks"],
            "china_dependency": sc["summary"]["china_dependency_pct"],
        }
    elif request.module == "carbon":
        context = {
            "module": "Net Zero",
            "annual_emissions_tons": store.carbon_data["summary"]["total_annual_emissions_tons"],
            "electrification_pct": store.carbon_data["summary"]["electrification_pct"],
            "carbon_savings_tons": store.carbon_data["summary"]["carbon_savings_tons"],
        }

    response = await agent.chat(request.message, context if context else None)
    return {"response": response, "module": request.module}
