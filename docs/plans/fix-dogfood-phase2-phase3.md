# Fix Plan: Dogfooding Phase 2-3 Issues

Dogfooding session tested the idea: "An open source AI Agentic system that takes an Idea, researches it, provides recommendations on the research and competitors, proposes an MVP, suggests architecture, produces standardised specs and finally implements the system."

Phase 1 output quality was strong. Phase 2 and 3 revealed cascading issues originating from the capability modeler's 3-5 max constraint. This plan fixes the root causes across 4 files and 13 changes.

## Root Cause Chain

```
capability-modeler: 3-5 max forced 6 stages into 1 mega-capability (CAP-F-002)
    |
    v
architect: CAP-F-002 only needed 1 decision for "coverage" (DEC-INTEGRITY-001)
    |
    v
Result: No architecture decision describes HOW the pipeline executes,
        only how its output is validated. The core product has no design spec.
```

## Changes

### File 1: agents/capability-modeler.md

**Change 1: Fix the contradiction between "3-5 max" and "one per IN SCOPE item"**

The guideline says "One capability per IN SCOPE item" but also "3-5 max". When the scoper overrides its 5-item limit for anchor compliance, the modeler has no way to follow both rules. It collapses distinct scope items into mega-capabilities that break downstream traceability.

Location: The "Functional Capabilities (3-5 max)" heading in the Guidelines section.

Change:

> **Functional Capabilities (3-5 max):**

To:

> **Functional Capabilities (one per IN SCOPE item, typically 3-5):**

And add after the existing bullet list:

> A mega-capability that bundles multiple distinct scope items into one loses traceability downstream: the architect cannot distinguish which decisions serve which scope items. Prefer one capability per distinct scope item over consolidation.

**Change 2: Reject cross-cutting mechanism capabilities that duplicate acceptance criteria**

In the dogfooding session, CAP-F-005 (context passing) restated what was already covered by CAP-F-002's acceptance criteria, inflating the count without adding granularity.

Location: Add to the "Scope Creep Detection" section.

Add:

> - Cross-cutting mechanisms already covered as acceptance criteria of another capability (e.g., "context passing" that only enables "pipeline coherence" is a criterion of the pipeline capability, not a standalone capability)

**Change 3: Add string-type check for system-traits explanations**

The dogfooding output had `explanations.realtime` as `false` (boolean) instead of a string explanation, with the actual text in a non-standard `realtime_explanation` key.

Location: Add to the "Self-Check" section.

Add:

> - Every value in the `explanations` object is a string (not boolean, not number, not null)?

### File 2: agents/architect.md

**Change 4: Add `llm_api` and `compute` to infrastructure categories**

The current enum (database, auth, payments, storage, email, hosting, search, realtime, video, scheduling) doesn't cover AI/LLM products where the API is the primary infrastructure dependency. The dogfooding session invented `llm_api` and `orchestration` categories, which were technically schema violations.

Location: Infrastructure category list in Part 1.

Change:

```
database | auth | payments | storage | email | hosting | search | realtime | video | scheduling
```

To:

```
database | auth | payments | storage | email | hosting | search | realtime | video | scheduling | llm_api | compute
```

**Change 5: Add `platform_opportunity` to build-buy JSON schema**

Part 0 mandates a platform assessment when `distribution` is `plugin_or_extension`, but the schema has no field for the result. The dogfooding session added an extra top-level field that a strict validator would reject.

Location: The JSON schema block in Part 1 (line 94 of architect.md), between `"system_summary"` and `"infrastructure_requirements"`.

Add `platform_opportunity` as a second field in the existing schema object:

```json
{
  "system_summary": "...",
  "platform_opportunity": {
    "assessed": true,
    "finding": "Summary of platform fit assessment",
    "platform_components_provided": ["What the platform gives for free"],
    "platform_components_not_provided": ["What you still need to build/buy"],
    "recommendation": "PLATFORM recommendation if applicable"
  },
  "infrastructure_requirements": [...]
}
```

Add note after the schema block: `platform_opportunity` is required when Part 0 assessment is performed, omitted otherwise.

**Change 6: Add `ORCHESTRATION` to architecture decision categories**

