# ADR-012: Visual Roadmap View

## Status
**Proposed** — 2026-01-19

## Context

### Current State

Generated stories are displayed as a flat list or JSON:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  📋 GENERATED STORIES (27)                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  ☐ Initialize Project Structure                                    High    │
│  ☐ Database Setup and Configuration                                High    │
│  ☐ Authentication Foundation                                       High    │
│  ☐ Create StartupIdea Entity Model                                 High    │
│  ☐ Create ValidationResult Entity Model                            High    │
│  ... (22 more)                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The Problem

**Flat lists hide structure.** A solo founder looking at 27 stories cannot see:

| Question | Current Answer |
|----------|----------------|
| "What's the critical path?" | Unclear — dependencies are text references |
| "What can I parallelize?" | Unknown — no visual grouping |
| "Where are the milestones?" | Missing — no phase boundaries |
| "What blocks what?" | Hidden — must read each story's dependencies |
| "How does this become a product?" | Opaque — no narrative flow |

### Dogfood Evidence

The Haytham stories have clear structure:
- **Layer 1 (Bootstrap):** 3 foundational stories
- **Layer 2 (Entities):** 6 data model stories (parallelizable)
- **Layer 3 (Infrastructure):** 3 cross-cutting concerns
- **Layer 4 (Features):** 15 user-facing features

This structure exists in the data (`layer:1`, `layer:2` labels) but is **invisible in the UI**.

### User Needs

| Persona | What They Need to See |
|---------|----------------------|
| Solo founder | "Show me the order to build things" |
| Technical founder | "Show me dependencies and parallel tracks" |
| Non-technical founder | "Show me when I'll have something working" |
| Contractor | "Show me what I can start now vs. later" |

---

## Decision

### Implement a Multi-View Roadmap Visualization

We will add three complementary views for the generated stories:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ROADMAP VISUALIZATION MODES                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                         │
│  │   LAYERS    │  │  TIMELINE   │  │ DEPENDENCY  │                         │
│  │    VIEW     │  │    VIEW     │  │    GRAPH    │                         │
│  └─────────────┘  └─────────────┘  └─────────────┘                         │
│        │                │                │                                  │
│        ▼                ▼                ▼                                  │
│  ┌───────────┐    ┌───────────┐    ┌───────────┐                           │
│  │ Swimlane  │    │ Gantt-    │    │ DAG       │                           │
│  │ by layer  │    │ style     │    │ network   │                           │
│  │           │    │ phases    │    │ graph     │                           │
│  └───────────┘    └───────────┘    └───────────┘                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### View 1: Layers View (Default)

