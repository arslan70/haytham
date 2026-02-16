"""Burr Actions for Workflow 2: Technical Translation.

These actions implement the 5 stages of the architect workflow as defined in ADR-005.
Each action reads from VectorDB and/or Backlog.md, processes the architecture diff,
and writes back to the state stores.

The stages are:
1. architecture_decisions: Define key technical decisions (DEC-*)
2. component_boundaries: Define component structure and entities (ENT-*)
3. story_generation: Generate stories with implements:CAP-* labels
4. story_validation: Validate all stories have proper traceability
5. dependency_ordering: Order stories by dependencies
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from burr.core import State, action

from haytham.phases.workflow_2.diff import ArchitectureDiff
from haytham.state.schema import create_decision, create_entity

logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions
# =============================================================================


def load_prompt(prompt_name: str) -> str:
    """Load a prompt template from the prompts directory.

    Args:
        prompt_name: Name of the prompt file (without .txt extension)

    Returns:
        Prompt text content
    """
    # Look in workflow_2 prompts directory
    prompts_dir = Path(__file__).parent / "prompts"
    prompt_file = prompts_dir / f"{prompt_name}.txt"

    if prompt_file.exists():
        return prompt_file.read_text()

    # Fallback: return a placeholder
    logger.warning(f"Prompt file not found: {prompt_file}")
    return f"[Placeholder prompt for {prompt_name}]"


def run_architect_agent(
    agent_name: str,
    prompt_template: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Execute an architect agent with the given context.

    Args:
        agent_name: Name of the agent (for logging)
        prompt_template: The prompt template to use
        context: Context to inject into the prompt

    Returns:
        Dict with output and metadata
    """
    import time

    from strands import Agent

    start_time = time.time()

    try:
        # Build the full prompt with context
        full_prompt = prompt_template

        # Replace context placeholders
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"  # {{key}}
            if placeholder in full_prompt:
                if isinstance(value, (dict, list)):
                    full_prompt = full_prompt.replace(placeholder, json.dumps(value, indent=2))
                else:
                    full_prompt = full_prompt.replace(placeholder, str(value))

        # Use the Bedrock model with strands Agent
        from haytham.agents.utils.model_provider import create_model

        # Create model with higher max_tokens to avoid MaxTokensReachedException
        model = create_model(max_tokens=8000)

        # Create a simple agent and run the prompt through it
        agent = Agent(
            model=model,
            system_prompt="You are an expert software architect. Follow the instructions precisely and output valid JSON when requested.",
        )

        # Call the agent
        result = agent(full_prompt)
        output_text = str(result)

        execution_time = time.time() - start_time

        return {
            "output": output_text,
            "status": "completed",
            "execution_time": execution_time,
        }

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Agent {agent_name} failed: {e}", exc_info=True)

        return {
            "output": f"Error: {str(e)}",
            "status": "failed",
            "error": str(e),
            "execution_time": execution_time,
        }


def extract_json_from_response(text: str) -> dict | None:
    """Extract JSON from agent response.

    Handles responses that include JSON in markdown code blocks.
    Also handles common LLM output issues like backtick template literals.

    Args:
        text: Raw agent response text

    Returns:
        Parsed JSON dict, or None if not found
    """

    def fix_backtick_strings(json_str: str) -> str:
        """Replace backtick template literals with proper JSON strings."""

        # Match backtick strings (including multiline)
        def replace_backtick(match):
            content = match.group(1)
            # Escape special characters for JSON string
            content = content.replace("\\", "\\\\")
            content = content.replace('"', '\\"')
            content = content.replace("\n", "\\n")
            content = content.replace("\r", "\\r")
            content = content.replace("\t", "\\t")
            return f'"{content}"'

        # Match backtick strings (non-greedy, multiline)
        return re.sub(r"`([\s\S]*?)`", replace_backtick, json_str)

    def try_parse(json_str: str) -> dict | None:
        """Try to parse JSON, with fallbacks for common issues."""
        # First try direct parse
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # Try fixing backtick template literals (LLM sometimes uses JS syntax)
        fixed = fix_backtick_strings(json_str)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        # Try removing trailing commas before ] or }
        fixed = re.sub(r",\s*([}\]])", r"\1", fixed)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        return None

    # Try to find JSON in code blocks
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if json_match:
        result = try_parse(json_match.group(1))
        if result:
            return result

    # Try the whole text as JSON
    result = try_parse(text)
    if result:
        return result

    # Try to find JSON object anywhere in the text
    obj_match = re.search(r"\{[\s\S]*\}", text)
    if obj_match:
        result = try_parse(obj_match.group(0))
        if result:
            return result

    return None


def store_decisions_in_vectordb(
    decisions: list[dict],
    session_manager: Any,
    source_stage: str = "architecture_decisions",
) -> list[str]:
    """Store decisions in VectorDB.

    Args:
        decisions: List of decision dicts with name, description, rationale, serves_capabilities
        session_manager: SessionManager instance
        source_stage: Name of the source stage

    Returns:
        List of created decision IDs
    """
    from haytham.state.vector_db import SystemStateDB

    db_path = session_manager.session_dir / "vector_db"
    db = SystemStateDB(str(db_path))

    created_ids = []

    for dec_data in decisions:
        try:
            decision = create_decision(
                name=dec_data.get("name", "Unnamed Decision"),
                description=dec_data.get("description", ""),
                rationale=dec_data.get("rationale", ""),
                source_stage=source_stage,
                affects=dec_data.get("affects", []),
                alternatives_considered=dec_data.get("alternatives_considered", []),
                serves_capabilities=dec_data.get("serves_capabilities", []),
            )

            entry_id = db.add_entry(decision)
            created_ids.append(entry_id)
            logger.info(f"Created decision: {entry_id} - {decision.name}")

        except Exception as e:
            logger.error(f"Failed to store decision: {e}")

    return created_ids


def store_entities_in_vectordb(
    entities: list[dict],
    session_manager: Any,
    source_stage: str = "component_boundaries",
) -> list[str]:
    """Store entities in VectorDB.

    Args:
        entities: List of entity dicts with name, description, attributes, relationships
        session_manager: SessionManager instance
        source_stage: Name of the source stage

    Returns:
        List of created entity IDs
    """
    from haytham.state.vector_db import SystemStateDB

    db_path = session_manager.session_dir / "vector_db"
    db = SystemStateDB(str(db_path))

    created_ids = []

    for ent_data in entities:
        try:
            entity = create_entity(
                name=ent_data.get("name", "Unnamed Entity"),
                description=ent_data.get("description", ""),
                attributes=ent_data.get("attributes", []),
                relationships=ent_data.get("relationships", []),
                source_stage=source_stage,
            )

            entry_id = db.add_entry(entity)
            created_ids.append(entry_id)
            logger.info(f"Created entity: {entry_id} - {entity.name}")

        except Exception as e:
            logger.error(f"Failed to store entity: {e}")

    return created_ids


# =============================================================================
# Stage 1: Architecture Decisions
# =============================================================================

