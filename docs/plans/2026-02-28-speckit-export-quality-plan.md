# Spec Kit Export Quality Fixes - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 6 quality issues found in spec-kit.zip export: broken summaries, duplicate scenarios, duplicate success criteria, nested code fences, duplicate API contract content, and non-measurable success criteria.

**Architecture:** Targeted fixes in existing files. No new modules. Upstream fix in `assembler.py` for summary extraction, shared utility in `spec_transforms.py` for fence stripping, remaining fixes in `speckit_exporter.py`.

**Tech Stack:** Python, Pydantic, pytest

---

### Task 1: Fix `_extract_summary()` to skip structural lines

**Files:**
- Modify: `haytham/workflow/contracts/assembler.py:81-93`
- Test: `tests/test_execution_contract.py` (class `TestSummaryExtraction`, after line 323)

**Step 1: Write the failing tests**

Add to `tests/test_execution_contract.py` in class `TestSummaryExtraction`:

```python
def test_skips_description_heading(self):
    content = "## Description\n\nThis story sets up the invite system."
    assert _extract_summary(content, "fallback") == "This story sets up the invite system."

def test_skips_code_fence_marker(self):
    content = "```markdown\n## Description\n\nActual content here.\n```"
    assert _extract_summary(content, "fallback") == "Actual content here."

def test_skips_multiple_structural_lines(self):
    content = "```markdown\n## Description\n\n## Files to Create\n\nReal summary line."
    assert _extract_summary(content, "fallback") == "Real summary line."

def test_falls_back_when_only_structural(self):
    content = "## Description\n\n## Files to Create\n"
    assert _extract_summary(content, "My Title") == "My Title"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_execution_contract.py::TestSummaryExtraction -v`
Expected: 4 FAIL (currently returns "Description" or "```markdown")

**Step 3: Write minimal implementation**

Replace `_extract_summary` in `haytham/workflow/contracts/assembler.py`:

```python
_STRUCTURAL_HEADINGS = frozenset({
    "description",
    "details",
    "overview",
    "files to create",
    "acceptance criteria",
    "configuration",
    "required permissions",
})


def _extract_summary(content: str, title: str) -> str:
    """Extract summary from story content.

    Takes the first non-empty, non-structural line, stripping markdown
    heading markers. Skips code fence delimiters and generic headings
    like "Description" or "Files to Create".
    Falls back to title if content is empty or only structural.
    """
    if not content or not content.strip():
        return title
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Skip code fence markers
        if stripped.startswith("```"):
            continue
        # Strip heading markers and check for structural headings
        heading_text = stripped.lstrip("#").strip()
        if heading_text.lower() in _STRUCTURAL_HEADINGS:
            continue
        return heading_text
    return title
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_execution_contract.py::TestSummaryExtraction -v`
Expected: ALL PASS (old tests + 4 new ones)

**Step 5: Commit**

```bash
git add haytham/workflow/contracts/assembler.py tests/test_execution_contract.py
git commit -m "fix: _extract_summary skips structural headings and code fences"
```

---

### Task 2: Add `strip_wrapping_fences()` to spec_transforms

**Files:**
- Modify: `haytham/exporters/spec_transforms.py` (add function at end of file)
- Test: `tests/test_spec_transforms.py` (add new test class at end)

**Step 1: Write the failing tests**

Add to `tests/test_spec_transforms.py`:

```python
from haytham.exporters.spec_transforms import strip_wrapping_fences


