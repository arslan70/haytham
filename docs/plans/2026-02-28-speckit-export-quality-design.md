# Spec Kit Export Quality Fixes

**Date:** 2026-02-28
**Branch:** `fix/speckit-export-quality`
**Scope:** Exporter + upstream contract assembly

## Problem

A review of an exported `spec-kit.zip` found 8 failures across 15 checks. Issues fall into two categories: exporter rendering bugs and upstream data quality.

### Exporter bugs

1. **Task descriptions are "Description" or leaked fences** (`tasks.md`): `_extract_summary()` in `assembler.py` takes the first non-empty line of story content. If the story starts with `## Description`, it returns literal "Description". If it starts with ` ```markdown `, that becomes the summary.
2. **Duplicate scenarios in spec.md**: `_render_spec()` iterates all acceptance criteria without dedup. OpenSpec already has `seen_scenarios` logic, Spec Kit doesn't.
3. **Duplicate success criteria**: `_collect_success_criteria()` collects all scenario names without dedup.
4. **Broken/nested code fences** (`data-model.md`, `contracts/api.md`): `_render_data_model()` and `_render_contracts()` dump `story.content` as-is. If content is wrapped in ` ```markdown ... ``` `, it creates nested fences.
5. **Duplicate content in api.md**: Multiple layer 3 stories have identical content. The exporter renders all of them.

### Upstream data quality

6. **Non-measurable success criteria**: `_collect_success_criteria()` uses `ac.scenario` (just the scenario title). No thresholds, percentages, or measurable outcomes.

## Approach: Targeted fixes in existing files

Fix each issue in its natural location. No new modules.

### Fix 1: `_extract_summary()` in `assembler.py`

Skip lines that are purely structural: generic headings ("Description", "Details", "Overview"), code fence markers, and blank-after-strip lines.

```python
_SKIP_HEADINGS = {"description", "details", "overview", "files to create", "acceptance criteria"}

def _extract_summary(content: str, title: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Skip code fence markers
        if stripped.startswith("```"):
            continue
        # Skip generic structural headings
        heading_text = stripped.lstrip("#").strip()
        if heading_text.lower() in _SKIP_HEADINGS:
            continue
        return heading_text
    return title
```

### Fix 2: Scenario dedup in `_render_spec()`

Port the `seen_scenarios` pattern from OpenSpec exporter.

```python
seen: set[tuple[str, str, str, str]] = set()
for ac in story.acceptance_criteria:
    key = (ac.scenario, ac.given, ac.when, ac.then)
    if key in seen:
        continue
    seen.add(key)
    # render scenario...
```

### Fix 3: Success criteria dedup in `_collect_success_criteria()`

Add a `seen` set and skip duplicates.

```python
@staticmethod
def _collect_success_criteria(stories: list[ContractStory]) -> list[str]:
    criteria: list[str] = []
    seen: set[str] = set()
    for story in stories:
        for ac in story.acceptance_criteria:
            if ac.scenario not in seen:
                seen.add(ac.scenario)
                criteria.append(ac.scenario)
    return criteria
```

### Fix 4: Code fence sanitization in `spec_transforms.py`

New utility function `strip_wrapping_fences()` that removes an outer fence wrapper if the entire content is enclosed in one.

```python
def strip_wrapping_fences(content: str) -> str:
    """Strip an outer ```language ... ``` wrapper if content is entirely enclosed."""
    lines = content.strip().splitlines()
    if len(lines) < 2:
        return content
    if lines[0].startswith("```") and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1])
    return content
```

Called in `_render_data_model()` and `_render_contracts()` before appending story content.

### Fix 5: Content dedup in `_render_contracts()`

Deduplicate stories by content hash before rendering. If two layer 3 stories have identical content, only render the first.

```python
def _render_contracts(self, layer_3_stories: list[ContractStory]) -> str:
    lines = ["# API Contracts", ""]
    seen_content: set[int] = set()
    for story in layer_3_stories:
        content_hash = hash(story.content.strip()) if story.content else 0
        if content_hash in seen_content:
            continue
        seen_content.add(content_hash)
        # render story...
```

### Fix 6: Richer success criteria

Include the Given/When/Then context in success criteria, not just the scenario name. This makes them actionable without being measurable metrics (which would require LLM changes).

```python
@staticmethod
def _collect_success_criteria(stories: list[ContractStory]) -> list[str]:
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

## Files to change

| File | Changes |
|------|---------|
| `haytham/workflow/contracts/assembler.py` | Fix `_extract_summary()` to skip structural lines |
| `haytham/exporters/speckit_exporter.py` | Dedup scenarios, dedup success criteria, dedup contracts, fence stripping |
| `haytham/exporters/spec_transforms.py` | Add `strip_wrapping_fences()` |
| `tests/test_speckit_exporter.py` | Tests for all 6 fixes |
| `tests/test_spec_transforms.py` | Test for `strip_wrapping_fences()` |
| `tests/test_contract_assembler.py` | Test for improved `_extract_summary()` |

## Testing strategy

Each fix gets at least one test:

1. `_extract_summary` with content starting with `## Description`, ` ```markdown `, and normal prose
2. Duplicate acceptance criteria across stories produce unique scenarios in spec.md
3. Success criteria are deduplicated
4. Content wrapped in ` ```markdown ``` ` has fences stripped
5. Duplicate story content in layer 3 produces single entry in api.md
6. Success criteria include Gherkin context when available