ARCHITECTURE_DECISIONS_PROMPT = """You are a Software Architect creating technical decisions for an MVP.

## Context

**System Goal:** {{system_goal}}

**MVP Scope:**
{{mvp_scope}}

**Capability Model (ALL capabilities that need architectural support):**
{{capabilities}}

**Build vs Buy Recommendations (services to use):**
{{build_buy_analysis}}

**Existing Decisions (if any):**
{{existing_decisions}}

## WHAT IS AN ARCHITECTURE DECISION?

Architecture decisions (DEC-*) specify HOW to implement the system using the recommended stack.
They bridge the gap between "what services to use" (Build/Buy) and "how to build features" (Stories).

**Decision Categories to Consider:**

1. **Authentication & Identity (DEC-AUTH-*)**
   - Auth method (email/password, social, magic link)
   - Session management
   - Anonymous handle generation (if applicable)

2. **Data Model & Schema (DEC-DB-*)**
   - Core tables/collections
   - Key constraints and indexes
   - Data integrity rules (e.g., prevent duplicates)

3. **Hosting & Deployment (DEC-DEPLOY-*)**
   - Frontend hosting strategy
   - API/backend deployment
   - Environment configuration

4. **Notifications & Email (DEC-NOTIFY-*)** (if email service recommended)
   - Email triggers and templates
   - Push notification strategy
   - Scheduled jobs/cron

5. **Real-Time & Sync (DEC-REALTIME-*)** (if real-time features needed)
   - Real-time update strategy
   - Subscription patterns
   - Fallback for offline

6. **Data Integrity & Validation (DEC-INTEGRITY-*)**
   - Input validation rules
   - Duplicate prevention constraints
   - Consistency guarantees

## CAPABILITY COVERAGE RULES

Your decisions MUST cover ALL capabilities from the Capability Model.

**Functional Capabilities (CAP-F-*):**
- Each CAP-F-* must appear in at least one decision's serves_capabilities
- These enable user-facing features

**Non-Functional Capabilities (CAP-NF-*):**
- CAP-NF-* capabilities often need DEDICATED decisions
- Data integrity, performance, usability requirements need explicit architectural support
- Do NOT ignore non-functional capabilities

## BUILD/BUY INTEGRATION

For each BUY recommendation in the Build vs Buy analysis, create decisions that specify:
- HOW to integrate the service
- WHAT features of the service to use
- HOW it serves specific capabilities

Example:
- Build/Buy: "Supabase for Database + Auth"
- Decision: "DEC-AUTH-001: Use Supabase Auth with email/password, generate random anonymous handles at registration, serves CAP-F-001, CAP-F-003"

## DECISION COUNT GUIDANCE

- Minimum: One decision per applicable category
- Target: 4-6 decisions for a typical MVP
- Maximum: One decision should not serve more than 4 capabilities (split if broader)

Do NOT artificially limit to 1-3 decisions if more are needed for complete coverage.

## OUTPUT FORMAT

Output valid JSON:

```json
{
  "decisions": [
    {
      "id": "DEC-AUTH-001",
      "name": "Authentication Strategy",
      "description": "What this decision entails - be specific about implementation",
      "rationale": "Why this is the right choice for THIS MVP given appetite and constraints",
      "serves_capabilities": ["CAP-F-001", "CAP-NF-002"],
      "implements_recommendation": "Which Build/Buy recommendation this implements (e.g., Supabase Auth)",
      "alternatives_considered": ["Alternative 1 - why not chosen", "Alternative 2 - why not chosen"]
    }
  ],
  "coverage_check": {
    "functional_capabilities_covered": ["CAP-F-001", "CAP-F-002"],
    "non_functional_capabilities_covered": ["CAP-NF-001"],
    "uncovered_capabilities": []
  },
  "summary": "Brief summary of architectural approach"
}
```

## SELF-CHECK (Required)

Before outputting, verify:
- [ ] Every CAP-F-* from the Capability Model is in at least one decision's serves_capabilities?
- [ ] Every CAP-NF-* from the Capability Model has architectural support?
- [ ] Every BUY recommendation from Build/Buy has a corresponding decision?
- [ ] No decision serves more than 4 capabilities (too broad = split it)?
- [ ] coverage_check.uncovered_capabilities is empty?
- [ ] Each decision has a specific implements_recommendation linking to Build/Buy?

If any check fails, ADD MORE DECISIONS until all capabilities are covered.

## MVP CONSTRAINTS

Remember this is an MVP with limited appetite:
- Prefer simple solutions over perfect solutions
- Use managed services (the BUY recommendations) over custom infrastructure
- One way to do things, not configurable options
- Ship fast, iterate later

Output ONLY valid JSON."""


@action(
    reads=[
        "system_goal",
        "mvp_scope",
        "capabilities",
        "existing_decisions",
        "architecture_diff",
        "diff_context",
        "session_manager",
    ],
    writes=[
        "architecture_decisions_status",
        "architecture_decisions_output",
        "new_decisions",
        "current_stage",
    ],
)
def architecture_decisions(state: State) -> tuple[dict, State]:
    """Stage 1: Define key architecture decisions (DEC-*).

    This stage:
    1. Reads the architecture diff to understand what needs decisions
    2. Generates decisions that serve uncovered capabilities
    3. Stores decisions in VectorDB with serves_capabilities metadata
    """
    logger.info("=" * 60)
    logger.info("STAGE 1: ARCHITECTURE DECISIONS")
    logger.info("=" * 60)

    # Get context from state
    system_goal = state.get("system_goal", "")
    mvp_scope = state.get("mvp_scope", "")
    capabilities = state.get("capabilities", [])
    existing_decisions = state.get("existing_decisions", [])
    diff: ArchitectureDiff = state.get("architecture_diff")
    diff_context = state.get("diff_context", "")
    session_manager = state.get("session_manager")

    # Check if there are uncovered capabilities
    if not diff or not diff.uncovered_capabilities:
        logger.info("No uncovered capabilities - skipping decision generation")
        return {"status": "skipped"}, state.update(
            architecture_decisions_status="completed",
            architecture_decisions_output="No decisions needed - all capabilities are covered",
            new_decisions=[],
            current_stage="architecture_decisions",
        )

    logger.info(f"Processing {len(diff.uncovered_capabilities)} uncovered capabilities")

    # Build context for the prompt
    context = {
        "system_goal": system_goal,
        "mvp_scope": mvp_scope[:2000] if mvp_scope else "",  # Truncate for token limits
        "diff_context": diff_context,
        "capabilities": json.dumps(
            [
                {"id": c.get("id"), "name": c.get("name"), "subtype": c.get("subtype")}
                for c in capabilities
            ],
            indent=2,
        ),
        "existing_decisions": json.dumps(
            [{"id": d.get("id"), "name": d.get("name")} for d in existing_decisions], indent=2
        )
        if existing_decisions
        else "[]",
    }

    # Run the agent
    result = run_architect_agent(
        agent_name="architecture_decisions",
        prompt_template=ARCHITECTURE_DECISIONS_PROMPT,
        context=context,
    )

    if result["status"] == "failed":
        return {"status": "failed"}, state.update(
            architecture_decisions_status="failed",
            architecture_decisions_output=result.get("error", "Unknown error"),
            new_decisions=[],
            current_stage="architecture_decisions",
        )

    # Parse the response
    parsed = extract_json_from_response(result["output"])

    if not parsed or "decisions" not in parsed:
        logger.warning("Could not parse decisions from agent output")
        return {"status": "completed"}, state.update(
            architecture_decisions_status="completed",
            architecture_decisions_output=result["output"],
            new_decisions=[],
            current_stage="architecture_decisions",
        )

    # Store decisions in VectorDB
    new_decision_ids = []
    if session_manager:
        new_decision_ids = store_decisions_in_vectordb(
            decisions=parsed["decisions"],
            session_manager=session_manager,
        )
        logger.info(f"Created {len(new_decision_ids)} decisions in VectorDB")

    # Build output summary
    output_md = "# Architecture Decisions\n\n"
    output_md += f"**Summary:** {parsed.get('summary', 'N/A')}\n\n"
    output_md += f"**Decisions Created:** {len(new_decision_ids)}\n\n"

    for i, dec in enumerate(parsed["decisions"], 1):
        output_md += f"## {i}. {dec.get('name', 'Unnamed')}\n\n"
        output_md += f"**Description:** {dec.get('description', 'N/A')}\n\n"
        output_md += f"**Rationale:** {dec.get('rationale', 'N/A')}\n\n"
        output_md += f"**Serves Capabilities:** {', '.join(dec.get('serves_capabilities', []))}\n\n"
        output_md += "---\n\n"

    return {"status": "completed", "decisions_count": len(new_decision_ids)}, state.update(
        architecture_decisions_status="completed",
        architecture_decisions_output=output_md,
        new_decisions=new_decision_ids,
        current_stage="architecture_decisions",
    )


