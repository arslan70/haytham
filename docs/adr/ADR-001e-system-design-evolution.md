# ADR-001e: System Design Evolution

**Status**: Proposed
**Date**: 2025-01-02
**Parent**: [ADR-001: Story-to-Implementation Pipeline](./ADR-001-story-to-implementation-pipeline.md)
**Depends On**:
- [ADR-001c: System State Model](./ADR-001c-system-state-model.md)
- [ADR-001d: Story Interpretation Engine](./ADR-001d-story-interpretation-engine.md)
**Scope**: Mapping interpreted stories to system state changes while maintaining coherence

---

## POC Simplifications

- **Retroactive Coherence**: Deferred. If interpretation is wrong, user manually triggers re-interpretation
- **Conflict Detection**: Simple check against existing state; no elaborate revision plans
- **Prerequisite Stories**: Generate and add to queue; require user approval (max 3 per story)
- **ID Scheme**: Uses S-XXX (stories), E-XXX (entities), D-XXX (decisions)
- **Test Case**: Notes App — simple stories with minimal conflicts
- **Entity Creation**: Entities are registered in state.json with status `"planned"` during Design Evolution. Task Generation then creates implementation tasks for planned entities.

**Example for Notes App:**
```
Story S-001 (Create Note) design evolution:
1. Entity E-002 (Note) needed but doesn't exist
2. Register E-002 in state.json with status: "planned"
3. Decision: D-001 - Use SQLite for storage
4. Task Generation will create: "T-001: Create Note model"
```

---

## Context

After a story is interpreted (Chunk 3), we know *what* the user wants. Now we must determine *how* this affects the system:

- What new entities, capabilities, or components are needed?
- Do these changes conflict with existing design decisions?
- Should earlier decisions be revised in light of new information?
- What architectural decisions must be made?

This stage is where **global coherence** is maintained or recovered. Without it:
- Each story is implemented in isolation
- Implicit conflicts accumulate
- System architecture drifts into incoherence
- Technical debt compounds silently

### The Design Evolution Problem

Consider a system that has implemented "User Authentication" (email/password). A new story arrives: "As a user, I want to log in with my Google account."

This story doesn't just add a feature — it potentially:
- Changes the User entity (needs `google_id` field)
- Changes the auth capability (new OAuth flow)
- May conflict with decisions made (e.g., "passwords are the only auth method")
- May require revisiting the session/token approach

The Design Evolution stage must detect these implications and handle them systematically.

---

## Decision

Implement a **System Design Evolution Engine** that:

1. Maps interpreted stories to system state changes
2. Detects conflicts with existing decisions
3. Proposes architectural decisions when needed
4. Handles retroactive coherence when conflicts arise
5. Generates prerequisite stories for discovered dependencies
6. Updates system state with full provenance tracking

---

## Design Evolution Pipeline

### Overview

```
┌─────────────────────┐
│  Interpreted Story  │
│   (from Chunk 3)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│                    IMPACT ANALYSIS                           │
│  Determine what system changes this story requires           │
└──────────┬──────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│                  CONFLICT DETECTION                          │
│  Check proposed changes against existing decisions           │
└──────────┬──────────────────────────────────────────────────┘
           │
           ├─── No conflicts ───────────────────┐
           │                                    │
           ▼                                    │
┌─────────────────────────────────────────┐    │
│         CONFLICT RESOLUTION             │    │
│  Determine: adapt, override, or revise  │    │
│                                         │    │
│  ┌───────────────────────────────────┐  │    │
│  │ HUMAN APPROVAL: Significant       │  │    │
│  │ architectural changes             │  │    │
│  └───────────────────────────────────┘  │    │
└──────────┬──────────────────────────────┘    │
           │                                    │
           ▼                                    │
┌─────────────────────────────────────────────────────────────┐
│                 DECISION GENERATION                          │
│  Create new decisions for unresolved architectural questions │
└──────────┬──────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│               PREREQUISITE GENERATION                        │
│  Create stories for required capabilities not yet planned    │
└──────────┬──────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│                 STATE UPDATE PROPOSAL                        │
│  Generate proposed changes to system state                   │
└──────────┬──────────────────────────────────────────────────┘
           │
           ├─── Minor changes (auto-apply) ────────┐
           │                                        │
           ▼                                        ▼
┌─────────────────────────────────┐    ┌─────────────────────┐
│     HUMAN APPROVAL REQUIRED     │    │   AUTO-APPLIED      │
│  Significant architectural      │    │   Update state      │
│  changes need confirmation      │    │   Continue to       │
│                                 │    │   Task Generation   │
└─────────────────────────────────┘    └─────────────────────┘
```

---

## Stage 1: Impact Analysis

