"""
Unstable and delayed endpoints — intentionally erratic for QA benchmarking.

GET /unstable        — randomly returns 200 or 500
GET /unstable/slow   — adds a random delay (0.5–3 s) before responding
"""

import random
import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["instability"])


@router.get("/unstable")
def unstable_endpoint():
    """Randomly succeeds or fails. ~50 % chance of a 500."""
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


@router.get("/unstable/slow")
def slow_endpoint():
    """Responds after a random delay (0.5 – 3 s). Always succeeds."""
    delay = round(random.uniform(0.5, 3.0), 2)
    time.sleep(delay)
    return {
        "status": "ok",
        "delay_seconds": delay,
    }
