"""
VoltEdge AI — Synthetic Data Generator
Generates realistic industrial EV fleet data for all 4 modules.
"""

import random
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any

random.seed(42)

# ─── Indian Cities & Routes ───────────────────────────────────────────────────
CITIES = ["Mumbai", "Delhi", "Pune", "Chennai", "Bangalore", "Hyderabad", "Kolkata", "Ahmedabad"]
DEPOTS = {
    "Mumbai": ["Navi Mumbai Depot", "Thane Logistics Hub", "JNPT Terminal"],
    "Delhi": ["Gurgaon Fleet Yard", "Noida Industrial Zone", "Faridabad Hub"],
    "Pune": ["Pimpri-Chinchwad Depot", "Chakan Industrial Area"],
    "Chennai": ["Sriperumbudur Hub", "Ennore Port Terminal"],
    "Bangalore": ["Peenya Industrial Area", "Electronic City Depot"],
    "Hyderabad": ["Shamshabad Logistics Park"],
    "Kolkata": ["Haldia Port Terminal"],
    "Ahmedabad": ["Sanand Industrial Hub"],
}

ROUTES = [
    {"id": "R001", "name": "Mumbai-Pune Express", "from": "Mumbai", "to": "Pune", "distance_km": 150, "type": "intercity"},
    {"id": "R002", "name": "Delhi-Gurgaon Shuttle", "from": "Delhi", "to": "Delhi", "distance_km": 45, "type": "urban"},
    {"id": "R003", "name": "Chennai Port Loop", "from": "Chennai", "to": "Chennai", "distance_km": 60, "type": "port"},
    {"id": "R004", "name": "Bangalore Tech Corridor", "from": "Bangalore", "to": "Bangalore", "distance_km": 35, "type": "urban"},
    {"id": "R005", "name": "Pune-Nashik Freight", "from": "Pune", "to": "Pune", "distance_km": 210, "type": "intercity"},
    {"id": "R006", "name": "Mumbai Intra-plant", "from": "Mumbai", "to": "Mumbai", "distance_km": 15, "type": "intra-plant"},
    {"id": "R007", "name": "Delhi NCR Distribution", "from": "Delhi", "to": "Delhi", "distance_km": 80, "type": "distribution"},
    {"id": "R008", "name": "Hyderabad Pharma Zone", "from": "Hyderabad", "to": "Hyderabad", "distance_km": 25, "type": "intra-plant"},
    {"id": "R009", "name": "Kolkata-Haldia Port", "from": "Kolkata", "to": "Kolkata", "distance_km": 130, "type": "port"},
    {"id": "R010", "name": "Ahmedabad GIDC Loop", "from": "Ahmedabad", "to": "Ahmedabad", "distance_km": 40, "type": "industrial"},
]

# ─── Vehicle Models ───────────────────────────────────────────────────────────
EV_MODELS = [
    {"model": "Tata Ace EV", "oem": "Tata Motors", "type": "Light Truck", "range_km": 154, "battery_kwh": 21.3, "price_lakh": 12.5, "payload_kg": 600},
    {"model": "Mahindra Treo Zor", "oem": "Mahindra Electric", "type": "3W Cargo", "range_km": 125, "battery_kwh": 10.24, "price_lakh": 3.5, "payload_kg": 450},
    {"model": "Ashok Leyland BOSS EV", "oem": "Ashok Leyland", "type": "Medium Truck", "range_km": 200, "battery_kwh": 140, "price_lakh": 45.0, "payload_kg": 5000},
    {"model": "BYD T5", "oem": "BYD India", "type": "Medium Truck", "range_km": 250, "battery_kwh": 150, "price_lakh": 55.0, "payload_kg": 4500},
    {"model": "Tata Ultra T.7 EV", "oem": "Tata Motors", "type": "Medium Truck", "range_km": 185, "battery_kwh": 130, "price_lakh": 38.0, "payload_kg": 4200},
    {"model": "Euler HiLoad EV", "oem": "Euler Motors", "type": "3W Cargo", "range_km": 151, "battery_kwh": 11.5, "price_lakh": 4.0, "payload_kg": 500},
]