Determine what system changes the story requires.

### Change Types

| Change Type | Description | Example |
|-------------|-------------|---------|
| **New Entity** | Story requires data structure not in system | "ShareLink" for sharing feature |
| **Entity Modification** | Story requires changes to existing entity | Add `google_id` to User |
| **New Capability** | Story requires new system functionality | "OAuth authentication" |
| **Capability Extension** | Story extends existing capability | Add "revoke" to sharing capability |
| **New Decision** | Story requires architectural choice | "Use OAuth 2.0 vs OpenID Connect" |
| **New Integration** | Story requires external system | "Google OAuth API" |
| **Constraint Change** | Story affects system constraints | "Now supports multi-tenant" |

### Impact Analysis Output

```yaml
# Example: Notes App - Search Notes (S-003)
impact_analysis:
  story_id: "S-003"
  analysis_timestamp: "2025-01-02T12:00:00Z"

  # Proposed changes
  proposed_changes:
    new_entities: []  # No new entities needed

    entity_modifications: []  # Note entity unchanged

    new_capabilities:
      - name: "Note Search"
        description: "Users can search notes by title and content"
        provides:
          - "Search notes by keyword"
          - "Return matching notes sorted by relevance"
        components:
          - type: "api_endpoint"
            path: "/api/notes/search"
            method: "GET"
            description: "Search notes"

    new_decisions_needed:
      - decision_topic: "search_implementation"
        question: "How should search be implemented?"
        options:
          - id: "A"
            choice: "SQLite LIKE queries"
            implications: "Simple, works for small datasets"
          - id: "B"
            choice: "SQLite FTS5"
            implications: "Better performance, relevance ranking"
        recommendation: "A"
        recommendation_rationale: "LIKE is sufficient for MVP"
        classification: "auto_resolvable"

  # Summary
  summary:
    new_entities: 0
    new_capabilities: 1
    new_decisions: 1
    conflicts_detected: 0
```

---

## Stage 2: Conflict Detection

Check proposed changes against existing decisions and state.

### Conflict Types

| Conflict Type | Description | Resolution Options |
|---------------|-------------|-------------------|
| **Decision Contradiction** | New requirement contradicts existing decision | Adapt, override, or revise |
| **Entity Incompatibility** | Proposed entity change breaks existing features | Migrate or redesign |
| **Capability Overlap** | New capability duplicates existing one | Merge or differentiate |
| **Constraint Violation** | Change violates active constraint | Request constraint change |
| **Dependency Conflict** | Circular or impossible dependencies | Restructure |

### Conflict Detection Rules

```yaml
conflict_detection_rules:
  - rule_id: "CONF-DEC-001"
    name: "Decision Contradiction"
    check: |
      For each new decision/choice, check if it contradicts
      any existing decision in decisions/*.yaml
    example:
      existing: "D-001: Use JWT for authentication"
      proposed: "Use server-side sessions for share link tracking"
      conflict: "Session state contradicts stateless JWT approach"

  - rule_id: "CONF-ENT-001"
    name: "Breaking Entity Change"
    check: |
      For each entity modification, check if any existing
      capability depends on the changed aspect
    example:
      existing: "User.email is used for login"
      proposed: "Remove User.email, use User.username instead"
      conflict: "Login capability depends on email field"

  - rule_id: "CONF-CAP-001"
    name: "Capability Duplication"
    check: |
      For each new capability, check if similar functionality
      exists in another capability
    example:
      existing: "CAP-002: File Sharing (shares files via links)"
      proposed: "CAP-003: Content Sharing (shares content via links)"
      conflict: "Potential duplication - should these be merged?"

  - rule_id: "CONF-CON-001"
    name: "Constraint Violation"
    check: |
      For each proposed change, verify it doesn't violate
      any active constraint in constraints.yaml
    example:
      constraint: "C-001: No external API dependencies"
      proposed: "Integrate with Google OAuth"
      conflict: "OAuth requires external API calls"
```

### Conflict Detection Output

```yaml
# Example: Notes App - Search Notes (S-003) - No conflicts
conflict_detection:
  story_id: "S-003"
  timestamp: "2025-01-02T14:00:00Z"

  conflicts_found: []

  requires_human_approval: false
  blocking: false
```

**Note**: For POC, conflict detection is a simple check against existing state. Most Notes App stories won't have conflicts since they're straightforward CRUD operations.

---

## Stage 3: Conflict Resolution

Handle detected conflicts through adaptation, override, or revision.

### Resolution Strategies

