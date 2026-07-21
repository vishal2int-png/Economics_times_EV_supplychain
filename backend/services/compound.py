"""
Compound risk engine — the cross-module intelligence layer.

Every signal here is individually visible in some existing module and
individually unalarming. The value is in the *correlation*: a cobalt export
restriction is a procurement footnote until you know which of your packs are
NMC, which of those are inside their replacement window, and that the
replacement lead time is longer than the runway you have left.

Each finding carries an explicit evidence chain naming the contributing
module, so a reviewer can audit why the platform escalated.
"""

from typing import Dict, List

from services.bpan import MODEL_CHEMISTRY

# Weeks from purchase order to delivered pack, by sourcing route.
REPLACEMENT_LEAD_TIME_WEEKS = {"NMC": 18, "LFP": 12}

# Capital procurement for battery packs is planned a year out, so a pack
# falling due inside this horizon is already a live procurement decision —
# not just one that has breached its lead time.
PLANNING_HORIZON_MONTHS = 12

# Materials whose disruption maps onto a cell chemistry.
MATERIAL_CHEMISTRY_EXPOSURE = {
    "cobalt": ["NMC"],
    "nickel": ["NMC"],
    "manganese": ["NMC"],
    "nmc": ["NMC"],
    "lithium": ["NMC", "LFP"],
    "graphite": ["NMC", "LFP"],
    "lfp": ["LFP"],
    "iron": ["LFP"],
}

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _disrupted_materials(supply_chain: Dict) -> List[Dict]:
    """Materials under active disruption, from alerts and supplier risk."""
    disrupted = []

    for alert in supply_chain["alerts"]:
        if alert["severity"] not in ("critical", "high"):
            continue
        text = f"{alert['message']} {alert['type']}".lower()
        for material in MATERIAL_CHEMISTRY_EXPOSURE:
            if material in text:
                disrupted.append({
                    "material": material,
                    "severity": alert["severity"],
                    "source": "supply_chain.alerts",
                    "signal": alert["message"],
                    "alert_id": alert["id"],
                })
                break

    for supplier in supply_chain["suppliers"]:
        if supplier["risk"]["risk_level"] != "critical":
            continue
        material_text = supplier["material"].lower()
        for material in MATERIAL_CHEMISTRY_EXPOSURE:
            if material in material_text:
                disrupted.append({
                    "material": material,
                    "severity": "critical",
                    "source": "supply_chain.suppliers",
                    "signal": (
                        f"{supplier['name']} ({supplier['country']}, Tier {supplier['tier']}) "
                        f"at composite risk {supplier['risk']['composite_risk']}"
                    ),
                    "supplier_id": supplier["id"],
                })
                break

    return disrupted


def _exposed_chemistries(disrupted: List[Dict]) -> Dict[str, List[Dict]]:
    """Map disrupted materials onto the cell chemistries they feed."""
    exposure: Dict[str, List[Dict]] = {}
    for d in disrupted:
        for chem in MATERIAL_CHEMISTRY_EXPOSURE.get(d["material"], []):
            exposure.setdefault(chem, []).append(d)
    return exposure


