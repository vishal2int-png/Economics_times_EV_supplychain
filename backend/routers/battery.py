"""Battery APM API Router"""

from fastapi import APIRouter, HTTPException
from data.seed_data import store

router = APIRouter(prefix="/api/battery", tags=["Battery APM"])


@router.get("/fleet-health")
def get_fleet_health():
    """Get battery health overview for all EVs."""
    evs = store.ev_vehicles
    soh_values = [v["battery"]["soh_pct"] for v in evs]
    critical = [v for v in evs if v["battery"]["soh_pct"] < 75]
    warning = [v for v in evs if 75 <= v["battery"]["soh_pct"] < 85]
    healthy = [v for v in evs if v["battery"]["soh_pct"] >= 85]

    return {
        "summary": {
            "total_evs": len(evs),
            "avg_soh": round(sum(soh_values) / len(soh_values), 1),
            "min_soh": round(min(soh_values), 1),
            "max_soh": round(max(soh_values), 1),
            "critical_count": len(critical),
            "warning_count": len(warning),
            "healthy_count": len(healthy),
        },
        "vehicles": [
            {
                "id": v["id"],
                "registration": v["registration"],
                "model": v["model"],
                "city": v["city"],
                "depot": v["depot"],
                "soh_pct": v["battery"]["soh_pct"],
                "soc_pct": v["battery"]["soc_pct"],
                "temperature_c": v["battery"]["temperature_c"],
                "cycle_count": v["battery"]["cycle_count"],
                "predicted_rul_months": v["battery"]["predicted_rul_months"],
                "degradation_rate": v["battery"]["degradation_rate_pct_month"],
                "status": v["status"],
                "thermal_event_count": len(v["battery"]["thermal_events"]),
            }
            for v in sorted(evs, key=lambda x: x["battery"]["soh_pct"])
        ],
    }


@router.get("/vehicle/{vehicle_id}")
def get_vehicle_battery(vehicle_id: str):
    """Get detailed battery data for a specific vehicle."""
    vehicle = store.get_vehicle(vehicle_id)
    if not vehicle or vehicle["type"] != "EV":
        raise HTTPException(status_code=404, detail="EV not found")
    return {
        "id": vehicle["id"],
        "registration": vehicle["registration"],
        "model": vehicle["model"],
        "oem": vehicle["oem"],
        "city": vehicle["city"],
        "depot": vehicle["depot"],
        "route_name": vehicle["route_name"],
        "daily_km": vehicle["daily_km"],
        "age_months": vehicle["age_months"],
        "battery_kwh": vehicle["battery_kwh"],
        "range_km": vehicle["range_km"],
        "battery": vehicle["battery"],
        "status": vehicle["status"],
    }


@router.get("/degradation/{vehicle_id}")
def get_degradation_curve(vehicle_id: str):
    """Get degradation history and prediction for a vehicle."""
    vehicle = store.get_vehicle(vehicle_id)
    if not vehicle or vehicle["type"] != "EV":
        raise HTTPException(status_code=404, detail="EV not found")

    battery = vehicle["battery"]
    return {
        "vehicle_id": vehicle_id,
        "current_soh": battery["soh_pct"],
        "degradation_rate": battery["degradation_rate_pct_month"],
        "predicted_rul_months": battery["predicted_rul_months"],
        "history": battery["degradation_history"],
        "charging_pattern": battery["charging_pattern"],
    }


@router.get("/alerts")
def get_battery_alerts():
    """Get maintenance alerts and thermal events across fleet."""
    alerts = []
    for v in store.ev_vehicles:
        battery = v["battery"]
        # Maintenance alerts based on SoH
        if battery["soh_pct"] < 75:
            alerts.append({
                "vehicle_id": v["id"],
                "registration": v["registration"],
                "type": "critical_soh",
                "severity": "critical",
                "message": f"Battery SoH at {battery['soh_pct']}% — replacement evaluation needed",
                "recommended_action": "Schedule battery diagnostic and replacement cost analysis",
            })
        elif battery["soh_pct"] < 85:
            alerts.append({
                "vehicle_id": v["id"],
                "registration": v["registration"],
                "type": "low_soh",
                "severity": "warning",
                "message": f"Battery SoH declining — currently {battery['soh_pct']}%, RUL: {battery['predicted_rul_months']} months",
                "recommended_action": "Optimize charging patterns, reduce fast-charging frequency",
            })

        # Thermal alerts
        for event in battery["thermal_events"][:2]:  # Latest 2
            if event["severity"] in ("high", "critical"):
                alerts.append({
                    "vehicle_id": v["id"],
                    "registration": v["registration"],
                    "type": "thermal_event",
                    "severity": event["severity"],
                    "message": f"Thermal event: {event['peak_temp_c']}°C for {event['duration_min']}min — {event['cause']}",
                    "recommended_action": "Inspect cooling system and BMS calibration",
                    "date": event["date"],
                })

        # High degradation rate
        if battery["degradation_rate_pct_month"] > 0.6:
            alerts.append({
                "vehicle_id": v["id"],
                "registration": v["registration"],
                "type": "fast_degradation",
                "severity": "warning",
                "message": f"Degradation rate {battery['degradation_rate_pct_month']:.2f}%/month — above fleet average",
                "recommended_action": "Review usage patterns, limit fast-charging, check cell balance",
            })

    return {
        "total_alerts": len(alerts),
        "critical": len([a for a in alerts if a["severity"] == "critical"]),
        "warnings": len([a for a in alerts if a["severity"] == "warning"]),
        "alerts": sorted(alerts, key=lambda x: {"critical": 0, "high": 1, "warning": 2, "low": 3}.get(x["severity"], 4)),
    }


@router.get("/maintenance-schedule")
def get_maintenance_schedule():
    """Get AI-recommended maintenance schedule."""
    schedule = []
    for v in store.ev_vehicles:
        battery = v["battery"]
        priority = "routine"
        window = "Next 90 days"

        if battery["soh_pct"] < 75:
            priority = "urgent"
            window = "Within 7 days"
        elif battery["soh_pct"] < 80:
            priority = "high"
            window = "Within 30 days"
        elif battery["soh_pct"] < 85:
            priority = "medium"
            window = "Within 60 days"
        elif any(e["severity"] in ("high", "critical") for e in battery["thermal_events"]):
            priority = "high"
            window = "Within 14 days"

        tasks = ["BMS diagnostic scan", "Cell balance check"]
        if battery["temperature_c"] > 45:
            tasks.append("Cooling system inspection")
        if battery["soh_pct"] < 85:
            tasks.append("Capacity test (full cycle)")
        if len(battery["thermal_events"]) > 2:
            tasks.append("Thermal management system review")

        schedule.append({
            "vehicle_id": v["id"],
            "registration": v["registration"],
            "model": v["model"],
            "city": v["city"],
            "priority": priority,
            "window": window,
            "soh_pct": battery["soh_pct"],
            "tasks": tasks,
            "estimated_downtime_hours": 2 if priority == "routine" else (4 if priority in ("medium", "high") else 8),
        })

    return {
        "schedule": sorted(schedule, key=lambda x: {"urgent": 0, "high": 1, "medium": 2, "routine": 3}[x["priority"]]),
        "summary": {
            "urgent": len([s for s in schedule if s["priority"] == "urgent"]),
            "high": len([s for s in schedule if s["priority"] == "high"]),
            "medium": len([s for s in schedule if s["priority"] == "medium"]),
            "routine": len([s for s in schedule if s["priority"] == "routine"]),
        },
    }
