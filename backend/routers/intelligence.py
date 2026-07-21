"""Multi-agent orchestration & compound intelligence API Router"""

from fastapi import APIRouter
from pydantic import BaseModel

from data.seed_data import store
from services import compound
from services.agents import AGENTS, orchestrator, tools

router = APIRouter(prefix="/api/intelligence", tags=["Agent Intelligence"])


class AgentQuery(BaseModel):
    query: str


@router.get("/agents")
def list_agents():
    """The specialist agent roster and the tools each one can call."""
    return {
        "orchestrator_mode": "llm" if orchestrator.llm_enabled else "deterministic",
        "agents": [
            {
                "key": key,
                "name": agent["name"],
                "role": agent["role"],
                "tools": tools.describe(agent["tools"]),
            }
            for key, agent in AGENTS.items()
        ],
    }


@router.post("/ask")
def ask(request: AgentQuery):
    """
    Route a question through the multi-agent orchestrator.
    Returns the synthesised answer plus the full execution trace.
    """
    return orchestrator.handle(request.query, store)


@router.get("/compound-risk")
def get_compound_risk():
    """
    Compound risks surfaced by correlating signals across modules —
    each with the evidence chain that produced it.
    """
    return compound.detect(store)
