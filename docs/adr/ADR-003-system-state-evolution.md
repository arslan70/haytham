# ADR-003: System State Evolution - From Document to Queryable Model

## Status
**Accepted.** 2026-01-09 (Implemented 2026-01-11)

## Context

The current approach (ADR-001a) produces an MVP specification as a **Markdown document**. While human-readable, this creates fundamental problems for Haytham's core mission:

### The Problem

1. **No queryable state.** Agents cannot ask "what capabilities exist?" or "what constraints apply here?"
2. **No incremental evolution.** Adding features means editing a document, not extending a model
3. **No traceability.** Cannot see the history of why the system looks the way it does
4. **Document drift.** Human-readable narrative diverges from structured reality

This breaks Haytham's core promise: *"Decisions are explicit, recorded, and revisitable."*

### Why This Matters Now

Haytham is a **governance and orchestration layer**. To propose improvements or orchestrate changes, the system must first know what exists. The current document-based approach requires:

- Re-parsing documents on every operation
- Inferring structure from unstructured text
- No formal diff mechanism for "what changed"

As systems grow, this becomes a bottleneck for both performance and reliability.

---

## Theoretical Foundations

This problem is well-studied in software engineering:

| Theory | Key Insight |
|--------|-------------|
| **Parnas (1972)** | A module should encapsulate one design decision that might change |
| **Perry & Wolf (1992)** | Architecture = {Elements, Form, Rationale}; rationale decays fastest |
| **ADRs (Nygard, 2011)** | Decisions have lifecycles: Proposed, Accepted, Deprecated, Superseded |
| **IEEE 42010** | Views are renderings of an underlying architecture description |
| **Event Sourcing (DDD)** | State is derived from a log of events, not stored directly |
| **Twin Peaks** | Requirements and architecture co-evolve; they're not sequential |

---

## Minimum Requirements

Any solution must satisfy:

| # | Requirement | Rationale |
|---|-------------|-----------|
| 1 | **Fast, cost-effective, consistent agent queries** | Agents need state without re-parsing documents every time |
| 2 | **Impact analysis + traceability** | Given a proposed change, retrieve related entities and their history. Timestamps enable point-in-time queries without explicit event sourcing |
| 3 | **Scalable for large systems** | Single JSON file won't scale to enterprise systems |
| 4 | **Use proven patterns** | Prefer established software engineering patterns over novel invention |
| 5 | **Use existing libraries/services** | Abstract complexity; don't reinvent infrastructure |

---

## Options Considered

### Option A: Schema-First Specification (Structured Artifacts)
Replace Markdown with structured YAML/JSON as the source of truth.

**Matches requirements**: 1, 2, 4, 5
**Rejected**: Less human-readable, steeper learning curve for stakeholders.

### Option B: Hybrid Document + Structured Index
Keep human-readable documents but generate/maintain a shadow structured index.

**Matches requirements**: 1, 4, partially 2
**Rejected**: Risk of drift between document and index, two sources of truth.

### Option C: Event-Sourced Decision Log
The specification isn't a document. It's a log of decisions. Current state is derived by replaying the log.

**Matches requirements**: 1, 2, 3, 4
**Rejected**: Current state requires aggregation, more complex to implement.

### Option D: Living Architecture Model (Multi-File ADR-style)
Extend ADR pattern to include capabilities, components, and decisions as separate files with cross-references.

**Matches requirements**: 1, 3, 4
**Rejected**: Needs tooling for "big picture" view, risk of orphaned files.

### Option E: Graph Database / Knowledge Graph
Store system state in a graph database (e.g., Neo4j, AWS Neptune).

**Matches requirements**: 1, 2, 3, 4, 5
**Rejected**: External dependency, higher operational complexity for small projects.

### Option F: Vector Database / Semantic Layer (CHOSEN)
Store system state as embeddings in a vector database. Agents query by semantic similarity rather than exact match.

**Matches requirements**: 1 (excellent), 2 (with temporal metadata), 3, 4, 5

### Option G: Hybrid Graph + Vector
Combine structured graph for relationships with vector embeddings for semantic search.

