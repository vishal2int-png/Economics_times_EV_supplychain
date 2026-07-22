"""Manufacturing Quality Intelligence (QMS) API Router"""

from fastapi import APIRouter

from data.seed_data import store
from services import qms as qms_service

router = APIRouter(prefix="/api/qms", tags=["Manufacturing Quality"])


@router.get("/metrics")
def get_metrics():
    """
    Defect-detection precision/recall on held-out batches, against a
    traditional 3-sigma SPC baseline.
    """
    return qms_service.get_engine().metrics()


@router.get("/control-charts")
def get_control_charts():
    """SPC control limits and process capability (Cpk) per parameter."""
    return {"parameters": qms_service.get_engine().control_charts()}


@router.get("/drift")
def get_drift(window: int = 120):
    """Process drift detected before it produces rejects."""
    return qms_service.get_engine().drift(window=window)


@router.get("/root-cause")
def get_root_cause():
    """Standardised model coefficients — what actually drives defects."""
    return {"features": qms_service.get_engine().feature_importance()}


@router.get("/flagged-batches")
def get_flagged_batches(limit: int = 20):
    """Highest-risk batches with per-batch driver attribution."""
    return {"batches": qms_service.get_engine().flagged_batches(limit=limit)}


@router.get("/supplier-quality")
def get_supplier_quality():
    """Incoming quality by cell supplier."""
    return {"suppliers": qms_service.get_engine().supplier_quality()}


@router.get("/traceability")
def get_traceability():
    """Cell batch -> pack (BPAN) -> vehicle lineage."""
    links = qms_service.get_engine().traceability(store.battery_passports)
    return {
        "total_links": len(links),
        "flagged_links": len([l for l in links if l["batch_flagged"]]),
        "links": links,
    }
