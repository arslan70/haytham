"""Tests for story generation quality.

These tests validate that generated stories follow our principles:
1. Specifications, not implementations (no code blocks with full implementations)
2. Gherkin format for behavioral stories (Layers 1-5)
3. Checklists + verification commands for setup stories (Layer 0)
4. All dependencies listed in Layer 0
5. File paths specified for each story
6. No hardcoded versions (use "latest")
7. Capability traceability (implements field populated)

Run with: pytest tests/test_story_quality.py -v
"""

import re
from typing import NamedTuple

import pytest


class StoryValidationResult(NamedTuple):
    """Result of validating a story."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]


class StoryValidator:
    """Validates stories against our quality principles."""

    # Patterns that indicate implementation code (bad)
    IMPLEMENTATION_PATTERNS = [
        (r"export\s+(default\s+)?function\s+\w+", "Contains exported function implementation"),
        (r"export\s+(default\s+)?class\s+\w+", "Contains exported class implementation"),
        (r"const\s+\w+\s*=\s*\([^)]*\)\s*=>", "Contains arrow function implementation"),
        (r'import\s+.*from\s+[\'"]', "Contains import statements (implementation detail)"),
        (r"@tailwind\s+(base|components|utilities)", "Contains Tailwind CSS directives"),
        (r"CREATE\s+TABLE", "Contains SQL CREATE TABLE (should be data model description)"),
        (r"INSERT\s+INTO", "Contains SQL INSERT (should be seed data description)"),
        (r"module\.exports\s*=", "Contains CommonJS export"),
        (r"<\w+\s+className=", "Contains JSX with className (implementation)"),
    ]

    # Patterns that indicate specification (good)
    SPECIFICATION_PATTERNS = [
        r"## Files to Create",
        r"## Acceptance Criteria",
        r"## Data Model",
        r"## Verification Commands",
    ]

    # Gherkin keywords
    GHERKIN_KEYWORDS = ["Given", "When", "Then", "And", "Scenario:"]

    def validate_story(self, story: dict, layer: int | None = None) -> StoryValidationResult:
        """Validate a single story against quality principles."""
        errors = []
        warnings = []

        content = story.get("content", "")
        story_id = story.get("id", "UNKNOWN")
        story_layer = layer if layer is not None else story.get("layer", 0)

        # Check 1: No implementation code
        impl_errors = self._check_no_implementation_code(content, story_id)
        errors.extend(impl_errors)

        # Check 2: Has file paths
        if (
            "## Files to Create" not in content
            and "/app/" not in content
            and "/lib/" not in content
        ):
            warnings.append(f"{story_id}: Missing file paths specification")

        # Check 3: Has acceptance criteria
        if "## Acceptance Criteria" not in content and "Scenario:" not in content:
            errors.append(f"{story_id}: Missing acceptance criteria")

        # Check 4: Layer-specific format
        if story_layer == 0:
            layer_errors = self._check_layer0_format(content, story_id)
            errors.extend(layer_errors)
        else:
            layer_warnings = self._check_behavioral_format(content, story_id)
            warnings.extend(layer_warnings)

        # Check 5: No hardcoded versions
        version_errors = self._check_no_hardcoded_versions(content, story_id)
        warnings.extend(version_errors)

        # Check 6: Has implements field
        if not story.get("implements"):
            warnings.append(f"{story_id}: Missing implements field (no capability traceability)")

        return StoryValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def _check_no_implementation_code(self, content: str, story_id: str) -> list[str]:
        """Check that story doesn't contain implementation code."""
        errors = []

        # Extract code blocks
        code_blocks = re.findall(r"```(\w+)?\n(.*?)```", content, re.DOTALL)

        for _lang, code in code_blocks:
            # Skip small code blocks (likely examples or file paths)
            if len(code.strip().split("\n")) <= 3:
                continue

            # Check for implementation patterns
            for pattern, message in self.IMPLEMENTATION_PATTERNS:
                if re.search(pattern, code, re.IGNORECASE):
                    errors.append(f"{story_id}: {message}")
                    break  # One error per code block is enough

        return errors

    def _check_layer0_format(self, content: str, story_id: str) -> list[str]:
        """Check Layer 0 stories have checklists and verification commands."""
        errors = []

        # Should have checklist format
        has_checklist = bool(re.search(r"- \[ \]", content))
        if not has_checklist:
            errors.append(f"{story_id}: Layer 0 story missing checklist format")

        # Should have verification commands
        has_verification = "## Verification Commands" in content or "```bash" in content
        if not has_verification:
            errors.append(f"{story_id}: Layer 0 story missing verification commands")

        return errors

    def _check_behavioral_format(self, content: str, story_id: str) -> list[str]:
        """Check behavioral stories (Layer 1-5) use Gherkin format."""
        warnings = []

        # Check for Gherkin keywords
        has_gherkin = any(kw in content for kw in self.GHERKIN_KEYWORDS)

        if not has_gherkin:
            warnings.append(
                f"{story_id}: Behavioral story should use Gherkin format (Given/When/Then)"
            )

        return warnings

    def _check_no_hardcoded_versions(self, content: str, story_id: str) -> list[str]:
        """Check for hardcoded version numbers."""
        warnings = []

        # Pattern for version numbers like "14.0.4", "^5.0.0", "~3.3.0"
        version_pattern = r'["\'][\^~]?\d+\.\d+\.\d+["\']'

        if re.search(version_pattern, content):
            warnings.append(f'{story_id}: Contains hardcoded version numbers (should use "latest")')

        return warnings

    def validate_story_set(self, stories: list[dict]) -> StoryValidationResult:
        """Validate a complete set of stories."""
        all_errors = []
        all_warnings = []

        for story in stories:
            result = self.validate_story(story)
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)

        # Cross-story validations
        cross_errors = self._check_cross_story_consistency(stories)
        all_errors.extend(cross_errors)

        return StoryValidationResult(
            is_valid=len(all_errors) == 0, errors=all_errors, warnings=all_warnings
        )

    def _check_cross_story_consistency(self, stories: list[dict]) -> list[str]:
        """Check consistency across stories."""
        errors = []

        # Collect all file paths created
        files_created = set()
        files_referenced = set()

        for story in stories:
            content = story.get("content", "")

            # Extract files to create
            create_section = re.search(r"## Files to Create\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
            if create_section:
                paths = re.findall(r"`(/[^`]+)`", create_section.group(1))
                files_created.update(paths)

            # Extract file references (imports, etc.)
            imports = re.findall(r'from\s+[\'"](@/[^"\']+)[\'"]', content)
            for imp in imports:
                # Convert @/ to /
                path = imp.replace("@/", "/")
                files_referenced.add(path)

        # Check for referenced but not created files
        missing = files_referenced - files_created
        for path in missing:
            errors.append(f"File referenced but not created: {path}")

        return errors


# =============================================================================
# FIXTURES - Example stories for testing
# =============================================================================

GOOD_LAYER0_STORY = {
    "id": "STORY-001",
    "title": "Initialize Project",
    "layer": 0,
    "implements": ["DEC-STACK-001"],
    "depends_on": [],
    "content": """## Description
Set up Next.js project with TypeScript and Supabase.

## Files to Create
- `/package.json` - Project dependencies
- `/tsconfig.json` - TypeScript configuration
- `/.env.example` - Environment variables template

## Acceptance Criteria
- [ ] package.json includes: next, react, @supabase/supabase-js (all "latest")
- [ ] TypeScript strict mode enabled
- [ ] Environment variables documented

## Verification Commands
```bash
npm install    # exits 0
npm run build  # exits 0
```
""",
}

GOOD_BEHAVIORAL_STORY = {
    "id": "STORY-006",
    "title": "User Registration",
    "layer": 1,
    "implements": ["CAP-F-001"],
    "depends_on": ["STORY-001"],
    "content": """## Description
Implement user registration with email/password.

## Files to Create
- `/app/register/page.tsx` - Registration page component

## Acceptance Criteria

```gherkin
Scenario: Successful registration
  Given I am on the registration page
  When I submit valid email "test@example.com" and password "password123"
  Then I should be redirected to dashboard
  And my account should be created in the database

Scenario: Registration with invalid email
  Given I am on the registration page
  When I submit invalid email "not-an-email"
  Then I should see error "Invalid email format"
  And no account should be created

Scenario: Registration with short password
  Given I am on the registration page
  When I submit password shorter than 6 characters
  Then I should see error "Password must be at least 6 characters"
```
""",
}

BAD_STORY_WITH_CODE = {
    "id": "STORY-002",
    "title": "Registration Page",
    "layer": 1,
    "implements": ["CAP-F-001"],
    "depends_on": ["STORY-001"],
    "content": """## Description
Create registration page.

## Files to Create
- `/app/register/page.tsx`

## Code
```typescript
import { createClient } from '@supabase/supabase-js'
import { redirect } from 'next/navigation'

export default function RegisterPage() {
  const handleSubmit = async (formData: FormData) => {
    'use server'
    const email = formData.get('email')
    const password = formData.get('password')
    // ... full implementation
  }

  return (
    <form className="max-w-md mx-auto">
      <input type="email" name="email" />
      <input type="password" name="password" />
      <button type="submit">Register</button>
    </form>
  )
}
```

## Acceptance Criteria
- [ ] User can register
""",
}

BAD_STORY_NO_ACCEPTANCE_CRITERIA = {
    "id": "STORY-003",
    "title": "Login Page",
    "layer": 1,
    "implements": [],
    "depends_on": ["STORY-001"],
    "content": """## Description
Create login page.

## Files to Create
- `/app/login/page.tsx`
""",
}

BAD_LAYER0_NO_VERIFICATION = {
    "id": "STORY-001",
    "title": "Initialize Project",
    "layer": 0,
    "implements": ["DEC-STACK-001"],
    "depends_on": [],
    "content": """## Description
Set up project.

## Files to Create
- `/package.json`

## Acceptance Criteria
- [ ] Project builds successfully
""",
}


# =============================================================================
# TESTS
# =============================================================================


class TestStoryValidator:
    """Tests for StoryValidator."""

    @pytest.fixture
    def validator(self):
        return StoryValidator()

    def test_good_layer0_story_passes(self, validator):
        """Good Layer 0 story with checklist and verification commands passes."""
        result = validator.validate_story(GOOD_LAYER0_STORY)

        assert result.is_valid, f"Expected valid, got errors: {result.errors}"
        assert len(result.errors) == 0

    def test_good_behavioral_story_passes(self, validator):
        """Good behavioral story with Gherkin passes."""
        result = validator.validate_story(GOOD_BEHAVIORAL_STORY)

        assert result.is_valid, f"Expected valid, got errors: {result.errors}"
        assert len(result.errors) == 0

    def test_story_with_implementation_code_fails(self, validator):
        """Story containing implementation code fails validation."""
        result = validator.validate_story(BAD_STORY_WITH_CODE)

        assert not result.is_valid
        assert any(
            "import statements" in e.lower() or "jsx" in e.lower() or "function" in e.lower()
            for e in result.errors
        )

    def test_story_without_acceptance_criteria_fails(self, validator):
        """Story without acceptance criteria fails validation."""
        result = validator.validate_story(BAD_STORY_NO_ACCEPTANCE_CRITERIA)

        assert not result.is_valid
        assert any("acceptance criteria" in e.lower() for e in result.errors)

    def test_layer0_without_verification_commands_fails(self, validator):
        """Layer 0 story without verification commands fails."""
        result = validator.validate_story(BAD_LAYER0_NO_VERIFICATION)

        assert not result.is_valid
        assert any("verification commands" in e.lower() for e in result.errors)

    def test_behavioral_story_without_gherkin_warns(self, validator):
        """Behavioral story without Gherkin format produces warning."""
        story = {
            "id": "STORY-005",
            "layer": 2,
            "implements": ["CAP-F-002"],
            "content": """## Description
Some feature.

## Files to Create
- `/app/feature/page.tsx`

## Acceptance Criteria
- [ ] Feature works
- [ ] Errors handled
""",
        }

        result = validator.validate_story(story)

        # Should have warning about Gherkin, but may still be valid
        assert any("gherkin" in w.lower() for w in result.warnings)

    def test_hardcoded_versions_warn(self, validator):
        """Hardcoded version numbers produce warnings."""
        story = {
            "id": "STORY-001",
            "layer": 0,
            "implements": ["DEC-STACK-001"],
            "content": """## Description
Set up project.

## Files to Create
- `/package.json`

## Acceptance Criteria
- [ ] package.json includes next "14.0.4", react "^18.2.0"

## Verification Commands
```bash
npm install
```
""",
        }

        result = validator.validate_story(story)

        assert any("hardcoded version" in w.lower() for w in result.warnings)

    def test_missing_implements_warns(self, validator):
        """Story without implements field produces warning."""
        story = {
            "id": "STORY-007",
            "layer": 1,
            "implements": [],  # Empty
            "content": """## Description
Some feature.

## Files to Create
- `/app/feature/page.tsx`

## Acceptance Criteria
```gherkin
Scenario: Feature works
  Given I am on the page
  When I do something
  Then it works
```
""",
        }

        result = validator.validate_story(story)

        assert any(
            "implements" in w.lower() or "traceability" in w.lower() for w in result.warnings
        )


class TestStorySetValidation:
    """Tests for validating story sets."""

    @pytest.fixture
    def validator(self):
        return StoryValidator()

    def test_good_story_set_passes(self, validator):
        """A well-formed story set passes validation."""
        stories = [GOOD_LAYER0_STORY, GOOD_BEHAVIORAL_STORY]

        result = validator.validate_story_set(stories)

        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_story_set_with_bad_story_fails(self, validator):
        """Story set containing a bad story fails."""
        stories = [GOOD_LAYER0_STORY, BAD_STORY_WITH_CODE]

        result = validator.validate_story_set(stories)

        assert not result.is_valid


# =============================================================================
# INTEGRATION TEST (expensive - run sparingly)
# =============================================================================


@pytest.mark.integration
@pytest.mark.skip(
    reason="Expensive integration test - run manually with pytest -m integration --no-skip"
)
class TestStoryGenerationIntegration:
    """Integration tests that actually run story generation.

    These are expensive (API calls) and slow. Run sparingly.
    """

    def test_generated_stories_pass_validation(self):
        """Stories generated by the agent pass validation."""
        from haytham.agents.worker_story_generator.story_swarm import (
            parse_stories_from_markdown,
            run_story_swarm,
        )

        # Minimal inputs for testing
        mvp_scope = "A simple todo app with user authentication"
        capability_model = "CAP-F-001: Create todos\nCAP-F-002: List todos"
        architecture_decisions = "DEC-STACK-001: Next.js with Supabase"
        build_buy_analysis = "BUY: Supabase for auth and database"

        # Generate stories
        stories_md = run_story_swarm(
            mvp_scope=mvp_scope,
            capability_model=capability_model,
            architecture_decisions=architecture_decisions,
            build_buy_analysis=build_buy_analysis,
            system_goal="Todo app",
        )

        # Parse and validate
        stories = parse_stories_from_markdown(stories_md)
        validator = StoryValidator()
        result = validator.validate_story_set(stories)

        # Print details for debugging
        if not result.is_valid:
            print("\n=== VALIDATION ERRORS ===")
            for error in result.errors:
                print(f"  - {error}")

        if result.warnings:
            print("\n=== VALIDATION WARNINGS ===")
            for warning in result.warnings:
                print(f"  - {warning}")

        assert result.is_valid, f"Generated stories failed validation: {result.errors}"
