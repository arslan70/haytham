"""Recommendation tool for validation summary.

This module encapsulates Stage-Gate scoring logic for GO/PIVOT/NO-GO decisions.
The agent records knockouts, dimension scores, and counter-signals via scalar-
parameter tools, then calls compute_verdict to apply consistent decision rules.

A module-level ``_scorecard`` accumulator collects items across tool calls
(same pattern as ``context_retrieval.py``).  Lifecycle helpers
``init_scorecard()`` / ``clear_scorecard()`` / ``get_scorecard()`` are plain
functions used by the stage executor to bracket each agent run.
``init_scorecard(risk_level=...)`` pre-sets authoritative upstream values
so the agent cannot re-derive or misextract them.

The legacy ``evaluate_recommendation()`` function is kept as a regular function
(no @tool decorator) for backward compatibility with existing tests and callers.

Decision rules (Robert Cooper Stage-Gate inspired):
- Any knockout FAIL -> NO-GO
- Composite avg <= 2.0 -> NO-GO
- Composite avg 2.1-3.5 -> PIVOT (CONDITIONAL GO)
- Composite avg > 3.5 -> GO
"""

import json
import re
import threading

from strands import tool

_INCONSISTENCY_PENALTY = 0.5
_HIGH_SCORE_THRESHOLD = 4
_INCONSISTENCY_TRIGGER = 2
_DIMENSION_FLOOR_SCORE = 2
_FLOOR_CAPPED_COMPOSITE = 3.0
_MIN_RECONCILED_FOR_HIGH_RISK_GO = 2
_MIN_EVIDENCE_LENGTH = 30

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