Swimlane visualization showing stories grouped by execution layer.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🗺️ ROADMAP                                    [Layers] Timeline  Graph    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  LAYER 1: BOOTSTRAP                                          12-20h total  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ ┌──────────────┐   ┌──────────────┐   ┌──────────────┐             │   │
│  │ │ Project      │──▶│ Database     │──▶│ Auth         │             │   │
│  │ │ Setup        │   │ Setup        │   │ Foundation   │             │   │
│  │ │ S (2-4h)     │   │ M (4-8h)     │   │ M (4-8h)     │             │   │
│  │ └──────────────┘   └──────────────┘   └──────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                          │                                  │
│                    ┌─────────────────────┼─────────────────────┐           │
│                    ▼                     ▼                     ▼           │
│  LAYER 2: ENTITIES                                           18-30h total  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐│   │
│  │ │ StartupIdea  │ │ Validation   │ │ MVPPlan      │ │ Market       ││   │
│  │ │ Entity       │ │ Result       │ │ Entity       │ │ Analysis     ││   │
│  │ │ S (2-4h)     │ │ S (2-4h)     │ │ S (2-4h)     │ │ S (2-4h)     ││   │
│  │ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘│   │
│  │ ┌──────────────┐ ┌──────────────┐                                  │   │
│  │ │ Risk         │ │ AIAgent      │  ← These 6 can be parallelized   │   │
│  │ │ Assessment   │ │ Entity       │                                  │   │
│  │ │ S (2-4h)     │ │ S (2-4h)     │                                  │   │
│  │ └──────────────┘ └──────────────┘                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                          │                                  │
│                                          ▼                                  │
│  LAYER 3: INFRASTRUCTURE                                     10-18h total  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                 │   │
│  │ │ API Gateway  │ │ Progressive  │ │ Data         │                 │   │
│  │ │ & Middleware │ │ Disclosure   │ │ Anonymtic.   │                 │   │
│  │ │ M (4-8h)     │ │ M (4-8h)     │ │ M (4-8h)     │                 │   │
│  │ └──────────────┘ └──────────────┘ └──────────────┘                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                          │                                  │
│                                          ▼                                  │
│  LAYER 4: FEATURES                                           40-70h total  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ...             │   │
│  │ │ Submit Idea  │ │ View Ideas   │ │ AI Concept   │                 │   │
│  │ │ M (4-8h)     │ │ M (4-8h)     │ │ Expansion    │                 │   │
│  │ └──────────────┘ └──────────────┘ │ L (8-16h)    │                 │   │
│  │                                   └──────────────┘                 │   │
│  │ [+12 more features...]                                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Legend: ──▶ dependency   S/M/L = estimate   [█] critical path             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Stories grouped by layer (swimlanes)
- Dependencies shown as arrows
- Parallelizable stories shown side-by-side
- Aggregate time per layer
- Collapsible layers for overview

---

### View 2: Timeline View

Phase-based view showing when features become available.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🗺️ ROADMAP                                     Layers [Timeline] Graph    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │     WEEK 1          WEEK 2          WEEK 3          WEEK 4          │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │                                                                     │   │
│  │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │   │
│  │  Foundation                                                         │   │
│  │  (Bootstrap + Entities)                                             │   │
│  │  "You have a working backend"                                       │   │
│  │                                                                     │   │
│  │  ░░░░░░░░░░░░░░░░░░░░▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░  │   │
│  │                      Infrastructure                                 │   │
│  │                      (API + UI Framework)                           │   │
│  │                      "You have API endpoints"                       │   │
│  │                                                                     │   │
│  │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  │   │
│  │                                      Core Features                  │   │
│  │                                      (MVP Features)                 │   │
│  │                                      "You have a usable product"    │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  MILESTONES                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  🏁 Day 3    Backend Foundation Complete                            │   │
│  │              • Database operational                                 │   │
│  │              • Authentication working                               │   │
│  │              • All entities created                                 │   │
│  │                                                                     │   │
│  │  🏁 Day 7    API Layer Complete                                     │   │
│  │              • All endpoints functional                             │   │
│  │              • Basic UI framework in place                          │   │
│  │                                                                     │   │
│  │  🏁 Day 14   MVP Complete                                           │   │
│  │              • All core features working                            │   │
│  │              • Ready for first users                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Time-based horizontal axis
- Phases as horizontal bars
- Milestone markers with descriptions
- "What you'll have" descriptions at each phase
- Based on effort estimates from ADR-011

---

### View 3: Dependency Graph

