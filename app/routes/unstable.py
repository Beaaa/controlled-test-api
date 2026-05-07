"""
Unstable and delayed endpoints — intentionally erratic for QA benchmarking.
"""

import random
import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["instability"])


# OPENAPI IMPERFECTION: no response_model, no documented error responses.
# The 500 failure case is completely invisible in the spec. The success
# response shape (status + message) is undocumented.
@router.get(
    "/unstable",
    summary="Unstable endpoint",
    # IMPERFECTION: description says "may fail" but doesn't specify
    # the failure mode, status code, or body structure
    description="Test endpoint that may fail randomly.",
)
def unstable_endpoint():
    if random.random() < 0.5:
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Random internal failure",
                "error_code": "UNSTABLE_FAILURE",
            },
        )
    return {
        "status": "ok",
        "message": "You got lucky this time.",
    }


# OPENAPI IMPERFECTION: documents a response_model that is only
# partially correct — the actual response includes 'delay_seconds'
# (a float) but the spec shows no schema at all. Also: the latency
# behavior is not mentioned in the spec.
@router.get(
    "/unstable/slow",
    # IMPERFECTION: no summary, no description, no response_model
)
def slow_endpoint():
    delay = round(random.uniform(0.5, 3.0), 2)
    time.sleep(delay)
    return {
        "status": "ok",
        "delay_seconds": delay,
    }
