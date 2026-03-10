# Plan: Structural Improvements

Follows the fix-dogfood-phase2-phase3 changes (already implemented, not yet committed). Addresses the underlying design flaws those issues were symptoms of.

## What we're fixing

| # | Structural Issue | Root Cause | Fix Type |
|---|---|---|---|
| 1 | Constraint propagation | Downstream agents don't know upstream counts | Command prompt change |
| 2 | Shallow validation | Validator checks syntax, not semantics | Cross-file validation in hooks |
| 3 | No inter-phase feedback | Architect can't flag bad input | Validation at phase boundary |
| 4 | Modeler task contamination | Two independent tasks share one prompt | Prompt restructuring |
| 5 | Rigid category enums | Unknown categories blocked instead of flagged | Prompt + validator adjustment |

Issues 2 and 3 share one implementation (cross-file checks in validate_schema.py).

## What we're NOT fixing

- **Architect infrastructure bias**: The fix plan already added ORCHESTRATION, llm_api, compute, and a self-check for core behavior. Further restructuring deferred until testing shows it's needed.
- **Multi-archetype test suite**: Valuable but a process task, not a code change. Run 2-3 non-web-app ideas after these changes land.
- **Deterministic correction on validation failure**: Hits the plugin framework ceiling. Accepted as probabilistic for Genesis.

## Changes

### Change 1: Pass scope item count to capability modeler

**Files:** `commands/specify.md`, `commands/haytham.md`

**Why:** The modeler doesn't know how many scope items exist. It guesses, and when it guesses wrong it collapses items into mega-capabilities. Passing the count explicitly turns "infer the right number" into "follow the number you were given."

**Where in specify.md:** Step 3, the agent launch prompt (line 83-84).

**Change:** Before launching the capability-modeler agent, add an instruction to read mvp-scope.md, count the IN SCOPE items, and include the count in the agent prompt.

Current:
```
Launch a **capability-modeler** agent with this task:
> Read the MVP scope from `.haytham/session/phase-2-what/mvp-scope.md`, idea analysis from `.haytham/session/phase-1-why/idea-analysis.md`, and concept anchor from `.haytham/session/phase-1-why/concept-anchor.json`. Produce the capability model and system traits. Write to `.haytham/session/phase-2-what/capabilities.json` and `.haytham/session/phase-2-what/system-traits.json`.
```

New:
```
Read `.haytham/session/phase-2-what/mvp-scope.md` and count the number of IN SCOPE items in the MVP Boundaries table. Then launch a **capability-modeler** agent with this task:
> Read the MVP scope from `.haytham/session/phase-2-what/mvp-scope.md`, idea analysis from `.haytham/session/phase-1-why/idea-analysis.md`, and concept anchor from `.haytham/session/phase-1-why/concept-anchor.json`. The MVP scope has [N] IN SCOPE items. Produce exactly one functional capability per IN SCOPE item. Write to `.haytham/session/phase-2-what/capabilities.json` and `.haytham/session/phase-2-what/system-traits.json`.
```

**Same change in haytham.md:** Step 9 (lines 280-281), identical modification.

---

### Change 2: Cross-file semantic validation in validate_schema.py

**File:** `scripts/validate_schema.py`

**Why:** The validator catches surface violations (wrong types, missing keys, invalid enums) but misses the failures that actually matter: mega-capabilities, incomplete coverage, traceability collapse. These are all checkable deterministically by reading two files at once.

**What to add:**

#### 2a: Capability count consistency (when capabilities.json is written)

After the existing capabilities.json validation block, add:

```python
# Cross-check: capability count vs scope items covered
traceability = data.get("traceability", {})
scope_items = traceability.get("scope_items_covered", [])
func_caps = caps.get("functional", [])
if scope_items and func_caps:
    diff = abs(len(func_caps) - len(scope_items))
    if diff > 2:
        warnings.append(
            f"Capability count ({len(func_caps)}) differs from "
            f"scope items covered ({len(scope_items)}) by {diff} "
            f"in {basename}. Expected roughly 1:1 mapping."
        )
```