DIESEL_MODELS = [
    {"model": "Tata Ace Gold Diesel", "oem": "Tata Motors", "type": "Light Truck", "mileage_kmpl": 20, "price_lakh": 6.5, "payload_kg": 750},
    {"model": "Mahindra Bolero Pickup", "oem": "Mahindra", "type": "Light Truck", "mileage_kmpl": 16, "price_lakh": 8.0, "payload_kg": 1200},
    {"model": "Ashok Leyland Dost", "oem": "Ashok Leyland", "type": "Light Truck", "mileage_kmpl": 18, "price_lakh": 7.5, "payload_kg": 1500},
    {"model": "Tata Ultra T.7 Diesel", "oem": "Tata Motors", "type": "Medium Truck", "mileage_kmpl": 10, "price_lakh": 18.0, "payload_kg": 5000},
    {"model": "Eicher Pro 2049", "oem": "Eicher", "type": "Medium Truck", "mileage_kmpl": 12, "price_lakh": 16.0, "payload_kg": 4500},
    {"model": "BharatBenz 1015R", "oem": "Daimler India", "type": "Heavy Truck", "mileage_kmpl": 6, "price_lakh": 22.0, "payload_kg": 10000},
]


def _generate_reg_number(city: str) -> str:
    city_codes = {
        "Mumbai": "MH-01", "Delhi": "DL-01", "Pune": "MH-12",
        "Chennai": "TN-09", "Bangalore": "KA-01", "Hyderabad": "TS-08",
        "Kolkata": "WB-01", "Ahmedabad": "GJ-01"
    }
    code = city_codes.get(city, "MH-01")
    return f"{code}-{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}-{random.randint(1000, 9999)}"


def _generate_battery_telemetry(vehicle_id: str, age_months: int, daily_km: float, fast_charge_pct: float) -> Dict:
    """Generate realistic battery degradation data."""
    # Calendar aging: ~2% per year baseline
    calendar_deg = (age_months / 12) * 2.0
    # Cycle aging: based on usage intensity
    cycle_count = int(daily_km * age_months * 30 / 250)  # rough cycles
    cycle_deg = (cycle_count / 1000) * 3.0
    # Fast charging penalty
    fast_charge_deg = fast_charge_pct * 0.05 * (age_months / 12)
    # Temperature stress (Indian climate)
    temp_deg = random.uniform(0.5, 2.0)

    total_deg = calendar_deg + cycle_deg + fast_charge_deg + temp_deg
    total_deg = min(total_deg, 30)  # cap at 30% degradation
    soh = max(70, 100 - total_deg + random.uniform(-1, 1))

    # Degradation rate (% per month)
    deg_rate = total_deg / max(age_months, 1)

    # Predicted RUL (months until SoH hits 70%)
    if deg_rate > 0:
        rul_months = max(0, int((soh - 70) / deg_rate))
    else:
        rul_months = 120

    # Current state
    soc = random.uniform(20, 95)
    temp = random.uniform(28, 48) if random.random() < 0.8 else random.uniform(48, 62)
    voltage = 350 + (soc / 100) * 50 + random.uniform(-5, 5)
    current = random.uniform(-150, 150)

    # Thermal events
    thermal_events = []
    num_thermal = 0
    if temp > 50:
        num_thermal = random.randint(1, 5)
    elif age_months > 24:
        num_thermal = random.randint(0, 3)

    for i in range(num_thermal):
        event_date = datetime.now() - timedelta(days=random.randint(1, age_months * 30))
        thermal_events.append({
            "date": event_date.strftime("%Y-%m-%d"),
            "peak_temp_c": round(random.uniform(50, 68), 1),
            "duration_min": random.randint(5, 45),
            "severity": random.choice(["low", "medium", "high"]) if random.random() < 0.7 else "critical",
            "cause": random.choice(["Fast charging in high ambient", "Prolonged heavy load", "Cell imbalance", "Cooling system fault"]),
        })

    # Generate monthly degradation history
    degradation_history = []
    for m in range(min(age_months, 24)):
        month_date = datetime.now() - timedelta(days=(age_months - m) * 30)
        m_soh = 100 - (total_deg * (m + 1) / age_months) + random.uniform(-0.3, 0.3)
        degradation_history.append({
            "month": month_date.strftime("%Y-%m"),
            "soh": round(max(70, min(100, m_soh)), 1),
        })

    return {
        "soh_pct": round(soh, 1),
        "soc_pct": round(soc, 1),
        "cycle_count": cycle_count,
        "temperature_c": round(temp, 1),
        "voltage_v": round(voltage, 1),
        "current_a": round(current, 1),
        "degradation_rate_pct_month": round(deg_rate, 3),
        "predicted_rul_months": rul_months,
        "thermal_events": sorted(thermal_events, key=lambda x: x["date"], reverse=True),
        "degradation_history": degradation_history,
        "charging_pattern": {
            "fast_charge_pct": round(fast_charge_pct * 100, 1),
            "avg_charge_depth": round(random.uniform(20, 40), 1),
            "avg_soc_at_charge_start": round(random.uniform(15, 35), 1),
            "overnight_depot_charge_pct": round((1 - fast_charge_pct) * 100, 1),
        },
    }


