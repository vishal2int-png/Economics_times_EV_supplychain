"""
Multi-agent orchestration layer.

Design intent: tools are the source of truth, the LLM is the reasoner.

Every number a specialist agent talks about comes from a deterministic tool
call against the live data store — the LLM never invents a figure, it
interprets figures it was handed. That keeps the platform auditable (a
requirement for anything touching safety and regulatory reporting) while
still giving genuinely agentic planning and synthesis.

Flow:
    query -> Planner (which specialists are relevant?)
          -> Specialists run their tools, reason over real results
          -> Synthesiser merges into one answer
    ...with the full trace returned for inspection.

Falls back to deterministic planning and template synthesis when no LLM key
is configured, so a live demo never depends on an external API.
"""

import json
import os
from datetime import datetime
from typing import Callable, Dict, List, Optional

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


# ══════════════════════════════════════════════════════════════════════════
# Tool registry — deterministic reads over the live store
# ══════════════════════════════════════════════════════════════════════════

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Dict] = {}

    def register(self, name: str, description: str):
        def decorator(fn: Callable):
            self._tools[name] = {"fn": fn, "description": description}
            return fn
        return decorator

    def run(self, name: str, store, **kwargs):
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name]["fn"](store, **kwargs)

    def describe(self, names: List[str]) -> List[Dict]:
        return [
            {"name": n, "description": self._tools[n]["description"]}
            for n in names if n in self._tools
        ]


tools = ToolRegistry()


@tools.register("battery_health_summary", "Fleet battery State-of-Health distribution and outliers.")
def _battery_health_summary(store):
    evs = store.ev_vehicles
    soh = [v["battery"]["soh_pct"] for v in evs]
    return {
        "total_evs": len(evs),
        "avg_soh": round(sum(soh) / len(soh), 1),
        "min_soh": round(min(soh), 1),
        "critical_count": len([s for s in soh if s < 75]),
        "warning_count": len([s for s in soh if 75 <= s < 85]),
        "worst_vehicles": [
            {"id": v["id"], "soh_pct": v["battery"]["soh_pct"],
             "rul_months": v["battery"]["predicted_rul_months"]}
            for v in sorted(evs, key=lambda x: x["battery"]["soh_pct"])[:5]
        ],
    }


@tools.register("degradation_accuracy", "Held-out accuracy of the RUL model vs a persistence baseline.")
def _degradation_accuracy(store):
    from services import degradation
    return degradation.evaluate_fleet(store.ev_vehicles)["summary"]


@tools.register("supply_risk_summary", "Multi-tier supplier risk posture and concentration.")
def _supply_risk_summary(store):
    sc = store.supply_chain
    return {
        "summary": sc["summary"],
        "highest_risk_suppliers": [
            {"id": s["id"], "name": s["name"], "country": s["country"], "tier": s["tier"],
             "material": s["material"], "composite_risk": s["risk"]["composite_risk"],
             "risk_level": s["risk"]["risk_level"]}
            for s in sorted(sc["suppliers"], key=lambda x: -x["risk"]["composite_risk"])[:5]
        ],
    }


@tools.register("supply_alerts", "Active supply chain disruption alerts.")
def _supply_alerts(store):
    return [
        {"id": a["id"], "severity": a["severity"], "type": a["type"], "message": a["message"]}
        for a in store.supply_chain["alerts"]
        if a["severity"] in ("critical", "high")
    ]


@tools.register("fleet_readiness_summary", "Electrification readiness scores across the diesel fleet.")
def _fleet_readiness_summary(store):
    fr = store.fleet_readiness
    return {
        "total_diesel": len(fr),
        "ready_now": len([r for r in fr if r["readiness"]["eri_score"] >= 80]),
        "avg_eri": round(sum(r["readiness"]["eri_score"] for r in fr) / max(len(fr), 1), 1),
        "top_candidates": [
            {"id": r["id"], "eri_score": r["readiness"]["eri_score"],
             "recommended_ev": r["readiness"]["recommended_ev"],
             "tco_savings_lakh": r["readiness"]["tco_comparison"]["savings_lakh"]}
            for r in fr if r["readiness"]["tco_comparison"]["ev_available"]
        ][:5],
        "blocked_no_ev_match": len([
            r for r in fr if not r["readiness"]["tco_comparison"]["ev_available"]
        ]),
    }


