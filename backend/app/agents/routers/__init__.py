"""Routing logic for adaptive legal agent."""

from app.agents.routers.safety_router import SafetyRouter, get_safety_router
from app.agents.routers.complexity_router import (
    ComplexityRouter,
    get_complexity_router,
    route_by_complexity,
    classify_complexity_heuristic,
)

__all__ = [
    "SafetyRouter",
    "get_safety_router",
    "ComplexityRouter",
    "get_complexity_router",
    "route_by_complexity",
    "classify_complexity_heuristic",
]
