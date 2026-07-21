"""Battery Pack Aadhaar (BPAN) traceability API Router"""

from fastapi import APIRouter, HTTPException
from data.seed_data import store
from services import bpan as bpan_service

router = APIRouter(prefix="/api/bpan", tags=["Battery Passport"])


@router.get("/registry")
def get_registry():
    """Fleet-wide battery passport registry with compliance rollup."""
    passports = store.battery_passports
    return {
        "summary": bpan_service.registry_summary(passports),
        "packs": [
            {
                "bpan": p["bpan"],
                "vehicle_id": p["vehicle_id"],
                "registration": p["registration"],
                "chemistry": p["static"]["bds"]["chemistry"],
                "capacity_kwh": p["static"]["bds"]["nominal_capacity_kwh"],
                "manufacturer": p["static"]["bmi"]["manufacturer"],
                "soh_pct": p["dynamic"]["soh_pct"],
                "lifecycle_status": p["dynamic"]["lifecycle_status"],
                "ais156_compliant": p["dynamic"]["safety"]["compliant"],
                "embedded_kg_co2e": p["static"]["bcf"]["embedded_kg_co2e"],
            }
            for p in passports
        ],
    }


@router.get("/passport/{identifier}")
def get_passport(identifier: str):
    """
    Full battery passport, looked up by BPAN or by vehicle id.
    Mirrors scanning the pack's QR code / 21-character identity.
    """
    key = identifier.strip().upper()
    passport = next(
        (p for p in store.battery_passports if p["bpan"] == key or p["vehicle_id"] == key),
        None,
    )
    if not passport:
        raise HTTPException(status_code=404, detail=f"No battery passport for '{identifier}'")
    return passport


@router.get("/validate/{bpan_code}")
def validate(bpan_code: str):
    """Validate a 21-character BPAN's structure and check character."""
    code = bpan_code.strip().upper()
    valid = bpan_service.validate_bpan(code)
    known = any(p["bpan"] == code for p in store.battery_passports)
    return {
        "bpan": code,
        "length_ok": len(code) == 21,
        "checksum_ok": valid,
        "registered_in_fleet": known,
    }


@router.get("/compliance")
def get_compliance():
    """AIS-156 Phase 2 safety audit across the fleet."""
    passports = store.battery_passports
    flagged = [p for p in passports if not p["dynamic"]["safety"]["compliant"]]
    return {
        "standard": "AIS-156 Phase 2",
        "total_packs": len(passports),
        "compliant": len(passports) - len(flagged),
        "flagged": len(flagged),
        "flagged_packs": [
            {
                "bpan": p["bpan"],
                "vehicle_id": p["vehicle_id"],
                "soh_pct": p["dynamic"]["soh_pct"],
                "findings": p["dynamic"]["safety"]["findings"],
                "thermal_events_severe": p["dynamic"]["safety"]["thermal_events_severe"],
            }
            for p in flagged
        ],
    }


@router.get("/second-life")
def get_second_life():
    """Packs approaching automotive EOL and their second-life routing."""
    passports = store.battery_passports
    candidates = [
        p for p in passports
        if p["dynamic"]["lifecycle_status"] in ("second_life_eligible", "recycle")
    ]
    # Residual stationary-storage value: usable kWh at current SoH.
    enriched = []
    for p in candidates:
        capacity = p["static"]["bds"]["nominal_capacity_kwh"]
        soh = p["dynamic"]["soh_pct"]
        usable_kwh = round(capacity * soh / 100, 1)
        enriched.append({
            "bpan": p["bpan"],
            "vehicle_id": p["vehicle_id"],
            "chemistry": p["static"]["bds"]["chemistry"],
            "soh_pct": soh,
            "lifecycle_status": p["dynamic"]["lifecycle_status"],
            "usable_kwh": usable_kwh,
            # ~Rs 4,000/kWh residual for second-life stationary storage
            "residual_value_inr": round(usable_kwh * 4000, 0),
            "recommended_application": (
                "Telecom tower backup / solar firming"
                if p["dynamic"]["lifecycle_status"] == "second_life_eligible"
                else "Material recovery via authorised recycler"
            ),
        })

    return {
        "total_candidates": len(enriched),
        "total_usable_kwh": round(sum(e["usable_kwh"] for e in enriched), 1),
        "total_residual_value_inr": round(sum(e["residual_value_inr"] for e in enriched), 0),
        "candidates": sorted(enriched, key=lambda x: x["soh_pct"]),
    }
