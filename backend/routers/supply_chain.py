"""Supply Chain Risk & Traceability API Router"""

from fastapi import APIRouter, HTTPException
from data.seed_data import store

router = APIRouter(prefix="/api/supply-chain", tags=["Supply Chain"])


@router.get("/overview")
def get_supply_chain_overview():
    """Get supply chain overview with risk summary."""
    sc = store.supply_chain
    return {
        "summary": sc["summary"],
        "tier_breakdown": {
            "tier_4_mining": len([s for s in sc["suppliers"] if s["tier"] == 4]),
            "tier_3_refining": len([s for s in sc["suppliers"] if s["tier"] == 3]),
            "tier_2_components": len([s for s in sc["suppliers"] if s["tier"] == 2]),
            "tier_1_cells": len([s for s in sc["suppliers"] if s["tier"] == 1]),
            "tier_0_assembly": len([s for s in sc["suppliers"] if s["tier"] == 0]),
        },
        "risk_distribution": {
            "critical": len([s for s in sc["suppliers"] if s["risk"]["risk_level"] == "critical"]),
            "high": len([s for s in sc["suppliers"] if s["risk"]["risk_level"] == "high"]),
            "medium": len([s for s in sc["suppliers"] if s["risk"]["risk_level"] == "medium"]),
            "low": len([s for s in sc["suppliers"] if s["risk"]["risk_level"] == "low"]),
        },
    }


@router.get("/suppliers")
def get_suppliers():
    """Get all suppliers with risk scores."""
    sc = store.supply_chain
    return {
        "suppliers": [
            {
                "id": s["id"],
                "name": s["name"],
                "tier": s["tier"],
                "material": s["material"],
                "country": s["country"],
                "region": s["region"],
                "lat": s["lat"],
                "lng": s["lng"],
                "capacity_tpa": s["capacity_tpa"],
                "risk": s["risk"],
                "quality_score": s["quality_score"],
                "esg_score": s["esg_score"],
                "financial_health": s["financial_health"],
            }
            for s in sc["suppliers"]
        ],
    }


@router.get("/map")
def get_supply_chain_map():
    """Get supply chain graph data for visualization."""
    sc = store.supply_chain
    nodes = [
        {
            "id": s["id"],
            "name": s["name"],
            "tier": s["tier"],
            "material": s["material"],
            "country": s["country"],
            "lat": s["lat"],
            "lng": s["lng"],
            "risk_level": s["risk"]["risk_level"],
            "risk_score": s["risk"]["composite_risk"],
        }
        for s in sc["suppliers"]
    ]
    return {"nodes": nodes, "links": sc["links"]}


@router.get("/risk-alerts")
def get_risk_alerts():
    """Get active supply chain risk alerts."""
    sc = store.supply_chain
    enriched_alerts = []
    for alert in sc["alerts"]:
        supplier = store.get_supplier(alert["supplier_id"])
        enriched_alerts.append({
            **alert,
            "supplier_name": supplier["name"] if supplier else "Unknown",
            "supplier_country": supplier["country"] if supplier else "Unknown",
            "supplier_tier": supplier["tier"] if supplier else -1,
        })
    return {
        "total": len(enriched_alerts),
        "critical": len([a for a in enriched_alerts if a["severity"] == "critical"]),
        "high": len([a for a in enriched_alerts if a["severity"] == "high"]),
        "alerts": enriched_alerts,
    }


@router.get("/supplier/{supplier_id}")
def get_supplier_detail(supplier_id: str):
    """Get detailed supplier info with upstream/downstream links."""
    supplier = store.get_supplier(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    sc = store.supply_chain
    upstream = [l for l in sc["links"] if l["to"] == supplier_id]
    downstream = [l for l in sc["links"] if l["from"] == supplier_id]

    # Enrich links with supplier names
    for link in upstream:
        src = store.get_supplier(link["from"])
        link["source_name"] = src["name"] if src else "Unknown"
    for link in downstream:
        dest = store.get_supplier(link["to"])
        link["dest_name"] = dest["name"] if dest else "Unknown"

    return {
        "supplier": supplier,
        "upstream_suppliers": upstream,
        "downstream_customers": downstream,
    }


@router.get("/traceability/{material}")
def get_material_traceability(material: str):
    """Trace a material through the supply chain."""
    sc = store.supply_chain
    material_lower = material.lower()

    # Find suppliers handling this material
    relevant = [s for s in sc["suppliers"] if material_lower in s["material"].lower()]
    if not relevant:
        raise HTTPException(status_code=404, detail=f"No suppliers found for material: {material}")

    # Build trace path
    trace = []
    for s in sorted(relevant, key=lambda x: x["tier"], reverse=True):
        trace.append({
            "tier": s["tier"],
            "supplier": s["name"],
            "country": s["country"],
            "material": s["material"],
            "risk_level": s["risk"]["risk_level"],
            "quality_score": s["quality_score"],
        })

    return {
        "material": material,
        "trace_path": trace,
        "total_suppliers_in_chain": len(trace),
    }
