"""
VoltEdge AI — FastAPI Backend
Industrial EV Supply Chain & Asset Intelligence Platform
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from data.seed_data import store


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: seed data
    store.initialize()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="VoltEdge AI — Industrial EV Intelligence",
    description="AI platform for EV fleet operations and supply chain intelligence",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from routers import battery, fleet, supply_chain, carbon, ai

app.include_router(battery.router)
app.include_router(fleet.router)
app.include_router(supply_chain.router)
app.include_router(carbon.router)
app.include_router(ai.router)


@app.get("/")
def root():
    return {
        "name": "VoltEdge AI",
        "tagline": "Powering India's Industrial EV Transition with Intelligent Operations",
        "version": "1.0.0",
        "modules": ["Battery APM", "Fleet Readiness", "Supply Chain Risk", "Net Zero Tracker"],
    }


@app.get("/api/dashboard")
def get_dashboard():
    """Command center overview with KPIs from all modules."""
    evs = store.ev_vehicles
    soh_values = [v["battery"]["soh_pct"] for v in evs]

    fleet_ready = store.fleet_readiness
    sc = store.supply_chain
    carbon = store.carbon_data

    return {
        "battery_apm": {
            "total_evs": len(evs),
            "avg_soh": round(sum(soh_values) / len(soh_values), 1),
            "critical_count": len([v for v in evs if v["battery"]["soh_pct"] < 75]),
            "warning_count": len([v for v in evs if 75 <= v["battery"]["soh_pct"] < 85]),
        },
        "fleet_readiness": {
            "total_diesel": len(store.diesel_vehicles),
            "ready_for_ev": len([r for r in fleet_ready if r["readiness"]["eri_score"] >= 80]),
            "avg_eri": round(sum(r["readiness"]["eri_score"] for r in fleet_ready) / max(len(fleet_ready), 1), 1),
            "potential_savings_lakh": round(sum(r["readiness"]["tco_comparison"]["savings_lakh"] for r in fleet_ready if r["readiness"]["tco_comparison"]["savings_lakh"] > 0), 1),
        },
        "supply_chain": {
            "total_suppliers": sc["summary"]["total_suppliers"],
            "critical_risks": sc["summary"]["critical_risks"],
            "high_risks": sc["summary"]["high_risks"],
            "china_dependency_pct": sc["summary"]["china_dependency_pct"],
            "india_localization_pct": sc["summary"]["india_localization_pct"],
            "active_alerts": len(sc["alerts"]),
        },
        "net_zero": {
            "annual_emissions_tons": carbon["summary"]["total_annual_emissions_tons"],
            "carbon_savings_tons": carbon["summary"]["carbon_savings_tons"],
            "electrification_pct": carbon["summary"]["electrification_pct"],
            "target_pct": carbon["summary"]["target_electrification_pct"],
            "on_track": carbon["summary"]["on_track"],
        },
        "fleet_overview": {
            "total_vehicles": len(store.vehicles),
            "ev_count": len(evs),
            "diesel_count": len(store.diesel_vehicles),
            "cities": list(set(v["city"] for v in store.vehicles)),
        },
    }
