# ADR-010: Stories Export to External Tools

## Status
**Proposed** — 2026-01-19

## Context

### Current State

After completing Workflow 3 (Story Generation), the system produces:
- `session/generated_stories.json` — 20-30 implementation-ready stories
- Each story includes title, description, acceptance criteria, labels, dependencies, priority, and execution order

```json
{
  "title": "Submit Startup Idea",
  "description": "Allow users to submit startup ideas with title, description, industry, and target market",
  "acceptance_criteria": [
    "Given an authenticated user, when they POST to /api/v1/ideas...",
    "Given missing required field, when user submits idea, then response 400..."
  ],
  "labels": ["implements:CAP-F-001", "type:feature", "layer:4"],
  "dependencies": ["Create StartupIdea Entity Model", "Authentication Foundation"],
  "priority": "high",
  "order": 13
}
```

### The Problem

**The generated stories are stranded.** A semi-technical solo founder — our primary persona — cannot easily use them:

| Current State | User Impact |
|---------------|-------------|
| Stories are JSON | Cannot import into project management tools |
| No export UI | Must manually copy-paste or write scripts |
| No format options | Each tool (Linear, Jira, Notion) needs different formats |
| Dependencies are title-based | External tools use IDs, not human-readable references |

### Dogfood Evidence

Running Haytham through itself revealed:
- The **stories are the most valuable output** — 27 implementation-ready tasks
- But a solo founder **cannot use them without technical effort**
- This is a critical gap in the value chain

### User Research

| Persona | Tool Preference | Export Need |
|---------|-----------------|-------------|
| Solo technical founder | Linear, GitHub Issues | Bulk import with dependencies |
| Non-technical founder | Notion, Trello | Kanban board format |
| Agency/Contractor handoff | Jira, Asana | Full metadata + estimates |
| Claude Code user | Backlog.md | Already supported via MCP |

---

## Decision

### Implement Multi-Format Story Export

We will add an export system that transforms `generated_stories.json` into formats compatible with popular project management tools.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        STORIES EXPORT ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐  │
│  │ generated_      │────▶│ Export           │────▶│ Format-specific     │  │
│  │ stories.json    │     │ Transformer      │     │ Output              │  │
│  └─────────────────┘     └──────────────────┘     └─────────────────────┘  │
│                                   │                                         │
│                                   ▼                                         │
│                          ┌──────────────────┐                               │
│                          │ Format Adapters  │                               │
│                          ├──────────────────┤                               │
│                          │ • LinearAdapter  │                               │
│                          │ • JiraAdapter    │                               │
│                          │ • NotionAdapter  │                               │
│                          │ • GitHubAdapter  │                               │
│                          │ • MarkdownAdapter│                               │
│                          │ • CSVAdapter     │                               │
│                          └──────────────────┘                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Supported Export Formats

#### Tier 1: File-Based Exports (MVP)

| Format | File Type | Use Case |
|--------|-----------|----------|
| **Linear CSV** | `.csv` | Bulk import via Linear's CSV importer |
| **Jira CSV** | `.csv` | Bulk import via Jira's external data import |
| **Markdown** | `.md` | Human-readable, Claude Code friendly |
| **Generic CSV** | `.csv` | Spreadsheet review, custom imports |

#### Tier 2: API-Based Exports (Post-MVP)

| Format | Integration | Use Case |
|--------|-------------|----------|
| **Linear API** | Direct push | One-click project setup |
| **GitHub Issues** | Direct push | Developer-native workflow |
| **Notion API** | Direct push | Non-technical founder workflow |

---

### Export Data Model

```python
@dataclass
class ExportableStory:
    """Normalized story format for export transformation."""

    # Core fields (always exported)
    id: str                          # Generated: STORY-001, STORY-002, etc.
    title: str
    description: str
    acceptance_criteria: list[str]
    priority: str                    # high, medium, low
    order: int                       # Execution order

    # Metadata (format-dependent)
    labels: list[str]                # implements:CAP-F-001, type:feature, etc.
    layer: int                       # Extracted from labels (1-4)
    story_type: str                  # Extracted: bootstrap, entity, infrastructure, feature

    # Dependencies (transformed per format)
    dependencies: list[str]          # Original: title-based
    dependency_ids: list[str]        # Transformed: STORY-XXX references

    # Optional enrichment
    estimate: str | None             # T-shirt size: XS, S, M, L, XL
    epic: str | None                 # Grouped by layer or capability
```