# =============================================================================
# Stage 2: Component Boundaries
# =============================================================================

COMPONENT_BOUNDARIES_PROMPT = """You are a Software Architect. Your task is to define component boundaries and domain entities (ENT-*) based on the architecture decisions.

## Context

**System Goal:** {{system_goal}}

**Architecture Decisions:**
{{decisions}}

**Capabilities:**
{{capabilities}}

## Your Task

Define the DOMAIN ENTITIES that emerge from the architecture decisions. Each entity:
1. Represents a core domain concept
2. Has clear attributes and relationships
3. Aligns with the bounded context

## Output Format

Output valid JSON:

```json
{
  "entities": [
    {
      "name": "Entity Name",
      "description": "What this entity represents",
      "attributes": ["attribute1", "attribute2"],
      "relationships": ["relates_to:OtherEntity", "contains:ChildEntity"],
      "bounded_context": "Which bounded context this belongs to"
    }
  ],
  "component_diagram": "ASCII diagram or description of component boundaries",
  "summary": "Brief summary of the domain model"
}
```

## Guidelines

- Focus on domain entities, not technical components
- Keep entities cohesive (single responsibility)
- Use ubiquitous language from the domain
- Consider aggregates and bounded contexts
- 3-6 entities is typical for an MVP

Output ONLY the JSON."""


@action(
    reads=["system_goal", "capabilities", "new_decisions", "existing_decisions", "session_manager"],
    writes=[
        "component_boundaries_status",
        "component_boundaries_output",
        "new_entities",
        "current_stage",
    ],
)
def component_boundaries(state: State) -> tuple[dict, State]:
    """Stage 2: Define component boundaries and domain entities (ENT-*).

    This stage:
    1. Reads the architecture decisions
    2. Identifies domain entities and their relationships
    3. Stores entities in VectorDB
    """
    logger.info("=" * 60)
    logger.info("STAGE 2: COMPONENT BOUNDARIES")
    logger.info("=" * 60)

    system_goal = state.get("system_goal", "")
    capabilities = state.get("capabilities", [])
    new_decisions = state.get("new_decisions", [])
    existing_decisions = state.get("existing_decisions", [])
    session_manager = state.get("session_manager")

    # Combine all decisions
    all_decision_ids = new_decisions + [d.get("id") for d in existing_decisions]

    if not all_decision_ids:
        logger.info("No decisions to base entities on")
        return {"status": "skipped"}, state.update(
            component_boundaries_status="completed",
            component_boundaries_output="No entities needed - no decisions to implement",
            new_entities=[],
            current_stage="component_boundaries",
        )

    # Build context
    context = {
        "system_goal": system_goal,
        "decisions": json.dumps(
            [
                {"id": d.get("id"), "name": d.get("name"), "description": d.get("description")}
                for d in existing_decisions
            ],
            indent=2,
        ),
        "capabilities": json.dumps(
            [{"id": c.get("id"), "name": c.get("name")} for c in capabilities], indent=2
        ),
    }

    # Run the agent
    result = run_architect_agent(
        agent_name="component_boundaries",
        prompt_template=COMPONENT_BOUNDARIES_PROMPT,
        context=context,
    )

    if result["status"] == "failed":
        return {"status": "failed"}, state.update(
            component_boundaries_status="failed",
            component_boundaries_output=result.get("error", "Unknown error"),
            new_entities=[],
            current_stage="component_boundaries",
        )

    # Parse the response
    parsed = extract_json_from_response(result["output"])

    if not parsed or "entities" not in parsed:
        logger.warning("Could not parse entities from agent output")
        return {"status": "completed"}, state.update(
            component_boundaries_status="completed",
            component_boundaries_output=result["output"],
            new_entities=[],
            current_stage="component_boundaries",
        )

    # Store entities in VectorDB
    new_entity_ids = []
    if session_manager:
        new_entity_ids = store_entities_in_vectordb(
            entities=parsed["entities"],
            session_manager=session_manager,
        )
        logger.info(f"Created {len(new_entity_ids)} entities in VectorDB")

    # Build output summary
    output_md = "# Component Boundaries & Domain Model\n\n"
    output_md += f"**Summary:** {parsed.get('summary', 'N/A')}\n\n"
    output_md += f"**Entities Created:** {len(new_entity_ids)}\n\n"

    if parsed.get("component_diagram"):
        output_md += f"## Component Diagram\n\n```\n{parsed['component_diagram']}\n```\n\n"

    output_md += "## Domain Entities\n\n"
    for i, ent in enumerate(parsed["entities"], 1):
        output_md += f"### {i}. {ent.get('name', 'Unnamed')}\n\n"
        output_md += f"**Description:** {ent.get('description', 'N/A')}\n\n"
        output_md += f"**Attributes:** {', '.join(ent.get('attributes', []))}\n\n"
        output_md += f"**Relationships:** {', '.join(ent.get('relationships', []))}\n\n"

    return {"status": "completed", "entities_count": len(new_entity_ids)}, state.update(
        component_boundaries_status="completed",
        component_boundaries_output=output_md,
        new_entities=new_entity_ids,
        current_stage="component_boundaries",
    )


# =============================================================================
# Stage 3: Story Generation
# =============================================================================