# Circular/vacuous phrases that indicate non-substantive reconciliation
_CIRCULAR_PHRASES = re.compile(
    r"(?:based on potential|score is conservative|already accounted|"
    r"noted and considered|taken into account|factored in$)",
    re.IGNORECASE,
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

_EVIDENCE_DEDUP_THRESHOLD = 0.70


def _word_overlap(a: str, b: str) -> float:
    """Compute word-level Jaccard overlap between two strings."""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def _check_evidence_dedup(evidence: str, dimensions: list[dict]) -> str | None:
    """Check if evidence overlaps >70% with any already-recorded dimension.

    Returns error msg or None.
    """
    for existing in dimensions:
        existing_evidence = existing.get("evidence", "")
        if _word_overlap(evidence, existing_evidence) > _EVIDENCE_DEDUP_THRESHOLD:
            return (
                f"REJECTED: evidence has >{int(_EVIDENCE_DEDUP_THRESHOLD * 100)}% word overlap "
                f"with '{existing['dimension']}'. Each dimension must cite distinct evidence. "
                f"Find a different data point and re-call."
            )
    return None


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
# Thread-local accumulator (same pattern as context_retrieval.py)
# ---------------------------------------------------------------------------

_thread_local = threading.local()


def _new_scorecard() -> dict:
    """Create a fresh scorecard with default structure."""
    return {
        "knockouts": [],
        "dimensions": [],
        "counter_signals": [],
        "risk_level": "",
        "evidence_quality": {},
    }


def _get_scorecard() -> dict:
    """Return the current thread's scorecard, initializing if needed."""
    if not hasattr(_thread_local, "scorecard"):
        _thread_local.scorecard = _new_scorecard()
    return _thread_local.scorecard


def clear_scorecard() -> None:
    """Reset the scorecard accumulator to empty state."""
    _thread_local.scorecard = _new_scorecard()


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
    if not risk_level or risk_level.upper() not in ("HIGH", "MEDIUM", "LOW"):
        raise ValueError(f"risk_level must be HIGH, MEDIUM, or LOW, got: {risk_level!r}")
    sc = _new_scorecard()
    sc["risk_level"] = risk_level.upper()
    _thread_local.scorecard = sc


def get_scorecard() -> dict:
    """Return a copy of the current scorecard state (testing/debugging only)."""
    return dict(_get_scorecard())


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _passes_structured_reconciliation(cs: dict) -> bool | None:
    """Check the structured reconciliation path for a counter-signal.

    Returns True if all 3 structured fields are populated and pass quality
    gates, False if they are populated but fail quality, or None if the
    structured fields are not populated (caller should fall back to legacy).
    """
    evidence = (cs.get("evidence_cited") or "").strip()
    why_holds = (cs.get("why_score_holds") or "").strip()
    what_changes = (cs.get("what_would_change_score") or "").strip()

    if not (evidence and why_holds and what_changes):
        return None  # Structured fields not populated — use legacy path

    if len(evidence) < _MIN_EVIDENCE_LENGTH:
        return False
    if _CIRCULAR_PHRASES.search(evidence):
        return False
    return True


_LEGACY_RECONCILED_MIN_CHARS = 20
_LEGACY_WELL_RECONCILED_MIN_CHARS = 50


def _is_signal_reconciled(cs: dict) -> bool:
    """Check whether a counter-signal has adequate reconciliation.

    Structured fields take priority: all three must be non-empty and the
    evidence must be substantive (>= 30 chars, no circular phrases).
    Fallback: legacy ``reconciliation`` text >= 20 chars.
    """
    structured = _passes_structured_reconciliation(cs)
    if structured is not None:
        return structured

    reconciliation = (cs.get("reconciliation") or "").strip()
    return len(reconciliation) >= _LEGACY_RECONCILED_MIN_CHARS


def _compute_confidence_hint(evidence_quality: dict) -> str | None:
    """Compute a confidence hint from evidence quality metrics.

    Rubric (priority order):
    1. Any contradicted critical claim -> LOW
    2. HIGH risk -> cap at MEDIUM (or LOW if < 50% external supported)
    3. < 40% external supported -> LOW
    4. 40-69% external supported -> MEDIUM
    5. >= 70% external supported AND risk != HIGH -> HIGH

    Returns None if evidence_quality is empty/insufficient.
    """
    if not evidence_quality:
        return None

    ext_supported = evidence_quality.get("external_supported", 0)
    ext_total = evidence_quality.get("external_total", 0)
    contradicted_critical = evidence_quality.get("contradicted_critical", 0)
    risk = evidence_quality.get("risk_level", "")

    # Rule 1: contradicted critical claim -> LOW
    if contradicted_critical >= 1:
        return "LOW"

    # Need external claims to compute further
    if ext_total == 0:
        return None

    pct = ext_supported / ext_total

    # Rule 2: HIGH risk -> cap at MEDIUM (or LOW if weak external)
    if risk.upper() == "HIGH":
        return "LOW" if pct < 0.5 else "MEDIUM"

    # Rule 3: < 40% -> LOW
    if pct < 0.4:
        return "LOW"

    # Rule 4: 40-69% -> MEDIUM
    if pct < 0.7:
        return "MEDIUM"

    # Rule 5: >= 70% -> HIGH
    return "HIGH"


def _count_well_reconciled_signals(counter_signals: list[dict]) -> int:
    """Count signals with strong reconciliation (stricter bar for risk veto override).

    Structured: all 3 fields populated + evidence quality gate.
    Legacy: reconciliation text >= 50 chars (stricter than the 20-char consistency check).
    """
    count = 0
    for cs in counter_signals:
        structured = _passes_structured_reconciliation(cs)
        if structured is not None:
            if structured:
                count += 1
        else:
            reconciliation = (cs.get("reconciliation") or "").strip()
            if len(reconciliation) >= _LEGACY_WELL_RECONCILED_MIN_CHARS:
                count += 1
    return count


def _check_counter_signal_consistency(
    counter_signals: list[dict],
    dimensions: list[dict],
) -> list[str]:
    """Check for unreconciled counter-signals on high-scored dimensions.

    Returns a list of human-readable warning strings.
    """
    dim_scores = {d["dimension"]: d["score"] for d in dimensions}
    warnings: list[str] = []

    for cs in counter_signals:
        if not _is_signal_reconciled(cs):
            for dim in cs.get("affected_dimensions", []):
                if dim_scores.get(dim, 0) >= _HIGH_SCORE_THRESHOLD:
                    warnings.append(
                        f"'{dim}' scored {dim_scores[dim]}/5 but counter-signal "
                        f"'{cs.get('signal', '?')}' has no substantive reconciliation"
                    )
    return warnings


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
    sc["knockouts"].append(
        {
            "criterion": criterion,
            "result": result.upper(),
            "evidence": evidence,
        }
    )
    n = len(sc["knockouts"])
    return f"Recorded knockout '{criterion}' = {result.upper()}. Total knockouts: {n}"


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
        if evidence fails validation for high scores or dedup check fails.
    """
    error = _validate_evidence(int(score), evidence)
    if error:
        return error

    sc = _get_scorecard()

    # Evidence dedup: reject if >70% word overlap with already-recorded dimension
    dedup_error = _check_evidence_dedup(evidence, sc["dimensions"])
    if dedup_error:
        return dedup_error

    sc["dimensions"].append(
        {
            "dimension": dimension,
            "score": int(score),
            "evidence": evidence,
        }
    )
    n = len(sc["dimensions"])
    return f"Recorded dimension '{dimension}' = {score}/5. Total dimensions: {n}"


@tool
def record_counter_signal(
    signal: str,
    source: str,
    affected_dimensions: str,
    evidence_cited: str,
    why_score_holds: str,
    what_would_change_score: str,
) -> str:
    """Record a counter-signal found in upstream context.

    Call this once for each counter-signal identified.

    Args:
        signal: The negative finding (quote or paraphrase upstream text).
        source: Which stage it came from (e.g. "risk_assessment").
        affected_dimensions: Comma-separated dimension names this signal
            affects (e.g. "Market Opportunity, Problem Severity").
        evidence_cited: Specific upstream evidence that justifies the current
            score despite this signal.
        why_score_holds: Reasoning for why the dimension score is still
            appropriate.
        what_would_change_score: What new evidence would cause the score to
            change.

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
            "evidence_cited": evidence_cited,
            "why_score_holds": why_score_holds,
            "what_would_change_score": what_would_change_score,
        }
    )
    n = len(sc["counter_signals"])
    return f"Recorded counter-signal '{signal[:40]}...'. Total signals: {n}"


