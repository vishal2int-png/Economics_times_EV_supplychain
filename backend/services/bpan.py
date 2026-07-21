"""
Battery Pack Aadhaar (BPAN) — lifecycle traceability layer.

Implements the identity + data architecture from MoRTH's draft Battery Pack
Aadhaar scheme: a 21-character alphanumeric identity per pack, split into an
immutable Static schema (manufacturing facts) and a Dynamic ledger (BDD) that
is updated across the operational life of the asset.

NOTE: BPAN is a *draft* MoRTH scheme. This module is built for
compliance-readiness, not as a claim of a live regulatory integration.

21-character layout:
    [0:2]   Country code                         (IN)
    [2:6]   Battery Manufacturer Identifier      (BMI — factory code)
    [6:8]   Chemistry code                       (NM = NMC, LF = LFP)
    [8:12]  Nominal capacity, kWh x 10           (zero-padded)
    [12:14] Year of manufacture                  (YY)
    [14:20] Serial                               (6 chars)
    [20]    Check character                      (mod-36 checksum)
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

ALPHANUM = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Cell chemistry by EV model. LFP dominates Indian commercial EVs (thermal
# stability in high ambient); NMC is used where energy density matters.
MODEL_CHEMISTRY = {
    "Tata Ace EV": "LFP",
    "Mahindra Treo Zor": "LFP",
    "Euler HiLoad EV": "LFP",
    "BYD T5": "LFP",
    "Ashok Leyland BOSS EV": "NMC",
    "Tata Ultra T.7 EV": "NMC",
    "Tata Intra EV": "LFP",
    "Mahindra ZEO": "LFP",
    "Switch IeV 4": "NMC",
}

# Factory codes (BMI) by OEM.
OEM_FACTORY = {
    "Tata Motors": "TAML",
    "Mahindra Electric": "MHEL",
    "Ashok Leyland": "ASLD",
    "BYD India": "BYDI",
    "Euler Motors": "EULR",
    "Switch Mobility": "SWCH",
}

# Battery Material Composition Section (BMCS) — mass % of critical minerals.
# Drives supply-chain exposure mapping in the compound risk engine.
CHEMISTRY_COMPOSITION = {
    "NMC": {"Lithium": 7.0, "Nickel": 12.4, "Cobalt": 4.1, "Manganese": 3.8, "Graphite": 16.2},
    "LFP": {"Lithium": 4.2, "Iron": 18.6, "Phosphorus": 10.4, "Cobalt": 0.0, "Graphite": 16.0},
}

# Embedded manufacturing carbon (BCF), kg CO2e per kWh of pack capacity.
# NMC is more carbon-intensive to produce than LFP.
CHEMISTRY_BCF_PER_KWH = {"NMC": 84.0, "LFP": 61.0}

# End-of-life thresholds for automotive traction use.
EOL_SOH_THRESHOLD = 70.0
SECOND_LIFE_CEILING = 80.0


def _check_char(body: str) -> str:
    """Mod-36 checksum over the 20-character body."""
    total = sum(ALPHANUM.index(c) * (i + 1) for i, c in enumerate(body) if c in ALPHANUM)
    return ALPHANUM[total % 36]


def _serial_from_id(vehicle_id: str) -> str:
    """Stable 6-char serial derived from the vehicle id (deterministic)."""
    h = 0
    for ch in vehicle_id:
        h = (h * 31 + ord(ch)) % (36 ** 6)
    out = ""
    for _ in range(6):
        out = ALPHANUM[h % 36] + out
        h //= 36
    return out


def generate_bpan(vehicle: Dict) -> str:
    """Build the 21-character Battery Pack Aadhaar Number for a vehicle."""
    chemistry = MODEL_CHEMISTRY.get(vehicle["model"], "LFP")
    factory = OEM_FACTORY.get(vehicle["oem"], "GENX")
    capacity_code = f"{int(round(vehicle['battery_kwh'] * 10)):04d}"[:4]
    mfg_year = (datetime.now() - timedelta(days=vehicle["age_months"] * 30)).strftime("%y")
    serial = _serial_from_id(vehicle["id"])

    body = f"IN{factory}{'NM' if chemistry == 'NMC' else 'LF'}{capacity_code}{mfg_year}{serial}"
    return body + _check_char(body)


def validate_bpan(bpan: str) -> bool:
    """Verify length and check character."""
    return len(bpan) == 21 and _check_char(bpan[:20]) == bpan[20]


def _lifecycle_status(soh: float) -> Dict:
    """Classify the pack against automotive EOL thresholds."""
    if soh >= SECOND_LIFE_CEILING:
        return {
            "status": "in_service",
            "detail": "Healthy for automotive traction duty.",
        }
    if soh >= EOL_SOH_THRESHOLD:
        return {
            "status": "second_life_eligible",
            "detail": (
                f"SoH {soh}% is below the {SECOND_LIFE_CEILING}% traction comfort band. "
                "Viable for stationary storage (telecom backup / solar firming) once retired."
            ),
        }
    return {
        "status": "recycle",
        "detail": (
            f"SoH {soh}% is at or below the {EOL_SOH_THRESHOLD}% automotive EOL threshold. "
            "Route to authorised recycler for material recovery."
        ),
    }


def _ais156_audit(vehicle: Dict) -> Dict:
    """
    AIS-156 Phase 2 safety posture derived from BMS telemetry.

    The standard mandates a microprocessor-based BMS with >=4 temperature
    sensors and thermal-runaway containment with audio-visual warning.
    """
    battery = vehicle["battery"]
    events = battery["thermal_events"]
    severe = [e for e in events if e["severity"] in ("high", "critical")]

    findings = []
    if battery["temperature_c"] > 50:
        findings.append(
            f"Pack temperature {battery['temperature_c']}degC exceeds the 50degC "
            "sustained-operation advisory — verify active cooling duty cycle."
        )
    if len(severe) >= 2:
        findings.append(
            f"{len(severe)} high/critical thermal events logged — recurring propagation "
            "risk; inspect cell balance and coolant loop."
        )
    if any(e["cause"] == "Cooling system fault" for e in events):
        findings.append(
            "Cooling system fault recorded — thermal containment capability may be "
            "degraded below the 5-minute no-fire requirement."
        )

    return {
        "standard": "AIS-156 Phase 2",
        "temperature_sensors": 4,
        "smart_bms": True,
        "compliant": len(findings) == 0,
        "findings": findings,
        "thermal_events_total": len(events),
        "thermal_events_severe": len(severe),
    }


def build_passport(vehicle: Dict) -> Dict:
    """Assemble the full static + dynamic battery passport for one EV."""
    chemistry = MODEL_CHEMISTRY.get(vehicle["model"], "LFP")
    battery = vehicle["battery"]
    bpan = generate_bpan(vehicle)
    capacity_kwh = vehicle["battery_kwh"]
    mfg_date = datetime.now() - timedelta(days=vehicle["age_months"] * 30)

    composition = CHEMISTRY_COMPOSITION[chemistry]
    bcf_per_kwh = CHEMISTRY_BCF_PER_KWH[chemistry]
    embedded_kg = round(bcf_per_kwh * capacity_kwh, 1)

    lifecycle = _lifecycle_status(battery["soh_pct"])

    return {
        "bpan": bpan,
        "bpan_valid": validate_bpan(bpan),
        "vehicle_id": vehicle["id"],
        "registration": vehicle["registration"],
        # ── Static schema (immutable unless remanufactured) ──────────────────
        "static": {
            "bmi": {
                "country_of_origin": "India",
                "manufacturer": vehicle["oem"],
                "factory_code": bpan[2:6],
                "manufacture_date": mfg_date.strftime("%Y-%m-%d"),
            },
            "bds": {
                "chemistry": chemistry,
                "chemistry_full": "Lithium Iron Phosphate" if chemistry == "LFP" else "Nickel Manganese Cobalt",
                "nominal_capacity_kwh": capacity_kwh,
                "nominal_voltage_v": 400 if capacity_kwh > 50 else 51.2,
                "vehicle_model": vehicle["model"],
            },
            "bmcs": {
                "composition_pct": composition,
                "critical_minerals": [m for m, pct in composition.items() if pct > 0],
                "cobalt_free": composition.get("Cobalt", 0) == 0,
            },
            "bcf": {
                "embedded_kg_co2e": embedded_kg,
                "kg_co2e_per_kwh": bcf_per_kwh,
                "basis": "Cell-to-pack manufacturing, cradle-to-gate",
            },
        },
        # ── Dynamic ledger (BDD) — updated across operational life ───────────
        "dynamic": {
            "soh_pct": battery["soh_pct"],
            "cycle_count": battery["cycle_count"],
            "predicted_rul_months": battery["predicted_rul_months"],
            "degradation_rate_pct_month": battery["degradation_rate_pct_month"],
            "lifecycle_status": lifecycle["status"],
            "lifecycle_detail": lifecycle["detail"],
            "safety": _ais156_audit(vehicle),
            "last_updated": datetime.now().isoformat(),
        },
    }


def build_registry(ev_vehicles: List[Dict]) -> List[Dict]:
    """Build passports for the whole EV fleet."""
    return [build_passport(v) for v in ev_vehicles]


def registry_summary(passports: List[Dict]) -> Dict:
    """Fleet-level traceability and compliance rollup."""
    total = len(passports)
    by_status: Dict[str, int] = {}
    by_chemistry: Dict[str, int] = {}
    for p in passports:
        status = p["dynamic"]["lifecycle_status"]
        by_status[status] = by_status.get(status, 0) + 1
        chem = p["static"]["bds"]["chemistry"]
        by_chemistry[chem] = by_chemistry.get(chem, 0) + 1

    non_compliant = [p for p in passports if not p["dynamic"]["safety"]["compliant"]]
    embedded_total = sum(p["static"]["bcf"]["embedded_kg_co2e"] for p in passports)
    cobalt_exposed = [p for p in passports if not p["static"]["bmcs"]["cobalt_free"]]

    return {
        "total_packs": total,
        "traceability_coverage_pct": 100.0 if total else 0.0,
        "by_lifecycle_status": by_status,
        "by_chemistry": by_chemistry,
        "ais156_compliant": total - len(non_compliant),
        "ais156_flagged": len(non_compliant),
        "cobalt_exposed_packs": len(cobalt_exposed),
        "cobalt_exposure_pct": round(len(cobalt_exposed) / max(total, 1) * 100, 1),
        "embedded_carbon_tons": round(embedded_total / 1000, 1),
        "second_life_candidates": by_status.get("second_life_eligible", 0),
    }