STORY_GENERATION_PROMPT = """You are a Technical Product Owner generating implementation-ready stories that a coding agent can execute sequentially to build a working MVP.

## Context
**Goal:** {{system_goal}}

**Capabilities to implement:** {{uncovered_capabilities}}

**Architecture Decisions:** {{decisions}}

**Domain Entities:** {{entities}}

## Story Quality Framework: INVEST Criteria

Every story MUST satisfy the INVEST criteria:
- **I**ndependent: Can be developed without waiting for other stories (except explicit dependencies)
- **N**egotiable: Describes WHAT, not HOW (implementation details left to developer)
- **V**aluable: Delivers value to users OR unblocks stories that do (bootstrap/entity stories enable features)
- **E**stimable: Clear enough that effort can be estimated (no ambiguous scope)
- **S**mall: Can be completed in 1-3 days by a single developer
- **T**estable: Has concrete acceptance criteria that can be verified

## Acceptance Criteria Format: BDD/Gherkin

Write acceptance criteria in Given-When-Then format for testability:
```
Given [precondition/context]
When [action/trigger]
Then [expected outcome/verification]
```

Example:
- Given a user is authenticated
- When they POST to /api/v1/challenges with valid data
- Then a new challenge is created with status 201
- And the response includes the challenge ID and created_at timestamp

## Story Categories (generate in this EXACT order)

### LAYER 1: PROJECT BOOTSTRAP (order: 1-3) - MANDATORY
⚠️ YOU MUST GENERATE THESE 3 STORIES FIRST. DO NOT SKIP LAYER 1.

Story 1 (order: 1):
- title: "Initialize Project Structure"
- labels: ["type:bootstrap", "layer:1"]
- dependencies: []

Story 2 (order: 2):
- title: "Database Setup and Configuration"
- labels: ["type:bootstrap", "layer:1"]
- dependencies: ["Initialize Project Structure"]

Story 3 (order: 3):
- title: "Authentication Foundation"
- labels: ["type:bootstrap", "layer:1"]
- dependencies: ["Database Setup and Configuration"]

### LAYER 2: ENTITY MODELS (order: 4-N)
Create ONE story per entity for database model creation:
- Create table/model with all attributes
- Set up relationships/foreign keys
- Add basic CRUD repository/service

Labels: `setup:ENT-xxx`, `type:entity`, `layer:2`
Dependencies: MUST include "Database Setup and Configuration"

### LAYER 3: INFRASTRUCTURE (order: N+1 to M)
Create stories for each architecture decision that requires infrastructure:
- API scaffolding, middleware, error handling
- Real-time sync setup (WebSocket/polling)
- Security policies, RBAC implementation
- External integrations setup

Labels: `setup:DEC-xxx`, `type:infrastructure`, `layer:3`
Dependencies: MUST include "Authentication Foundation" and relevant entity model stories

### LAYER 4: FEATURES (order: M+1 to end)
Create stories implementing each capability:
- Full user-facing functionality
- API endpoints with request/response specs
- UI components if applicable

**API Endpoint Requirements:** For every API endpoint, specify:
- HTTP method and path: `POST /api/v1/challenges`
- Request body schema: `{ "name": string, "start_date": ISO8601 }`
- Response schema: `{ "id": uuid, "created_at": ISO8601 }`
- Error responses: `400 Bad Request`, `401 Unauthorized`, `404 Not Found`

**Accessibility Requirements (WCAG 2.1 AA):** For UI-facing stories:
- Keyboard navigation: All interactive elements reachable via Tab
- Screen reader support: ARIA labels for non-text elements
- Color contrast: 4.5:1 minimum for normal text
- Focus indicators: Visible focus state for all interactive elements
- Form labels: Every input has an associated label

Labels: `implements:CAP-xxx`, `uses:DEC-xxx`, `touches:ENT-xxx`, `type:feature`, `layer:4`
Dependencies: MUST list the entity model stories for entities this feature touches

## Output Format
```json
{
  "stories": [
    {
      "title": "Initialize Project Structure",
      "description": "Set up the project with chosen tech stack, dependencies, and tooling",
      "acceptance_criteria": [
        "Project initialized with Python/FastAPI (or Node/Express)",
        "Dependencies installed: ORM, auth library, testing framework",
        "Linting and formatting configured",
        "Basic folder structure created: /src, /tests, /migrations",
        "README with setup instructions"
      ],
      "labels": ["type:bootstrap", "layer:1"],
      "dependencies": [],
      "priority": "high",
      "order": 1
    },
    {
      "title": "Create Member Entity Model",
      "description": "Implement the Member database model with all attributes and relationships",
      "acceptance_criteria": [
        "Given the database is configured, when Member model is defined, then table 'members' is created with columns: id (UUID PK), name (VARCHAR 255), email (VARCHAR 255 UNIQUE), gym_id (UUID FK), created_at (TIMESTAMP)",
        "Given Member has gym_id, when saved, then foreign key constraint to gyms.id is enforced",
        "Given a valid Member object, when repository.create() is called, then member is persisted and ID returned",
        "Given an existing member ID, when repository.get_by_id() is called, then member data is returned or None",
        "Given Member model changes, when tests run, then all CRUD operations pass"
      ],
      "labels": ["setup:ENT-005", "type:entity", "layer:2"],
      "dependencies": ["Database Setup and Configuration"],
      "priority": "high",
      "order": 5
    },
    {
      "title": "Member Profile View",
      "description": "Allow members to view their profile information",
      "acceptance_criteria": [
        "Given an authenticated member, when they GET /api/v1/members/me, then response 200 with { id, name, email, gym_name, joined_at }",
        "Given an unauthenticated request, when they GET /api/v1/members/me, then response 401 Unauthorized",
        "Given the profile page renders, when Tab key is pressed, then focus moves through all interactive elements in logical order",
        "Given screen reader is active, when profile loads, then all data fields have ARIA labels"
      ],
      "labels": ["implements:CAP-F-001", "uses:DEC-001", "touches:ENT-005", "type:feature", "layer:4"],
      "dependencies": ["Create Member Entity Model", "Authentication Foundation"],
      "priority": "high",
      "order": 12
    }
  ],
  "summary": "X stories generated across 4 layers"
}
```

## Critical Rules - MUST FOLLOW
1. **LAYER 1 IS MANDATORY** - First 3 stories MUST be: Initialize Project, Database Setup, Auth Foundation
2. **EVERY story in layers 2-4 MUST have dependencies** - Empty dependencies array is NOT allowed for non-bootstrap stories
3. **Every entity needs its own model creation story** - Don't skip any ENT-*
4. **Dependencies must form a valid DAG** - No circular dependencies
5. **BDD acceptance criteria** - Use Given-When-Then format for all acceptance criteria
6. **API endpoints must include schemas** - Specify method, path, request/response schemas, error codes
7. **UI stories need WCAG criteria** - Include keyboard nav, screen reader, contrast requirements
8. **Order field must be sequential** - 1, 2, 3, ... with no gaps
9. **Feature stories depend on their entities** - If feature touches ENT-005, its dependencies MUST include that entity's model story title
10. **INVEST compliance** - Every story must be Independent, Negotiable, Valuable, Estimable, Small, Testable

Output ONLY valid JSON. Generate 20-30 stories for a complete MVP."""