This uses data already inside capabilities.json (the traceability.scope_items_covered list), so no cross-file read needed.

#### 2b: Mega-capability detection (when capabilities.json is written)

```python
# Check for mega-capabilities (one capability serving multiple scope items)
for cap in func_caps:
    scope_item = cap.get("serves_scope_item", "")
    # Detect pipe-separated or comma-separated scope items in a single field
    if " | " in scope_item or ", " in scope_item:
        cap_id = cap.get("id", "unknown")
        warnings.append(
            f"Capability {cap_id} serves multiple scope items: "
            f"'{scope_item}'. Split into one capability per scope item."
        )
```

#### 2c: Architecture coverage cross-check (when architecture-decisions.json is written)

When architecture-decisions.json is validated, read capabilities.json to verify coverage:

```python
if basename == "architecture-decisions.json":
    # Cross-reference coverage against capabilities
    coverage = data.get("coverage_check", {})
    uncovered = coverage.get("uncovered", [])
    if uncovered:
        warnings.append(
            f"Architecture has uncovered capabilities: "
            f"{uncovered} in {basename}"
        )

    # Cross-file: verify claimed coverage matches actual capabilities
    session_dir = os.path.dirname(os.path.dirname(file_path))
    caps_path = os.path.join(session_dir, "phase-2-what", "capabilities.json")
    if os.path.exists(caps_path):
        try:
            with open(caps_path) as cf:
                caps_data = json.load(cf)
            all_cap_ids = set()
            for cap in caps_data.get("capabilities", {}).get("functional", []):
                all_cap_ids.add(cap.get("id", ""))
            for cap in caps_data.get("capabilities", {}).get("non_functional", []):
                all_cap_ids.add(cap.get("id", ""))
            covered = set(coverage.get("functional_covered", []))
            covered.update(coverage.get("non_functional_covered", []))
            actually_uncovered = all_cap_ids - covered
            if actually_uncovered:
                warnings.append(
                    f"Architecture claims full coverage but these capabilities "
                    f"from capabilities.json are not in coverage_check: "
                    f"{sorted(actually_uncovered)}"
                )
        except (json.JSONDecodeError, KeyError):
            pass
```

#### 2d: Decision ID format validation (when architecture-decisions.json is written)

```python
    # Validate decision ID format
    import re
    valid_categories = {"AUTH", "DB", "DEPLOY", "NOTIFY", "REALTIME",
                        "INTEGRITY", "ORCHESTRATION", "STACK"}
    for decision in data.get("decisions", []):
        dec_id = decision.get("id", "")
        match = re.match(r"^DEC-([A-Z]+)-(\d{3})$", dec_id)
        if not match:
            warnings.append(
                f"Invalid decision ID format '{dec_id}' in {basename}. "
                f"Expected DEC-CATEGORY-NNN."
            )
        elif match.group(1) not in valid_categories:
            warnings.append(
                f"Unknown decision category '{match.group(1)}' in "
                f"{dec_id} in {basename}. "
                f"Known: {sorted(valid_categories)}"
            )
```

---

### Change 3: Separate capability and trait tasks in modeler prompt

**File:** `agents/capability-modeler.md`

**Why:** The modeler produces capabilities.json and system-traits.json in one pass. The boolean-in-explanations bug happened because the LLM echoed `realtime: false` from traits into the explanations field. Sharper separation prevents cross-contamination.

**Changes:**

Between Part 1 and Part 2 (after the Scope Creep Detection section, before Part 2: System Traits), add:

```markdown
**Write `capabilities.json` now, before starting Part 2.** Part 2 is an independent classification task. Do not reference Part 1 output when writing Part 2.
```

Split the current Self-Check into two sections:

