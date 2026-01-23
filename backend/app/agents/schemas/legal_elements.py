"""Legal element schemas organized by legal area.

These schemas define the elements that must typically be satisfied for various
legal claims, defences, and actions under Australian law. They provide a
framework for the legal elements mapping stage to assess case viability.

Note: These are simplified educational frameworks, not legal advice.
"""

from typing import TypedDict


class ElementDefinition(TypedDict):
    """Definition of a single legal element."""
    name: str
    description: str
    typical_evidence: list[str]


class LegalAreaElements(TypedDict):
    """Elements framework for a legal area."""
    area: str
    sub_category: str
    claim_type: str
    elements: list[ElementDefinition]
    relevant_legislation: list[str]
    key_defences: list[str]


# ============================================
# Tenancy Law Elements
# ============================================

TENANCY_BOND_REFUND: LegalAreaElements = {
    "area": "tenancy",
    "sub_category": "bond_refund",
    "claim_type": "Bond refund claim",
    "elements": [
        {
            "name": "Valid tenancy agreement",
            "description": "A valid residential tenancy agreement existed",
            "typical_evidence": ["Lease/tenancy agreement", "Bond lodgement receipt"],
        },
        {
            "name": "Bond paid",
            "description": "Bond was paid to landlord/agent or bond authority",
            "typical_evidence": ["Payment receipt", "Bond authority statement", "Bank transfer record"],
        },
        {
            "name": "Tenancy ended",
            "description": "The tenancy has properly concluded",
            "typical_evidence": ["Notice to vacate", "End of lease document", "Keys returned receipt"],
        },
        {
            "name": "Property condition",
            "description": "Property returned in reasonable condition (fair wear and tear)",
            "typical_evidence": ["Entry condition report", "Exit condition report", "Photos", "Cleaning receipts"],
        },
        {
            "name": "No outstanding rent/costs",
            "description": "All rent and agreed costs are paid, or legitimate deductions only",
            "typical_evidence": ["Rent receipts", "Final rent statement", "Invoice for legitimate damages"],
        },
    ],
    "relevant_legislation": [
        "Residential Tenancies Act 1997 (Vic)",
        "Residential Tenancies Act 2010 (NSW)",
        "Residential Tenancies and Rooming Accommodation Act 2008 (Qld)",
        "Residential Tenancies Act 1987 (WA)",
    ],
    "key_defences": [
        "Property damage beyond fair wear and tear",
        "Outstanding rent or utility payments",
        "Cleaning required beyond reasonable standard",
        "Unpaid break lease fees (if applicable)",
    ],
}

TENANCY_EVICTION: LegalAreaElements = {
    "area": "tenancy",
    "sub_category": "eviction_notice",
    "claim_type": "Challenge to eviction notice",
    "elements": [
        {
            "name": "Valid notice",
            "description": "Notice was served correctly with required information",
            "typical_evidence": ["Copy of notice", "Proof of service", "Timeline of notice"],
        },
        {
            "name": "Correct notice period",
            "description": "Required notice period was provided",
            "typical_evidence": ["Notice date", "Tenancy type (fixed/periodic)", "State-specific requirements"],
        },
        {
            "name": "Valid grounds",
            "description": "Landlord has valid legal grounds for eviction",
            "typical_evidence": ["Stated reason on notice", "Evidence of breach (if alleged)"],
        },
        {
            "name": "Procedural compliance",
            "description": "Proper procedures followed (no self-help eviction)",
            "typical_evidence": ["Communication records", "Tribunal/court orders (if any)"],
        },
    ],
    "relevant_legislation": [
        "Residential Tenancies Act 1997 (Vic)",
        "Residential Tenancies Act 2010 (NSW)",
        "Residential Tenancies and Rooming Accommodation Act 2008 (Qld)",
    ],
    "key_defences": [
        "Valid grounds for eviction exist",
        "Proper notice period provided",
        "Breach of tenancy agreement by tenant",
        "End of fixed term agreement",
    ],
}