@tool
def set_evidence_quality(
    external_supported: int,
    external_total: int,
    contradicted_critical: int,
) -> str:
    """Set evidence quality metrics from the risk assessment claims analysis.

    Call this once after scoring all dimensions. Risk level is pre-set by the
    system from upstream state and does not need to be provided.

    Args:
        external_supported: Number of externally supported claims.
        external_total: Total number of external claims evaluated.
        contradicted_critical: Number of contradicted critical-severity claims.

    Returns:
        Confirmation message.
    """
    sc = _get_scorecard()
    risk_level = sc["risk_level"]
    sc["evidence_quality"] = {
        "external_supported": int(external_supported),
        "external_total": int(external_total),
        "contradicted_critical": int(contradicted_critical),
        "risk_level": risk_level,
    }
    return (
        f"Evidence quality set (risk_level={risk_level} from system): "
        f"{external_supported}/{external_total} external, "
        f"{contradicted_critical} contradicted critical"
    )


@tool
def compute_verdict() -> str:
    """Compute the final Go/No-Go verdict from the accumulated scorecard.

    Call this after recording all knockouts, dimension scores, counter-signals,
    and risk/evidence. Reads from the module-level scorecard accumulator and
    applies Stage-Gate decision rules.

    Returns:
        JSON string with verdict, recommendation, composite_score, warnings,
        adjusted, floor_capped, floor_violations, risk_capped, and
        confidence_hint.  Returns an error message if required data is missing.
    """
    sc = _get_scorecard()
    knockouts = sc["knockouts"]
    dimensions = sc["dimensions"]
    signals = sc["counter_signals"]
    risk_level = sc["risk_level"]
    eq = sc["evidence_quality"]

    # Validate required data
    if not knockouts:
        return json.dumps(
            {
                "error": "No knockout results recorded. Call record_knockout for each of the 3 criteria first.",
            }
        )
    if not dimensions:
        return json.dumps(
            {
                "error": "No dimension scores recorded. Call record_dimension_score for each of the 6 dimensions first.",
            }
        )

    # Check for missing required dimensions
    recorded_dims = {d["dimension"] for d in dimensions}
    missing = [d for d in _REQUIRED_DIMENSIONS if d not in recorded_dims]
    if missing:
        return json.dumps(
            {
                "error": (
                    f"Missing {len(missing)} required dimension(s): {', '.join(missing)}. "
                    f"Call record_dimension_score for each missing dimension, then call compute_verdict again."
                ),
            }
        )

    # Delegate to the core logic
    return evaluate_recommendation(
        knockout_results=json.dumps(knockouts),
        dimension_scores=json.dumps(dimensions),
        counter_signals=json.dumps(signals),
        risk_level=risk_level,
        evidence_quality=json.dumps(eq) if eq else "{}",
    )


# ---------------------------------------------------------------------------
# Legacy function (no @tool decorator — called directly by tests and
# compute_verdict).  Signature and body unchanged for backward compat.
# ---------------------------------------------------------------------------