@action(
    reads=["system_goal", "architecture_diff", "session_manager"],
    writes=[
        "story_generation_status",
        "story_generation_output",
        "generated_stories",
        "current_stage",
    ],
)
def story_generation(state: State) -> tuple[dict, State]:
    """Stage 3: Generate stories with implements:CAP-* labels.

    This stage:
    1. Reads the architecture diff for capabilities needing stories
    2. Fetches decisions/entities from VectorDB for context
    3. Generates user stories that implement those capabilities
    4. Adds traceability labels (implements:, uses:, touches:)
    5. Prepares stories for Backlog.md (written in dependency_ordering)

    Note: Stories are generated for BOTH:
    - uncovered_capabilities: caps that need decisions AND stories
    - capabilities_without_stories: caps that have decisions but no stories
    """
    logger.info("=" * 60)
    logger.info("STAGE 3: STORY GENERATION")
    logger.info("=" * 60)

    system_goal = state.get("system_goal", "")
    diff: ArchitectureDiff = state.get("architecture_diff")
    session_manager = state.get("session_manager")

    # Combine capabilities that need stories:
    # 1. uncovered_capabilities - new caps that got decisions this run
    # 2. capabilities_without_stories - existing caps with decisions but no stories
    caps_needing_stories = []
    if diff:
        caps_needing_stories = list(
            set((diff.uncovered_capabilities or []) + (diff.capabilities_without_stories or []))
        )

    if not caps_needing_stories:
        logger.info("No capabilities need stories - all have stories already")
        return {"status": "skipped"}, state.update(
            story_generation_status="completed",
            story_generation_output="No stories needed - all capabilities have stories",
            generated_stories=[],
            current_stage="story_generation",
        )

    logger.info(f"Generating stories for {len(caps_needing_stories)} capabilities")

    # Fetch all data from VectorDB directly to avoid state type issues
    # (new_decisions/new_entities in state are ID strings, not dicts)
    slim_capabilities = []
    slim_decisions = []
    slim_entities = []

    if session_manager:
        try:
            from haytham.state.vector_db import SystemStateDB

            db_path = session_manager.session_dir / "vector_db"
            db = SystemStateDB(str(db_path))

            # Fetch capabilities
            all_caps = db.get_capabilities()
            caps_needing_set = set(caps_needing_stories)
            for c in all_caps:
                if c.get("id") in caps_needing_set:
                    slim_capabilities.append(
                        {
                            "id": c.get("id"),
                            "name": c.get("name"),
                            "description": c.get("description", "")[:200],
                            "subtype": c.get("subtype"),
                        }
                    )

            # Fetch all decisions from VectorDB
            all_decisions = db.get_decisions()
            for d in all_decisions:
                slim_decisions.append(
                    {
                        "id": d.get("id"),
                        "name": d.get("name"),
                        "description": d.get("description", "")[:200],
                        "serves_capabilities": d.get("metadata", {}).get("serves_capabilities", [])
                        or d.get("serves_capabilities", []),
                    }
                )

            # Fetch all entities from VectorDB
            all_entities = db.get_entities()
            for e in all_entities:
                slim_entities.append(
                    {
                        "id": e.get("id"),
                        "name": e.get("name"),
                        "description": e.get("description", "")[:200],
                        "attributes": (
                            e.get("metadata", {}).get("attributes", []) or e.get("attributes", [])
                        )[:5],
                    }
                )

        except Exception as e:
            logger.warning(f"Could not fetch data from VectorDB: {e}")
            # Fallback to just IDs
            slim_capabilities = [{"id": cap_id} for cap_id in caps_needing_stories]
    else:
        slim_capabilities = [{"id": cap_id} for cap_id in caps_needing_stories]

    # Build context with slim data to avoid token overflow
    context = {
        "system_goal": system_goal,
        "uncovered_capabilities": json.dumps(slim_capabilities, indent=2),
        "decisions": json.dumps(slim_decisions, indent=2),
        "entities": json.dumps(slim_entities, indent=2),
    }

    # Run the agent
    result = run_architect_agent(
        agent_name="story_generation",
        prompt_template=STORY_GENERATION_PROMPT,
        context=context,
    )

    if result["status"] == "failed":
        return {"status": "failed"}, state.update(
            story_generation_status="failed",
            story_generation_output=result.get("error", "Unknown error"),
            generated_stories=[],
            current_stage="story_generation",
        )

    # Parse the response
    parsed = extract_json_from_response(result["output"])

    if not parsed or "stories" not in parsed:
        logger.warning("Could not parse stories from agent output")
        return {"status": "completed"}, state.update(
            story_generation_status="completed",
            story_generation_output=result["output"],
            generated_stories=[],
            current_stage="story_generation",
        )

    stories = parsed["stories"]
    logger.info(f"Generated {len(stories)} stories")

    # Build output summary
    output_md = "# Generated Stories\n\n"
    output_md += f"**Summary:** {parsed.get('summary', 'N/A')}\n\n"
    output_md += f"**Stories Generated:** {len(stories)}\n\n"

    for i, story in enumerate(stories, 1):
        output_md += f"## {i}. {story.get('title', 'Untitled')}\n\n"
        output_md += f"**Description:** {story.get('description', 'N/A')}\n\n"
        output_md += f"**Labels:** {', '.join(story.get('labels', []))}\n\n"
        output_md += f"**Story Points:** {story.get('story_points', 'N/A')}\n\n"
        output_md += "**Acceptance Criteria:**\n"
        for ac in story.get("acceptance_criteria", []):
            output_md += f"- {ac}\n"
        output_md += "\n---\n\n"

    # Save stories to JSON for AI Judge evaluation (ADR-006)
    if session_manager and stories:
        stories_file = session_manager.session_dir / "generated_stories.json"
        stories_file.write_text(json.dumps(stories, indent=2))
        logger.info(f"Saved {len(stories)} stories to {stories_file}")

    return {"status": "completed", "stories_count": len(stories)}, state.update(
        story_generation_status="completed",
        story_generation_output=output_md,
        generated_stories=stories,
        current_stage="story_generation",
    )


# =============================================================================
# Stage 4: Story Validation (AI Judge Quality Gate)
# =============================================================================

STORY_EVALUATION_PROMPT = """You are an expert QA engineer and software architect acting as a JUDGE to evaluate whether a set of implementation stories will successfully produce a working MVP.

## MVP Goal
{{system_goal}}

## Required Capabilities (must ALL be implemented)
{{capabilities}}

## Required Entities (must ALL have model creation stories)
{{entities}}

## Stories to Evaluate
{{stories}}

## Evaluation Criteria

Score each criterion from 0-10:

### 1. LAYER COMPLETENESS (0-10)
- Has Project Bootstrap story (project init, dependencies)?
- Has Database Setup story?
- Has Authentication Foundation story?
- Has Entity Model stories?
- Has Infrastructure/Decision stories?
- Has Feature stories?

### 2. ENTITY COVERAGE (0-10)
- Does EVERY entity (ENT-*) have a dedicated model creation story?
- Count: X entities covered / Y total entities

### 3. CAPABILITY COVERAGE (0-10)
- Does EVERY capability (CAP-*) have at least one feature story implementing it?
- Count: X capabilities covered / Y total capabilities

### 4. DEPENDENCY VALIDITY (0-10)
- Do dependencies form a valid DAG (no circular dependencies)?
- Do feature stories depend on their required entity models?
- Do layer 2+ stories depend on layer 1 bootstrap?

### 5. ACCEPTANCE CRITERIA QUALITY (0-10)
**BDD Format Check:**
- Do acceptance criteria use Given-When-Then format?
- Are preconditions (Given) clearly stated?
- Are actions (When) specific and testable?
- Are outcomes (Then) verifiable?

**API Specification Check (for feature stories):**
- Is HTTP method and path specified? (e.g., `POST /api/v1/resource`)
- Is request body schema defined?
- Is response schema defined?
- Are error responses listed? (400, 401, 404, etc.)

**WCAG 2.1 AA Check (for UI stories):**
- Is keyboard navigation mentioned?
- Is screen reader support specified?
- Are color contrast requirements noted?
- Are focus indicators required?

Can a coding agent implement each story without ambiguity?

### 6. IMPLEMENTATION ORDER (0-10)
- Is the order field sequential and logical?
- Can stories be executed in order without blockers?

### 7. INVEST COMPLIANCE (0-10)
Check each story against INVEST criteria:
- **I**ndependent: Can it be developed without other stories (except explicit deps)?
- **N**egotiable: Does it describe WHAT not HOW?
- **V**aluable: Does it deliver user value OR enable other stories?
- **E**stimable: Is scope clear enough to estimate?
- **S**mall: Can it be done in 1-3 days?
- **T**estable: Are acceptance criteria verifiable?

Flag stories that violate INVEST (e.g., too large, unclear scope, untestable).

## Output Format
```json
{
  "verdict": "PASS" or "FAIL",
  "overall_score": 0-100,
  "scores": {
    "layer_completeness": {"score": 0-10, "reasoning": "..."},
    "entity_coverage": {"score": 0-10, "reasoning": "...", "missing": ["ENT-xxx"]},
    "capability_coverage": {"score": 0-10, "reasoning": "...", "missing": ["CAP-xxx"]},
    "dependency_validity": {"score": 0-10, "reasoning": "...", "issues": []},
    "acceptance_criteria_quality": {"score": 0-10, "reasoning": "...", "weak_stories": [], "bdd_compliance": "X/Y stories use Given-When-Then", "api_specs": "X/Y feature stories have full API specs", "wcag_compliance": "X/Y UI stories have WCAG criteria"},
    "implementation_order": {"score": 0-10, "reasoning": "..."},
    "invest_compliance": {"score": 0-10, "reasoning": "...", "violations": [{"story": "...", "violation": "Too large / Not testable / etc."}]}
  },
  "critical_gaps": ["List of critical issues that MUST be fixed"],
  "recommendations": ["List of improvements"],
  "shortcomings": [
    {
      "issue": "Specific description of what is wrong or missing",
      "severity": "high" or "medium" or "low",
      "affected_area": "layer_completeness|entity_coverage|capability_coverage|dependency_validity|acceptance_criteria|implementation_order|invest_compliance|bdd_format|api_specs|wcag_compliance",
      "suggestion": "Concrete suggestion for how to fix this in future generations"
    }
  ],
  "prompt_improvements": [
    "Specific improvement to make in the story generation prompt to prevent this issue"
  ],
  "summary": "One paragraph assessment"
}
```

## Verdict Rules
- **PASS**: Overall score >= 70 AND no critical gaps AND entity_coverage >= 8 AND capability_coverage >= 8
- **FAIL**: Otherwise

## IMPORTANT: Improvement Signals
Even if the verdict is PASS, provide `shortcomings` for ANY quality issues found. These signals help improve the story generation system over time. Be specific and actionable in your suggestions.

Output ONLY valid JSON."""


