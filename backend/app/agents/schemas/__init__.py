"""Schemas for adaptive legal agent."""

from app.agents.schemas.emergency_resources import EMERGENCY_RESOURCES, get_resources_for_risk
from app.agents.schemas.legal_elements import (
    get_element_schema,
    get_areas_with_schemas,
    ELEMENT_SCHEMAS,
    LegalAreaElements,
    ElementDefinition,
)

__all__ = [
    # Emergency resources
    "EMERGENCY_RESOURCES",
    "get_resources_for_risk",
    # Legal elements
    "get_element_schema",
    "get_areas_with_schemas",
    "ELEMENT_SCHEMAS",
    "LegalAreaElements",
    "ElementDefinition",
]