class TestStripWrappingFences:
    def test_strips_markdown_wrapper(self):
        content = "```markdown\n## Description\n\nActual content.\n```"
        assert strip_wrapping_fences(content) == "## Description\n\nActual content."

    def test_strips_gherkin_wrapper(self):
        content = "```gherkin\nScenario: Login\n  Given a user\n```"
        assert strip_wrapping_fences(content) == "Scenario: Login\n  Given a user"

    def test_strips_plain_wrapper(self):
        content = "```\nSome content\n```"
        assert strip_wrapping_fences(content) == "Some content"

    def test_preserves_internal_fences(self):
        content = "Some text\n```python\ncode\n```\nMore text"
        assert strip_wrapping_fences(content) == content

    def test_preserves_no_fences(self):
        content = "Just plain text\nwith multiple lines"
        assert strip_wrapping_fences(content) == content

    def test_preserves_empty(self):
        assert strip_wrapping_fences("") == ""

    def test_preserves_single_line(self):
        assert strip_wrapping_fences("one line") == "one line"

    def test_handles_whitespace_around_fences(self):
        content = "  ```markdown  \n## Content\n  ```  "
        assert strip_wrapping_fences(content) == "## Content"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_spec_transforms.py::TestStripWrappingFences -v`
Expected: ImportError (function doesn't exist yet)

**Step 3: Write minimal implementation**

Add to end of `haytham/exporters/spec_transforms.py`:

```python
def strip_wrapping_fences(content: str) -> str:
    """Strip an outer code fence wrapper if the content is entirely enclosed.

    Handles ``markdown``, ``gherkin``, and bare fence markers. Preserves
    content that contains internal fences but isn't fully wrapped.
    """
    if not content:
        return content
    lines = content.strip().splitlines()
    if len(lines) < 2:
        return content
    if lines[0].strip().startswith("```") and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1])
    return content
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_spec_transforms.py::TestStripWrappingFences -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add haytham/exporters/spec_transforms.py tests/test_spec_transforms.py
git commit -m "feat: add strip_wrapping_fences utility for content sanitization"
```

---

### Task 3: Deduplicate scenarios in `_render_spec()`

**Files:**
- Modify: `haytham/exporters/speckit_exporter.py:101-153` (`_render_spec` method)
- Test: `tests/test_speckit_exporter.py` (add to `TestSpec` class)

**Step 1: Write the failing test**

Add to `tests/test_speckit_exporter.py` in class `TestSpec`:

```python
def test_duplicate_scenarios_deduplicated(self):
    """Identical acceptance criteria across stories should appear only once."""
    duplicate_ac = AcceptanceCriterion(
        id="AC-001",
        scenario="Validation failure",
        given="invalid input is provided",
        when="the form is submitted",
        then="an error message is shown",
    )
    project = _make_project(
        stories=[
            ContractStory(
                id="STORY-010",
                title="Story A",
                layer=3,
                summary="First story",
                implements=["CAP-F-001"],
                acceptance_criteria=[duplicate_ac],
            ),
            ContractStory(
                id="STORY-011",
                title="Story B",
                layer=3,
                summary="Second story",
                implements=["CAP-F-001"],
                acceptance_criteria=[duplicate_ac],
            ),
        ],
        scope_items=[
            ExportableScopeItem(
                name="User Authentication",
                description="Auth stuff.",
                capabilities=["CAP-F-001"],
                stories=["STORY-010", "STORY-011"],
            ),
        ],
    )
    tree = SpecKitExporter().export_tree(project)
    spec = tree[".specify/specs/001-user-authentication/spec.md"]
    assert spec.count("**Scenario: Validation failure**") == 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_speckit_exporter.py::TestSpec::test_duplicate_scenarios_deduplicated -v`
Expected: FAIL (count is 2, expected 1)

**Step 3: Write minimal implementation**

Edit `_render_spec` in `haytham/exporters/speckit_exporter.py`. Add a `seen_scenarios` set before the scenario rendering loop:

```python
# In _render_spec, replace the scenario_stories block (lines 113-128):
scenario_stories = [s for s in stories if s.layer in (3, 4)]
if scenario_stories:
    lines.append("## User Scenarios & Testing")
    lines.append("")
    seen_scenarios: set[tuple[str, str, str, str]] = set()
    for idx, story in enumerate(scenario_stories, 1):
        lines.append(f"### User Story {idx} - {story.title}")
        lines.append("")
        if story.summary:
            lines.append(story.summary)
            lines.append("")
        for ac in story.acceptance_criteria:
            key = (ac.scenario, ac.given, ac.when, ac.then)
            if key in seen_scenarios:
                continue
            seen_scenarios.add(key)
            lines.append(f"**Scenario: {ac.scenario}**")
            lines.append("")
            lines.extend(render_gherkin_scenario(ac, bold_keywords=False))
            lines.append("")
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_speckit_exporter.py::TestSpec -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add haytham/exporters/speckit_exporter.py tests/test_speckit_exporter.py
git commit -m "fix: deduplicate scenarios in Spec Kit spec.md"
```

---

### Task 4: Deduplicate success criteria and add Gherkin context

**Files:**
- Modify: `haytham/exporters/speckit_exporter.py:278-285` (`_collect_success_criteria` method)
- Test: `tests/test_speckit_exporter.py` (add new test class)

**Step 1: Write the failing tests**

Add new class to `tests/test_speckit_exporter.py`:

```python
class TestSuccessCriteria:
    def test_duplicate_criteria_deduplicated(self):
        """Same scenario name from different stories should appear once."""
        ac = AcceptanceCriterion(
            id="AC-001",
            scenario="Validation failure",
            given="invalid input",
            when="form submitted",
            then="error shown",
        )
        project = _make_project(
            stories=[
                ContractStory(
                    id="STORY-010",
                    title="Story A",
                    layer=3,
                    summary="First",
                    implements=["CAP-F-001"],
                    acceptance_criteria=[ac],
                ),
                ContractStory(
                    id="STORY-011",
                    title="Story B",
                    layer=3,
                    summary="Second",
                    implements=["CAP-F-001"],
                    acceptance_criteria=[ac],
                ),
            ],
            scope_items=[
                ExportableScopeItem(
                    name="User Authentication",
                    description="Auth.",
                    capabilities=["CAP-F-001"],
                    stories=["STORY-010", "STORY-011"],
                ),
            ],
        )
        tree = SpecKitExporter().export_tree(project)
        spec = tree[".specify/specs/001-user-authentication/spec.md"]
        assert spec.count("Validation failure") == 1

    def test_criteria_include_gherkin_context(self):
        """Success criteria should include Given/When/Then context."""
        project = _make_project()  # default project has STORY-003 with AC
        tree = SpecKitExporter().export_tree(project)
        spec = tree[".specify/specs/001-user-authentication/spec.md"]
        # Should have enriched format, not bare scenario name
        assert "Given " in spec.split("## Success Criteria")[1]
        assert "when " in spec.split("## Success Criteria")[1]
        assert "then " in spec.split("## Success Criteria")[1]

    def test_criteria_without_gherkin_uses_scenario_name(self):
        """AC without given/when/then falls back to scenario name only."""
        project = _make_project(
            stories=[
                ContractStory(
                    id="STORY-010",
                    title="Setup",
                    layer=3,
                    summary="Setup story",
                    implements=["CAP-F-001"],
                    acceptance_criteria=[
                        AcceptanceCriterion(id="AC-001", scenario="Service initialized"),
                    ],
                ),
            ],
            scope_items=[
                ExportableScopeItem(
                    name="User Authentication",
                    description="Auth.",
                    capabilities=["CAP-F-001"],
                    stories=["STORY-010"],
                ),
            ],
        )
        tree = SpecKitExporter().export_tree(project)
        spec = tree[".specify/specs/001-user-authentication/spec.md"]
        assert "Service initialized" in spec
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_speckit_exporter.py::TestSuccessCriteria -v`
Expected: FAIL (duplicates present, no Gherkin context)

**Step 3: Write minimal implementation**

Replace `_collect_success_criteria` in `haytham/exporters/speckit_exporter.py`:

```python
@staticmethod
def _collect_success_criteria(stories: list[ContractStory]) -> list[str]:
    """Collect unique success criteria from story acceptance_criteria.

    Deduplicates by scenario name. When Given/When/Then are available,
    includes them for richer, more actionable criteria text.
    """
    criteria: list[str] = []
    seen: set[str] = set()
    for story in stories:
        for ac in story.acceptance_criteria:
            if ac.scenario in seen:
                continue
            seen.add(ac.scenario)
            if ac.given and ac.when and ac.then:
                criteria.append(
                    f"{ac.scenario}: Given {ac.given}, when {ac.when}, then {ac.then}"
                )
            else:
                criteria.append(ac.scenario)
    return criteria
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_speckit_exporter.py::TestSuccessCriteria -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add haytham/exporters/speckit_exporter.py tests/test_speckit_exporter.py
git commit -m "fix: deduplicate success criteria and add Gherkin context"
```

---

### Task 5: Strip wrapping fences in data-model and contracts rendering

**Files:**
- Modify: `haytham/exporters/speckit_exporter.py:238-272` (`_render_data_model` and `_render_contracts`)
- Test: `tests/test_speckit_exporter.py` (add to `TestConditionalFiles`)

**Step 1: Write the failing tests**

Add to `tests/test_speckit_exporter.py` in class `TestConditionalFiles`:

```python
def test_data_model_strips_wrapping_fences(self):
    """Layer 2 story content wrapped in ```markdown should have fences stripped."""
    project = _make_project(
        stories=[
            ContractStory(
                id="STORY-002",
                title="User table schema",
                layer=2,
                summary="Define the user data model",
                content="```markdown\n## Users Table\n\n| Column | Type |\n|---|---|\n| id | UUID |\n```",
                implements=["CAP-F-001"],
                depends_on=["STORY-001"],
            ),
            ContractStory(
                id="STORY-001",
                title="Project scaffolding",
                layer=0,
                summary="Set up the initial project structure",
                implements=["CAP-F-001"],
            ),
        ],
    )
    tree = SpecKitExporter().export_tree(project)
    dm = tree[".specify/specs/001-user-authentication/data-model.md"]
    assert "```markdown" not in dm
    assert "## Users Table" in dm