TENANCY_REPAIRS: LegalAreaElements = {
    "area": "tenancy",
    "sub_category": "repairs_maintenance",
    "claim_type": "Repairs and maintenance claim",
    "elements": [
        {
            "name": "Landlord obligation",
            "description": "The repair falls under landlord's obligations",
            "typical_evidence": ["Nature of repair", "Lease terms", "Legislation reference"],
        },
        {
            "name": "Proper notification",
            "description": "Tenant properly notified landlord of the issue",
            "typical_evidence": ["Written request", "Email/text messages", "Date of notification"],
        },
        {
            "name": "Reasonable time elapsed",
            "description": "Landlord given reasonable time to respond (urgency considered)",
            "typical_evidence": ["Timeline of communications", "Urgency level of repair"],
        },
        {
            "name": "Failure to repair",
            "description": "Landlord has not made the required repairs",
            "typical_evidence": ["Current state of property", "Photos", "Inspection records"],
        },
    ],
    "relevant_legislation": [
        "Residential Tenancies Act 1997 (Vic) s.68-69",
        "Residential Tenancies Act 2010 (NSW) s.63-64",
        "Residential Tenancies and Rooming Accommodation Act 2008 (Qld) s.185",
    ],
    "key_defences": [
        "Damage caused by tenant",
        "Insufficient notice provided",
        "Repair is cosmetic/not required",
        "Access denied by tenant",
    ],
}


# ============================================
# Employment Law Elements
# ============================================

EMPLOYMENT_UNFAIR_DISMISSAL: LegalAreaElements = {
    "area": "employment",
    "sub_category": "unfair_dismissal",
    "claim_type": "Unfair dismissal claim",
    "elements": [
        {
            "name": "Employment relationship",
            "description": "An employment relationship existed (not contractor)",
            "typical_evidence": ["Employment contract", "Payslips", "Tax records", "Work patterns"],
        },
        {
            "name": "Minimum employment period",
            "description": "Employed for required minimum period (6 months or 12 months for small business)",
            "typical_evidence": ["Start date", "Termination date", "Employment records"],
        },
        {
            "name": "Dismissal occurred",
            "description": "Employment was terminated at employer's initiative",
            "typical_evidence": ["Termination letter", "Resignation (if forced)", "Communication records"],
        },
        {
            "name": "Harsh, unjust or unreasonable",
            "description": "The dismissal was harsh, unjust or unreasonable",
            "typical_evidence": ["Reason given", "Warnings received", "Investigation process", "Comparator treatment"],
        },
        {
            "name": "Procedural fairness",
            "description": "Employee was (or should have been) given opportunity to respond",
            "typical_evidence": ["Show cause letters", "Meeting records", "Response opportunities"],
        },
    ],
    "relevant_legislation": [
        "Fair Work Act 2009 (Cth) Part 3-2",
        "Fair Work Regulations 2009",
    ],
    "key_defences": [
        "Genuine redundancy",
        "Small business fair dismissal code compliance",
        "Valid reason for dismissal",
        "Proper process followed",
        "Serious misconduct",
    ],
}

EMPLOYMENT_UNDERPAYMENT: LegalAreaElements = {
    "area": "employment",
    "sub_category": "underpayment",
    "claim_type": "Underpayment/wage theft claim",
    "elements": [
        {
            "name": "Employment relationship",
            "description": "An employment relationship existed",
            "typical_evidence": ["Contract", "Payslips", "Tax records", "Work performed"],
        },
        {
            "name": "Applicable instrument",
            "description": "Relevant award, agreement, or minimum wage applies",
            "typical_evidence": ["Award coverage", "Enterprise agreement", "Employment contract"],
        },
        {
            "name": "Work performed",
            "description": "Work was performed as claimed",
            "typical_evidence": ["Timesheets", "Rosters", "Emails showing work", "Witness statements"],
        },
        {
            "name": "Underpayment amount",
            "description": "Payment received was less than legal entitlement",
            "typical_evidence": ["Payslips", "Bank statements", "Award/agreement rates", "Calculation spreadsheet"],
        },
    ],
    "relevant_legislation": [
        "Fair Work Act 2009 (Cth)",
        "National Employment Standards",
        "Modern Awards",
    ],
    "key_defences": [
        "Correct classification and payment",
        "Offset arrangements",
        "Time-barred claims (6 years)",
        "Contractor not employee",
    ],
}


