"""Recommendation tool for validation summary.

This module encapsulates Stage-Gate scoring logic for GO/PIVOT/NO-GO decisions.
The agent records knockouts, dimension scores, and counter-signals via scalar-
parameter tools. The verdict is computed deterministically by
``build_scorer_output()`` after the agent finishes.

A module-level ``_scorecard`` accumulator collects items across tool calls
(same pattern as ``context_retrieval.py``).  Lifecycle helpers
``init_scorecard()`` / ``clear_scorecard()`` / ``get_scorecard()`` are plain
functions used by the stage executor to bracket each agent run.
``init_scorecard(risk_level=...)`` pre-sets authoritative upstream values
so the agent cannot re-derive or misextract them.

``evaluate_recommendation()`` is kept as a JSON-string wrapper for backward
compatibility with existing tests.

Decision rules (Robert Cooper Stage-Gate inspired):
- Any knockout FAIL -> NO-GO
- Any dimension <= 2 -> cap composite at 3.0
- Composite avg <= 2.0 -> NO-GO
- Composite avg 2.1-3.5 -> PIVOT
- Composite avg > 3.5, risk HIGH -> PIVOT (unconditional)
- Composite avg > 3.5, risk != HIGH -> GO
"""

import json
import re

from strands import tool

_HIGH_SCORE_THRESHOLD = 4
_DIMENSION_FLOOR_SCORE = 2
_FLOOR_CAPPED_COMPOSITE = 3.0

# Valid upstream context keys that the scorer receives
_VALID_SOURCES = frozenset(
    {
        "idea_analysis",
        "market_context",
        "risk_assessment",
        "pivot_strategy",
        "concept_anchor",
        "founder_context",
    }
)

# Regex to extract (source: X) tag from evidence text (supports spaces and underscores)
_SOURCE_TAG_RE = re.compile(r"\(source:\s*([\w ]+)\)")

# Rubric phrases that indicate the LLM copied the scoring rubric
# instead of citing actual upstream data
_RUBRIC_PHRASES = (
    # Level 4-5 rubric descriptions
    "users pay for workarounds today",
    "constraints are realistic and comparable products have solved them",
    "large addressable market with strong growth",
    "clear differentiation with moderate defensibility",
    "clearly feasible with known technology and reasonable effort",
    "feasible with known technology and reasonable effort",
    "no significant operational constraints",
    # Level 3 rubric descriptions (seen copied verbatim in reports)
    "moderate pain, users actively seek solutions",
    "some differentiation but easily replicable",
    "achievable with significant effort and some risk",
    "plausible revenue model; competitors use similar pricing models",
    "operational constraints exist but are manageable with effort",
    "moderate adjustment; product changes some workflows but leverages familiar interaction patterns",
)

# ---------------------------------------------------------------------------
# Evidence validation for high scores
# ---------------------------------------------------------------------------


def _normalize_source(source: str) -> str:
    """Normalize source name: lowercase, replace spaces with underscores."""
    return source.strip().lower().replace(" ", "_")


# The 6 required scored dimensions (ADR-023 final)
_REQUIRED_DIMENSIONS = (
    "Problem Severity",
    "Market Opportunity",
    "Competitive Differentiation",
    "Execution Feasibility",
    "Revenue Viability",
    "Adoption & Engagement Risk",
)


def _validate_evidence(score: int, evidence: str) -> str | None:
    """Validate evidence for a dimension score. Returns error msg or None."""
    # Rubric phrase check applies to ALL scores
    evidence_lower = evidence.lower()
    for phrase in _RUBRIC_PHRASES:
        if phrase in evidence_lower:
            return (
                f"REJECTED: evidence contains rubric text '{phrase}'. "
                f"Cite a specific finding from upstream data instead. "
                f"Re-call with real evidence."
            )

    # Source tag + validity check only for high scores
    if score < _HIGH_SCORE_THRESHOLD:
        return None

    source_match = _SOURCE_TAG_RE.search(evidence)
    if not source_match:
        return (
            f"REJECTED: score {score} requires '(source: stage_name)' in evidence. "
            f"Valid sources: {', '.join(sorted(_VALID_SOURCES))}. "
            f"Re-call with sourced evidence or lower the score to 3."
        )

    source_name = _normalize_source(source_match.group(1))
    if source_name not in _VALID_SOURCES:
        return (
            f"REJECTED: '{source_name}' is not a valid upstream stage. "
            f"Valid sources: {', '.join(sorted(_VALID_SOURCES))}. "
            f"Re-call with a valid source."
        )

    return None


