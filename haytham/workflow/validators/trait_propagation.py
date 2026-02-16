"""Trait propagation enforcement (ADR-022 Part 2b).

Extracts key constraints from system_traits into a structured constraints dict
that downstream post-processors can check against.

The constraints dict is stored in Burr state and includes:
- System traits from the system-traits stage
- Core invariants from the concept anchor
- Derived constraints (e.g., closed community -> invite-only auth)
"""

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from burr.core import State

logger = logging.getLogger(__name__)


@dataclass
class Constraints:
    """Extracted constraints from system traits and concept anchor.

    Used by downstream stages to validate consistency.
    """

    # From system traits
    realtime: bool | None = None
    offline: bool | None = None
    multi_tenant: bool | None = None
    authentication: bool | None = None

    # From concept anchor invariants
    community_model: str | None = None  # "closed", "open", "hybrid"
    group_structure: str | None = None  # e.g., "1:7", "flexible"

    # Derived constraints
    auth_model: str | None = None  # "invite_only", "public_signup", "social"

    # Raw traits for detailed checks
    raw_traits: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for state storage."""
        return {
            "realtime": self.realtime,
            "offline": self.offline,
            "multi_tenant": self.multi_tenant,
            "authentication": self.authentication,
            "community_model": self.community_model,
            "group_structure": self.group_structure,
            "auth_model": self.auth_model,
            "raw_traits": self.raw_traits,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Constraints":
        """Create from dictionary."""
        return cls(
            realtime=data.get("realtime"),
            offline=data.get("offline"),
            multi_tenant=data.get("multi_tenant"),
            authentication=data.get("authentication"),
            community_model=data.get("community_model"),
            group_structure=data.get("group_structure"),
            auth_model=data.get("auth_model"),
            raw_traits=data.get("raw_traits", {}),
        )


def extract_traits_from_output(output: str) -> dict[str, Any]:
    """Extract traits from system-traits stage output.

    Handles various output formats:
    - Markdown tables: | trait | value |
    - Key-value pairs: trait: value
    - JSON-like: "trait": value

    Args:
        output: System traits stage output

    Returns:
        Dict of trait name to value
    """
    traits = {}

    # Skip words that are likely table headers, not trait names
    header_words = {"trait", "name", "property", "key", "attribute", "field"}

    # Pattern 1: Markdown table rows
    table_pattern = r"\|\s*(\w+)\s*\|\s*([^|]+)\s*\|"
    for match in re.finditer(table_pattern, output):
        name = match.group(1).lower().strip()
        value = match.group(2).strip()
        # Skip header rows
        if name in header_words or value.lower() in ("value", "status", "setting"):
            continue
        traits[name] = _normalize_value(value)

    # Pattern 2: Key-value pairs (various formats)
    kv_patterns = [
        r"^\s*-?\s*\*?\*?(\w+)\*?\*?\s*:\s*(.+?)$",  # - **trait**: value or trait: value
        r'"(\w+)"\s*:\s*"?([^",\n}]+)"?',  # JSON-like
    ]

    for pattern in kv_patterns:
        for match in re.finditer(pattern, output, re.MULTILINE):
            name = match.group(1).lower().strip()
            value = match.group(2).strip()
            if name not in traits and name not in header_words:  # Don't override table values
                traits[name] = _normalize_value(value)

    return traits


def _normalize_value(value: str) -> bool | str:
    """Normalize a trait value."""
    value_lower = value.lower().strip()

    # Boolean values
    if value_lower in ("true", "yes", "required", "needed", "✓", "✅"):
        return True
    if value_lower in ("false", "no", "not required", "not needed", "✗", "❌", "n/a"):
        return False

    return value_lower


def extract_anchor_constraints(anchor_str: str) -> dict[str, str]:
    """Extract constraints from concept anchor string.

    Args:
        anchor_str: Formatted concept anchor string

    Returns:
        Dict of constraint name to value
    """
    constraints = {}

    # Look for community model in invariants
    if "closed" in anchor_str.lower():
        constraints["community_model"] = "closed"
    elif "open" in anchor_str.lower():
        constraints["community_model"] = "open"

    # Look for group structure
    group_pattern = r"(\d+:\d+)\s*(?:structure|ratio|group)"
    match = re.search(group_pattern, anchor_str, re.IGNORECASE)
    if match:
        constraints["group_structure"] = match.group(1)

    # Look for specific invariants
    if "invite" in anchor_str.lower():
        constraints["auth_model"] = "invite_only"

    return constraints


def derive_constraints(
    traits: dict[str, Any],
    anchor_constraints: dict[str, str],
) -> dict[str, Any]:
    """Derive additional constraints from traits and anchor.

    For example, if community_model is "closed", derive auth_model as "invite_only".

    Args:
        traits: Extracted system traits
        anchor_constraints: Constraints from concept anchor

    Returns:
        Dict of derived constraints
    """
    derived = {}

    # Derive auth model from community model
    community_model = anchor_constraints.get("community_model")
    if community_model == "closed" and "auth_model" not in anchor_constraints:
        derived["auth_model"] = "invite_only"

    # Derive realtime from traits if not explicitly set
    if "realtime" not in traits:
        # Check for realtime indicators in raw traits
        for key, value in traits.items():
            if "realtime" in key.lower() or "websocket" in key.lower():
                derived["realtime"] = value

    return derived


def extract_constraints(
    system_traits_output: str,
    anchor_str: str | None = None,
) -> Constraints:
    """Extract all constraints from system traits and anchor.

    Args:
        system_traits_output: Output from system-traits stage
        anchor_str: Optional concept anchor string

    Returns:
        Constraints object with all extracted values
    """
    # Extract from system traits
    traits = extract_traits_from_output(system_traits_output)

    # Extract from anchor
    anchor_constraints = {}
    if anchor_str:
        anchor_constraints = extract_anchor_constraints(anchor_str)

    # Derive additional constraints
    derived = derive_constraints(traits, anchor_constraints)

    # Build Constraints object
    return Constraints(
        realtime=traits.get("realtime") or derived.get("realtime"),
        offline=traits.get("offline"),
        multi_tenant=traits.get("multi_tenant") or traits.get("multitenant"),
        authentication=traits.get("authentication") or traits.get("auth"),
        community_model=anchor_constraints.get("community_model"),
        group_structure=anchor_constraints.get("group_structure"),
        auth_model=anchor_constraints.get("auth_model") or derived.get("auth_model"),
        raw_traits=traits,
    )


def constraints_post_processor(output: str, state: "State") -> dict[str, Any]:
    """Post-processor to extract constraints after system-traits stage.

    This function is called after system-traits completes to extract
    constraints into Burr state for downstream validation.

    Args:
        output: System traits stage output
        state: Current Burr state

    Returns:
        Dict with constraints to add to state
    """
    anchor_str = state.get("concept_anchor_str")
    constraints = extract_constraints(output, anchor_str)

    return {
        "constraints": constraints.to_dict(),
    }


def validate_against_constraints(
    output: str,
    constraints: dict[str, Any],
    stage_name: str,
) -> list[str]:
    """Validate stage output against extracted constraints.

    Args:
        output: Stage output to validate
        constraints: Constraints dict from state
        stage_name: Name of stage being validated

    Returns:
        List of warning messages
    """
    warnings = []
    output_lower = output.lower()

    # Check realtime constraint
    realtime = constraints.get("realtime")
    if realtime is False:
        realtime_keywords = ["realtime", "real-time", "websocket", "subscription", "live update"]
        for keyword in realtime_keywords:
            if keyword in output_lower:
                # Check if negated
                if not _is_negated(output_lower, keyword):
                    warnings.append(
                        f"Constraints indicate realtime=false, but {stage_name} "
                        f"mentions '{keyword}' without negation"
                    )
                    break

    # Check community model constraint
    community_model = constraints.get("community_model")
    if community_model == "closed":
        open_keywords = ["public signup", "open registration", "anyone can join"]
        for keyword in open_keywords:
            if keyword in output_lower:
                warnings.append(
                    f"Constraints indicate closed community, but {stage_name} mentions '{keyword}'"
                )
                break

    # Check auth model constraint
    auth_model = constraints.get("auth_model")
    if auth_model == "invite_only":
        public_auth_keywords = ["public signup", "self-registration", "open auth"]
        for keyword in public_auth_keywords:
            if keyword in output_lower:
                warnings.append(
                    f"Constraints indicate invite-only auth, but {stage_name} mentions '{keyword}'"
                )
                break

    return warnings


def _is_negated(text: str, keyword: str) -> bool:
    """Check if a keyword is negated in text."""
    negation_patterns = [
        f"no {keyword}",
        f"not {keyword}",
        f"without {keyword}",
        f"{keyword} is not",
        f"{keyword} isn't",
        f"don't need {keyword}",
        f"doesn't need {keyword}",
    ]
    return any(pattern in text for pattern in negation_patterns)


def create_constraints_validator() -> callable:
    """Create a post-validator that checks constraints.

    Returns:
        Validator function that takes (output, state) and returns warnings
    """

    def validator(output: str, state: "State") -> list[str]:
        constraints = state.get("constraints", {})
        if not constraints:
            return []

        return validate_against_constraints(
            output,
            constraints,
            "current stage",
        )

    return validator
