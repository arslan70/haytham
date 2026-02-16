"""Ambiguity detection for story interpretation.

Identifies ambiguous requirements in user stories that may need
clarification before implementation can proceed.

Reference: ADR-001d: Story Interpretation Engine - Stage 2
"""

import re
from dataclasses import dataclass, field

from haytham.project.state_models import Ambiguity, Story


@dataclass
class DetectedAmbiguity:
    """An ambiguity detected during story analysis."""

    category: str  # scope, target, mechanism, permission, lifecycle, edge_case, constraint, ui_ux
    location: str  # Where in the story this was detected
    text: str  # The ambiguous text
    question: str  # Question to ask for clarification
    options: list[str] = field(default_factory=list)
    default: str | None = None
    default_rationale: str = ""

    def to_ambiguity(self, classification: str = "decision_required") -> Ambiguity:
        """Convert to Ambiguity model for storage."""
        return Ambiguity(
            question=self.question,
            classification=classification,
            options=self.options,
            default=self.default,
            resolved=False,
        )


# ========== Detection Rules ==========

# Keywords that trigger specific ambiguity checks
AMBIGUITY_PATTERNS = {
    "scope": {
        "triggers": ["all", "any", "my", "content", "items", "data"],
        "question_template": "Does '{noun}' include all {noun} or a specific subset?",
    },
    "mechanism": {
        "triggers": ["share", "send", "export", "publish", "notify", "search"],
        "question_template": "How should '{action}' work?",
    },
    "permission": {
        "triggers": ["share", "access", "view", "edit", "collaborate"],
        "question_template": "What permissions should {recipient} have?",
    },
    "lifecycle": {
        "triggers": ["share", "grant", "allow", "enable", "create"],
        "question_template": "Is this action permanent or can it be undone?",
    },
    "validation": {
        "triggers": ["enter", "input", "provide", "submit", "create"],
        "question_template": "What validation rules should apply to {field}?",
    },
}

# Specific ambiguity detection rules
DETECTION_RULES = [
    {
        "id": "SEARCH_SCOPE",
        "pattern": r"search\s+(?:my\s+)?(\w+)",
        "category": "scope",
        "question": "What fields should the search include?",
        "options": ["Title only", "Title and content", "Full-text search"],
        "default": "Title and content",
        "rationale": "Title and content covers most use cases without complexity",
    },
    {
        "id": "SEARCH_UI",
        "pattern": r"search\s+",
        "category": "ui_ux",
        "question": "Should search be instant (as-you-type) or require a submit button?",
        "options": ["Instant search (as-you-type)", "Submit button required"],
        "default": "Instant search (as-you-type)",
        "rationale": "Instant search is modern UX expectation",
        "auto_resolvable": True,
    },
    {
        "id": "DELETE_CONFIRMATION",
        "pattern": r"delete\s+(?:a\s+)?(\w+)",
        "category": "ui_ux",
        "question": "Should deletion require confirmation?",
        "options": ["Yes, show confirmation dialog", "No, delete immediately"],
        "default": "Yes, show confirmation dialog",
        "rationale": "Confirmation prevents accidental deletion",
        "auto_resolvable": True,
    },
    {
        "id": "DELETE_PERMANENCE",
        "pattern": r"delete\s+",
        "category": "lifecycle",
        "question": "Should deleted items be permanently removed or soft-deleted (recoverable)?",
        "options": ["Permanent deletion", "Soft delete (recoverable)"],
        "default": "Permanent deletion",
        "rationale": "Simpler for MVP; soft delete adds complexity",
        "auto_resolvable": True,
    },
    {
        "id": "LIST_ORDERING",
        "pattern": r"(?:list|view|see|show)\s+(?:all\s+)?(?:my\s+)?(\w+)",
        "category": "ui_ux",
        "question": "How should the list be sorted?",
        "options": ["Newest first", "Oldest first", "Alphabetical", "Custom order"],
        "default": "Newest first",
        "rationale": "Most recent items are typically most relevant",
        "auto_resolvable": True,
    },
    {
        "id": "LIST_PAGINATION",
        "pattern": r"(?:list|view|see|show)\s+(?:all\s+)?",
        "category": "constraint",
        "question": "Should the list be paginated or show all items?",
        "options": ["Paginated (20 items per page)", "Show all items", "Infinite scroll"],
        "default": "Show all items",
        "rationale": "For MVP with limited data, show all is simpler",
        "auto_resolvable": True,
    },
    {
        "id": "CONTENT_LENGTH",
        "pattern": r"(?:create|add|write|enter)\s+(?:a\s+)?(\w+)",
        "category": "validation",
        "question": "What is the maximum length for content?",
        "options": ["1,000 characters", "10,000 characters", "No limit"],
        "default": "10,000 characters",
        "rationale": "Reasonable limit for simple notes",
        "auto_resolvable": True,
    },
    {
        "id": "TITLE_REQUIRED",
        "pattern": r"title",
        "category": "validation",
        "question": "Is a title required?",
        "options": ["Yes, required", "No, optional"],
        "default": "Yes, required",
        "rationale": "Titles help identify items in lists",
        "auto_resolvable": True,
    },
]


