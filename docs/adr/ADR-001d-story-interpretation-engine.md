# ADR-001d: Story Interpretation Engine

**Status**: Proposed
**Date**: 2025-01-02
**Parent**: [ADR-001: Story-to-Implementation Pipeline](./ADR-001-story-to-implementation-pipeline.md)
**Depends On**: [ADR-001c: System State Model](./ADR-001c-system-state-model.md)
**Scope**: Parsing stories, surfacing ambiguities, and producing interpreted specifications

---

## POC Simplifications

- **ID Scheme**: Stories use S-XXX (e.g., S-001, S-002)
- **Ambiguities**: Stored as properties of stories in state.json, not separate files
- **Test Case**: Notes App with simple stories (Create Note, List Notes, Search Notes, Delete Note)
- **Question Presentation**: Console-based, one story at a time

**Example for Notes App:**
```
Story S-003 (Search Notes) ambiguity:
- Question: "Search in title only or content too?"
- Classification: Decision Required
- Options: A) Title only, B) Title and content, C) Full-text search
- Default: B (Title and content)
```

---

## Context

User stories in the MVP specification are written from a user-centric perspective. They describe *what* users want to do, not *how* the system should implement it. Each story contains:

- **Explicit content**: What's directly stated
- **Implicit content**: What's assumed but not stated
- **Ambiguous content**: What could be interpreted multiple ways
- **Missing content**: What's needed but not mentioned

### The Interpretation Problem

Consider this story:
> "As a user, I want to share my content with others so that they can see what I've created."

This raises numerous questions:
- Share with whom? (specific users, public, link-based)
- Share what content? (all content, selected items, specific types)
- What permissions do recipients get? (view only, edit, re-share)
- How is sharing done? (email, link, in-app, social media)
- What happens when content is updated? (recipients see changes?)
- Can sharing be revoked?

Without explicit interpretation, each downstream stage might assume different answers, creating an incoherent system.

### Requirements

1. **Surface Ambiguities**: Make implicit decisions explicit
2. **Classify Decisions**: Separate auto-resolvable from human-required
3. **Check Consistency**: Verify against existing system state
4. **Preserve Intent**: Don't change what the user actually asked for
5. **Enable Traceability**: Link interpretations back to source

---

## Decision

Implement a **Story Interpretation Engine** that processes each story through a structured analysis pipeline, producing an "Interpreted Story" artifact with:

1. Parsed story components
2. Identified ambiguities with classifications
3. Proposed resolutions or questions for user
4. Consistency check results against system state
5. Explicit assumptions made

---

## Interpretation Pipeline

### Overview

```
┌─────────────────┐
│   User Story    │
│  (from MVP Spec)│
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                    PARSING STAGE                             │
│  Extract: actors, actions, objects, conditions, outcomes     │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                 AMBIGUITY DETECTION                          │
│  Identify: missing details, vague terms, multiple meanings   │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│               CLASSIFICATION & RESOLUTION                    │
│  For each ambiguity: auto-resolve or escalate to user        │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                 CONSISTENCY CHECK                            │
│  Verify against: existing entities, capabilities, decisions  │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│               PREREQUISITE DETECTION                         │
│  Identify: required capabilities not yet in system           │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                  OUTPUT GENERATION                           │
│  Produce: Interpreted Story + Questions + Assumptions        │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│   Auto-Resolved │     │  Needs Human    │
│   (continue)    │     │  Input (block)  │
└─────────────────┘     └─────────────────┘
```

---

## Stage 1: Parsing

Extract structured components from the user story.

### Story Grammar

```
User Story = Actor + Action + Object + [Condition] + Outcome

Actor    = "As a <role>"
Action   = "I want to <verb> <object>"
Object   = The thing being acted upon
Condition = "when <circumstance>" | "given <state>"
Outcome  = "so that <benefit>"
```

### Parsing Output