def generate_vehicles(n_ev: int = 20, n_diesel: int = 30) -> List[Dict]:
    """Generate a mixed fleet of EV and diesel vehicles."""
    vehicles = []

    for i in range(n_ev):
        city = random.choice(CITIES)
        model_info = random.choice(EV_MODELS)
        route = random.choice(ROUTES)
        age_months = random.randint(3, 36)
        daily_km = random.uniform(40, min(model_info["range_km"] * 0.85, 220))
        fast_charge_pct = random.uniform(0.1, 0.7)

        depot_list = DEPOTS.get(city, ["Main Depot"])
        battery = _generate_battery_telemetry(f"EV-{i+1:03d}", age_months, daily_km, fast_charge_pct)

        vehicles.append({
            "id": f"EV-{i+1:03d}",
            "registration": _generate_reg_number(city),
            "type": "EV",
            "model": model_info["model"],
            "oem": model_info["oem"],
            "vehicle_type": model_info["type"],
            "city": city,
            "depot": random.choice(depot_list),
            "route_id": route["id"],
            "route_name": route["name"],
            "daily_km": round(daily_km, 1),
            "age_months": age_months,
            "battery_kwh": model_info["battery_kwh"],
            "range_km": model_info["range_km"],
            "price_lakh": model_info["price_lakh"],
            "payload_kg": model_info["payload_kg"],
            "battery": battery,
            "status": "active" if battery["soh_pct"] > 75 else ("maintenance" if battery["soh_pct"] > 70 else "critical"),
            "monthly_cost_inr": round(daily_km * 30 * random.uniform(2.5, 4.0), 0),  # electricity cost
        })

    for i in range(n_diesel):
        city = random.choice(CITIES)
        model_info = random.choice(DIESEL_MODELS)
        route = random.choice(ROUTES)
        age_months = random.randint(6, 96)
        daily_km = random.uniform(50, 300)

        depot_list = DEPOTS.get(city, ["Main Depot"])

        vehicles.append({
            "id": f"DSL-{i+1:03d}",
            "registration": _generate_reg_number(city),
            "type": "Diesel",
            "model": model_info["model"],
            "oem": model_info["oem"],
            "vehicle_type": model_info["type"],
            "city": city,
            "depot": random.choice(depot_list),
            "route_id": route["id"],
            "route_name": route["name"],
            "daily_km": round(daily_km, 1),
            "age_months": age_months,
            "mileage_kmpl": model_info["mileage_kmpl"],
            "price_lakh": model_info["price_lakh"],
            "payload_kg": model_info["payload_kg"],
            "status": "active",
            "monthly_cost_inr": round((daily_km * 30 / model_info["mileage_kmpl"]) * 95, 0),  # diesel ₹95/L
        })

    return vehicles