```yaml
resolution_strategies:
  adapt:
    description: "Modify the proposed change to work within existing decisions"
    when_to_use:
      - "Conflict is minor"
      - "Adaptation is straightforward"
      - "Doesn't compromise the story's intent"
    human_approval: "Only if adaptation is non-obvious"
    example: "Use temporary state for OAuth while keeping JWT sessions"

  override:
    description: "Accept the conflict as a known exception"
    when_to_use:
      - "New story is higher priority"
      - "Conflict is acceptable trade-off"
      - "Documenting exception is sufficient"
    human_approval: "Always required"
    example: "Accept that OAuth adds external dependency"

  revise:
    description: "Update earlier decision(s) to accommodate new requirement"
    when_to_use:
      - "Original decision was wrong or incomplete"
      - "New information changes the calculus"
      - "Multiple stories would benefit from revision"
    human_approval: "Always required"
    triggers: "Retroactive coherence process"
    example: "Change from 'pure stateless' to 'stateless with exceptions'"
```

### Retroactive Coherence Process

When a revision is chosen:

```yaml
retroactive_coherence:
  trigger:
    story_id: "F-010"
    conflict_id: "CONF-F010-01"
    resolution: "revise"
    decision_to_revise: "D-001"

  analysis:
    original_decision:
      id: "D-001"
      title: "Use JWT for stateless authentication"
      made_for_story: "F-001"
      rationale: "Stateless for scalability"

    new_understanding: |
      Pure stateless is too restrictive. Some features (OAuth,
      certain security flows) benefit from brief stateful windows.

    proposed_revision:
      new_title: "Use JWT for authentication with stateful exceptions"
      new_rationale: |
        JWT for session tokens (stateless), but allow temporary
        server-side state for specific flows (OAuth, password reset).

  impact_assessment:
    stories_affected:
      - story_id: "F-001"
        impact: "None - JWT sessions unchanged"
        action: "No reprocessing needed"

      - story_id: "F-005"
        impact: "Password reset could now use stateful tokens"
        action: "Optional enhancement, no reprocessing needed"

    entities_affected: []

    capabilities_affected:
      - capability_id: "CAP-001"
        impact: "Documentation update only"
        action: "Update capability description"

    code_affected:
      - file: "src/services/auth_service.py"
        impact: "None - implementation already supports this"
        action: "No code changes needed"

  execution_plan:
    - step: 1
      action: "Create snapshot before revision"
      status: "pending"

    - step: 2
      action: "Update decision D-001 with new title and rationale"
      status: "pending"

    - step: 3
      action: "Update capability CAP-001 documentation"
      status: "pending"

    - step: 4
      action: "Mark F-010 conflict as resolved"
      status: "pending"

    - step: 5
      action: "Continue F-010 processing"
      status: "pending"

  approval_required: true
  approval_reason: "Revising architectural decision D-001"
```

---

## Stage 4: Decision Generation

Create new decisions for unresolved architectural questions.

### Decision Template

```yaml
# Example: Notes App - Search implementation decision
# Stored in state.json decisions array
decision:
  id: "D-002"
  title: "Use SQLite LIKE for search"
  made_at: "2025-01-02T12:30:00Z"
  rationale: "LIKE queries are sufficient for MVP scale"
  affects: ["S-003"]
```

---

## Stage 5: Prerequisite Generation

Generate stories for required capabilities not yet planned.

### Prerequisite Detection

```yaml
# Example: Notes App - Search Notes (S-003)
# Most simple stories don't need prerequisites
prerequisite_detection:
  story_id: "S-003"

  requirements:
    entities_needed:
      - name: "Note"
        status: "exists"  # Already implemented in S-001

  generated_prerequisites: []  # No prerequisites needed
```

**Note**: For POC, prerequisite generation is simple. If a prerequisite is needed, it's added to the stories array in state.json and requires user approval.

---

## Stage 6: State Update Proposal

Generate proposed changes to system state.

### Update Proposal Schema

```yaml
# Example: Notes App - Search Notes (S-003)
# For POC, updates are applied directly to state.json
state_update:
  story_id: "S-003"

  changes:
    - update story S-003 status to "designed"
    - add decision D-002 (Use SQLite LIKE for search)

  approval:
    required: true
    reason: "New capability requires confirmation"
```

**Note**: For POC, state updates are simple. The state.json file is updated directly after user approval.

---

## User Approval Interface

### Approval Presentation

```markdown
## Design Review: Search Notes (S-003)

I've analyzed how to implement the search feature.

---

### New Capability: Note Search

This adds a search endpoint:
- GET /api/notes/search?q=keyword
- Searches title and content
- Returns matching notes

### Design Decision: Search Implementation

I'll use **SQLite LIKE queries** for search.

**Why:** Simple and sufficient for MVP. Can upgrade to FTS5 later if needed.

---

## Approval Required

**Please confirm:**
- [ ] Add search capability with LIKE queries

[Approve] [Request Changes]
```