# ============================================
# Family Law Elements
# ============================================

FAMILY_DOMESTIC_VIOLENCE_ORDER: LegalAreaElements = {
    "area": "family",
    "sub_category": "domestic_violence_order",
    "claim_type": "Application for DVO/AVO",
    "elements": [
        {
            "name": "Relevant relationship",
            "description": "A relevant domestic relationship exists or existed",
            "typical_evidence": ["Relationship history", "Cohabitation evidence", "Family connections"],
        },
        {
            "name": "Domestic violence",
            "description": "Domestic violence has occurred (physical, emotional, economic, etc.)",
            "typical_evidence": ["Incident reports", "Medical records", "Photos", "Witness statements"],
        },
        {
            "name": "Fear of future violence",
            "description": "Applicant fears future domestic violence",
            "typical_evidence": ["Pattern of behaviour", "Threats made", "Escalation evidence"],
        },
        {
            "name": "Protection needed",
            "description": "An order is necessary to protect the applicant",
            "typical_evidence": ["Current living situation", "Children involved", "Safety concerns"],
        },
    ],
    "relevant_legislation": [
        "Family Violence Protection Act 2008 (Vic)",
        "Crimes (Domestic and Personal Violence) Act 2007 (NSW)",
        "Domestic and Family Violence Protection Act 2012 (Qld)",
    ],
    "key_defences": [
        "No domestic relationship",
        "Alleged conduct did not occur",
        "No fear reasonably held",
        "Cross-application warranted",
    ],
}

FAMILY_CHILD_CUSTODY: LegalAreaElements = {
    "area": "family",
    "sub_category": "child_custody",
    "claim_type": "Parenting orders (custody/visitation)",
    "elements": [
        {
            "name": "Child's best interests",
            "description": "Proposed arrangement serves the child's best interests",
            "typical_evidence": [
                "Current arrangements",
                "Child's wishes (if appropriate age)",
                "Each parent's circumstances",
            ],
        },
        {
            "name": "Meaningful relationship",
            "description": "Child benefits from meaningful relationship with both parents",
            "typical_evidence": ["Relationship history", "Involvement in child's life", "Communication patterns"],
        },
        {
            "name": "Protection from harm",
            "description": "Child is protected from harm, abuse, neglect, or family violence",
            "typical_evidence": ["Safety concerns", "Family violence history", "Child protection involvement"],
        },
        {
            "name": "Practical considerations",
            "description": "Arrangement is practical and workable",
            "typical_evidence": ["Proximity of homes", "Work schedules", "School arrangements", "Child's activities"],
        },
    ],
    "relevant_legislation": [
        "Family Law Act 1975 (Cth) Part VII",
    ],
    "key_defences": [
        "Safety concerns about other parent",
        "Child's expressed wishes",
        "Practical impossibility of proposed arrangement",
        "History of non-compliance with orders",
    ],
}


# ============================================
# Consumer/Contract Elements
# ============================================

CONSUMER_REFUND: LegalAreaElements = {
    "area": "consumer",
    "sub_category": "refund",
    "claim_type": "Consumer guarantee refund claim",
    "elements": [
        {
            "name": "Consumer transaction",
            "description": "Purchase was a consumer transaction under ACL",
            "typical_evidence": ["Receipt", "Invoice", "Transaction record", "Price paid"],
        },
        {
            "name": "Consumer guarantee breach",
            "description": "Goods/services failed to meet a consumer guarantee",
            "typical_evidence": ["Nature of defect", "Expert report", "Photos", "Comparison to description"],
        },
        {
            "name": "Major failure (for refund)",
            "description": "The failure is a major failure (or multiple minor failures)",
            "typical_evidence": ["Impact on use", "Safety issues", "Inability to fix", "Repeated failures"],
        },
        {
            "name": "Timeframe",
            "description": "Claim made within reasonable time",
            "typical_evidence": ["Purchase date", "Discovery date", "Communication timeline"],
        },
    ],
    "relevant_legislation": [
        "Australian Consumer Law (Schedule 2 of Competition and Consumer Act 2010)",
    ],
    "key_defences": [
        "Not a consumer transaction",
        "Damage caused by consumer",
        "Issue disclosed before purchase",
        "Reasonable time for remedy not given",
    ],
}