```yaml
# Example (Notes App): "As a user, I want to search my notes so that I can quickly find what I need"

parsed_story:
  story_id: "S-003"
  raw_text: "As a user, I want to search my notes so that I can quickly find what I need"

  components:
    actor:
      role: "user"
      resolved_to: "registered_user"  # From system state roles

    action:
      verb: "search"
      verb_type: "read"  # create | read | update | delete | distribution | communication

    object:
      primary: "notes"
      possessive: true  # "my notes" implies ownership
      quantity: "all"  # search across all notes

    outcome:
      benefit: "find quickly"
      beneficiary: "user"

  acceptance_criteria:
    - id: "AC-003-01"
      raw: "Given I have notes, when I search by keyword, then matching notes are displayed"
      parsed:
        precondition: "notes exist, owned by actor"
        trigger: "search action"
        postcondition: "matching notes displayed"
```

### Entity Extraction

Identify entities referenced (existing or new):

```yaml
entities_referenced:
  - name: "Note"
    status: "exists"  # In system state
    entity_id: "E-002"

  - name: "search"
    status: "capability_needed"
    type: "action"
    needs_clarification: true  # What fields to search?
```

---

## Stage 2: Ambiguity Detection

Systematically identify what's not specified.

### Ambiguity Categories

| Category | Description | Example |
|----------|-------------|---------|
| **Scope** | What's included/excluded | "content" - all types or specific? |
| **Target** | Who/what is affected | "others" - anyone or selected? |
| **Mechanism** | How something happens | "share" - via link, email, in-app? |
| **Permission** | Access levels | Recipients can view, edit, or re-share? |
| **Lifecycle** | Duration and changes | Permanent or revocable? Updates visible? |
| **Edge Cases** | Unusual situations | Share with self? Share already-shared? |
| **Constraints** | Limits and boundaries | Max recipients? Content size limits? |
| **UI/UX** | User experience | Button location? Confirmation dialog? |

### Detection Rules

```yaml
ambiguity_detection_rules:
  - rule_id: "AMB-SCOPE-001"
    pattern: "possessive + plural noun without qualifier"
    example: "my content", "my items", "my posts"
    question_template: "Does '{noun}' refer to all {noun} or a selection?"

  - rule_id: "AMB-TARGET-001"
    pattern: "vague recipient"
    triggers: ["others", "people", "users", "everyone", "anyone"]
    question_template: "Who specifically can '{action}'? Options: specific users, anyone with link, defined groups"

  - rule_id: "AMB-MECHANISM-001"
    pattern: "action verb without method"
    triggers: ["share", "send", "export", "publish"]
    question_template: "How should '{action}' work? Options: {mechanism_options}"

  - rule_id: "AMB-PERMISSION-001"
    pattern: "sharing or access without permission level"
    triggers: ["share", "access", "view", "collaborate"]
    question_template: "What can recipients do? Options: view only, edit, full access"

  - rule_id: "AMB-LIFECYCLE-001"
    pattern: "action without duration"
    triggers: ["share", "grant", "allow", "enable"]
    question_template: "Is this permanent or can it be revoked?"
```

### Detection Output

```yaml
# Example: Notes App - Search Notes (S-003)
ambiguities_detected:
  - id: "AMB-S003-01"
    category: "scope"
    location: "action.search"
    text: "search my notes"
    question: "What fields should the search include?"
    options:
      - id: "A"
        label: "Title only"
        implications: "Fast, simple"
      - id: "B"
        label: "Title and content"
        implications: "More comprehensive, slightly slower"
      - id: "C"
        label: "Full-text search"
        implications: "Most thorough, requires FTS setup"
    default: "B"
    default_rationale: "Title and content covers most use cases"

  - id: "AMB-S003-02"
    category: "ui_ux"
    location: "implicit"
    text: "(not mentioned)"
    question: "Should search be instant (as-you-type) or require submit?"
    options:
      - id: "A"
        label: "Instant search"
        implications: "Better UX, more API calls"
      - id: "B"
        label: "Submit button"
        implications: "Simpler, fewer API calls"
    default: "A"
    default_rationale: "Instant search is modern UX expectation"
```