---

### Format Specifications

#### Linear CSV Format

Linear's CSV importer expects:

```csv
Title,Description,Priority,Labels,Parent Issue
"Initialize Project Structure","Set up the project with chosen tech stack...","High","bootstrap,layer-1",""
"Database Setup and Configuration","Configure database connection...","High","bootstrap,layer-1","Initialize Project Structure"
```

**Mapping:**

| Our Field | Linear Field | Transformation |
|-----------|--------------|----------------|
| `title` | Title | Direct |
| `description` + `acceptance_criteria` | Description | Concatenate with markdown |
| `priority` | Priority | Capitalize: high → High |
| `labels` | Labels | Comma-separated, cleaned |
| `dependencies[0]` | Parent Issue | First dependency only (Linear limitation) |

#### Jira CSV Format

Jira's external import expects:

```csv
Summary,Description,Issue Type,Priority,Labels,Linked Issues
"Initialize Project Structure","Set up the project...","Story","High","bootstrap","blocks STORY-002, blocks STORY-003"
```

**Mapping:**

| Our Field | Jira Field | Transformation |
|-----------|------------|----------------|
| `title` | Summary | Direct |
| `description` + `acceptance_criteria` | Description | Wiki markup format |
| `story_type` | Issue Type | Map: bootstrap→Task, feature→Story |
| `priority` | Priority | Map: high→High, medium→Medium |
| `dependencies` | Linked Issues | "blocks STORY-XXX" format |

#### Markdown Format

Human-readable format for documentation or Claude Code:

```markdown
# Generated Stories

## Layer 1: Bootstrap (3 stories)

### STORY-001: Initialize Project Structure
**Priority:** High | **Type:** Bootstrap | **Estimate:** M

Set up the project with chosen tech stack, dependencies, and tooling

**Acceptance Criteria:**
- [ ] Project initialized with Python/FastAPI framework
- [ ] Dependencies installed: SQLAlchemy ORM, JWT auth library...
- [ ] Linting and formatting configured with Black and Flake8

**Dependencies:** None

---

### STORY-002: Database Setup and Configuration
**Priority:** High | **Type:** Bootstrap | **Estimate:** M

**Dependencies:** STORY-001

...
```

#### Generic CSV Format

Universal format for spreadsheet review:

```csv
ID,Title,Description,Acceptance Criteria,Priority,Type,Layer,Dependencies,Labels,Order
STORY-001,"Initialize Project Structure","Set up the project...","1. Project initialized with...",High,bootstrap,1,"",bootstrap|layer-1,1
STORY-002,"Database Setup and Configuration","Configure database...","1. Database connection...",High,bootstrap,1,STORY-001,bootstrap|layer-1,2
```

---

### User Interface

#### Stories View Export Panel

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  📋 GENERATED STORIES (27)                                    [Export ▼]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Export dropdown reveals:                                                   │
│  ┌─────────────────────────────────────┐                                   │
│  │ 📥 Export Stories                   │                                   │
│  ├─────────────────────────────────────┤                                   │
│  │ 📊 Linear (CSV)                     │                                   │
│  │ 🎫 Jira (CSV)                       │                                   │
│  │ 📝 Markdown                         │                                   │
│  │ 📄 Generic CSV                      │                                   │
│  ├─────────────────────────────────────┤                                   │
│  │ ⚙️  Export Settings...              │                                   │
│  └─────────────────────────────────────┘                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Export Settings Modal

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ⚙️  EXPORT SETTINGS                                              [×]      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Include in export:                                                         │
│  ☑ Acceptance criteria                                                      │
│  ☑ Dependencies                                                             │
│  ☑ Labels                                                                   │
│  ☐ T-shirt estimates (experimental)                                         │
│                                                                             │
│  Story ID prefix: [STORY-    ]                                              │
│                                                                             │
│  Filter by layer:                                                           │
│  ☑ Layer 1: Bootstrap    (3 stories)                                        │
│  ☑ Layer 2: Entities     (6 stories)                                        │
│  ☑ Layer 3: Infrastructure (3 stories)                                      │
│  ☑ Layer 4: Features     (15 stories)                                       │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│                                              [Cancel]  [Export Selected]    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Implementation