@tools.register("carbon_summary", "Fleet emissions, Scope 1/2/3 split and savings vs all-diesel.")
def _carbon_summary(store):
    return store.carbon_data["summary"]


@tools.register("carbon_next_actions", "Ranked electrification actions by carbon impact.")
def _carbon_next_actions(store):
    route_emissions = {r["route_id"]: r for r in store.carbon_data["route_emissions"]}
    out = []
    for v in store.fleet_readiness[:6]:
        monthly = v.get("monthly_cost_inr", 0) / 95 * 2.68
        out.append({
            "vehicle_id": v["id"],
            "route": v["route_name"],
            "eri_score": v["readiness"]["eri_score"],
            "annual_co2_saved_tons": round(monthly * 12 / 1000, 1),
        })
    return sorted(out, key=lambda x: -x["annual_co2_saved_tons"])


@tools.register("bpan_compliance", "AIS-156 Phase 2 safety audit and battery passport coverage.")
def _bpan_compliance(store):
    from services.bpan import registry_summary
    summary = registry_summary(store.battery_passports)
    flagged = [
        {"vehicle_id": p["vehicle_id"], "bpan": p["bpan"],
         "findings": p["dynamic"]["safety"]["findings"]}
        for p in store.battery_passports if not p["dynamic"]["safety"]["compliant"]
    ]
    return {"summary": summary, "flagged_packs": flagged[:5]}


@tools.register("bpan_chemistry_exposure", "Pack chemistry mix and critical-mineral exposure.")
def _bpan_chemistry_exposure(store):
    packs = store.battery_passports
    by_chem: Dict[str, int] = {}
    for p in packs:
        c = p["static"]["bds"]["chemistry"]
        by_chem[c] = by_chem.get(c, 0) + 1
    cobalt = [p for p in packs if not p["static"]["bmcs"]["cobalt_free"]]
    return {
        "by_chemistry": by_chem,
        "cobalt_exposed_packs": len(cobalt),
        "cobalt_exposure_pct": round(len(cobalt) / max(len(packs), 1) * 100, 1),
        "embedded_carbon_tons": round(
            sum(p["static"]["bcf"]["embedded_kg_co2e"] for p in packs) / 1000, 1
        ),
    }


@tools.register("second_life_inventory", "Packs near automotive EOL and their second-life value.")
def _second_life_inventory(store):
    out = []
    for p in store.battery_passports:
        if p["dynamic"]["lifecycle_status"] == "in_service":
            continue
        cap = p["static"]["bds"]["nominal_capacity_kwh"]
        usable = round(cap * p["dynamic"]["soh_pct"] / 100, 1)
        out.append({
            "vehicle_id": p["vehicle_id"], "bpan": p["bpan"],
            "soh_pct": p["dynamic"]["soh_pct"], "usable_kwh": usable,
            "residual_value_inr": round(usable * 4000),
            "status": p["dynamic"]["lifecycle_status"],
        })
    return {"candidates": out, "total_residual_value_inr": sum(o["residual_value_inr"] for o in out)}


@tools.register("compound_risk", "Cross-module compound risks no single module would flag.")
def _compound_risk(store):
    from services import compound
    result = compound.detect(store)
    return {
        "summary": result["summary"],
        "findings": [
            {"id": f["id"], "title": f["title"], "severity": f["severity"],
             "confidence": f["confidence"], "summary": f["summary"],
             "recommended_actions": f["recommended_actions"]}
            for f in result["findings"]
        ],
    }


# ══════════════════════════════════════════════════════════════════════════
# Specialist agents
# ══════════════════════════════════════════════════════════════════════════