def test_contracts_strips_wrapping_fences(self):
    """Layer 3 story content wrapped in ```markdown should have fences stripped."""
    project = _make_project(
        stories=[
            ContractStory(
                id="STORY-003",
                title="Login endpoint",
                layer=3,
                summary="Implement login API",
                content="```markdown\n## POST /auth/login\n\nAccepts OAuth token.\n```",
                implements=["CAP-F-001"],
                depends_on=["STORY-001"],
                acceptance_criteria=[
                    AcceptanceCriterion(
                        id="AC-001",
                        scenario="Login",
                        given="a user",
                        when="they submit a token",
                        then="session returned",
                    ),
                ],
            ),
            ContractStory(
                id="STORY-001",
                title="Project scaffolding",
                layer=0,
                summary="Setup",
                implements=["CAP-F-001"],
            ),
        ],
    )
    tree = SpecKitExporter().export_tree(project)
    api = tree[".specify/specs/001-user-authentication/contracts/api.md"]
    assert "```markdown" not in api
    assert "## POST /auth/login" in api
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_speckit_exporter.py::TestConditionalFiles::test_data_model_strips_wrapping_fences tests/test_speckit_exporter.py::TestConditionalFiles::test_contracts_strips_wrapping_fences -v`
Expected: FAIL (```markdown still present)