class AmbiguityDetector:
    """Detects ambiguities in user stories.

    Analyzes story text and acceptance criteria to identify
    points that need clarification.

    Reference: ADR-001d: Ambiguity Detection
    """

    def __init__(self, custom_rules: list | None = None):
        """Initialize with optional custom detection rules.

        Args:
            custom_rules: Additional detection rules to use
        """
        self.rules = DETECTION_RULES.copy()
        if custom_rules:
            self.rules.extend(custom_rules)

    def detect(self, story: Story) -> list[DetectedAmbiguity]:
        """Detect ambiguities in a story.

        Args:
            story: Story to analyze

        Returns:
            List of detected ambiguities
        """
        ambiguities = []

        # Combine story text for analysis
        full_text = self._get_full_text(story)

        # Apply each detection rule
        seen_rules = set()  # Avoid duplicate detections
        for rule in self.rules:
            if rule["id"] in seen_rules:
                continue

            if re.search(rule["pattern"], full_text, re.IGNORECASE):
                ambiguity = DetectedAmbiguity(
                    category=rule["category"],
                    location=f"story:{story.id}",
                    text=self._extract_match_context(full_text, rule["pattern"]),
                    question=rule["question"],
                    options=rule["options"],
                    default=rule.get("default"),
                    default_rationale=rule.get("rationale", ""),
                )
                ambiguities.append(ambiguity)
                seen_rules.add(rule["id"])

        return ambiguities

    def classify(
        self, ambiguities: list[DetectedAmbiguity]
    ) -> tuple[list[DetectedAmbiguity], list[DetectedAmbiguity]]:
        """Classify ambiguities as auto-resolvable or decision-required.

        Args:
            ambiguities: List of detected ambiguities

        Returns:
            Tuple of (auto_resolvable, decision_required) ambiguities
        """
        auto_resolvable = []
        decision_required = []

        for amb in ambiguities:
            # Find matching rule
            rule = self._find_rule_for_ambiguity(amb)

            if rule and rule.get("auto_resolvable", False):
                auto_resolvable.append(amb)
            else:
                decision_required.append(amb)

        return auto_resolvable, decision_required

    def _get_full_text(self, story: Story) -> str:
        """Get combined text from story for analysis."""
        parts = [
            story.title,
            story.user_story,
            *story.acceptance_criteria,
        ]
        return " ".join(parts)

    def _extract_match_context(self, text: str, pattern: str) -> str:
        """Extract the matching context from text."""
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 20)
            return text[start:end].strip()
        return ""

    def _find_rule_for_ambiguity(self, amb: DetectedAmbiguity) -> dict | None:
        """Find the detection rule that matches an ambiguity."""
        for rule in self.rules:
            if rule["question"] == amb.question:
                return rule
        return None


def detect_story_ambiguities(story: Story) -> list[Ambiguity]:
    """Convenience function to detect and convert ambiguities.

    Args:
        story: Story to analyze

    Returns:
        List of Ambiguity objects ready for storage
    """
    detector = AmbiguityDetector()
    detected = detector.detect(story)
    auto, required = detector.classify(detected)

    result = []

    # Auto-resolved ambiguities
    for amb in auto:
        ambiguity = amb.to_ambiguity("auto_resolvable")
        # Auto-resolve with default
        if amb.default:
            ambiguity.resolved = True
            ambiguity.resolution = amb.default
        result.append(ambiguity)

    # Decision-required ambiguities
    for amb in required:
        result.append(amb.to_ambiguity("decision_required"))

    return result