---

## Stage 3: Classification & Resolution

Determine which ambiguities can be auto-resolved vs need human input.

### Classification Criteria

```yaml
classification_criteria:
  decision_required:
    # ANY of these triggers human escalation
    - criterion: "affects_core_ux"
      description: "Changes how users fundamentally interact"
      examples: ["sharing mechanism", "navigation structure", "core workflow"]

    - criterion: "multiple_valid_approaches"
      description: "No clear industry standard, legitimate trade-offs"
      examples: ["permission model", "notification strategy"]

    - criterion: "hard_to_change_later"
      description: "Would require significant rework to change"
      examples: ["data model decisions", "API contracts", "auth model"]

    - criterion: "cost_implications"
      description: "Affects resources, pricing, or third-party services"
      examples: ["storage approach", "email service", "API limits"]

    - criterion: "security_or_privacy"
      description: "Affects data protection or user privacy"
      examples: ["default visibility", "data retention", "sharing scope"]

  auto_resolvable:
    # ALL of these must be true for auto-resolution
    - criterion: "industry_standard_exists"
      description: "Common convention that users expect"
      examples: ["email format validation", "password requirements", "date formats"]

    - criterion: "easy_to_change_later"
      description: "Can be modified without significant rework"
      examples: ["button labels", "color choices", "default sort order"]

    - criterion: "low_user_impact"
      description: "Users unlikely to notice or care"
      examples: ["internal naming", "log verbosity", "cache duration"]

    - criterion: "technical_detail"
      description: "Implementation choice, not product choice"
      examples: ["variable naming", "file structure", "HTTP methods"]
```

### Classification Output

```yaml
# Example: Notes App - Search Notes (S-003)
ambiguity_classifications:
  - ambiguity_id: "AMB-S003-01"
    classification: "decision_required"
    rationale: "Affects search functionality; user should decide scope"
    triggers: ["affects_core_ux"]
    escalation_priority: "medium"

  - ambiguity_id: "AMB-S003-02"
    classification: "auto_resolvable"
    rationale: "Instant search is modern standard; easy to change"
    resolution: "A"  # Instant search
    resolution_type: "accepted_default"
```

---

## Stage 4: Consistency Check

Verify the story against existing system state.

### Check Types

```yaml
consistency_checks:
  - check_id: "entity_exists"
    description: "Referenced entities exist in system state"
    action_on_fail: "flag_as_prerequisite"

  - check_id: "capability_exists"
    description: "Required capabilities are implemented"
    action_on_fail: "flag_as_prerequisite"

  - check_id: "no_conflicting_decisions"
    description: "Story doesn't contradict existing decisions"
    action_on_fail: "flag_as_conflict"

  - check_id: "role_permissions_valid"
    description: "Actor role can perform the action"
    action_on_fail: "flag_as_permission_issue"

  - check_id: "constraint_compliance"
    description: "Story doesn't violate active constraints"
    action_on_fail: "flag_as_constraint_violation"
```

### Check Output

```yaml
# Example: Notes App - Search Notes (S-003)
consistency_results:
  story_id: "S-003"
  timestamp: "2025-01-02T11:00:00Z"

  checks:
    - check: "entity_exists"
      target: "Note"
      result: "pass"
      entity_id: "E-002"

    - check: "capability_exists"
      target: "user_authentication"
      result: "pass"

    - check: "no_conflicting_decisions"
      result: "pass"
      checked_decisions: ["D-001"]

  summary:
    passed: 3
    failed: 0
    prerequisites_needed: []
    conflicts_found: []
```

---

## Stage 5: Prerequisite Detection

Identify capabilities or entities that must exist before this story can be implemented.

### Detection Logic