**Step 3: Write minimal implementation**

Add import at top of `haytham/exporters/speckit_exporter.py`:

```python
from haytham.exporters.spec_transforms import (
    group_stories_by_layer,
    render_gherkin_scenario,
    slugify,
    strip_wrapping_fences,
    traits_to_constitution_articles,
)
```

Update `_render_data_model`:

```python
def _render_data_model(self, layer_2_stories: list[ContractStory]) -> str:
    """Render data-model.md from layer 2 stories."""
    lines: list[str] = []
    lines.append("# Data Model")
    lines.append("")

    for story in layer_2_stories:
        lines.append(f"## {story.title}")
        lines.append("")
        if story.content:
            lines.append(strip_wrapping_fences(story.content))
            lines.append("")
        elif story.summary:
            lines.append(story.summary)
            lines.append("")

    return "\n".join(lines)
```

Update `_render_contracts`:

```python
def _render_contracts(self, layer_3_stories: list[ContractStory]) -> str:
    """Render contracts/api.md from layer 3 stories."""
    lines: list[str] = []
    lines.append("# API Contracts")
    lines.append("")

    for story in layer_3_stories:
        lines.append(f"## {story.title}")
        lines.append("")
        if story.content:
            lines.append(strip_wrapping_fences(story.content))
            lines.append("")
        elif story.summary:
            lines.append(story.summary)
            lines.append("")

    return "\n".join(lines)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_speckit_exporter.py::TestConditionalFiles -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add haytham/exporters/speckit_exporter.py tests/test_speckit_exporter.py
git commit -m "fix: strip wrapping code fences from data-model and contracts content"
```