**Matches requirements**: 1, 2, 3, 4, 5
**Rejected for MVP**: Higher complexity. Can layer in graph later if needed.

---

## Decision

### Vector Database with Temporal Metadata

We implement **Option F: Vector Database** using LanceDB with temporal metadata for traceability.

**Key Insight**: Vector DBs excel at the *discovery* problem, "what's related to X?" With temporal metadata, they also handle *traceability*, "when did this change and why?"

| Requirement | How Vector DB Satisfies It |
|-------------|---------------------------|
| Agent queries | Semantic similarity search + metadata filters |
| Impact + traceability | Temporal metadata (`created_at`, `supersedes`, `superseded_by`) |
| Scalable | Embedded (LanceDB) or managed services (Pinecone, Weaviate) |
| Proven pattern | RAG is now industry-standard for LLM applications |
| Existing tooling | Rich ecosystem, well-documented SDKs |

---

## Implementation

### 1. Vector Database: LanceDB

#### Evaluation Criteria

| Criterion | Weight | Chroma | LanceDB |
|-----------|--------|--------|---------|
| **Embedded/Serverless** | High | SQLite-backed | File-backed (Lance format) |
| **Python SDK Quality** | High | Good | Excellent |
| **Metadata Filtering** | High | Good | Excellent (SQL-like) |
| **Persistence** | High | SQLite | Lance columnar format |
| **Performance** | Medium | Good | Better (columnar, vectorized) |
| **Multi-modal Support** | Low | No | Yes (images, future use) |
| **Active Development** | Medium | Yes | Yes (backed by LanceDB Inc) |

**Choice: LanceDB**

**Rationale:**
1. **File-based persistence** aligns with current session directory pattern
2. **SQL-like filtering** makes temporal queries natural
3. **Columnar format** provides efficient storage and fast scans
4. **No external server.** Embedded in Python process
5. **Better suited for append-heavy workloads** (our temporal pattern)

```python
import lancedb

# Connection (file-based, no server)
db = lancedb.connect("session/vector_db")
```

---

### 2. Embedding Model: Amazon Titan

**Decision:** Use `amazon.titan-embed-text-v2:0` via AWS Bedrock

**Rationale:**
- Consistent with existing Bedrock infrastructure
- No additional API keys or services
- 1024-dimension embeddings (good balance of quality/performance)
- Supports up to 8,192 tokens per input

**Implementation:** `haytham/state/embedder.py`

---

### 3. Domain Model: Generic Capability Schema

Rather than rigid schemas per capability type, we use a **flexible base schema** with type-specific metadata.

#### Base Entry Schema

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal, Any

class SystemStateEntry(BaseModel):
    """Base schema for all entries in the vector database."""

    # Identity
    id: str = Field(..., description="Unique identifier (e.g., CAP-F-001, DEC-003)")
    type: Literal["capability", "decision", "entity", "constraint"]

    # Content (embedded for semantic search)
    name: str = Field(..., description="Short name/title")
    description: str = Field(..., description="Detailed description")

    # Classification
    subtype: str | None = Field(None, description="Type-specific classification")
    tags: list[str] = Field(default_factory=list)

    # Relationships
    affects: list[str] = Field(default_factory=list, description="IDs of related entries")
    depends_on: list[str] = Field(default_factory=list, description="IDs of dependencies")

    # Temporal (for traceability)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    supersedes: str | None = Field(None, description="ID of entry this replaces")
    superseded_by: str | None = Field(None, description="ID of entry that replaced this")

    # Provenance
    source_stage: str | None = Field(None, description="Workflow stage that created this")
    rationale: str | None = Field(None, description="Why this exists or was decided")

    # Flexible metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