---

## Agent Design

```python
class SystemDesignEvolutionEngine:
    """Maps interpreted stories to system state changes."""

    def __init__(self, system_state: SystemState):
        self.state = system_state
        self.impact_analyzer = ImpactAnalyzer(system_state)
        self.conflict_detector = ConflictDetector(system_state)
        self.decision_generator = DecisionGenerator()
        self.prerequisite_generator = PrerequisiteGenerator(system_state)

    def evolve(self, interpreted_story: InterpretedStory) -> DesignEvolutionResult:
        """Main design evolution pipeline."""

        # Stage 1: Impact analysis
        impact = self.impact_analyzer.analyze(interpreted_story)

        # Stage 2: Conflict detection
        conflicts = self.conflict_detector.detect(impact)

        # Stage 3: Conflict resolution (may require human input)
        if conflicts:
            resolutions = self._resolve_conflicts(conflicts)
            if resolutions.requires_human_approval:
                return DesignEvolutionResult(
                    status="blocked_on_conflicts",
                    conflicts=conflicts,
                    proposed_resolutions=resolutions
                )

        # Stage 4: Decision generation
        new_decisions = self.decision_generator.generate(
            interpreted_story,
            impact
        )

        # Stage 5: Prerequisite generation
        prerequisites = self.prerequisite_generator.generate(
            interpreted_story,
            impact
        )

        # Stage 6: State update proposal
        proposal = self._create_update_proposal(
            interpreted_story,
            impact,
            new_decisions,
            prerequisites
        )

        return DesignEvolutionResult(
            status="ready_for_approval" if proposal.requires_approval else "auto_approved",
            impact=impact,
            decisions=new_decisions,
            prerequisites=prerequisites,
            proposal=proposal
        )

    def apply_proposal(
        self,
        proposal: StateUpdateProposal,
        approval: Approval
    ) -> SystemState:
        """Apply approved proposal to system state."""

        # Create snapshot before changes
        self.state.create_snapshot(f"pre-{proposal.story_id}")

        # Apply changes
        for change in proposal.changes:
            self._apply_change(change)

        # Update story status
        self.state.update_story_status(
            proposal.story_id,
            status="designed",
            design_details=proposal.summary
        )

        # Add prerequisite stories to queue
        for prereq in proposal.prerequisites:
            self.state.add_story(prereq, status="pending")

        # Increment version and update checksums
        self.state.increment_version()

        return self.state
```

---

## Consequences

### Positive

1. **Global Coherence**: Changes are checked against entire system state
2. **Conflict Prevention**: Issues caught before implementation
3. **Retroactive Coherence**: Can revise earlier decisions systematically
4. **Full Traceability**: Every design choice is documented
5. **Prerequisite Discovery**: Dependencies found and tracked

### Negative

1. **Complexity**: Many interacting components
2. **Approval Overhead**: Significant changes require human review
3. **Potential Bottleneck**: Conflicts can block progress

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Missed conflicts | Low | High | Conservative detection rules |
| Revision cascade | Low | High | Limit revision scope, require approval |
| Over-generation of prerequisites | Medium | Medium | Only generate for true blockers |

---

## Resolved Questions (POC)

1. **Revision Depth Limit**: ~~How many levels of retroactive revision?~~ → **Zero.** Retroactive coherence is deferred per master ADR. If design is wrong, user manually re-interprets.

2. **Parallel Story Processing**: ~~Handle conflicting state updates?~~ → **N/A.** Sequential processing only per master ADR. No parallel stories.

3. **Speculative Design**: ~~Pre-analyze future stories?~~ → **No.** Process stories one at a time. No look-ahead.

---

## Future Enhancements

- Retroactive coherence with revision cascades
- Parallel story processing with conflict resolution
- Speculative design analysis for upcoming stories
- Automated conflict resolution strategies
- Design pattern recognition and suggestions

---

## Next Steps

Upon approval:

1. Implement impact analyzer
2. Build conflict detection engine
3. Create decision generator
4. Implement retroactive coherence mechanism
5. Design approval interface
6. Proceed to ADR-001f (Task Generation & Refinement)

---

## Related Documents

- [ADR-001: Story-to-Implementation Pipeline](./ADR-001-story-to-implementation-pipeline.md) (parent)
- [ADR-001c: System State Model](./ADR-001c-system-state-model.md) (state structure)
- [ADR-001d: Story Interpretation Engine](./ADR-001d-story-interpretation-engine.md) (input)
- [ADR-001f: Task Generation & Refinement](./ADR-001f-task-generation-refinement.md) (next stage)
