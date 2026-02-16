"""Story coherence validation (ADR-022 Part 4).

Provides programmatic validators for:
1. Framework conflict detection - detects multiple frameworks for same component

These are genuinely mechanical checks that work reliably on story output
without requiring LLM calls.

Note: Story count validation was removed as static limits don't account for
varying complexity across different startup ideas.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FrameworkConflict:
    """Conflict when multiple frameworks are used for the same component type."""

    component_type: str  # e.g., "frontend", "backend", "database"
    frameworks_detected: list[str]
    story_ids: list[str]  # Stories that reference these frameworks
    description: str


@dataclass
class StoryCoherenceReport:
    """Full coherence report for story generation output."""

    story_count: int
    max_layer: int
    framework_conflicts: list[FrameworkConflict] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if stories pass coherence validation."""
        # Frontend framework conflicts are blocking
        if any(c.component_type == "frontend" for c in self.framework_conflicts):
            return False
        return True

    @property
    def warnings(self) -> list[str]:
        """Get non-blocking warnings."""
        warnings = []
        for conflict in self.framework_conflicts:
            if conflict.component_type != "frontend":
                warnings.append(conflict.description)
        return warnings

    @property
    def errors(self) -> list[str]:
        """Get blocking errors."""
        errors = []
        for conflict in self.framework_conflicts:
            if conflict.component_type == "frontend":
                errors.append(f"BLOCKING: {conflict.description}")
        return errors

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "story_count": self.story_count,
            "max_layer": self.max_layer,
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "framework_conflicts": [
                {
                    "component_type": c.component_type,
                    "frameworks": c.frameworks_detected,
                    "story_ids": c.story_ids,
                }
                for c in self.framework_conflicts
            ],
        }


# =============================================================================
# Story Metrics Detection (informational only, no limits enforced)
# =============================================================================

# Patterns to detect story identifiers
STORY_ID_PATTERN = re.compile(r"STORY-\d{3}", re.IGNORECASE)


def count_stories(content: str) -> int:
    """Count stories in generation output (informational only).

    Args:
        content: Story generation output (markdown or JSON)

    Returns:
        Number of stories detected
    """
    story_ids = set(STORY_ID_PATTERN.findall(content))
    return len(story_ids)


def detect_max_layer(content: str) -> int:
    """Detect the highest layer number in story output (informational only).

    Args:
        content: Story generation output

    Returns:
        Maximum layer number found (0 if none detected)
    """
    layer_pattern = re.compile(r'"?layer"?\s*[=:]\s*(\d+)', re.IGNORECASE)
    matches = layer_pattern.findall(content)

    if matches:
        return max(int(m) for m in matches)
    return 0


# =============================================================================
# Framework Conflict Detection
# =============================================================================

# Known frameworks by category
FRONTEND_FRAMEWORKS = {
    "react": "React",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "vue": "Vue",
    "nuxt": "Nuxt",
    "angular": "Angular",
    "svelte": "Svelte",
    "sveltekit": "SvelteKit",
    "astro": "Astro",
    "remix": "Remix",
    "solid": "SolidJS",
    "qwik": "Qwik",
}

BACKEND_FRAMEWORKS = {
    "express": "Express",
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "rails": "Rails",
    "spring": "Spring",
    "nest": "NestJS",
    "hono": "Hono",
    "elysia": "Elysia",
}

CSS_FRAMEWORKS = {
    "tailwind": "Tailwind CSS",
    "bootstrap": "Bootstrap",
    "material-ui": "Material UI",
    "mui": "Material UI",
    "chakra": "Chakra UI",
    "shadcn": "shadcn/ui",
    "styled-components": "styled-components",
    "emotion": "Emotion",
}


def detect_frameworks(content: str) -> dict[str, set[str]]:
    """Detect frameworks mentioned in content.

    Args:
        content: Story generation output

    Returns:
        Dict mapping component type to set of detected frameworks
    """
    content_lower = content.lower()
    detected: dict[str, set[str]] = {
        "frontend": set(),
        "backend": set(),
        "css": set(),
    }

    for key, name in FRONTEND_FRAMEWORKS.items():
        if key in content_lower:
            detected["frontend"].add(name)

    for key, name in BACKEND_FRAMEWORKS.items():
        if key in content_lower:
            detected["backend"].add(name)

    for key, name in CSS_FRAMEWORKS.items():
        if key in content_lower:
            detected["css"].add(name)

    return detected


def detect_framework_conflicts(content: str) -> list[FrameworkConflict]:
    """Detect framework conflicts in story output.

    A conflict occurs when multiple frameworks of the same category
    are detected for what should be a single component. Exceptions:
    - Astro + React is OK (Astro can use React components)
    - Next.js counts as both framework and React (not a conflict)

    Args:
        content: Story generation output

    Returns:
        List of detected conflicts
    """
    detected = detect_frameworks(content)
    conflicts = []

    # Check frontend framework conflicts
    frontend = detected["frontend"]
    if len(frontend) > 1:
        # Filter known compatible combinations
        compatible = False

        # Astro + React/Vue/Svelte is OK (Astro islands)
        if "Astro" in frontend and len(frontend) == 2:
            other = (frontend - {"Astro"}).pop()
            if other in ("React", "Vue", "Svelte", "SolidJS"):
                compatible = True

        # Next.js/Remix IS React - not a conflict
        if frontend == {"Next.js", "React"} or frontend == {"Remix", "React"}:
            compatible = True

        # Nuxt IS Vue - not a conflict
        if frontend == {"Nuxt", "Vue"}:
            compatible = True

        # SvelteKit IS Svelte - not a conflict
        if frontend == {"SvelteKit", "Svelte"}:
            compatible = True

        if not compatible:
            conflicts.append(
                FrameworkConflict(
                    component_type="frontend",
                    frameworks_detected=sorted(frontend),
                    story_ids=[],  # Would need parsing to identify specific stories
                    description=(
                        f"Multiple frontend frameworks detected: {', '.join(sorted(frontend))}. "
                        "An MVP should use a single frontend framework for consistency."
                    ),
                )
            )

    # Backend conflicts are warnings, not blocking (microservices might use multiple)
    backend = detected["backend"]
    if len(backend) > 1:
        conflicts.append(
            FrameworkConflict(
                component_type="backend",
                frameworks_detected=sorted(backend),
                story_ids=[],
                description=(
                    f"Multiple backend frameworks detected: {', '.join(sorted(backend))}. "
                    "Consider if this complexity is needed for an MVP."
                ),
            )
        )

    return conflicts


# =============================================================================
# Main Validation Entry Point
# =============================================================================


def validate_story_coherence(
    story_output: str,
    appetite_str: str | None = None,
) -> StoryCoherenceReport:
    """Validate story generation output for coherence.

    Performs mechanical checks that don't require LLM calls:
    1. Framework conflict detection - multiple frameworks for same component

    Note: Story count and layer limits are not enforced as they don't account
    for varying complexity across different startup ideas.

    Args:
        story_output: Story generation output (markdown or JSON)
        appetite_str: Appetite from MVP scope (unused, kept for API compatibility)

    Returns:
        StoryCoherenceReport with validation results
    """
    story_count = count_stories(story_output)
    max_layer = detect_max_layer(story_output)

    # Check framework conflicts (the only validation that matters)
    framework_conflicts = detect_framework_conflicts(story_output)

    return StoryCoherenceReport(
        story_count=story_count,
        max_layer=max_layer,
        framework_conflicts=framework_conflicts,
    )