Network visualization showing the full dependency structure.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🗺️ ROADMAP                                     Layers  Timeline [Graph]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                           ┌─────────┐                                       │
│                           │ Project │                                       │
│                           │ Setup   │                                       │
│                           └────┬────┘                                       │
│                                │                                            │
│                                ▼                                            │
│                           ┌─────────┐                                       │
│                           │ Database│                                       │
│                           │ Setup   │                                       │
│                           └────┬────┘                                       │
│                                │                                            │
│           ┌────────────────────┼────────────────────┐                       │
│           ▼                    ▼                    ▼                       │
│      ┌─────────┐          ┌─────────┐          ┌─────────┐                  │
│      │ Auth    │          │ Startup │          │ Valid.  │                  │
│      │ Found.  │          │ Idea    │          │ Result  │    ... more      │
│      └────┬────┘          │ Entity  │          │ Entity  │                  │
│           │               └─────────┘          └─────────┘                  │
│           │                    │                    │                       │
│           └────────────────────┼────────────────────┘                       │
│                                ▼                                            │
│                           ┌─────────┐                                       │
│                           │ Submit  │                                       │
│                           │ Idea    │                                       │
│                           │ Feature │                                       │
│                           └─────────┘                                       │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│  [Zoom +] [Zoom -] [Reset] [Export SVG]      Showing 27 nodes, 42 edges    │
│                                                                             │
│  Click a node to see details:                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Selected: Submit Startup Idea                                       │   │
│  │ Estimate: M (4-8h) | Priority: High | Layer: 4                      │   │
│  │ Depends on: Auth Foundation, StartupIdea Entity                     │   │
│  │ Blocks: View Validation Results, AI Concept Expansion               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Interactive DAG visualization
- Click to select and highlight paths
- Zoom and pan controls
- Shows "blocks" and "blocked by"
- Critical path highlighting
- Export to SVG for documentation

---

### Data Model

```python
@dataclass
class RoadmapNode:
    """A story represented as a roadmap node."""
    id: str
    title: str
    layer: int
    estimate_size: str
    estimate_hours: tuple[int, int]  # (min, max)
    priority: str
    story_type: str

    # Graph relationships
    depends_on: list[str]  # Node IDs
    blocks: list[str]      # Node IDs (reverse dependencies)

    # Computed properties
    earliest_start: int | None = None  # Computed from dependencies
    is_critical_path: bool = False     # Part of longest path


@dataclass
class RoadmapPhase:
    """A phase/milestone in the timeline view."""
    name: str
    description: str
    layers_included: list[int]
    total_hours: tuple[int, int]
    milestone_description: str  # "What you'll have"
    stories: list[RoadmapNode]


@dataclass
class Roadmap:
    """Complete roadmap model for visualization."""
    nodes: list[RoadmapNode]
    phases: list[RoadmapPhase]
    critical_path: list[str]  # Node IDs in critical path
    total_estimate: tuple[int, int]
```

---

### Implementation

#### Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Layers View | Streamlit + custom CSS | Native to our stack, swimlanes via columns |
| Timeline View | Plotly Gantt | Interactive, built-in timeline support |
| Dependency Graph | Graphviz/PyGraphviz | Standard DAG rendering, SVG export |

#### Directory Structure

```
haytham/
├── roadmap/
│   ├── __init__.py
│   ├── models.py           # RoadmapNode, RoadmapPhase, Roadmap
│   ├── builder.py          # Build roadmap from stories
│   ├── critical_path.py    # Critical path calculation
│   └── exporters.py        # SVG, PNG export

frontend_streamlit/
├── views/
│   └── roadmap.py          # New roadmap view page
├── components/
│   ├── layers_view.py      # Swimlane component
│   ├── timeline_view.py    # Gantt component
│   └── graph_view.py       # DAG component
```

#### Critical Path Algorithm

```python
def compute_critical_path(nodes: list[RoadmapNode]) -> list[str]:
    """
    Compute the critical path using longest path in DAG.

    The critical path is the sequence of dependent stories
    that determines the minimum project duration.
    """
    # Build adjacency list
    graph = {n.id: n.depends_on for n in nodes}
    hours = {n.id: n.estimate_hours[1] for n in nodes}  # Use max estimate

    # Topological sort
    sorted_nodes = topological_sort(graph)

    # Forward pass: earliest start times
    earliest = {n: 0 for n in sorted_nodes}
    for node in sorted_nodes:
        for dep in graph[node]:
            earliest[node] = max(earliest[node], earliest[dep] + hours[dep])

    # Find longest path (critical path)
    # ... standard longest path algorithm

    return critical_path_node_ids
```

#### Streamlit Integration