# ---------------------------------------------------------------------------
# Module-level scorecard accumulator
# ---------------------------------------------------------------------------
# Uses a plain module-level dict instead of threading.local() because the
# Strands SDK runs agents in a ThreadPoolExecutor worker thread. Thread-local
# storage would isolate the main thread (init/clear/build) from the worker
# thread (tools). The init -> agent run -> build -> clear lifecycle ensures
# there's no concurrent access.


def _new_scorecard() -> dict:
    """Create a fresh scorecard with default structure."""
    return {
        "knockouts": [],
        "dimensions": [],
        "counter_signals": [],
        "risk_level": "",
    }


_scorecard: dict = _new_scorecard()


def _get_scorecard() -> dict:
    """Return the current scorecard."""
    return _scorecard


def clear_scorecard() -> None:
    """Reset the scorecard accumulator to empty state."""
    global _scorecard
    _scorecard = _new_scorecard()


def init_scorecard(*, risk_level: str) -> None:
    """Initialize scorecard with authoritative upstream values.

    Pre-sets values that the system already extracted in prior stages.
    Call this instead of clear_scorecard() when upstream values are available.
    The agent's tools will use these pre-set values directly.

    Args:
        risk_level: Authoritative risk level from the Burr state
            (extracted by risk_assessment stage). Must be HIGH, MEDIUM, or LOW.

    Raises:
        ValueError: If risk_level is empty or not a valid level.
    """
    global _scorecard
    if not risk_level or risk_level.upper() not in ("HIGH", "MEDIUM", "LOW"):
        raise ValueError(f"risk_level must be HIGH, MEDIUM, or LOW, got: {risk_level!r}")
    sc = _new_scorecard()
    sc["risk_level"] = risk_level.upper()
    _scorecard = sc


def get_scorecard() -> dict:
    """Return a copy of the current scorecard state (testing/debugging only)."""
    return dict(_get_scorecard())


# ---------------------------------------------------------------------------
# Scalar-parameter @tool functions (Nova Lite v1 compatible)
# ---------------------------------------------------------------------------


@tool
def record_knockout(criterion: str, result: str, evidence: str) -> str:
    """Record a knockout criterion evaluation result.

    Call this once for each of the 3 knockout criteria (Problem Reality,
    Channel Access, Regulatory/Ethical).

    Args:
        criterion: Name of the knockout criterion (e.g. "Problem Reality").
        result: "PASS" or "FAIL".
        evidence: Brief evidence supporting the result.

    Returns:
        Confirmation message with current knockout count.
    """
    sc = _get_scorecard()
    new_entry = {
        "criterion": criterion,
        "result": result.upper(),
        "evidence": evidence,
    }

    # Replace existing entry for same criterion (model may re-record after
    # evidence rejection), otherwise append.
    replaced = False
    for i, k in enumerate(sc["knockouts"]):
        if k["criterion"] == criterion:
            sc["knockouts"][i] = new_entry
            replaced = True
            break
    if not replaced:
        sc["knockouts"].append(new_entry)

    n = len(sc["knockouts"])
    verb = "Updated" if replaced else "Recorded"
    return f"{verb} knockout '{criterion}' = {result.upper()}. Total knockouts: {n}"


@tool
def record_dimension_score(dimension: str, score: int, evidence: str) -> str:
    """Record a scored dimension evaluation.

    Call this once for each of the 6 scored dimensions.

    Args:
        dimension: Name of the dimension (e.g. "Problem Severity").
        score: Score from 1 to 5.
        evidence: Brief evidence supporting the score.

    Returns:
        Confirmation message with current dimension count, or REJECTED message
        if evidence fails validation for high scores.
    """
    error = _validate_evidence(int(score), evidence)
    if error:
        return error

    sc = _get_scorecard()

    new_entry = {
        "dimension": dimension,
        "score": int(score),
        "evidence": evidence,
    }

    # Replace existing entry for same dimension (model may re-record after
    # evidence rejection), otherwise append.
    replaced = False
    for i, d in enumerate(sc["dimensions"]):
        if d["dimension"] == dimension:
            sc["dimensions"][i] = new_entry
            replaced = True
            break
    if not replaced:
        sc["dimensions"].append(new_entry)

    n = len(sc["dimensions"])
    verb = "Updated" if replaced else "Recorded"
    return f"{verb} dimension '{dimension}' = {score}/5. Total dimensions: {n}"