#### Directory Structure

```
haytham/
├── exporters/
│   ├── __init__.py
│   ├── base.py              # BaseExporter ABC
│   ├── models.py            # ExportableStory dataclass
│   ├── transformer.py       # JSON → ExportableStory transformation
│   ├── linear_exporter.py   # Linear CSV format
│   ├── jira_exporter.py     # Jira CSV format
│   ├── markdown_exporter.py # Markdown format
│   └── csv_exporter.py      # Generic CSV format

frontend_streamlit/
├── views/
│   └── stories.py           # Add export UI components
├── lib/
│   └── export_utils.py      # Streamlit download helpers
```

#### Core Classes

```python
# haytham/exporters/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import BinaryIO

from .models import ExportableStory


class BaseExporter(ABC):
    """Base class for all story exporters."""

    format_name: str
    file_extension: str
    mime_type: str

    @abstractmethod
    def export(self, stories: list[ExportableStory]) -> str:
        """Transform stories to export format string."""
        pass

    def export_to_file(self, stories: list[ExportableStory], file: BinaryIO) -> None:
        """Write exported content to file."""
        content = self.export(stories)
        file.write(content.encode('utf-8'))

    def get_filename(self, project_name: str) -> str:
        """Generate export filename."""
        safe_name = project_name.lower().replace(' ', '-')
        return f"{safe_name}-stories.{self.file_extension}"
```

```python
# haytham/exporters/transformer.py

import json
from pathlib import Path

from .models import ExportableStory


def load_stories(session_path: Path) -> list[ExportableStory]:
    """Load and transform stories from generated_stories.json."""

    stories_file = session_path / "generated_stories.json"
    with open(stories_file) as f:
        raw_stories = json.load(f)

    # Build title → ID mapping for dependency resolution
    title_to_id = {
        story["title"]: f"STORY-{i+1:03d}"
        for i, story in enumerate(raw_stories)
    }

    exportable = []
    for i, story in enumerate(raw_stories):
        story_id = f"STORY-{i+1:03d}"

        # Extract layer from labels
        layer = 4  # default
        for label in story.get("labels", []):
            if label.startswith("layer:"):
                layer = int(label.split(":")[1])
                break

        # Extract story type from labels
        story_type = "feature"
        for label in story.get("labels", []):
            if label.startswith("type:"):
                story_type = label.split(":")[1]
                break

        # Transform dependencies to IDs
        dependency_ids = [
            title_to_id[dep]
            for dep in story.get("dependencies", [])
            if dep in title_to_id
        ]

        exportable.append(ExportableStory(
            id=story_id,
            title=story["title"],
            description=story["description"],
            acceptance_criteria=story.get("acceptance_criteria", []),
            priority=story.get("priority", "medium"),
            order=story.get("order", i + 1),
            labels=story.get("labels", []),
            layer=layer,
            story_type=story_type,
            dependencies=story.get("dependencies", []),
            dependency_ids=dependency_ids,
            estimate=None,  # Future: AI-generated estimates
            epic=None,      # Future: Capability grouping
        ))

    return exportable
```

```python
# haytham/exporters/linear_exporter.py

import csv
import io

from .base import BaseExporter
from .models import ExportableStory


class LinearExporter(BaseExporter):
    """Export stories to Linear-compatible CSV format."""

    format_name = "Linear"
    file_extension = "csv"
    mime_type = "text/csv"

    def export(self, stories: list[ExportableStory]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        # Linear CSV headers
        writer.writerow([
            "Title",
            "Description",
            "Priority",
            "Labels",
            "Parent Issue"
        ])

        for story in stories:
            # Build description with acceptance criteria
            description = story.description
            if story.acceptance_criteria:
                description += "\n\n## Acceptance Criteria\n"
                for ac in story.acceptance_criteria:
                    description += f"- [ ] {ac}\n"

            # Clean labels for Linear (remove colons)
            labels = ",".join(
                label.replace(":", "-")
                for label in story.labels
            )

            # Linear only supports single parent
            parent = story.dependencies[0] if story.dependencies else ""

            writer.writerow([
                story.title,
                description,
                story.priority.capitalize(),
                labels,
                parent
            ])

        return output.getvalue()
```