```python
# frontend_streamlit/views/roadmap.py

import streamlit as st
from haytham.roadmap import build_roadmap, compute_critical_path
from components.layers_view import render_layers_view
from components.timeline_view import render_timeline_view
from components.graph_view import render_graph_view


def render_roadmap():
    st.title("🗺️ Roadmap")

    # Load stories and build roadmap
    stories = load_stories()
    roadmap = build_roadmap(stories)

    # View selector
    view = st.radio(
        "View mode",
        ["Layers", "Timeline", "Graph"],
        horizontal=True,
        label_visibility="collapsed"
    )

    if view == "Layers":
        render_layers_view(roadmap)
    elif view == "Timeline":
        render_timeline_view(roadmap)
    else:
        render_graph_view(roadmap)

    # Summary stats
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Stories", len(roadmap.nodes))
    with col2:
        min_h, max_h = roadmap.total_estimate
        st.metric("Estimated Hours", f"{min_h}-{max_h}h")
    with col3:
        st.metric("Critical Path", f"{len(roadmap.critical_path)} stories")
```

---

### Navigation Integration

Add roadmap as a new view in the Streamlit navigation:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  HAYTHAM                                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  📊 Dashboard                                                               │
│  🔍 Discovery                                                               │
│  📋 MVP Spec                                                                │
│  📝 Stories          ← Current                                              │
│  🗺️ Roadmap          ← NEW                                                  │
│  ▶️ Execution                                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| View adoption | >60% of users view roadmap | Page view tracking |
| Time on page | >30s average | Analytics |
| Export usage | >20% export SVG/image | Feature tracking |
| User satisfaction | >4/5 "helps me plan" | Survey |

---

### Rollout Plan

#### Phase 1: Layers View (Week 1)
1. Implement `RoadmapNode` and `Roadmap` models
2. Build roadmap from stories with layer grouping
3. Create swimlane visualization in Streamlit
4. Add to navigation

#### Phase 2: Timeline View (Week 2)
1. Implement `RoadmapPhase` model
2. Integrate with effort estimates (ADR-011)
3. Create Plotly Gantt visualization
4. Add milestone descriptions

#### Phase 3: Dependency Graph (Week 3)
1. Implement critical path algorithm
2. Create Graphviz DAG renderer
3. Add interactivity (click to select)
4. Add SVG export

---

## Consequences

### Positive

1. **Clear execution order** — Founders know what to build first
2. **Dependency visibility** — Blockers are obvious
3. **Parallelization opportunities** — Side-by-side stories can be delegated
4. **Milestone planning** — Natural checkpoints become visible
5. **Communication tool** — Share roadmap with contractors/investors

### Negative

1. **Complexity** — Three views to build and maintain
2. **Performance** — Graph rendering may be slow for large story sets
3. **Mobile experience** — Complex visualizations don't work well on mobile

### Risks

1. **Over-engineering** — Users may only use one view
   - **Mitigation:** Launch layers view first, add others based on demand

2. **Estimate dependency** — Timeline view requires ADR-011 estimates
   - **Mitigation:** Show timeline without hours if estimates unavailable

---

## Alternatives Considered

### Alternative A: Kanban Board Only

Simple To Do / In Progress / Done columns.

**Rejected because:**
- Doesn't show dependencies or execution order
- Loses layer structure
- Standard tool, no differentiation

### Alternative B: External Tool Integration

Push to Miro/Mural for visualization.

**Rejected because:**
- Requires additional account
- Loses real-time sync with story changes
- Friction in workflow

### Alternative C: Static Image Export Only

Generate roadmap as PNG/SVG without interactive UI.

**Rejected because:**
- No drill-down capability
- Must regenerate on any change
- Poor UX for exploration

---

## References

- [ADR-010: Stories Export](./ADR-010-stories-export.md)
- [ADR-011: Story Effort Estimation](./ADR-011-story-effort-estimation.md)
- [Plotly Gantt Charts](https://plotly.com/python/gantt/)
- [Graphviz Documentation](https://graphviz.org/documentation/)