@dataclass
class AIJudgeResult:
    """Result from AI judge evaluation."""

    passed: bool
    overall_score: int
    scores: dict
    critical_gaps: list[str]
    recommendations: list[str]
    shortcomings: list[dict]  # Each dict has: issue, severity, affected_area, suggestion
    prompt_improvements: list[str]  # Specific prompt improvements to prevent issues
    summary: str
    raw_output: str


def write_improvement_signals(
    judge_result: "AIJudgeResult",
    session_manager,
    run_id: str = None,
) -> str | None:
    """Write improvement signals from AI Judge to project/improvement_signals.md.

    This captures quality issues for continuous system improvement without blocking users.

    Args:
        judge_result: The AI Judge evaluation result
        session_manager: Session manager with session_dir path
        run_id: Optional workflow run ID for tracking

    Returns:
        Path to the signals file, or None if no signals to write
    """

    # Collect all signals
    signals = []

    # Add shortcomings from AI Judge
    for shortcoming in judge_result.shortcomings:
        signals.append(
            {
                "type": "ai_judge_shortcoming",
                "severity": shortcoming.get("severity", "medium"),
                "issue": shortcoming.get("issue", "Unknown issue"),
                "affected_area": shortcoming.get("affected_area", "unknown"),
                "suggestion": shortcoming.get("suggestion", ""),
            }
        )

    # Add critical gaps as high-severity signals
    for gap in judge_result.critical_gaps:
        signals.append(
            {
                "type": "critical_gap",
                "severity": "high",
                "issue": gap,
                "affected_area": "story_generation",
                "suggestion": "",
            }
        )

    # Add prompt improvement suggestions
    for improvement in judge_result.prompt_improvements:
        signals.append(
            {
                "type": "prompt_improvement",
                "severity": "medium",
                "issue": "Story generation prompt needs improvement",
                "affected_area": "prompt_engineering",
                "suggestion": improvement,
            }
        )

    if not signals:
        logger.info("No improvement signals to write")
        return None

    # Build the signals file path
    if not session_manager:
        logger.warning("No session_manager provided, cannot write improvement signals")
        return None

    signals_dir = session_manager.session_dir / "project"
    signals_dir.mkdir(parents=True, exist_ok=True)
    signals_file = signals_dir / "improvement_signals.md"

    # Build the content to append
    timestamp = datetime.now().isoformat()
    content = f"\n---\n\n## Run: {timestamp}"
    if run_id:
        content += f" (Run ID: {run_id})"
    content += "\n\n"

    content += f"**Overall Score:** {judge_result.overall_score}/100\n"
    content += f"**Verdict:** {'PASS' if judge_result.passed else 'FAIL'}\n\n"

    # Group signals by severity
    high_signals = [s for s in signals if s["severity"] == "high"]
    medium_signals = [s for s in signals if s["severity"] == "medium"]
    low_signals = [s for s in signals if s["severity"] == "low"]

    if high_signals:
        content += "### High Severity Issues\n\n"
        for signal in high_signals:
            content += f"- **[{signal['type']}]** {signal['issue']}\n"
            if signal.get("suggestion"):
                content += f"  - *Suggestion:* {signal['suggestion']}\n"
        content += "\n"

    if medium_signals:
        content += "### Medium Severity Issues\n\n"
        for signal in medium_signals:
            content += f"- **[{signal['type']}]** {signal['issue']}\n"
            if signal.get("suggestion"):
                content += f"  - *Suggestion:* {signal['suggestion']}\n"
        content += "\n"

    if low_signals:
        content += "### Low Severity Issues\n\n"
        for signal in low_signals:
            content += f"- **[{signal['type']}]** {signal['issue']}\n"
            if signal.get("suggestion"):
                content += f"  - *Suggestion:* {signal['suggestion']}\n"
        content += "\n"

    # Add summary
    content += f"### Summary\n\n{judge_result.summary}\n"

    # Write/append to file
    if signals_file.exists():
        # Append to existing file
        with open(signals_file, "a") as f:
            f.write(content)
    else:
        # Create new file with header
        header = "# Improvement Signals\n\n"
        header += "This file captures quality issues identified by the AI Judge during story generation.\n"
        header += "These signals are used for continuous system improvement and should be reviewed periodically.\n"
        with open(signals_file, "w") as f:
            f.write(header + content)

    logger.info(f"Wrote {len(signals)} improvement signals to {signals_file}")
    return str(signals_file)