AGENTS: Dict[str, Dict] = {
    "battery_apm": {
        "name": "Battery APM Agent",
        "role": "Predictive battery health, degradation physics and remaining useful life.",
        "tools": ["battery_health_summary", "degradation_accuracy", "second_life_inventory"],
        "keywords": ["battery", "soh", "health", "degrad", "rul", "cell", "thermal",
                     "charge", "charging", "maintenance", "second life", "accuracy"],
    },
    "supply_chain": {
        "name": "Supply Chain Risk Agent",
        "role": "Multi-tier supplier risk, critical minerals and disruption monitoring.",
        "tools": ["supply_risk_summary", "supply_alerts", "bpan_chemistry_exposure"],
        "keywords": ["supply", "supplier", "cobalt", "lithium", "nickel", "graphite",
                     "china", "risk", "disruption", "material", "geopolit", "sourcing"],
    },
    "procurement": {
        "name": "Procurement & Readiness Agent",
        "role": "Electrification readiness scoring, TCO and EV procurement planning.",
        "tools": ["fleet_readiness_summary", "carbon_next_actions"],
        "keywords": ["procure", "readiness", "eri", "tco", "replace", "diesel",
                     "electrif", "transition", "buy", "fleet", "roadmap", "cost"],
    },
    "carbon": {
        "name": "Carbon Intelligence Agent",
        "role": "Scope 1/2/3 accounting, BRSR Core reporting and decarbonisation priorities.",
        "tools": ["carbon_summary", "carbon_next_actions", "bpan_chemistry_exposure"],
        "keywords": ["carbon", "emission", "co2", "scope", "net zero", "brsr", "esg",
                     "green", "grid", "renewable", "decarbon"],
    },
    "compliance": {
        "name": "Compliance & Traceability Agent",
        "role": "Battery Pack Aadhaar traceability and AIS-156 Phase 2 safety compliance.",
        "tools": ["bpan_compliance", "bpan_chemistry_exposure"],
        "keywords": ["compliance", "ais", "aadhaar", "bpan", "passport", "traceab",
                     "regulat", "safety", "audit", "standard"],
    },
}

ORCHESTRATOR_MODEL = "gemini-2.0-flash"


def _plan_deterministic(query: str) -> List[str]:
    """Keyword-scored agent selection — the fallback planner."""
    q = query.lower()
    scored = []
    for key, agent in AGENTS.items():
        score = sum(1 for kw in agent["keywords"] if kw in q)
        if score:
            scored.append((score, key))
    if not scored:
        # Nothing matched: this is a broad question, so sweep the portfolio.
        return ["battery_apm", "supply_chain", "carbon"]
    scored.sort(key=lambda x: -x[0])
    return [key for _, key in scored[:3]]