@tool
def record_counter_signal(
    signal: str,
    source: str,
    affected_dimensions: str,
    reconciliation: str,
) -> str:
    """Record a counter-signal found in upstream context.

    Counter-signals are displayed in the report for transparency but do not
    override the deterministic verdict rules.

    Args:
        signal: The negative finding (quote or paraphrase upstream text).
        source: Which stage it came from (e.g. "risk_assessment").
        affected_dimensions: Comma-separated dimension names this signal
            affects (e.g. "Market Opportunity, Problem Severity").
        reconciliation: Why the dimension score is still appropriate despite
            this signal, and what evidence would change it.

    Returns:
        Confirmation message with current counter-signal count, or REJECTED
        message if the source is not a valid upstream stage.
    """
    normalized_source = _normalize_source(source)
    if normalized_source not in _VALID_SOURCES:
        return (
            f"REJECTED: '{source}' is not a valid upstream stage. "
            f"Valid sources: {', '.join(sorted(_VALID_SOURCES))}. "
            f"Re-call with a valid source."
        )

    sc = _get_scorecard()
    dims = [d.strip() for d in affected_dimensions.split(",") if d.strip()]
    sc["counter_signals"].append(
        {
            "signal": signal,
            "source": normalized_source,
            "affected_dimensions": dims,
            "reconciliation": reconciliation,
        }
    )
    n = len(sc["counter_signals"])
    return f"Recorded counter-signal '{signal[:40]}...'. Total signals: {n}"


# ---------------------------------------------------------------------------
# Core verdict logic (dict-based, no serialization overhead)
# ---------------------------------------------------------------------------


def _evaluate_core(
    knockouts: list[dict],
    dimensions: list[dict],
    risk_level: str,
) -> dict:
    """Apply Stage-Gate decision rules to produce a verdict dict.

    This is the single source of truth for scoring logic. Called by
    ``build_scorer_output()`` (dicts from scorecard) and
    ``evaluate_recommendation()`` (JSON-string wrapper for backward compat).

    Decision Rules:
        1. Any knockout FAIL -> NO-GO
        2. Any dimension <= 2 -> cap composite at 3.0
        3. Composite <= 2.0 -> NO-GO
        4. Composite 2.1-3.5 -> PIVOT
        5. Composite > 3.5, risk HIGH -> PIVOT (unconditional)
        6. Composite > 3.5, risk != HIGH -> GO
    """
    # Check knockouts -- any FAIL is an immediate NO-GO
    has_knockout_fail = any(k.get("result", "").upper() == "FAIL" for k in knockouts)

    if has_knockout_fail:
        return {
            "verdict": "NO-GO",
            "recommendation": "NO-GO",
            "composite_score": 0.0,
            "reason": "Knockout criterion failed",
            "warnings": [],
            "adjusted": False,
        }

    # Compute composite score
    scores = [d["score"] for d in dimensions]
    if not scores:
        return {
            "verdict": "NO-GO",
            "recommendation": "NO-GO",
            "composite_score": 0.0,
            "reason": "No dimension scores provided",
            "warnings": [],
            "adjusted": False,
        }

    composite = sum(scores) / len(scores)

    # Floor rule: if any dimension scores at or below the floor, cap composite
    floor_violations = [d["dimension"] for d in dimensions if d["score"] <= _DIMENSION_FLOOR_SCORE]
    floor_capped = False
    if floor_violations and composite > _FLOOR_CAPPED_COMPOSITE:
        composite = _FLOOR_CAPPED_COMPOSITE
        floor_capped = True

    # Apply threshold rules
    if composite <= 2.0:
        verdict = "NO-GO"
        recommendation = "NO-GO"
    elif composite <= 3.5:
        verdict = "CONDITIONAL GO"
        recommendation = "PIVOT"
    else:
        verdict = "GO"
        recommendation = "GO"

    # Risk veto: HIGH risk always caps GO -> PIVOT
    risk_capped = False
    if risk_level.upper() == "HIGH" and recommendation == "GO":
        verdict = "CONDITIONAL GO"
        recommendation = "PIVOT"
        risk_capped = True

    return {
        "verdict": verdict,
        "recommendation": recommendation,
        "composite_score": round(composite, 1),
        "warnings": [],
        "adjusted": False,
        "floor_capped": floor_capped,
        "floor_violations": floor_violations,
        "risk_capped": risk_capped,
    }