Current (single Self-Check at the end):
```markdown
## Self-Check

Before outputting:
- Every capability's serves_scope_item quotes an actual IN SCOPE item?
- Every flow reference exists in the MVP Scope input?
- Capability count within +/-2 of IN SCOPE count?
- No features added that aren't in IN SCOPE?
- All 8 traits present?
- Anchor invariants correctly mapped to traits?
- Multi-select traits use arrays, single-select use strings?
- Every value in the `explanations` object is a string (not boolean, not number, not null)?
```

New (two separate self-checks):
```markdown
## Part 1 Self-Check

Before writing capabilities.json:
- Every capability's serves_scope_item quotes an actual IN SCOPE item?
- Every flow reference exists in the MVP Scope input?
- Capability count within +/-2 of IN SCOPE count?
- No features added that aren't in IN SCOPE?

## Part 2 Self-Check

Before writing system-traits.json:
- All 8 traits present?
- Anchor invariants correctly mapped to traits?
- Multi-select traits use arrays, single-select use strings?
- Every value in the `explanations` object is a string (not boolean, not number, not null)?
- Each explanation is a sentence explaining WHY, not a copy of the trait value?
```

---

### Change 4: Allow custom infrastructure categories in architect prompt

**File:** `agents/architect.md`

**Why:** The fixed category enum requires expansion every time a new product type surfaces. The validator already warns non-blocking. The prompt should tell the architect that custom categories are acceptable when none fit.

**Where:** After the category list in Part 1 (line 106-107 area).

Add after the `"category": "database | auth | ..."` line in the JSON schema:

```
If the system needs infrastructure that doesn't fit these categories, use a descriptive lowercase slug (e.g., `ml_pipeline`, `iot_gateway`). The standard categories cover most cases. Use them when they fit; invent when they don't.
```

**Validator change in validate_schema.py:** Change the infrastructure category check from "invalid category" to "non-standard category" in the warning message. Keep the warning (it's informational), but soften the language so it doesn't read as an error.

---

### Change 5: Tests for new validation logic

**File:** `tests/test_plugin_sanity.py`

New test cases for Changes 2a-2d:

- `test_capabilities_count_vs_scope_items`: Create fixture where functional count differs from scope_items_covered by 4. Expect warning about count mismatch.
- `test_mega_capability_detection`: Create fixture where serves_scope_item contains "Scope Item A | Scope Item B". Expect warning about multiple scope items.
- `test_architecture_uncovered_capabilities`: Create fixture where coverage_check.uncovered is non-empty. Expect warning.
- `test_architecture_coverage_cross_check`: Create capabilities.json fixture with CAP-F-001 through CAP-F-003. Create architecture-decisions.json fixture where coverage_check.functional_covered only lists CAP-F-001 and CAP-F-002. Expect warning about CAP-F-003 being uncovered.
- `test_decision_id_format`: Create fixture with "DEC-BANANA-001". Expect warning about unknown category.

New fixtures needed:
- `tests/fixtures/capabilities_count_mismatch.json`
- `tests/fixtures/capabilities_mega.json`
- `tests/fixtures/arch_decisions_uncovered.json`
- `tests/fixtures/arch_decisions_coverage_mismatch.json` (needs companion `capabilities_for_cross_check.json`)
- `tests/fixtures/arch_decisions_bad_id.json`

---

## Implementation order

1. Change 3 (modeler prompt separation) - standalone, no dependencies
2. Change 4 (architect custom categories) - standalone, no dependencies
3. Change 2 (cross-file validation) - the bulk of the work
4. Change 5 (tests) - depends on Change 2
5. Change 1 (constraint propagation in commands) - standalone, do last so it can be tested with a real run

Changes 1-2 and 3-4 are independent and can be done in parallel.

## Verification

After implementation, run:
```bash
python3 -m pytest tests/test_plugin_sanity.py -v
```

Then test with a non-web-app idea to verify the structural improvements work for product types the system wasn't originally designed for.