```yaml
prerequisite_detection:
  # Pattern-based detection
  patterns:
    - pattern: "share with specific users"
      requires: ["user_lookup_capability", "user_list_or_search"]

    - pattern: "share via link"
      requires: ["share_link_entity", "unique_link_generation"]

    - pattern: "revoke sharing"
      requires: ["share_record_entity", "share_management_ui"]

    - pattern: "view shared content"
      requires: ["shared_content_view", "permission_check_capability"]

  # Implicit prerequisites
  implicit:
    - trigger: "any user action"
      requires: ["user_authentication"]

    - trigger: "data persistence"
      requires: ["database_entity"]

    - trigger: "user notification"
      requires: ["notification_capability"]
```

### Prerequisite Output

```yaml
# Example: Notes App - Search Notes (S-003)
prerequisites_detected:
  story_id: "S-003"

  required_entities: []  # Note entity already exists

  required_capabilities:
    - capability: "text_search"
      reason: "Need to search Note content"
      status: "not_exists"
      action: "include_in_story"  # Part of this story

  existing_dependencies:
    - entity_id: "E-002"
      name: "Note"
      status: "implemented"

  generated_prerequisite_stories: []  # No prerequisites needed
```

---

## Stage 6: Output Generation

Produce the Interpreted Story artifact.

### Interpreted Story Schema

```yaml
# Example: Notes App - Search Notes (S-003)
# Stored as property of story in state.json
interpretation:
  story_id: "S-003"
  interpreted_at: "2025-01-02T11:30:00Z"

  # Original story
  original:
    title: "Search Notes"
    user_story: "As a user, I want to search my notes so that I can quickly find what I need"
    acceptance_criteria:
      - "Given I have notes, when I search by keyword, then matching notes are displayed"
    priority: "P0"

  # Parsed components
  parsed:
    actor: "registered_user"
    action: "search"
    object: "Note"
    outcome: "find matching notes"

  # Ambiguities
  ambiguities:
    - id: "AMB-S003-01"
      question: "What fields should the search include?"
      classification: "decision_required"
      options: ["Title only", "Title and content", "Full-text search"]
      default: "Title and content"
      resolved: false

    - id: "AMB-S003-02"
      question: "Instant search or submit button?"
      classification: "auto_resolvable"
      resolution: "Instant search"
      resolved: true

  # Prerequisites
  prerequisites: []

  # Assumptions
  assumptions:
    - "User must be logged in to search their notes"
    - "Search is case-insensitive"

  # Status
  status: "blocked"  # Awaiting user decision on AMB-S003-01
```

---

## User Escalation Interface

When ambiguities require user input:

### Question Presentation

```markdown
## Questions About: Search Notes (S-003)

I'm interpreting your story about searching notes and need a decision from you.

---

### Question: What fields should the search include?

Your story says users can "search my notes" — I need to know the search scope.

**Option A: Title only**
- Fastest performance
- Simple to implement
- Best for: quick lookups when you remember the title

**Option B: Title and content** (Recommended)
- Searches both title and note body
- Good balance of coverage and performance
- Best for: most use cases

**Option C: Full-text search**
- Most comprehensive search
- Requires SQLite FTS5 setup
- Best for: large note collections

**My recommendation:** Option B covers most use cases without complexity.

---

**Please select your choice:**
- [ ] A / [ ] B / [ ] C
```

---

## Agent Design

### Story Interpretation Agent

