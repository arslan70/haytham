"""Risk classification tool for startup validation.

This tool encapsulates business rules for risk level classification,
allowing the agent to focus on analysis while the tool applies
consistent decision criteria.
"""

from strands import tool


@tool
def classify_risk_level(
    high_risk_count: int,
    medium_risk_count: int,
    unsupported_claims: int,
    contradicted_claims: int,
    external_unsupported_claims: int = 0,
    contradicted_critical_claims: int = 0,
) -> str:
    """Classify the overall risk level for a startup based on validation findings.

    Call this tool after you have analyzed all claims and identified risks.
    Provide the counts from your analysis and the tool will apply consistent
    business rules to determine the overall risk level.

    Args:
        high_risk_count: Number of HIGH severity risks identified
        medium_risk_count: Number of MEDIUM severity risks identified
        unsupported_claims: Number of claims that could not be validated
        contradicted_claims: Number of claims that were contradicted by evidence
        external_unsupported_claims: Number of external claims that are unsupported or contradicted
        contradicted_critical_claims: Number of critical-severity claims that were contradicted

    Returns:
        Risk level classification: "HIGH", "MEDIUM", or "LOW"

    Business Rules:
        HIGH: 1+ contradicted critical claim, OR 3+ external unsupported,
              OR 2+ high risks, OR 2+ contradicted claims,
              OR (1 high risk AND 2+ unsupported)
        MEDIUM: 2 external unsupported, OR 1 high risk, OR 3+ medium risks,
                OR 3+ unsupported claims
        LOW: All other cases (risks are manageable)
    """
    # Critical claim escalation — one contradicted critical claim is existential
    if contradicted_critical_claims >= 1:
        return "HIGH"

    # External-specific escalation — external unsupported claims are higher-signal
    if external_unsupported_claims >= 3:
        return "HIGH"

    # HIGH risk conditions
    if high_risk_count >= 2:
        return "HIGH"
    if contradicted_claims >= 2:
        return "HIGH"
    if high_risk_count >= 1 and unsupported_claims >= 2:
        return "HIGH"

    # External-specific medium escalation
    if external_unsupported_claims >= 2:
        return "MEDIUM"

    # MEDIUM risk conditions
    if high_risk_count >= 1:
        return "MEDIUM"
    if medium_risk_count >= 3:
        return "MEDIUM"
    if unsupported_claims >= 3:
        return "MEDIUM"

    # LOW risk - manageable
    return "LOW"