def _compute_eri_score(vehicle: Dict) -> Dict:
    """Compute Electrification Readiness Index for a diesel vehicle."""
    # Route compatibility (30%)
    daily_km = vehicle["daily_km"]
    # Assume typical EV range of 180km
    if daily_km <= 100:
        route_score = 95
    elif daily_km <= 150:
        route_score = 80
    elif daily_km <= 200:
        route_score = 60
    elif daily_km <= 250:
        route_score = 35
    else:
        route_score = 15

    # Depot dwell time (20%) — assume predictable schedules score higher
    route_type = next((r["type"] for r in ROUTES if r["id"] == vehicle["route_id"]), "urban")
    dwell_scores = {"intra-plant": 95, "urban": 85, "industrial": 80, "distribution": 70, "port": 65, "intercity": 40}
    dwell_score = dwell_scores.get(route_type, 60)

    # TCO advantage (25%)
    diesel_monthly = vehicle["monthly_cost_inr"]
    ev_monthly_est = daily_km * 30 * 3.2  # ₹3.2/km avg EV
    tco_saving_pct = ((diesel_monthly - ev_monthly_est) / diesel_monthly) * 100 if diesel_monthly > 0 else 0
    tco_score = min(100, max(0, tco_saving_pct * 2))

    # Infrastructure readiness (15%)
    city_infra = {"Mumbai": 82, "Delhi": 85, "Pune": 78, "Chennai": 72, "Bangalore": 80, "Hyderabad": 68, "Kolkata": 55, "Ahmedabad": 62}
    infra_score = city_infra.get(vehicle["city"], 50)

    # Operational criticality (10%) — lower criticality = easier to replace
    crit_scores = {"Light Truck": 85, "3W Cargo": 90, "Medium Truck": 60, "Heavy Truck": 30}
    crit_score = crit_scores.get(vehicle["vehicle_type"], 50)

    # Weighted ERI
    eri = (route_score * 0.30 + dwell_score * 0.20 + tco_score * 0.25 + infra_score * 0.15 + crit_score * 0.10)

    # Find best EV match
    best_ev = None
    for ev in EV_MODELS:
        if ev["range_km"] >= daily_km * 1.15:  # 15% buffer
            if best_ev is None or ev["price_lakh"] < best_ev["price_lakh"]:
                best_ev = ev

    # TCO comparison
    years = 7
    diesel_tco = vehicle["price_lakh"] + (diesel_monthly * 12 * years / 100000)
    ev_price = best_ev["price_lakh"] if best_ev else 35.0
    fame_subsidy = ev_price * 0.15  # ~15% FAME-II subsidy
    ev_tco = (ev_price - fame_subsidy) + (ev_monthly_est * 12 * years / 100000)

    return {
        "eri_score": round(eri, 1),
        "eri_grade": "A" if eri >= 80 else ("B" if eri >= 65 else ("C" if eri >= 50 else "D")),
        "breakdown": {
            "route_compatibility": round(route_score, 1),
            "depot_dwell_time": round(dwell_score, 1),
            "tco_advantage": round(tco_score, 1),
            "infrastructure_readiness": round(infra_score, 1),
            "operational_criticality": round(crit_score, 1),
        },
        "recommended_ev": best_ev["model"] if best_ev else "No suitable match — consider range-extended EV",
        "recommended_ev_oem": best_ev["oem"] if best_ev else "N/A",
        "tco_comparison": {
            "diesel_tco_lakh": round(diesel_tco, 2),
            "ev_tco_lakh": round(ev_tco, 2),
            "savings_lakh": round(diesel_tco - ev_tco, 2),
            "savings_pct": round(((diesel_tco - ev_tco) / diesel_tco) * 100, 1) if diesel_tco > 0 else 0,
            "breakeven_months": max(6, int((ev_price - fame_subsidy - vehicle["price_lakh"]) * 100000 / max(1, (diesel_monthly - ev_monthly_est)))) if diesel_monthly > ev_monthly_est else 999,
            "yearly_breakdown": {
                "diesel": [round(vehicle["price_lakh"] + (diesel_monthly * 12 * y / 100000), 2) for y in range(1, years + 1)],
                "ev": [round((ev_price - fame_subsidy) + (ev_monthly_est * 12 * y / 100000), 2) for y in range(1, years + 1)],
            }
        },
        "transition_priority": "immediate" if eri >= 80 else ("next_quarter" if eri >= 65 else ("next_year" if eri >= 50 else "evaluate")),
    }


def generate_fleet_readiness(vehicles: List[Dict]) -> List[Dict]:
    """Generate ERI scores for all diesel vehicles."""
    diesel_vehicles = [v for v in vehicles if v["type"] == "Diesel"]
    results = []
    for v in diesel_vehicles:
        eri = _compute_eri_score(v)
        results.append({**v, "readiness": eri})
    return sorted(results, key=lambda x: x["readiness"]["eri_score"], reverse=True)