class Orchestrator:
    def __init__(self):
        self.model = None
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if GENAI_AVAILABLE and api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel(ORCHESTRATOR_MODEL)
                print(f"[OK] Agent orchestrator online ({ORCHESTRATOR_MODEL})")
            except Exception as exc:
                print(f"[WARN] Orchestrator LLM init failed: {exc}. Deterministic mode.")
        else:
            print("[WARN] No LLM key — orchestrator running in deterministic mode.")

    @property
    def llm_enabled(self) -> bool:
        return self.model is not None

    # ── Planning ─────────────────────────────────────────────────────────
    def plan(self, query: str) -> Dict:
        if not self.model:
            return {"agents": _plan_deterministic(query), "planner": "deterministic"}

        roster = "\n".join(f"- {k}: {v['role']}" for k, v in AGENTS.items())
        prompt = (
            "You route questions to specialist agents on an industrial EV intelligence "
            "platform.\n\nAvailable agents:\n" + roster +
            f"\n\nUser question: {query}\n\n"
            "Reply with ONLY a JSON array of the agent keys that should handle this "
            'question (1-3 of them), e.g. ["battery_apm","carbon"]. No other text.'
        )
        try:
            raw = self.model.generate_content(prompt).text.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            picked = [a for a in json.loads(raw) if a in AGENTS]
            if picked:
                return {"agents": picked[:3], "planner": "llm"}
        except Exception as exc:
            print(f"[WARN] LLM planning failed ({exc}); using deterministic planner.")
        return {"agents": _plan_deterministic(query), "planner": "deterministic-fallback"}

    # ── Specialist execution ─────────────────────────────────────────────
    def run_agent(self, agent_key: str, query: str, store) -> Dict:
        agent = AGENTS[agent_key]
        tool_results = {}
        for tool_name in agent["tools"]:
            try:
                tool_results[tool_name] = tools.run(tool_name, store)
            except Exception as exc:
                tool_results[tool_name] = {"error": str(exc)}

        finding = self._reason(agent, query, tool_results)
        return {
            "agent": agent_key,
            "agent_name": agent["name"],
            "tools_called": list(tool_results.keys()),
            "tool_results": tool_results,
            "finding": finding,
        }

    def _reason(self, agent: Dict, query: str, tool_results: Dict) -> str:
        if not self.model:
            return self._template_finding(agent, tool_results)
        prompt = (
            f"You are the {agent['name']} on VoltEdge AI, an industrial EV intelligence "
            f"platform for Indian fleet operators.\nYour remit: {agent['role']}\n\n"
            f"User question: {query}\n\n"
            "Tool results (this is the ONLY factual data you may use — never invent "
            "numbers, and quote the figures exactly as given):\n"
            f"```json\n{json.dumps(tool_results, indent=2, default=str)[:6000]}\n```\n\n"
            "Write 3-5 sentences of analysis for a fleet operations manager. Lead with the "
            "single most decision-relevant fact. Use Indian context (Rs, Indian OEMs, "
            "CEA grid factors, BRSR). Be specific and actionable. No preamble."
        )
        try:
            return self.model.generate_content(prompt).text.strip()
        except Exception as exc:
            print(f"[WARN] {agent['name']} reasoning failed ({exc}); using template.")
            return self._template_finding(agent, tool_results)

    def _template_finding(self, agent: Dict, tool_results: Dict) -> str:
        """Deterministic narrative built straight from tool output."""
        bits: List[str] = []
        for name, res in tool_results.items():
            if not isinstance(res, dict) or "error" in res:
                continue
            if name == "battery_health_summary":
                bits.append(
                    f"Fleet SoH averages {res['avg_soh']}% across {res['total_evs']} EVs, "
                    f"with {res['critical_count']} critical and {res['warning_count']} in warning. "
                    f"Weakest pack: {res['worst_vehicles'][0]['id']} at "
                    f"{res['worst_vehicles'][0]['soh_pct']}% "
                    f"({res['worst_vehicles'][0]['rul_months']} months RUL)."
                )
            elif name == "degradation_accuracy":
                bits.append(
                    f"RUL forecasts validate at {res['model_rmse_pct_soh']} %SoH RMSE on held-out "
                    f"data — {res['rmse_improvement_pct']}% better than a persistence baseline, "
                    f"beating it on {res['vehicles_beating_baseline']} of "
                    f"{res['evaluated_vehicles']} vehicles."
                )
            elif name == "supply_risk_summary":
                s = res["summary"]
                top = res["highest_risk_suppliers"][0]
                bits.append(
                    f"{s['critical_risks']} critical and {s['high_risks']} high-risk suppliers "
                    f"across {s['total_suppliers']} tracked; concentration sits at "
                    f"{s['china_dependency_pct']}% in China against {s['india_localization_pct']}% "
                    f"localised. Highest exposure: {top['name']} ({top['country']}, "
                    f"risk {top['composite_risk']})."
                )
            elif name == "supply_alerts" and isinstance(res, list) and res:
                bits.append(f"{len(res)} active high/critical alerts, led by: {res[0]['message']}")
            elif name == "fleet_readiness_summary":
                bits.append(
                    f"{res['ready_now']} of {res['total_diesel']} diesel vehicles score ERI >= 80 "
                    f"(fleet average {res['avg_eri']}). Best candidate {res['top_candidates'][0]['id']} "
                    f"-> {res['top_candidates'][0]['recommended_ev']}, saving Rs "
                    f"{res['top_candidates'][0]['tco_savings_lakh']}L over 7 years. "
                    f"{res['blocked_no_ev_match']} vehicles have no viable EV match yet."
                )
            elif name == "carbon_summary":
                bits.append(
                    f"Fleet emits {res['total_annual_emissions_tons']} t CO2e/yr "
                    f"(Scope 1 {res['scope1_pct']}%, Scope 2 {res['scope2_pct']}%, "
                    f"Scope 3 {res['scope3_pct']}%), saving {res['carbon_savings_tons']} t "
                    f"({res['carbon_savings_pct']}%) versus an all-diesel fleet at "
                    f"{res['electrification_pct']}% electrification."
                )
            elif name == "bpan_compliance":
                s = res["summary"]
                bits.append(
                    f"All {s['total_packs']} packs carry a Battery Pack Aadhaar; "
                    f"{s['ais156_flagged']} are flagged under AIS-156 Phase 2 and "
                    f"{s['second_life_candidates']} are second-life candidates."
                )
            elif name == "bpan_chemistry_exposure":
                bits.append(
                    f"Chemistry mix {res['by_chemistry']}, with {res['cobalt_exposure_pct']}% of packs "
                    f"cobalt-exposed and {res['embedded_carbon_tons']} t CO2e embedded in manufacturing."
                )
            elif name == "second_life_inventory" and res.get("candidates"):
                bits.append(
                    f"{len(res['candidates'])} packs are past traction duty, holding Rs "
                    f"{res['total_residual_value_inr']:,} of second-life stationary value."
                )
        return " ".join(bits) if bits else "No material findings from this agent's tools."

    # ── Synthesis ────────────────────────────────────────────────────────
    def synthesise(self, query: str, agent_runs: List[Dict]) -> str:
        if not agent_runs:
            return "No agents were engaged for this question."
        if len(agent_runs) == 1:
            return agent_runs[0]["finding"]

        if not self.model:
            return "\n\n".join(f"**{r['agent_name']}** — {r['finding']}" for r in agent_runs)

        findings = "\n\n".join(f"{r['agent_name']}: {r['finding']}" for r in agent_runs)
        prompt = (
            "You are the lead analyst on VoltEdge AI. Several specialist agents have "
            f"reported on this question:\n\n\"{query}\"\n\nAgent findings:\n{findings}\n\n"
            "Write a single integrated answer in markdown for a fleet operations manager. "
            "Open with the headline conclusion, then the supporting detail, then a short "
            "'Recommended actions' list. Draw out any connection *between* the agents' "
            "findings. Reuse their numbers exactly — introduce no new figures."
        )
        try:
            return self.model.generate_content(prompt).text.strip()
        except Exception as exc:
            print(f"[WARN] Synthesis failed ({exc}); concatenating findings.")
            return "\n\n".join(f"**{r['agent_name']}** — {r['finding']}" for r in agent_runs)

    # ── Entry point ──────────────────────────────────────────────────────
    def handle(self, query: str, store) -> Dict:
        started = datetime.now()
        plan = self.plan(query)
        runs = [self.run_agent(key, query, store) for key in plan["agents"]]
        answer = self.synthesise(query, runs)
        elapsed_ms = int((datetime.now() - started).total_seconds() * 1000)

        return {
            "query": query,
            "answer": answer,
            "mode": "llm" if self.llm_enabled else "deterministic",
            "trace": {
                "planner": plan["planner"],
                "agents_engaged": plan["agents"],
                "elapsed_ms": elapsed_ms,
                "steps": [
                    {
                        "agent": r["agent"],
                        "agent_name": r["agent_name"],
                        "tools_called": r["tools_called"],
                        "finding": r["finding"],
                    }
                    for r in runs
                ],
            },
        }


orchestrator = Orchestrator()