# ---------------------------------------------------------------------------
# Legacy JSON-string wrapper (called by tests). Delegates to _evaluate_core().
# ---------------------------------------------------------------------------


def evaluate_recommendation(
    knockout_results: str,
    dimension_scores: str,
    counter_signals: str = "[]",
    risk_level: str = "",
    evidence_quality: str = "{}",
) -> str:
    """Evaluate the Go/No-Go recommendation using Stage-Gate scorecard rules.

    JSON-string wrapper for backward compatibility with existing tests.
    Delegates to ``_evaluate_core()`` for the actual logic.

    Args:
        knockout_results: JSON array of knockout results.
        dimension_scores: JSON array of dimension scores.
        counter_signals: Unused, kept for backward compatibility.
        risk_level: Risk level ("HIGH", "MEDIUM", "LOW"). Optional, default "".
        evidence_quality: Unused, kept for backward compatibility.

    Returns:
        JSON string with verdict, recommendation, composite_score, warnings, etc.
    """
    result = _evaluate_core(
        knockouts=json.loads(knockout_results),
        dimensions=json.loads(dimension_scores),
        risk_level=risk_level,
    )
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Build ScorerOutput from the scorecard accumulator
# ---------------------------------------------------------------------------

_GUIDANCE_TEMPLATES = {
    "NO-GO": "Do not proceed. Fundamental issues identified{gaps}. Re-evaluate the concept or explore a different problem space.",
    "PIVOT": "Concept has potential but needs significant changes before proceeding{gaps}. Validate assumptions with customer discovery before building.",
    "GO": "Proceed with MVP development{gaps}. Validate core assumptions early and track key metrics from day one.",
}


def _build_guidance(recommendation: str, critical_gaps: list[str]) -> str:
    """Generate deterministic guidance from verdict and critical gaps."""
    template = _GUIDANCE_TEMPLATES.get(recommendation, _GUIDANCE_TEMPLATES["PIVOT"])
    if critical_gaps:
        gap_str = f". Focus on: {', '.join(critical_gaps)}"
    else:
        gap_str = ""
    return template.format(gaps=gap_str)


def build_scorer_output() -> dict | None:
    """Build a ScorerOutput dict from the scorecard accumulator.

    Call this AFTER the scorer agent finishes but BEFORE clear_scorecard().
    Returns None if the scorecard is incomplete (missing knockouts or
    dimensions, meaning the agent failed before the core tools ran).

    The verdict is always computed deterministically from the accumulated
    scores. The LLM's job is qualitative (evaluating evidence, assigning
    scores). The verdict is pure math from those scores.

    Returns:
        Dict matching the ScorerOutput schema, or None if data is incomplete.
    """
    sc = _get_scorecard()

    knockouts = sc["knockouts"]
    dimensions = sc["dimensions"]
    if not knockouts or not dimensions:
        return None

    # Check all 6 required dimensions are present
    recorded_dims = {d["dimension"] for d in dimensions}
    missing = [d for d in _REQUIRED_DIMENSIONS if d not in recorded_dims]
    if missing:
        return None

    verdict_result = _evaluate_core(
        knockouts=knockouts,
        dimensions=dimensions,
        risk_level=sc["risk_level"],
    )

    recommendation = verdict_result.get("recommendation", "")
    critical_gaps = [d["dimension"] for d in dimensions if d["score"] <= _DIMENSION_FLOOR_SCORE]

    return {
        "knockout_criteria": knockouts,
        "counter_signals": sc["counter_signals"],
        "scorecard": dimensions,
        "composite_score": verdict_result.get("composite_score", 0.0),
        "verdict": verdict_result.get("verdict", ""),
        "recommendation": recommendation,
        "floor_capped": verdict_result.get("floor_capped", False),
        "risk_capped": verdict_result.get("risk_capped", False),
        "critical_gaps": critical_gaps,
        "guidance": _build_guidance(recommendation, critical_gaps),
        "risk_level": sc["risk_level"],
    }