# ─── Supply Chain Data ────────────────────────────────────────────────────────
SUPPLIERS = [
    # Tier 4: Mining
    {"id": "SUP-001", "name": "Tenke Fungurume Mining", "tier": 4, "material": "Cobalt", "country": "DR Congo", "region": "Africa",
     "lat": -10.62, "lng": 26.12, "capacity_tpa": 15000, "geo_risk": 85, "quality_score": 72, "esg_score": 45, "financial_health": 60},
    {"id": "SUP-002", "name": "Greenbushes Lithium", "tier": 4, "material": "Lithium (Spodumene)", "country": "Australia", "region": "Oceania",
     "lat": -33.85, "lng": 116.06, "capacity_tpa": 80000, "geo_risk": 12, "quality_score": 95, "esg_score": 88, "financial_health": 92},
    {"id": "SUP-003", "name": "PT Vale Indonesia", "tier": 4, "material": "Nickel", "country": "Indonesia", "region": "SE Asia",
     "lat": -2.57, "lng": 121.58, "capacity_tpa": 75000, "geo_risk": 45, "quality_score": 82, "esg_score": 65, "financial_health": 78},
    {"id": "SUP-004", "name": "Atacama Lithium (SQM)", "tier": 4, "material": "Lithium (Brine)", "country": "Chile", "region": "S. America",
     "lat": -23.50, "lng": -68.20, "capacity_tpa": 120000, "geo_risk": 30, "quality_score": 90, "esg_score": 70, "financial_health": 85},

    # Tier 3: Refining
    {"id": "SUP-005", "name": "Ganfeng Lithium Refinery", "tier": 3, "material": "Lithium Hydroxide", "country": "China", "region": "East Asia",
     "lat": 28.68, "lng": 115.89, "capacity_tpa": 100000, "geo_risk": 65, "quality_score": 91, "esg_score": 55, "financial_health": 88},
    {"id": "SUP-006", "name": "Umicore Refining", "tier": 3, "material": "Cobalt Sulfate", "country": "Belgium", "region": "Europe",
     "lat": 51.22, "lng": 4.40, "capacity_tpa": 20000, "geo_risk": 8, "quality_score": 97, "esg_score": 92, "financial_health": 90},
    {"id": "SUP-007", "name": "Manikaran Power Refinery", "tier": 3, "material": "Lithium Hydroxide", "country": "India", "region": "South Asia",
     "lat": 19.07, "lng": 72.87, "capacity_tpa": 5000, "geo_risk": 25, "quality_score": 78, "esg_score": 72, "financial_health": 65},

    # Tier 2: Cathode/Anode Manufacturing
    {"id": "SUP-008", "name": "Shanshan Technology", "tier": 2, "material": "NMC Cathode", "country": "China", "region": "East Asia",
     "lat": 28.23, "lng": 112.94, "capacity_tpa": 200000, "geo_risk": 65, "quality_score": 88, "esg_score": 52, "financial_health": 82},
    {"id": "SUP-009", "name": "BTR New Material", "tier": 2, "material": "Graphite Anode", "country": "China", "region": "East Asia",
     "lat": 22.54, "lng": 114.05, "capacity_tpa": 150000, "geo_risk": 65, "quality_score": 85, "esg_score": 50, "financial_health": 80},
    {"id": "SUP-010", "name": "Epsilon Advanced Materials", "tier": 2, "material": "Graphite Anode", "country": "India", "region": "South Asia",
     "lat": 17.38, "lng": 78.48, "capacity_tpa": 8000, "geo_risk": 25, "quality_score": 80, "esg_score": 75, "financial_health": 60},

    # Tier 1: Cell Manufacturing
    {"id": "SUP-011", "name": "CATL (Ningde)", "tier": 1, "material": "NMC/LFP Cells", "country": "China", "region": "East Asia",
     "lat": 26.66, "lng": 119.54, "capacity_tpa": 500000, "geo_risk": 65, "quality_score": 94, "esg_score": 60, "financial_health": 95},
    {"id": "SUP-012", "name": "BYD Battery", "tier": 1, "material": "LFP Blade Cells", "country": "China", "region": "East Asia",
     "lat": 22.64, "lng": 114.02, "capacity_tpa": 300000, "geo_risk": 65, "quality_score": 92, "esg_score": 62, "financial_health": 93},
    {"id": "SUP-013", "name": "Amara Raja Energy", "tier": 1, "material": "Li-ion Cells", "country": "India", "region": "South Asia",
     "lat": 13.63, "lng": 79.42, "capacity_tpa": 16000, "geo_risk": 25, "quality_score": 82, "esg_score": 78, "financial_health": 72},
    {"id": "SUP-014", "name": "Exide Energy Solutions", "tier": 1, "material": "Li-ion Cells", "country": "India", "region": "South Asia",
     "lat": 12.97, "lng": 77.59, "capacity_tpa": 12000, "geo_risk": 25, "quality_score": 79, "esg_score": 76, "financial_health": 68},

    # Tier 0: Pack Assembly (OEM)
    {"id": "SUP-015", "name": "Tata AutoComp (Pack Assembly)", "tier": 0, "material": "Battery Packs", "country": "India", "region": "South Asia",
     "lat": 18.62, "lng": 73.80, "capacity_tpa": 50000, "geo_risk": 20, "quality_score": 88, "esg_score": 82, "financial_health": 85},
]

