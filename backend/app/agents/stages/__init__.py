"""Stage implementations for adaptive legal agent workflow."""

from app.agents.stages.safety_gate import (
    safety_gate_node,
    route_after_safety,
    format_escalation_response,
)
from app.agents.stages.issue_identification import (
    issue_identification_node,
    get_issue_identifier,
)
from app.agents.stages.jurisdiction import (
    jurisdiction_node,
    get_jurisdiction_resolver,
)

__all__ = [
    # Stage 0: Safety Gate
    "safety_gate_node",
    "route_after_safety",
    "format_escalation_response",
    # Stage 1: Issue Identification
    "issue_identification_node",
    "get_issue_identifier",
    # Stage 2: Jurisdiction
    "jurisdiction_node",
    "get_jurisdiction_resolver",
]