def evaluate_stories_with_ai_judge(
    stories: list[dict],
    capabilities: list[dict],
    entities: list[dict],
    system_goal: str,
) -> AIJudgeResult:
    """Use AI as a judge to evaluate story quality for MVP completeness.

    This is a quality gate that ensures generated stories are sufficient
    for a coding agent to build a working MVP.

    Args:
        stories: Generated stories to evaluate
        capabilities: All capabilities that should be implemented
        entities: All entities that should have models
        system_goal: The MVP goal description

    Returns:
        AIJudgeResult with verdict and detailed feedback
    """
    # Build context for the judge
    context = {
        "system_goal": system_goal,
        "capabilities": json.dumps(
            [
                {"id": c.get("id"), "name": c.get("name"), "subtype": c.get("subtype")}
                for c in capabilities
            ],
            indent=2,
        ),
        "entities": json.dumps(
            [{"id": e.get("id"), "name": e.get("name")} for e in entities], indent=2
        ),
        "stories": json.dumps(
            [
                {
                    "title": s.get("title"),
                    "description": s.get("description"),
                    "labels": s.get("labels", []),
                    "dependencies": s.get("dependencies", []),
                    "acceptance_criteria": s.get("acceptance_criteria", []),
                    "order": s.get("order"),
                }
                for s in stories
            ],
            indent=2,
        ),
    }

    # Run the AI judge
    result = run_architect_agent(
        agent_name="story_evaluation_judge",
        prompt_template=STORY_EVALUATION_PROMPT,
        context=context,
    )

    if result["status"] == "failed":
        return AIJudgeResult(
            passed=False,
            overall_score=0,
            scores={},
            critical_gaps=["AI Judge evaluation failed"],
            recommendations=[],
            shortcomings=[
                {
                    "issue": "AI Judge evaluation failed",
                    "severity": "high",
                    "affected_area": "system",
                    "suggestion": "Check model availability and prompt",
                }
            ],
            prompt_improvements=[],
            summary=f"Evaluation error: {result.get('error', 'Unknown')}",
            raw_output=result.get("output", ""),
        )

    # Parse the judge's response
    parsed = extract_json_from_response(result["output"])

    if not parsed:
        return AIJudgeResult(
            passed=False,
            overall_score=0,
            scores={},
            critical_gaps=["Could not parse AI Judge response"],
            recommendations=[],
            shortcomings=[
                {
                    "issue": "AI Judge response could not be parsed as JSON",
                    "severity": "high",
                    "affected_area": "system",
                    "suggestion": "Improve JSON extraction logic or prompt",
                }
            ],
            prompt_improvements=["Add stricter JSON output instructions to AI Judge prompt"],
            summary="Failed to parse evaluation response",
            raw_output=result["output"],
        )

    return AIJudgeResult(
        passed=parsed.get("verdict", "FAIL") == "PASS",
        overall_score=parsed.get("overall_score", 0),
        scores=parsed.get("scores", {}),
        critical_gaps=parsed.get("critical_gaps", []),
        recommendations=parsed.get("recommendations", []),
        shortcomings=parsed.get("shortcomings", []),
        prompt_improvements=parsed.get("prompt_improvements", []),
        summary=parsed.get("summary", "No summary provided"),
        raw_output=result["output"],
    )


@dataclass
class StoryValidationResult:
    """Result of story validation."""

    passed: bool
    message: str
    valid_stories: list[dict]
    invalid_stories: list[dict]


def validate_story_labels(stories: list[dict]) -> StoryValidationResult:
    """Validate that all stories have proper traceability labels.

    Stories must have EITHER:
    - `implements:CAP-*` label (for feature stories)
    - `setup:DEC-*` or `setup:ENT-*` label (for foundation stories)

    Args:
        stories: List of story dicts with labels

    Returns:
        StoryValidationResult with pass/fail and details
    """
    valid = []
    invalid = []

    for story in stories:
        labels = story.get("labels", [])
        # Feature stories have implements: labels
        has_implements = any(lbl.startswith("implements:") for lbl in labels)
        # Foundation stories have setup: labels
        has_setup = any(lbl.startswith("setup:") for lbl in labels)

        if has_implements or has_setup:
            valid.append(story)
        else:
            invalid.append(story)

    if invalid:
        return StoryValidationResult(
            passed=False,
            message=f"{len(invalid)} stories are missing traceability labels (implements: or setup:)",
            valid_stories=valid,
            invalid_stories=invalid,
        )

    return StoryValidationResult(
        passed=True,
        message=f"All {len(valid)} stories have proper traceability",
        valid_stories=valid,
        invalid_stories=[],
    )


@action(
    reads=["generated_stories"],
    writes=[
        "story_validation_status",
        "story_validation_output",
        "validated_stories",
        "current_stage",
    ],
)
def story_validation(state: State) -> tuple[dict, State]:
    """Stage 4: Basic Story Validation.

    Performs basic label validation to ensure stories have traceability labels.
    AI Judge evaluation is available as a separate manual action (button).

    See ADR-006: Manual Quality Evaluation Pattern
    """
    logger.info("=" * 60)
    logger.info("STAGE 4: STORY VALIDATION")
    logger.info("=" * 60)

    generated_stories = state.get("generated_stories", [])

    if not generated_stories:
        logger.info("No stories to validate")
        return {"status": "skipped"}, state.update(
            story_validation_status="completed",
            story_validation_output="No stories to validate",
            validated_stories=[],
            current_stage="story_validation",
        )

    # Basic label validation
    label_result = validate_story_labels(generated_stories)
    logger.info(
        f"Label validation: passed={label_result.passed}, valid={len(label_result.valid_stories)}"
    )

    # Build output
    output_md = "# Story Validation Report\n\n"
    output_md += "## Label Traceability Check\n\n"
    output_md += f"**Status:** {'✅ PASSED' if label_result.passed else '⚠️ ISSUES FOUND'}\n"
    output_md += (
        f"**Valid Stories:** {len(label_result.valid_stories)} / {len(generated_stories)}\n\n"
    )

    if label_result.invalid_stories:
        output_md += "**Stories missing labels:**\n"
        for story in label_result.invalid_stories:
            output_md += f"- {story.get('title', 'Untitled')}\n"
        output_md += "\n"

    output_md += "---\n\n"
    output_md += (
        "*Use the 'Evaluate Stories' button to run AI Judge for detailed quality assessment.*\n"
    )

    logger.info(f"Validation complete - {len(generated_stories)} stories ready")

    return {"status": "completed", "stories_count": len(generated_stories)}, state.update(
        story_validation_status="completed",
        story_validation_output=output_md,
        validated_stories=generated_stories,  # Pass all stories through
        current_stage="story_validation",
    )


# =============================================================================
# Manual AI Judge Evaluation (Button Action)
# =============================================================================


def run_ai_judge_evaluation(session_manager, run_id: str = None) -> dict:
    """Run AI Judge evaluation on generated stories.

    This is a manual action triggered via button after story generation.
    Results are written to project/improvement_signals.md for human review.

    See ADR-006: Manual Quality Evaluation Pattern

    Args:
        session_manager: Session manager with session_dir path
        run_id: Optional workflow run ID for tracking

    Returns:
        Dict with evaluation results
    """
    logger.info("=" * 60)
    logger.info("AI JUDGE EVALUATION (Manual Trigger)")
    logger.info("=" * 60)

    # Load generated stories from session
    stories_file = session_manager.session_dir / "generated_stories.json"
    if not stories_file.exists():
        return {
            "status": "error",
            "message": "No generated stories found. Run story generation first.",
        }

    with open(stories_file) as f:
        stories = json.load(f)

    if not stories:
        return {
            "status": "error",
            "message": "Generated stories file is empty.",
        }

    # Load capabilities and entities from VectorDB
    capabilities = []
    entities = []
    system_goal = ""

    try:
        from haytham.state.vector_db import SystemStateDB

        db_path = session_manager.session_dir / "vector_db"
        db = SystemStateDB(str(db_path))
        capabilities = db.get_capabilities()
        entities = db.get_entities()

        # Try to get system goal from session
        mvp_spec_file = session_manager.session_dir / "mvp-specification" / "mvp_spec.md"
        if mvp_spec_file.exists():
            system_goal = mvp_spec_file.read_text()[:500]  # First 500 chars
    except Exception as e:
        logger.warning(f"Could not load context for judge: {e}")

    # Run AI Judge
    logger.info(f"Evaluating {len(stories)} stories with AI Judge...")
    judge_result = evaluate_stories_with_ai_judge(
        stories=stories,
        capabilities=capabilities,
        entities=entities,
        system_goal=system_goal,
    )

    # Write improvement signals
    signals_file = write_improvement_signals(judge_result, session_manager, run_id)

    # Build result report
    result = {
        "status": "completed",
        "verdict": "PASS" if judge_result.passed else "FAIL",
        "overall_score": judge_result.overall_score,
        "scores": judge_result.scores,
        "critical_gaps": judge_result.critical_gaps,
        "shortcomings_count": len(judge_result.shortcomings),
        "recommendations": judge_result.recommendations,
        "summary": judge_result.summary,
        "signals_file": signals_file,
    }

    logger.info(f"AI Judge verdict: {result['verdict']} (score: {result['overall_score']}/100)")
    if signals_file:
        logger.info(f"Improvement signals written to: {signals_file}")

    return result