# ============================================
# Criminal Law Elements (for context/information)
# ============================================

CRIMINAL_ASSAULT: LegalAreaElements = {
    "area": "criminal",
    "sub_category": "assault",
    "claim_type": "Assault charge (prosecution must prove)",
    "elements": [
        {
            "name": "Physical contact or threat",
            "description": "Accused made physical contact or caused fear of immediate violence",
            "typical_evidence": ["Victim statement", "Medical evidence", "Witness statements", "CCTV"],
        },
        {
            "name": "Intentional or reckless",
            "description": "The act was intentional or reckless (not accidental)",
            "typical_evidence": ["Circumstances of incident", "Prior conduct", "Statements made"],
        },
        {
            "name": "Without consent",
            "description": "The contact was without consent",
            "typical_evidence": ["Victim statement", "Nature of relationship", "Context of interaction"],
        },
        {
            "name": "Without lawful excuse",
            "description": "No lawful excuse (e.g., self-defence) applied",
            "typical_evidence": ["Full incident context", "Who initiated", "Proportionality"],
        },
    ],
    "relevant_legislation": [
        "Crimes Act 1900 (NSW) s.61",
        "Crimes Act 1958 (Vic) s.31",
        "Criminal Code Act 1899 (Qld) s.335",
    ],
    "key_defences": [
        "Self-defence",
        "Defence of another",
        "Consent",
        "Accident",
        "Lawful correction (limited)",
    ],
}


# ============================================
# Element Lookup Functions
# ============================================

# Map of area/sub_category to element definitions
ELEMENT_SCHEMAS: dict[str, LegalAreaElements] = {
    "tenancy/bond_refund": TENANCY_BOND_REFUND,
    "tenancy/bond_dispute": TENANCY_BOND_REFUND,  # Alias
    "tenancy/eviction_notice": TENANCY_EVICTION,
    "tenancy/eviction": TENANCY_EVICTION,  # Alias
    "tenancy/repairs_maintenance": TENANCY_REPAIRS,
    "tenancy/repairs": TENANCY_REPAIRS,  # Alias
    "employment/unfair_dismissal": EMPLOYMENT_UNFAIR_DISMISSAL,
    "employment/unfair_termination": EMPLOYMENT_UNFAIR_DISMISSAL,  # Alias
    "employment/underpayment": EMPLOYMENT_UNDERPAYMENT,
    "employment/wages": EMPLOYMENT_UNDERPAYMENT,  # Alias
    "employment/wage_theft": EMPLOYMENT_UNDERPAYMENT,  # Alias
    "family/domestic_violence_order": FAMILY_DOMESTIC_VIOLENCE_ORDER,
    "family/domestic_violence": FAMILY_DOMESTIC_VIOLENCE_ORDER,  # Alias
    "family/dvo": FAMILY_DOMESTIC_VIOLENCE_ORDER,  # Alias
    "family/avo": FAMILY_DOMESTIC_VIOLENCE_ORDER,  # Alias
    "family/child_custody": FAMILY_CHILD_CUSTODY,
    "family/custody": FAMILY_CHILD_CUSTODY,  # Alias
    "family/parenting": FAMILY_CHILD_CUSTODY,  # Alias
    "consumer/refund": CONSUMER_REFUND,
    "consumer/consumer_guarantee": CONSUMER_REFUND,  # Alias
    "contract/refund": CONSUMER_REFUND,  # Alias
    "criminal/assault": CRIMINAL_ASSAULT,
}


def get_element_schema(area: str, sub_category: str) -> LegalAreaElements | None:
    """
    Get the element schema for a given legal area and sub-category.

    Args:
        area: Legal area (e.g., "tenancy", "employment")
        sub_category: Specific sub-category (e.g., "bond_refund", "unfair_dismissal")

    Returns:
        LegalAreaElements if found, None otherwise
    """
    key = f"{area}/{sub_category}"
    return ELEMENT_SCHEMAS.get(key)


def get_areas_with_schemas() -> list[str]:
    """Get list of area/sub_category combinations that have element schemas."""
    return list(ELEMENT_SCHEMAS.keys())