def evaluate_recommendation(
    knockout_results: str,
    dimension_scores: str,
    counter_signals: str = "[]",
    risk_level: str = "",
    evidence_quality: str = "{}",
) -> str:
    """Evaluate the Go/No-Go recommendation using Stage-Gate scorecard rules.

    Call this tool after you have evaluated all knockout criteria and scored
    all dimensions. The tool applies consistent business rules and returns
    the verdict plus composite score.

    Args:
        knockout_results: JSON array of knockout results.
            Each item: {"criterion": "...", "result": "PASS" or "FAIL", "evidence": "..."}
        dimension_scores: JSON array of dimension scores.
            Each item: {"dimension": "...", "score": 1-5, "evidence": "..."}
        counter_signals: JSON array of counter-signals collected from upstream.
            Each item: {"signal": "...", "source": "...", "affected_dimensions": [...],
            "evidence_cited": "...", "why_score_holds": "...", "what_would_change_score": "..."}
            Optional -- omit or pass "[]" for backward compatibility.
        risk_level: Overall risk level from upstream risk assessment ("HIGH", "MEDIUM", "LOW").
            If "HIGH" and verdict would be GO, caps to PIVOT unless counter-signals are well-reconciled.
            Optional -- omit or pass "" for backward compatibility.
        evidence_quality: JSON object with evidence quality metrics for confidence computation.
            Keys: external_supported, external_total, contradicted_critical, risk_level.
            Optional -- omit or pass "{}" to skip confidence hint.

    Returns:
        JSON string with verdict, recommendation, composite_score, warnings, adjusted,
        floor_capped, floor_violations, risk_capped, and confidence_hint.

    Decision Rules:
        NO-GO: Any knockout FAIL, OR composite score <= 2.0
        PIVOT: Composite score 2.1-3.5 (CONDITIONAL GO -- maps to PIVOT for downstream compat)
        GO: Composite score > 3.5 and all knockouts PASS
        Consistency: If 2+ counter-signal inconsistencies found, apply -0.5 penalty to composite
        Risk Veto: HIGH risk caps GO -> PIVOT unless >= 2 counter-signals are well-reconciled
    """
    # Parse inputs
    knockouts = json.loads(knockout_results)
    dimensions = json.loads(dimension_scores)
    signals = json.loads(counter_signals)
    eq = json.loads(evidence_quality) if evidence_quality else {}

    # Check knockouts -- any FAIL is an immediate NO-GO
    has_knockout_fail = any(k.get("result", "").upper() == "FAIL" for k in knockouts)

    if has_knockout_fail:
        return json.dumps(
            {
                "verdict": "NO-GO",
                "recommendation": "NO-GO",
                "composite_score": 0.0,
                "reason": "Knockout criterion failed",
                "warnings": [],
                "adjusted": False,
            }
        )

    # Compute composite score
    scores = [d["score"] for d in dimensions]
    if not scores:
        return json.dumps(
            {
                "verdict": "NO-GO",
                "recommendation": "NO-GO",
                "composite_score": 0.0,
                "reason": "No dimension scores provided",
                "warnings": [],
                "adjusted": False,
            }
        )

    composite = sum(scores) / len(scores)

    # Floor rule: if any dimension scores at or below the floor, cap composite
    floor_violations = [d["dimension"] for d in dimensions if d["score"] <= _DIMENSION_FLOOR_SCORE]
    floor_capped = False
    if floor_violations and composite > _FLOOR_CAPPED_COMPOSITE:
        composite = _FLOOR_CAPPED_COMPOSITE
        floor_capped = True

    # Counter-signal consistency check
    warnings = _check_counter_signal_consistency(signals, dimensions)

    # Warn if too few counter-signals for the data quality
    if len(signals) < 2:
        warnings.append(
            f"Only {len(signals)} counter-signal(s) recorded. Review upstream for unsupported "
            "claims, HIGH risks, and unsubstantiated support patterns."
        )

    adjusted = False
    if len(warnings) >= _INCONSISTENCY_TRIGGER:
        composite = max(0.0, composite - _INCONSISTENCY_PENALTY)
        adjusted = True

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

    # Risk level veto: HIGH risk caps GO -> PIVOT unless well-reconciled
    risk_capped = False
    if (
        risk_level.upper() == "HIGH"
        and recommendation == "GO"
        and _count_well_reconciled_signals(signals) < _MIN_RECONCILED_FOR_HIGH_RISK_GO
    ):
        verdict = "CONDITIONAL GO"
        recommendation = "PIVOT"
        risk_capped = True

    # Compute confidence hint from evidence quality
    confidence_hint = _compute_confidence_hint(eq)

    return json.dumps(
        {
            "verdict": verdict,
            "recommendation": recommendation,
            "composite_score": round(composite, 1),
            "warnings": warnings,
            "adjusted": adjusted,
            "floor_capped": floor_capped,
            "floor_violations": floor_violations,
            "risk_capped": risk_capped,
            "confidence_hint": confidence_hint,
        }
    )