def detect(store) -> Dict:
    """Run all compound rules against the live data store."""
    findings: List[Dict] = []
    passports = store.battery_passports
    supply_chain = store.supply_chain

    disrupted = _disrupted_materials(supply_chain)
    exposure = _exposed_chemistries(disrupted)

    # ── Rule 1: material disruption x chemistry exposure x replacement window ──
    for chemistry, signals in exposure.items():
        lead_weeks = REPLACEMENT_LEAD_TIME_WEEKS[chemistry]
        lead_months = lead_weeks / 4.33
        window_months = max(lead_months * 1.5, PLANNING_HORIZON_MONTHS)

        at_risk = [
            p for p in passports
            if p["static"]["bds"]["chemistry"] == chemistry
            and p["dynamic"]["predicted_rul_months"] is not None
            and p["dynamic"]["predicted_rul_months"] <= window_months
        ]
        if not at_risk:
            continue

        worst = min(at_risk, key=lambda p: p["dynamic"]["predicted_rul_months"])
        runway = worst["dynamic"]["predicted_rul_months"]
        shortfall_months = round(lead_months - runway, 1)
        top_severity = min((s["severity"] for s in signals), key=lambda s: SEVERITY_RANK[s])

        findings.append({
            "id": f"CMP-CHEM-{chemistry}",
            "title": f"{chemistry} supply disruption collides with pack replacement window",
            "severity": "critical" if shortfall_months > 0 else "high",
            "confidence": 0.86 if len(signals) > 1 else 0.72,
            "summary": (
                f"{len(at_risk)} {chemistry} pack(s) fall due for replacement inside the "
                f"{PLANNING_HORIZON_MONTHS}-month procurement planning horizon "
                f"({lead_weeks}-week lead time), while {len(signals)} upstream "
                f"disruption signal(s) hit the {chemistry} material chain. "
                + (
                    f"Earliest pack has {runway} months of runway against a "
                    f"{round(lead_months, 1)}-month lead time — a {shortfall_months}-month shortfall."
                    if shortfall_months > 0 else
                    f"Earliest pack has {runway} months of runway; the window is still coverable "
                    "but closing."
                )
            ),
            "evidence": [
                {"module": s["source"], "signal": s["signal"], "severity": s["severity"]}
                for s in signals
            ] + [
                {
                    "module": "battery_apm.rul",
                    "signal": (
                        f"{worst['vehicle_id']} ({worst['bpan']}) at SoH "
                        f"{worst['dynamic']['soh_pct']}%, RUL {runway} months"
                    ),
                    "severity": "high",
                },
                {
                    "module": "bpan.bmcs",
                    "signal": f"{len(at_risk)} packs identified as {chemistry} via material composition",
                    "severity": "info",
                },
            ],
            "affected_assets": [
                {
                    "vehicle_id": p["vehicle_id"],
                    "bpan": p["bpan"],
                    "soh_pct": p["dynamic"]["soh_pct"],
                    "rul_months": p["dynamic"]["predicted_rul_months"],
                }
                for p in sorted(at_risk, key=lambda x: x["dynamic"]["predicted_rul_months"])[:8]
            ],
            "lead_time_weeks": lead_weeks,
            "recommended_actions": (
                [
                    f"Raise the {chemistry} replacement PO now — every week of delay extends the shortfall.",
                    "Dual-source: qualify an India-localised cell supplier to cut the lead time.",
                ] + (
                    ["Pivot new procurement to LFP — removes cobalt/nickel exposure entirely "
                     "and shortens lead time to 12 weeks."]
                    if chemistry == "NMC" else
                    ["Increase buffer stock on LFP cells while the disruption persists."]
                )
            ),
            "single_module_would_miss": (
                f"Supply chain sees a {top_severity} material alert. Battery APM sees packs ageing "
                "normally. Neither connects the disruption to the replacement window — "
                + (
                    "which has already closed."
                    if shortfall_months > 0 else
                    "which is still open, but only just."
                )
            ),
        })

    # ── Rule 2: thermal safety x charging behaviour ────────────────────────────
    thermal_cluster = []
    for p in passports:
        safety = p["dynamic"]["safety"]
        if safety["compliant"] or safety["thermal_events_severe"] < 1:
            continue
        vehicle = store.get_vehicle(p["vehicle_id"])
        if not vehicle:
            continue
        fast_pct = vehicle["battery"]["charging_pattern"]["fast_charge_pct"]
        if fast_pct < 40:
            continue
        thermal_cluster.append({
            "vehicle_id": p["vehicle_id"],
            "bpan": p["bpan"],
            "city": vehicle["city"],
            "fast_charge_pct": fast_pct,
            "pack_temp_c": vehicle["battery"]["temperature_c"],
            "severe_events": safety["thermal_events_severe"],
            "soh_pct": p["dynamic"]["soh_pct"],
        })

    if thermal_cluster:
        cities = sorted({c["city"] for c in thermal_cluster})
        findings.append({
            "id": "CMP-THERMAL-FASTCHARGE",
            "title": "Fast-charging habit is driving the thermal-event cluster",
            "severity": "high",
            "confidence": 0.81,
            "summary": (
                f"{len(thermal_cluster)} pack(s) combine AIS-156 thermal findings with a "
                f"fast-charge share above 40%, concentrated in {', '.join(cities)}. "
                "The charging policy — not cell defects — is the common factor, so this is "
                "correctable through depot scheduling rather than pack replacement."
            ),
            "evidence": [
                {
                    "module": "bpan.ais156",
                    "signal": f"{len(thermal_cluster)} packs with severe thermal events and open findings",
                    "severity": "high",
                },
                {
                    "module": "battery_apm.charging_pattern",
                    "signal": (
                        "Fast-charge share "
                        f"{min(c['fast_charge_pct'] for c in thermal_cluster)}–"
                        f"{max(c['fast_charge_pct'] for c in thermal_cluster)}% on affected packs"
                    ),
                    "severity": "medium",
                },
            ],
            "affected_assets": thermal_cluster[:8],
            "recommended_actions": [
                "Shift affected vehicles to overnight depot AC charging; cap DC fast-charge to 70% SoC.",
                "Re-sequence depot charging into cooler night hours to cut thermal load.",
                "Inspect coolant loop on packs with a recorded cooling-system fault.",
            ],
            "single_module_would_miss": (
                "Safety sees isolated thermal events. APM sees a charging pattern. Only the "
                "correlation shows one is causing the other."
            ),
        })

    # ── Rule 3: supplier concentration x carbon intensity of the pivot ────────
    china_suppliers = [s for s in supply_chain["suppliers"] if s["country"] == "China"]
    china_pct = supply_chain["summary"]["china_dependency_pct"]
    nmc_packs = [p for p in passports if p["static"]["bds"]["chemistry"] == "NMC"]
    if china_pct >= 30 and nmc_packs:
        embedded = round(sum(p["static"]["bcf"]["embedded_kg_co2e"] for p in nmc_packs) / 1000, 1)
        findings.append({
            "id": "CMP-CONCENTRATION-CARBON",
            "title": "Single-geography concentration also carries the embedded-carbon penalty",
            "severity": "medium",
            "confidence": 0.74,
            "summary": (
                f"{china_pct}% of the supplier base sits in one geography, and the {len(nmc_packs)} "
                f"NMC packs it feeds carry {embedded} t CO2e of embedded manufacturing carbon "
                f"({round(sum(p['static']['bcf']['kg_co2e_per_kwh'] for p in nmc_packs) / len(nmc_packs))} "
                "kg CO2e/kWh). Localising supply cuts both the concentration risk and the "
                "Scope 3 number in the same move."
            ),
            "evidence": [
                {
                    "module": "supply_chain.summary",
                    "signal": f"{china_pct}% supplier concentration across {len(china_suppliers)} suppliers",
                    "severity": "medium",
                },
                {
                    "module": "bpan.bcf",
                    "signal": f"{embedded} t CO2e embedded in NMC packs",
                    "severity": "medium",
                },
                {
                    "module": "carbon.scope3",
                    "signal": "Embedded pack carbon reports under Scope 3 for BRSR Core",
                    "severity": "info",
                },
            ],
            "affected_assets": [
                {"vehicle_id": p["vehicle_id"], "bpan": p["bpan"],
                 "embedded_kg_co2e": p["static"]["bcf"]["embedded_kg_co2e"]}
                for p in nmc_packs[:8]
            ],
            "recommended_actions": [
                "Qualify Indian cell suppliers (Amara Raja, Exide Energy) for the next tranche.",
                "Weight LFP in future procurement — lower embedded carbon and no cobalt exposure.",
                "Book embedded pack carbon into the Scope 3 ledger ahead of BRSR Core assurance.",
            ],
            "single_module_would_miss": (
                "Supply chain reports concentration. Carbon reports Scope 3. Neither shows that "
                "one procurement decision moves both."
            ),
        })

    findings.sort(key=lambda f: (SEVERITY_RANK[f["severity"]], -f["confidence"]))

    return {
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "summary": {
            "total_findings": len(findings),
            "critical": len([f for f in findings if f["severity"] == "critical"]),
            "high": len([f for f in findings if f["severity"] == "high"]),
            "medium": len([f for f in findings if f["severity"] == "medium"]),
            "modules_correlated": sorted({
                e["module"].split(".")[0] for f in findings for e in f["evidence"]
            }),
        },
        "findings": findings,
    }