#### Streamlit Integration

```python
# frontend_streamlit/views/stories.py (additions)

import streamlit as st
from pathlib import Path

from haytham.exporters import (
    LinearExporter,
    JiraExporter,
    MarkdownExporter,
    CSVExporter,
    load_stories,
)


def render_export_button():
    """Render the export dropdown and handle downloads."""

    session_path = Path("session")
    stories = load_stories(session_path)

    exporters = {
        "Linear (CSV)": LinearExporter(),
        "Jira (CSV)": JiraExporter(),
        "Markdown": MarkdownExporter(),
        "Generic CSV": CSVExporter(),
    }

    col1, col2 = st.columns([3, 1])

    with col2:
        format_choice = st.selectbox(
            "Export format",
            options=list(exporters.keys()),
            label_visibility="collapsed",
        )

        exporter = exporters[format_choice]
        content = exporter.export(stories)
        filename = exporter.get_filename(st.session_state.get("project_name", "project"))

        st.download_button(
            label=f"📥 Export to {exporter.format_name}",
            data=content,
            file_name=filename,
            mime=exporter.mime_type,
        )
```

---

### Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Export completion rate | >90% of users who view stories | Track export button clicks |
| Format coverage | 4 formats in MVP | Count implemented exporters |
| Import success rate | >95% successful imports | User feedback + support tickets |
| Time to first export | <30 seconds from stories view | UX timing measurement |

---

### Rollout Plan

#### Phase 1: File-Based Exports (Week 1-2)

1. Implement `ExportableStory` model and transformer
2. Implement `LinearExporter` and `MarkdownExporter`
3. Add export UI to stories view
4. Manual testing with Linear import

#### Phase 2: Additional Formats (Week 3)

1. Implement `JiraExporter` and `CSVExporter`
2. Add export settings modal
3. Add layer filtering

#### Phase 3: Enrichment (Week 4+)

1. Add T-shirt size estimation (AI-generated)
2. Add epic grouping by capability
3. Evaluate API-based exports for Tier 2

---

## Consequences

### Positive

1. **Immediate usability** — Stories become actionable without technical effort
2. **Tool flexibility** — Users can use their preferred project management tool
3. **Handoff ready** — Solo founders can share with contractors/agencies
4. **Reduced friction** — One-click from validation to project backlog

### Negative

1. **Format maintenance** — Must track changes to Linear/Jira import formats
2. **Lossy transformation** — Some metadata may not map to all tools
3. **No round-trip** — Changes in external tools don't sync back

### Risks

1. **Format drift** — External tools may change import formats
   - **Mitigation:** Version exporters, monitor tool changelogs

2. **Dependency mapping** — Complex dependencies may not import correctly
   - **Mitigation:** Document limitations, provide manual linking instructions

---

## Alternatives Considered

### Alternative A: API-First Integration

Build direct API integrations with Linear, Jira, Notion from the start.

**Rejected because:**
- Requires OAuth setup and API key management
- Higher complexity for MVP
- File-based import is sufficient for initial validation
- Can add API integrations in Phase 2 based on demand

### Alternative B: Single Universal Format

Export only to a universal format (like CSV) and let users transform.

**Rejected because:**
- Poor UX — users must learn each tool's import quirks
- Acceptance criteria formatting differs per tool
- Dependencies handled differently everywhere
- Our value is removing this friction

### Alternative C: Backlog.md Only

Rely solely on Backlog.md MCP integration for Claude Code users.

**Rejected because:**
- Only serves Claude Code users
- Non-technical founders need GUI tools
- Agencies/contractors often mandate specific tools

---

## References

- [ADR-009: Workflow Separation](./ADR-009-workflow-separation.md)
- [Linear CSV Import Documentation](https://linear.app/docs/import-issues)
- [Jira CSV Import Documentation](https://support.atlassian.com/jira-cloud-administration/docs/import-data-from-a-csv-file/)