The current categories (AUTH, DB, DEPLOY, NOTIFY, REALTIME, INTEGRITY) have no home for pipeline/workflow design decisions. The dogfooding session misused DEC-REALTIME-001 for a synchronous stdin checkpoint because no better category existed.

Location: Architecture Decision Categories list in Part 2.

Add:

> 7. **ORCHESTRATION**: Pipeline/workflow sequencing, stage definitions, context accumulation, state machine design, inter-step interaction patterns (if the product's core value involves multi-step coordination)

And add to Decision ID Format:

> DEC-ORCHESTRATION-001

**Change 7: Require architecture decision for the core product behavior**

The dogfooding session's architect claimed full coverage of the 6-stage pipeline with only a validation decision (DEC-INTEGRITY-001), without specifying the execution model. Validation is necessary but not sufficient.

Location: Add to Coverage Requirements in Part 2.

Add:

> - If a capability covers the product's core behavior ("THE ONE THING" from MVP scope), it must have at least one architecture decision describing HOW that behavior executes, not just how it is validated. Validation decisions (INTEGRITY) address quality; orchestration/execution decisions address design. The core capability needs both.

### File 3: scripts/validate_schema.py

**Change 8: Validate system-traits explanation values are strings**

The PostToolUse hook checks that `traits` and `explanations` keys exist, but doesn't validate that explanation values are strings. The boolean `false` for `explanations.realtime` passed silently.

Location: Add special validation block for `system-traits.json`.

Logic:
- For each key in `explanations`, check `isinstance(value, str)`
- Warn if value is bool, int, float, None, list, or dict
- Warn if any key in `explanations` doesn't match one of the 8 trait names

**Change 9: Fix flow reference validation for pipe-separated values**

Current code checks `flow not in ("Flow 1", "Flow 2", "Flow 3")` but the capability-modeler schema example shows `"Flow 1 | Flow 2 | Flow 3"` as pipe-separated. Every capability in the dogfooding output used `"Flow 1 | Flow 2"`, which would fail the current check.

Location: Flow validation in the `capabilities.json` special validation block.

Change: Split `user_flow` on `" | "`, strip whitespace, validate each part is in `{"Flow 1", "Flow 2", "Flow 3"}`.

**Change 10: Validate infrastructure requirement categories**

No validation currently exists for `build-buy.json` field values. Invalid categories (like the invented `orchestration`) pass silently.

Location: Add special validation block for `build-buy.json`.

Logic:
- For each item in `infrastructure_requirements`, check `category` is in the valid set: `{database, auth, payments, storage, email, hosting, search, realtime, video, scheduling, llm_api, compute}`
- For each item in `recommended_stack`, check `recommendation` is in `{BUILD, BUY, HYBRID, PLATFORM}`

### File 4: tests/ (test updates for Changes 8-10)

Changes 8-10 add new validation logic to `validate_schema.py`. Without corresponding tests, the new logic is unverified and regressions will be silent.

**Change 11: Add test fixtures and cases for system-traits validation (covers Change 8)**

New fixture: `tests/fixtures/valid_system_traits.json`
```json
{
  "traits": {
    "interface": ["browser"], "auth": "multi_user", "deployment": ["cloud_hosted"],
    "data_layer": "remote_db", "realtime": false, "communication": "none",
    "payments": "none", "scheduling": "none"
  },
  "explanations": {
    "interface": "Web app", "auth": "Multiple users", "deployment": "Cloud",
    "data_layer": "Needs persistence", "realtime": "No live updates needed",
    "communication": "No messaging", "payments": "Free MVP", "scheduling": "Not applicable"
  }
}
```

New fixture: `tests/fixtures/invalid_system_traits.json`
```json
{
  "traits": {
    "interface": ["browser"], "auth": "multi_user", "deployment": ["cloud_hosted"],
    "data_layer": "remote_db", "realtime": false, "communication": "none",
    "payments": "none", "scheduling": "none"
  },
  "explanations": {
    "interface": "Web app", "auth": "Multiple users", "deployment": "Cloud",
    "data_layer": "Needs persistence", "realtime": false,
    "communication": "No messaging", "payments": "Free MVP", "scheduling": "Not applicable"
  }
}
```

New tests in `TestSchemaValidation`:
- `test_valid_system_traits`: valid fixture produces no warnings
- `test_invalid_system_traits_boolean_explanation`: invalid fixture warns about non-string value for `realtime`

**Change 12: Add test fixture and case for pipe-separated flow validation (covers Change 9)**

Update fixture: `tests/fixtures/valid_capabilities.json` -- add a second functional capability with `"user_flow": "Flow 1 | Flow 2"` to verify pipe-separated parsing passes.

New fixture: `tests/fixtures/invalid_capabilities_bad_flow_part.json`
```json
{
  "summary": "Capability model",
  "capabilities": {
    "functional": [
      {
        "id": "CAP-001", "name": "Feature",
        "serves_scope_item": "IN-001",
        "user_flow": "Flow 1 | Flow 99"
      }
    ],
    "non_functional": []
  },
  "traceability": {},
  "metadata": {}
}
```

New test: `test_invalid_capabilities_bad_flow_part` -- verifies that `"Flow 99"` within a pipe-separated value triggers a warning.

Existing test impact: `test_invalid_capabilities_bad_flow` uses `"Flow 99"` (single value, no pipe). After Change 9, splitting on `" | "` yields `["Flow 99"]`, which still fails validation. The warning message must keep the phrase `"invalid flow ref"` so this test continues to pass.

**Change 13: Add test fixtures and cases for build-buy validation (covers Change 10)**

New fixture: `tests/fixtures/valid_build_buy.json`
```json
{
  "system_summary": "Test system",
  "infrastructure_requirements": [
    {"category": "database", "need": "Persistence", "capabilities_served": ["CAP-F-001"]},
    {"category": "llm_api", "need": "AI inference", "capabilities_served": ["CAP-F-002"]}
  ],
  "recommended_stack": [
    {"name": "Supabase", "category": "database", "recommendation": "BUY",
     "rationale": "All-in-one", "capabilities_served": ["CAP-F-001"]},
    {"name": "OpenAI API", "category": "llm_api", "recommendation": "BUY",
     "rationale": "Best models", "capabilities_served": ["CAP-F-002"]}
  ],
  "stack_rationale": "Simple stack",
  "total_integration_effort": "2-3 days",
  "estimated_monthly_cost": "$0-$50"
}
```

New fixture: `tests/fixtures/invalid_build_buy.json`
```json
{
  "system_summary": "Test system",
  "infrastructure_requirements": [
    {"category": "orchestration", "need": "Pipeline", "capabilities_served": ["CAP-F-001"]}
  ],
  "recommended_stack": [
    {"name": "Custom", "category": "orchestration", "recommendation": "MAGIC",
     "rationale": "Because", "capabilities_served": ["CAP-F-001"]}
  ],
  "stack_rationale": "Test",
  "total_integration_effort": "1 day",
  "estimated_monthly_cost": "$0"
}
```

New tests in `TestSchemaValidation`:
- `test_valid_build_buy`: valid fixture produces no warnings
- `test_invalid_build_buy_bad_category`: invalid fixture warns about `"orchestration"` category
- `test_invalid_build_buy_bad_recommendation`: invalid fixture warns about `"MAGIC"` recommendation

## What This Plan Does NOT Change

- **Phase 1 agents** (research-briefer length, SOM caveat, hypothesis classification): not re-running Phase 1
- **MVP scoper**: its output was good; the problems cascaded from the capability modeler
- **State tracking in project.yaml**: real issue but orthogonal to output quality; defer
- **60% completion threshold in CAP-NF-001**: inherited from scope, not a modeler/architect problem

## Verification After Re-run

After implementing and re-running from Phase 2:

1. Capabilities should have ~6-8 functional capabilities (one per stage + trigger + checkpoints + output), not 5
2. No mega-capability bundling multiple distinct scope items
3. `system-traits.json` explanations are all strings
4. `build-buy.json` uses valid categories including `llm_api`
5. Architecture decisions include a DEC-ORCHESTRATION-001 covering pipeline execution model
6. The core pipeline capability is covered by both an ORCHESTRATION and an INTEGRITY decision
7. No schema validation warnings from PostToolUse hook