```

**Implementation:** `haytham/state/schema.py`

#### Capability Subtypes

```python
CAPABILITY_SUBTYPES = {
    "functional": "What the system does for users",
    "non_functional": "Quality attributes (performance, security, etc.)",
    "operational": "How the system is run (deployment, monitoring, etc.)",
}
```

#### ID Generation Convention

| Type | Prefix | Example |
|------|--------|---------|
| Capability (functional) | `CAP-F-` | `CAP-F-001` |
| Capability (non-functional) | `CAP-NF-` | `CAP-NF-001` |
| Capability (operational) | `CAP-OP-` | `CAP-OP-001` |
| Decision | `DEC-` | `DEC-001` |
| Entity | `ENT-` | `ENT-001` |
| Constraint | `CON-` | `CON-001` |

---

### 4. Traceability via Temporal Metadata

Instead of structural diffs, we achieve traceability through timestamped entries with supersession links:

| Field | Purpose |
|-------|---------|
| `created_at` | When this entry was created |
| `supersedes` | ID of entry this replaces (for evolution tracking) |
| `superseded_by` | ID of entry that replaced this (null = current) |
| `affects` | IDs of related entries (for impact analysis) |

**Query patterns enabled:**
- *Current state*: `superseded_by = ''`
- *Point-in-time*: `created_at <= T AND superseded_by IS NULL`
- *Evolution*: Follow `supersedes` chain backwards
- *Impact analysis*: `similarity_search() + filter by affects`

---

### 5. SystemStateDB API

**Implementation:** `haytham/state/vector_db.py`

#### Write Operations

| Method | Purpose |
|--------|---------|
| `add_entry(entry)` | Add new entry (checks for duplicates) |
| `supersede_entry(old_id, new_entry)` | Create new version, mark old as superseded |
| `delete_entry(entry_id)` | Remove entry by ID |

#### Read Operations

| Method | Purpose |
|--------|---------|
| `get_by_id(entry_id)` | Get specific entry |
| `find_similar(query, type, limit)` | Semantic similarity search |
| `get_current_state(type, subtype)` | All non-superseded entries |
| `get_capabilities(subtype)` | All current capabilities |
| `get_decisions()` | All current decisions |
| `get_entities()` | All current entities |
| `get_history(entry_id)` | Follow supersedes chain |
| `impact_analysis(query)` | Find affected entries |
| `find_by_name(name, type)` | Exact name lookup |

---

### 6. Directory Structure

```
haytham/
├── state/                          # System state management
│   ├── __init__.py
│   ├── vector_db.py               # SystemStateDB class
│   ├── embedder.py                # TitanEmbedder class
│   ├── schema.py                  # SystemStateEntry, IDGenerator
│   ├── coverage.py                # Capability coverage queries
│   └── supersede.py               # Supersede detection

session/
└── vector_db/                     # LanceDB storage
    └── system_state.lance/        # LanceDB table files
```

---

### 7. Connection to Workflow

The `capability_model` stage in Workflow 1 outputs structured capabilities to the vector database. See [ADR-004](./ADR-004-multi-phase-workflow-architecture.md) for workflow integration details.

User stories are NOT stored in the vector DB. They are generated on-demand and stored in Backlog.md per [ADR-002](./ADR-002-backlog-md-integration.md).

---

## Consequences

### Positive
- **Queryable state**: Agents can ask "what capabilities exist?" semantically
- **Traceability**: Full history via `supersedes` chain
- **Scalable**: LanceDB handles large datasets efficiently
- **LLM-native**: Semantic search aligns with agent query patterns
- **Consistent stack**: Amazon Titan stays in Bedrock ecosystem

### Negative
- **New dependency**: LanceDB adds to dependency footprint
- **Embedding costs**: Each write requires Bedrock API call
- **Schema migration**: Future schema changes require migration logic
- **Learning curve**: Team needs to understand vector DB patterns

### Neutral
- **MVP Spec deprecated**: Existing MVP Spec logic replaced by capability_model stage
- **Stories separated**: User stories in Backlog.md (cleaner separation)

---

## Related Documents

- [ADR-001c: System State Model](./ADR-001c-system-state-model.md). Original POC approach (superseded)
- [ADR-001a: MVP Spec Enhancement](./ADR-001a-mvp-spec-enhancement.md). Document-based specification (superseded)
- [ADR-002: Backlog.md Integration](./ADR-002-backlog-md-integration.md). Task management
- [ADR-004: Multi-Phase Workflow Architecture](./ADR-004-multi-phase-workflow-architecture.md). Workflow boundaries
- [Project Haytham Concept Paper](../concept-paper.md). Core vision and principles