# =============================================================================
# Stage 5: Dependency Ordering
# =============================================================================

DEPENDENCY_ORDERING_PROMPT = """You are a Project Manager. Your task is to order stories by their dependencies.

## Stories to Order

{{stories}}

## Your Task

Analyze the stories and determine the optimal execution order based on:
1. Data dependencies (entity creation before usage)
2. Technical dependencies (infrastructure before features)
3. Business value (high priority features early)

## Output Format

Output valid JSON:

```json
{
  "ordered_stories": [
    {
      "title": "Story Title",
      "order": 1,
      "dependencies": ["Other Story Title"],
      "rationale": "Why this order"
    }
  ],
  "dependency_graph": "ASCII representation of dependencies",
  "summary": "Brief explanation of ordering strategy"
}
```

## Guidelines

- Foundation stories (entity setup) should come first
- Stories with no dependencies can be parallelized
- Consider MVP scope - essential features before nice-to-haves
- Keep sprint planning in mind

Output ONLY the JSON."""


@action(
    reads=["validated_stories", "session_manager"],
    writes=[
        "dependency_ordering_status",
        "dependency_ordering_output",
        "ordered_stories",
        "current_stage",
    ],
)
def dependency_ordering(state: State) -> tuple[dict, State]:
    """Stage 5: Order stories by their dependencies.

    This stage:
    1. Analyzes story dependencies
    2. Creates an optimal execution order
    3. Updates story priority in preparation for Backlog.md
    """
    logger.info("=" * 60)
    logger.info("STAGE 5: DEPENDENCY ORDERING")
    logger.info("=" * 60)

    validated_stories = state.get("validated_stories", [])
    session_manager = state.get("session_manager")

    if not validated_stories:
        logger.info("No stories to order")
        return {"status": "skipped"}, state.update(
            dependency_ordering_status="completed",
            dependency_ordering_output="No stories to order",
            ordered_stories=[],
            current_stage="dependency_ordering",
        )

    # Build context
    context = {
        "stories": json.dumps(
            [
                {
                    "title": s.get("title"),
                    "labels": s.get("labels", []),
                    "story_points": s.get("story_points"),
                }
                for s in validated_stories
            ],
            indent=2,
        ),
    }

    # Run the agent
    result = run_architect_agent(
        agent_name="dependency_ordering",
        prompt_template=DEPENDENCY_ORDERING_PROMPT,
        context=context,
    )

    if result["status"] == "failed":
        return {"status": "failed"}, state.update(
            dependency_ordering_status="failed",
            dependency_ordering_output=result.get("error", "Unknown error"),
            ordered_stories=validated_stories,  # Return unordered as fallback
            current_stage="dependency_ordering",
        )

    # Parse the response
    parsed = extract_json_from_response(result["output"])

    if not parsed or "ordered_stories" not in parsed:
        logger.warning("Could not parse ordering from agent output")
        return {"status": "completed"}, state.update(
            dependency_ordering_status="completed",
            dependency_ordering_output=result["output"],
            ordered_stories=validated_stories,
            current_stage="dependency_ordering",
        )

    # Build output
    output_md = "# Story Dependency Ordering\n\n"
    output_md += f"**Summary:** {parsed.get('summary', 'N/A')}\n\n"

    if parsed.get("dependency_graph"):
        output_md += f"## Dependency Graph\n\n```\n{parsed['dependency_graph']}\n```\n\n"

    output_md += "## Execution Order\n\n"
    for os in parsed["ordered_stories"]:
        output_md += f"{os.get('order', '?')}. **{os.get('title', 'Untitled')}**\n"
        output_md += f"   - Dependencies: {', '.join(os.get('dependencies', [])) or 'None'}\n"
        output_md += f"   - Rationale: {os.get('rationale', 'N/A')}\n\n"

    # Merge ordering info back into stories
    ordered_stories = []
    ordering_map = {s["title"]: s for s in parsed["ordered_stories"]}

    for story in validated_stories:
        story_copy = story.copy()
        if story["title"] in ordering_map:
            story_copy["order"] = ordering_map[story["title"]].get("order", 999)
            story_copy["dependencies"] = ordering_map[story["title"]].get("dependencies", [])
        else:
            story_copy["order"] = 999
        ordered_stories.append(story_copy)

    # Sort by order
    ordered_stories.sort(key=lambda s: s.get("order", 999))

    logger.info(f"Ordered {len(ordered_stories)} stories")

    # ==========================================================================
    # Create draft tasks in Backlog.md
    # Stories go directly to Backlog.md per ADR-003 (no intermediate storage)
    # ==========================================================================
    backlog_created = 0
    backlog_failed = 0

    if session_manager and ordered_stories:
        try:
            from haytham.backlog import BacklogCLI

            project_dir = session_manager.session_dir.parent
            cli = BacklogCLI(project_dir)

            # Ensure backlog is initialized
            if not cli.is_initialized():
                cli.init("Haytham MVP")
                logger.info("Initialized Backlog.md in project directory")

            for story in ordered_stories:
                try:
                    title = story.get("title", "Untitled Story")
                    description = story.get("description", "")
                    priority = story.get("priority", "medium")
                    story_points = story.get("story_points", 0)
                    acceptance_criteria = story.get("acceptance_criteria", [])

                    # Build labels from traceability
                    labels = story.get("labels", [])

                    # Add story points as label if present
                    if story_points:
                        labels.append(f"points:{story_points}")

                    # Create draft task
                    task_id = cli.create_task(
                        title=title,
                        description=description,
                        priority=priority,
                        labels=labels,
                        acceptance_criteria=acceptance_criteria,
                        draft=True,
                    )

                    if task_id:
                        backlog_created += 1
                        logger.info(f"Created draft task {task_id}: {title}")
                    else:
                        backlog_failed += 1
                        logger.warning(f"Failed to create task: {title}")

                except Exception as e:
                    backlog_failed += 1
                    logger.error(f"Error creating task for story: {e}")

            logger.info(f"Backlog.md: Created {backlog_created} drafts, {backlog_failed} failed")

        except ImportError:
            logger.warning("BacklogCLI not available - stories not saved to Backlog.md")
        except Exception as e:
            logger.error(f"Failed to create Backlog.md tasks: {e}")

    # Add backlog creation summary to output
    if backlog_created > 0:
        output_md += "\n## Backlog.md Tasks\n\n"
        output_md += f"**Created:** {backlog_created} draft tasks\n"
        if backlog_failed > 0:
            output_md += f"**Failed:** {backlog_failed} tasks\n"
        output_md += "\n📋 Review drafts at: [Task Browser](http://localhost:6420/drafts)\n"

    return {
        "status": "completed",
        "stories_count": len(ordered_stories),
        "backlog_created": backlog_created,
    }, state.update(
        dependency_ordering_status="completed",
        dependency_ordering_output=output_md,
        ordered_stories=ordered_stories,
        current_stage="dependency_ordering",
    )