---

### Task 6: Deduplicate content in `_render_contracts()`

**Files:**
- Modify: `haytham/exporters/speckit_exporter.py` (`_render_contracts` method, already modified in Task 5)
- Test: `tests/test_speckit_exporter.py` (add to `TestConditionalFiles`)

**Step 1: Write the failing test**

Add to `tests/test_speckit_exporter.py` in class `TestConditionalFiles`:

```python
def test_contracts_deduplicates_identical_content(self):
    """Two layer 3 stories with identical content should only render once."""
    shared_content = "## POST /api/sessions\n\nCreate a new session."
    project = _make_project(
        stories=[
            ContractStory(
                id="STORY-010",
                title="Session API",
                layer=3,
                summary="Session endpoint",
                content=shared_content,
                implements=["CAP-F-001"],
                acceptance_criteria=[
                    AcceptanceCriterion(
                        id="AC-001",
                        scenario="Create session",
                        given="authenticated user",
                        when="POST request",
                        then="201 returned",
                    ),
                ],
            ),
            ContractStory(
                id="STORY-011",
                title="Session API (duplicate)",
                layer=3,
                summary="Session endpoint duplicate",
                content=shared_content,
                implements=["CAP-F-001"],
                acceptance_criteria=[
                    AcceptanceCriterion(
                        id="AC-001",
                        scenario="Create session",
                        given="authenticated user",
                        when="POST request",
                        then="201 returned",
                    ),
                ],
            ),
            ContractStory(
                id="STORY-001",
                title="Setup",
                layer=0,
                summary="Setup",
                implements=["CAP-F-001"],
            ),
        ],
        scope_items=[
            ExportableScopeItem(
                name="User Authentication",
                description="Auth.",
                capabilities=["CAP-F-001"],
                stories=["STORY-010", "STORY-011", "STORY-001"],
            ),
        ],
    )
    tree = SpecKitExporter().export_tree(project)
    api = tree[".specify/specs/001-user-authentication/contracts/api.md"]
    assert api.count("Create a new session.") == 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_speckit_exporter.py::TestConditionalFiles::test_contracts_deduplicates_identical_content -v`
Expected: FAIL (count is 2)

**Step 3: Write minimal implementation**

Update `_render_contracts` to add content dedup (building on Task 5's fence stripping):

```python
def _render_contracts(self, layer_3_stories: list[ContractStory]) -> str:
    """Render contracts/api.md from layer 3 stories.

    Strips wrapping code fences and deduplicates stories with
    identical content.
    """
    lines: list[str] = []
    lines.append("# API Contracts")
    lines.append("")

    seen_content: set[str] = set()
    for story in layer_3_stories:
        content = strip_wrapping_fences(story.content) if story.content else ""
        content_key = content.strip()
        if content_key and content_key in seen_content:
            continue
        if content_key:
            seen_content.add(content_key)

        lines.append(f"## {story.title}")
        lines.append("")
        if content:
            lines.append(content)
            lines.append("")
        elif story.summary:
            lines.append(story.summary)
            lines.append("")

    return "\n".join(lines)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_speckit_exporter.py::TestConditionalFiles -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add haytham/exporters/speckit_exporter.py tests/test_speckit_exporter.py
git commit -m "fix: deduplicate identical content in Spec Kit API contracts"
```

---

### Task 7: Run full test suite and lint

**Step 1: Run lint**

Run: `uv run ruff check haytham/ --fix && uv run ruff format haytham/`
Expected: Clean

**Step 2: Run full unit tests**

Run: `uv run pytest tests/ -v -m "not integration" -x`
Expected: ALL PASS

**Step 3: Fix any failures**

If any tests fail, diagnose and fix.

**Step 4: Commit any lint fixes**

```bash
git add -A && git commit -m "chore: lint and format fixes"
```
(Only if there were changes.)