```python
class StoryInterpretationEngine:
    """Interprets user stories into explicit specifications."""

    def __init__(self, system_state: SystemState):
        self.state = system_state
        self.parser = StoryParser()
        self.ambiguity_detector = AmbiguityDetector()
        self.classifier = AmbiguityClassifier()
        self.consistency_checker = ConsistencyChecker(system_state)
        self.prerequisite_detector = PrerequisiteDetector(system_state)

    def interpret(self, story: Story) -> InterpretedStory:
        """Main interpretation pipeline."""

        # Stage 1: Parse
        parsed = self.parser.parse(story)

        # Stage 2: Detect ambiguities
        ambiguities = self.ambiguity_detector.detect(parsed, story.acceptance_criteria)

        # Stage 3: Classify and resolve
        classified = self.classifier.classify(ambiguities)
        resolved, pending = self._split_by_resolution(classified)

        # Stage 4: Consistency check
        consistency = self.consistency_checker.check(parsed, self.state)

        # Stage 5: Prerequisite detection
        prerequisites = self.prerequisite_detector.detect(parsed, resolved)

        # Stage 6: Generate output
        interpreted = InterpretedStory(
            original=story,
            parsed=parsed,
            resolved_ambiguities=resolved,
            pending_ambiguities=pending,
            consistency=consistency,
            prerequisites=prerequisites,
            assumptions=self._collect_assumptions(parsed, resolved),
            status="blocked" if pending else "ready"
        )

        return interpreted

    def apply_user_decisions(
        self,
        interpreted: InterpretedStory,
        decisions: Dict[str, str]
    ) -> InterpretedStory:
        """Apply user decisions to pending ambiguities."""

        for ambiguity_id, choice in decisions.items():
            ambiguity = interpreted.get_pending_ambiguity(ambiguity_id)
            ambiguity.resolve(choice, resolved_by="user")
            interpreted.move_to_resolved(ambiguity)

        # Re-check prerequisites with new decisions
        interpreted.prerequisites = self.prerequisite_detector.detect(
            interpreted.parsed,
            interpreted.resolved_ambiguities
        )

        # Update status
        if not interpreted.pending_ambiguities:
            interpreted.status = "ready"

        return interpreted
```

---

## Consequences

### Positive

1. **Explicit Ambiguities**: Nothing is silently assumed
2. **User Control**: Important decisions surface to user
3. **Consistency**: Verified against existing system before proceeding
4. **Traceability**: Every assumption is documented
5. **Prerequisites Found**: Dependencies identified early

### Negative

1. **Increased Latency**: User decisions block progress
2. **Question Fatigue**: Too many questions may overwhelm user
3. **Over-Analysis**: May surface trivial ambiguities

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Too many questions | Medium | Medium | Aggressive auto-resolution for low-impact items |
| Wrong classification | Low | High | Conservative: when in doubt, ask user |
| Missing ambiguities | Medium | Medium | Iterative refinement of detection rules |
| Prerequisite explosion | Low | Medium | Batch related prerequisites together |

---

## Resolved Questions (POC)

1. **Question Batching**: ~~All questions at once or one story at a time?~~ → **One story at a time.** Per master ADR "no batching". Sequential processing.

2. **Learning from Decisions**: ~~Learn to auto-resolve similar ambiguities?~~ → **No.** Each run is independent. No learning/persistence across sessions.

3. **Ambiguity Confidence**: ~~Should ambiguities have confidence scores?~~ → **No.** Binary classification only: `decision_required` or `auto_resolvable`.

4. **Partial Interpretation**: ~~Proceed with some ambiguities pending?~~ → **No.** All `decision_required` ambiguities must be resolved before proceeding. Block until resolved.

---

## Future Enhancements

- Batch presentation of all questions across stories
- Learning from user decisions to auto-resolve similar ambiguities
- Confidence scores for ambiguity classification
- Partial interpretation with parallel resolution
- Natural language parsing improvements

---

## Next Steps

Upon approval:

1. Implement story parser with grammar rules
2. Build ambiguity detection rule engine
3. Create classification criteria evaluator
4. Implement consistency checker against system state
5. Design user question interface
6. Proceed to ADR-001e (System Design Evolution)

---

## Related Documents

- [ADR-001: Story-to-Implementation Pipeline](./ADR-001-story-to-implementation-pipeline.md) (parent)
- [ADR-001a: MVP Spec Enhancement](./ADR-001a-mvp-spec-enhancement.md) (input format)
- [ADR-001c: System State Model](./ADR-001c-system-state-model.md) (state queries)
- [ADR-001e: System Design Evolution](./ADR-001e-system-design-evolution.md) (next stage)
