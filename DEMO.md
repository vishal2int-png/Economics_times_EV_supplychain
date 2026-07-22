# Demo script — VoltEdge AI

~6 minutes. Numbers below are live as of the current seed; re-check after any code change.

## Before you start

- [ ] Backend running from `backend/` on :8000
- [ ] Frontend running on :3000
- [ ] `GEMINI_API_KEY` set **before** starting the backend — the Agent Console badge should
      read `LLM`, not `DETERMINISTIC`
- [ ] <http://localhost:8000/docs> open in a second tab for technical questions

---

## 1 · Command Center — 30 sec

Open `/`. Four KPI tiles across battery, fleet, supply chain and carbon.

> "One industrial fleet operator. Four domains that today live in four disconnected tools —
> and the decisions that matter fall in the gaps between them."

## 2 · Agent Console — 2 min · **lead with this**

Open `/agent-console`. Scroll to **Compound Risk** and open the NMC finding. Read the evidence
chain aloud, top to bottom:

- `supply_chain.alerts` — DRC cobalt export restriction, spot price +18%
- `supply_chain.suppliers` — Tenke Fungurume, Tier 4, composite risk 59.1
- `bpan.bmcs` — material composition identifies which packs are NMC
- `battery_apm.rul` — earliest exposed pack at 78.4% SoH, 11 months runway
- against an **18-week** procurement lead time

Then read the "Why one module misses it" line. That sentence is the answer to *"isn't this
just a dashboard?"*

Now click a sample query chip — **"Which diesel vehicles should we electrify first?"** Point at
the trace: the planner routes to the Procurement agent, you can see which tools it called, and
the synthesised answer below.

> "Every number an agent states came from a deterministic tool call. The model reasons over
> the results — it never invents a figure. That's a hard requirement once you're touching
> battery safety and regulatory reporting."

## 3 · Battery APM — 1.5 min · **the technical beat**

Open `/battery-apm`. The **Validated on Real Cells** panel:

- Model RMSE **2.281 %SoH** vs **3.718** persistence baseline — **38.6% better**
- RUL error **16 cycles**, 10.6% of cell life
- Per-cell table: 3 of 4 NASA cells beat baseline

> "This is validated against real measured cells from NASA's ageing dataset — 636 charge
> cycles, with ground-truth end-of-life. The model form is physics-informed: a square-root
> term for SEI-layer calendar ageing, linear for cycling loss."

If challenged on the synthetic-vs-real gap, the note under the table already concedes it —
say so before they do.

Now **click any vehicle row.** The drill-down opens: measured-vs-forecast degradation curve
out to the 70% EOL line, the battery passport, AIS-156 status.

## 4 · Quality (QMS) — 1.5 min

Open `/quality`.

- Defect recall **85.4%** vs **52.1%** for conventional 3σ SPC
- ROC-AUC **0.903**, flagging 17.7% of batches for re-inspection
- **+16** additional escapes caught on the same held-out batches

> "The model uses only process and incoming-material data — everything known before in-line
> inspection runs. That's the lead time: we catch it before the cells are built into packs."

Open the **Process Drift** tab: coating thickness has walked 4.9σ off baseline **while still
inside spec** — so no reject has been raised, and conventional SPC is silent.

Open **Cell → Pack → Vehicle** and click a row to land on a real vehicle's passport.

Say the data is synthetic before anyone asks — the banner on screen already does.

## 5 · Fleet Readiness — 45 sec · **the honest beat**

Open `/fleet-readiness`. Only 2 of 30 are ready now; **21 have no viable EV at all**.

> "Our payload and range matching says the replacement vehicle doesn't exist yet in India.
> That's not a gap in the tool — it's the finding. It's why industrial penetration is under
> 2.5%, and it's what a naive tool hides when it recommends a three-wheeler for a ten-tonne
> truck."

## 6 · Net Zero — 30 sec

Open `/net-zero`. 64.6 t CO₂e saved vs all-diesel, 40% electrified.

If challenged on assumptions: `/api/carbon/summary` returns `grid_factor_kg_per_kwh` (CEA
0.71) and `renewable_depot_share_pct` (30%) explicitly.

> "Our assumptions are inspectable, not buried."

---

## Likely questions

**"Is the data real?"**
Battery degradation — yes, NASA PCoE, four cells, 636 cycles, and we excluded seven cells that
failed a physical-plausibility check. Manufacturing quality — synthetic, and labelled on
screen; no open defect corpus exists. Carbon — modelled with assumptions exposed via API.

**"What's actually AI here, versus rules?"**
Three learned components: the degradation model (fit per asset, with recency weighting selected
on an inner validation split), the defect classifier, and the agent layer. The compound risk
engine is deliberately rule-based and auditable — you do not want a language model deciding
whether to escalate a battery safety finding.

**"Why is precision only 30% on defects?"**
Because defects are rare (6%) and we tune for recall — missing an escape that reaches pack
assembly costs far more than re-inspecting a good batch. It's a screening tool: re-inspect
17.7% of production, catch 85% of escapes. SPC catches 52% for 11.7%.

**"Would this scale?"**
The store is in-memory for the prototype; every service reads through one interface, so it
swaps for a real database without touching the intelligence layer. Agents are stateless and
tool-bounded.

---

## Don't claim

- That BPAN is live — it's a **draft** MoRTH scheme, built for compliance-readiness
- That the NASA data comes from NASA directly — it's a **community mirror** (CC0)
- The synthetic-fleet accuracy figure (0.475 RMSE) as a real-world result — use 2.281
- That QMS numbers come from a real production line