SUPPLY_CHAIN_LINKS = [
    {"from": "SUP-001", "to": "SUP-006", "material": "Cobalt Ore", "volume_pct": 60},
    {"from": "SUP-002", "to": "SUP-005", "material": "Spodumene", "volume_pct": 70},
    {"from": "SUP-002", "to": "SUP-007", "material": "Spodumene", "volume_pct": 30},
    {"from": "SUP-004", "to": "SUP-005", "material": "Lithium Brine", "volume_pct": 50},
    {"from": "SUP-003", "to": "SUP-008", "material": "Nickel Matte", "volume_pct": 80},
    {"from": "SUP-005", "to": "SUP-008", "material": "Lithium Hydroxide", "volume_pct": 65},
    {"from": "SUP-006", "to": "SUP-008", "material": "Cobalt Sulfate", "volume_pct": 55},
    {"from": "SUP-007", "to": "SUP-010", "material": "Lithium Hydroxide", "volume_pct": 40},
    {"from": "SUP-008", "to": "SUP-011", "material": "NMC Cathode", "volume_pct": 70},
    {"from": "SUP-009", "to": "SUP-011", "material": "Graphite Anode", "volume_pct": 60},
    {"from": "SUP-009", "to": "SUP-012", "material": "Graphite Anode", "volume_pct": 40},
    {"from": "SUP-008", "to": "SUP-012", "material": "LFP Cathode", "volume_pct": 30},
    {"from": "SUP-010", "to": "SUP-013", "material": "Graphite Anode", "volume_pct": 90},
    {"from": "SUP-010", "to": "SUP-014", "material": "Graphite Anode", "volume_pct": 70},
    {"from": "SUP-011", "to": "SUP-015", "material": "NMC Cells", "volume_pct": 50},
    {"from": "SUP-012", "to": "SUP-015", "material": "LFP Cells", "volume_pct": 30},
    {"from": "SUP-013", "to": "SUP-015", "material": "Li-ion Cells", "volume_pct": 15},
    {"from": "SUP-014", "to": "SUP-015", "material": "Li-ion Cells", "volume_pct": 5},
]


def _compute_supplier_risk(supplier: Dict) -> Dict:
    """Compute composite risk score for a supplier."""
    geo = supplier["geo_risk"]
    quality = 100 - supplier["quality_score"]
    esg = 100 - supplier["esg_score"]
    financial = 100 - supplier["financial_health"]

    # Check concentration risk
    downstream_links = [l for l in SUPPLY_CHAIN_LINKS if l["from"] == supplier["id"]]
    avg_volume = sum(l["volume_pct"] for l in downstream_links) / max(len(downstream_links), 1)
    concentration = min(100, avg_volume * 1.2)

    composite = geo * 0.30 + quality * 0.25 + concentration * 0.20 + esg * 0.15 + financial * 0.10
    risk_level = "critical" if composite >= 50 else ("high" if composite >= 35 else ("medium" if composite >= 20 else "low"))

    return {
        "composite_risk": round(composite, 1),
        "risk_level": risk_level,
        "breakdown": {
            "geopolitical": round(geo, 1),
            "quality": round(quality, 1),
            "concentration": round(concentration, 1),
            "esg_compliance": round(esg, 1),
            "financial_stability": round(financial, 1),
        },
    }


def generate_supply_chain() -> Dict:
    """Generate complete supply chain data with risk scores."""
    suppliers_with_risk = []
    for s in SUPPLIERS:
        risk = _compute_supplier_risk(s)
        suppliers_with_risk.append({**s, "risk": risk})

    # Generate risk alerts
    alerts = []
    alert_templates = [
        {"type": "price_spike", "severity": "high", "message": "Cobalt spot price surged 18% this week due to DRC export restrictions"},
        {"type": "quality_deviation", "severity": "medium", "message": "Incoming inspection flagged 3.2% defect rate on NMC cathode batch — above 2% threshold"},
        {"type": "supply_disruption", "severity": "critical", "message": "Shipping delays at Shanghai port — estimated 2-week delay on cell shipments from CATL"},
        {"type": "geopolitical", "severity": "high", "message": "New EU battery regulation (CBAM) may impact carbon cost of Chinese-sourced cells by 8-12%"},
        {"type": "esg_violation", "severity": "medium", "message": "Artisanal mining concerns flagged for Tier 4 cobalt supplier — ESG audit recommended"},
        {"type": "capacity", "severity": "low", "message": "Amara Raja announced 50% capacity expansion — new GWh line operational by Q2 2027"},
        {"type": "quality_deviation", "severity": "high", "message": "Cell impedance variance exceeds SPC limits in latest LFP batch — root cause analysis initiated"},
        {"type": "price_spike", "severity": "medium", "message": "Lithium carbonate prices stabilizing after 6-month correction — procurement window opening"},
    ]
    for i, alert in enumerate(alert_templates):
        date = datetime.now() - timedelta(hours=random.randint(1, 168))
        alerts.append({
            "id": f"ALERT-{i+1:03d}",
            "timestamp": date.isoformat(),
            "supplier_id": random.choice([s["id"] for s in SUPPLIERS]),
            **alert,
        })

    return {
        "suppliers": suppliers_with_risk,
        "links": SUPPLY_CHAIN_LINKS,
        "alerts": sorted(alerts, key=lambda x: x["timestamp"], reverse=True),
        "summary": {
            "total_suppliers": len(SUPPLIERS),
            "critical_risks": len([s for s in suppliers_with_risk if s["risk"]["risk_level"] == "critical"]),
            "high_risks": len([s for s in suppliers_with_risk if s["risk"]["risk_level"] == "high"]),
            "china_dependency_pct": round(len([s for s in SUPPLIERS if s["country"] == "China"]) / len(SUPPLIERS) * 100, 1),
            "india_localization_pct": round(len([s for s in SUPPLIERS if s["country"] == "India"]) / len(SUPPLIERS) * 100, 1),
        },
    }


# ─── Carbon / Net Zero Data ──────────────────────────────────────────────────
EMISSION_FACTORS = {
    "diesel_kg_co2_per_liter": 2.68,
    "electricity_kg_co2_per_kwh": 0.71,  # India CEA 2024 grid average
    "diesel_density_kg_per_liter": 0.832,
}

STATE_GRID_FACTORS = {
    "Maharashtra": 0.78, "Delhi": 0.82, "Tamil Nadu": 0.62, "Karnataka": 0.55,
    "Telangana": 0.72, "West Bengal": 0.92, "Gujarat": 0.68,
}

CITY_TO_STATE = {
    "Mumbai": "Maharashtra", "Pune": "Maharashtra", "Delhi": "Delhi",
    "Chennai": "Tamil Nadu", "Bangalore": "Karnataka", "Hyderabad": "Telangana",
    "Kolkata": "West Bengal", "Ahmedabad": "Gujarat",
}


def generate_carbon_data(vehicles: List[Dict]) -> Dict:
    """Generate carbon emissions data for the fleet."""
    now = datetime.now()
    monthly_data = []

    for m in range(12):
        month_date = now - timedelta(days=(11 - m) * 30)
        month_label = month_date.strftime("%Y-%m")

        scope1 = 0  # Direct diesel emissions
        scope2 = 0  # Electricity for EVs
        scope3 = 0  # Upstream/third-party

        for v in vehicles:
            monthly_km = v["daily_km"] * 30

            if v["type"] == "Diesel":
                fuel_liters = monthly_km / v["mileage_kmpl"]
                scope1 += fuel_liters * EMISSION_FACTORS["diesel_kg_co2_per_liter"]
                scope3 += fuel_liters * 0.58  # Upstream diesel supply chain
            else:
                kwh_consumed = monthly_km * v["battery_kwh"] / v["range_km"]
                state = CITY_TO_STATE.get(v["city"], "Maharashtra")
                grid_factor = STATE_GRID_FACTORS.get(state, 0.71)
                scope2 += kwh_consumed * grid_factor
                scope3 += kwh_consumed * 0.12  # Upstream electricity

        monthly_data.append({
            "month": month_label,
            "scope1_kg": round(scope1, 1),
            "scope2_kg": round(scope2, 1),
            "scope3_kg": round(scope3, 1),
            "total_kg": round(scope1 + scope2 + scope3, 1),
        })

    # Counterfactual: what if ALL were diesel
    counterfactual_monthly = []
    for m, md in enumerate(monthly_data):
        diesel_total = md["scope1_kg"]
        for v in [v for v in vehicles if v["type"] == "EV"]:
            monthly_km = v["daily_km"] * 30
            equiv_mileage = 14  # avg diesel equivalent
            fuel_liters = monthly_km / equiv_mileage
            diesel_total += fuel_liters * EMISSION_FACTORS["diesel_kg_co2_per_liter"]
        counterfactual_monthly.append({
            "month": md["month"],
            "total_kg": round(diesel_total, 1),
        })

    # Route-level emissions
    route_emissions = []
    for route in ROUTES:
        route_vehicles = [v for v in vehicles if v["route_id"] == route["id"]]
        total_emissions = 0
        for v in route_vehicles:
            monthly_km = v["daily_km"] * 30
            if v["type"] == "Diesel":
                total_emissions += (monthly_km / v["mileage_kmpl"]) * EMISSION_FACTORS["diesel_kg_co2_per_liter"]
            else:
                kwh = monthly_km * v["battery_kwh"] / v["range_km"]
                state = CITY_TO_STATE.get(v["city"], "Maharashtra")
                total_emissions += kwh * STATE_GRID_FACTORS.get(state, 0.71)

        route_emissions.append({
            "route_id": route["id"],
            "route_name": route["name"],
            "monthly_emissions_kg": round(total_emissions, 1),
            "vehicle_count": len(route_vehicles),
            "ev_count": len([v for v in route_vehicles if v["type"] == "EV"]),
            "intensity_kg_per_km": round(total_emissions / max(route["distance_km"], 1), 2),
        })

    ev_count = len([v for v in vehicles if v["type"] == "EV"])
    total_count = len(vehicles)

    # Carbon savings
    actual_total = sum(m["total_kg"] for m in monthly_data)
    counterfactual_total = sum(m["total_kg"] for m in counterfactual_monthly)

    return {
        "monthly_emissions": monthly_data,
        "counterfactual": counterfactual_monthly,
        "route_emissions": sorted(route_emissions, key=lambda x: x["monthly_emissions_kg"], reverse=True),
        "summary": {
            "total_annual_emissions_tons": round(actual_total / 1000, 1),
            "scope1_pct": round(sum(m["scope1_kg"] for m in monthly_data) / max(actual_total, 1) * 100, 1),
            "scope2_pct": round(sum(m["scope2_kg"] for m in monthly_data) / max(actual_total, 1) * 100, 1),
            "scope3_pct": round(sum(m["scope3_kg"] for m in monthly_data) / max(actual_total, 1) * 100, 1),
            "carbon_savings_tons": round((counterfactual_total - actual_total) / 1000, 1),
            "carbon_savings_pct": round((counterfactual_total - actual_total) / max(counterfactual_total, 1) * 100, 1),
            "electrification_pct": round(ev_count / max(total_count, 1) * 100, 1),
            "target_electrification_pct": 60.0,
            "net_zero_target_year": 2035,
            "on_track": ev_count / max(total_count, 1) >= 0.3,
        },
    }


# ─── Master Data Store ────────────────────────────────────────────────────────
class DataStore:
    """In-memory data store for the application."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def initialize(self):
        if self._initialized:
            return
        print("[VoltEdge] Generating synthetic data...")
        self.vehicles = generate_vehicles(20, 30)
        self.ev_vehicles = [v for v in self.vehicles if v["type"] == "EV"]
        self.diesel_vehicles = [v for v in self.vehicles if v["type"] == "Diesel"]
        self.fleet_readiness = generate_fleet_readiness(self.vehicles)
        self.supply_chain = generate_supply_chain()
        self.carbon_data = generate_carbon_data(self.vehicles)
        self._initialized = True
        print(f"[OK] Data ready: {len(self.ev_vehicles)} EVs, {len(self.diesel_vehicles)} Diesel, {len(self.supply_chain['suppliers'])} suppliers")

    def get_vehicle(self, vehicle_id: str) -> Dict | None:
        return next((v for v in self.vehicles if v["id"] == vehicle_id), None)

    def get_fleet_readiness_for_vehicle(self, vehicle_id: str) -> Dict | None:
        return next((v for v in self.fleet_readiness if v["id"] == vehicle_id), None)

    def get_supplier(self, supplier_id: str) -> Dict | None:
        return next((s for s in self.supply_chain["suppliers"] if s["id"] == supplier_id), None)


# Global store instance
store = DataStore()
