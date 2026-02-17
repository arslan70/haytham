"""
Agent Factory module for Haytham workflows.

This module provides the agent factory for creating specialist agents
used in the Burr workflow engine.

## Usage

```python
from haytham.agents.factory.agent_factory import create_agent_by_name

# Create any agent by name
agent = create_agent_by_name("concept_expansion")
result = agent("Analyze this startup idea...")
```

## Available Agents

- concept_expansion: Analyzes and expands startup ideas
- market_intelligence: Conducts market research
- competitor_analysis: Analyzes competitive landscape
- startup_validator: Assesses risks and validates assumptions
- pivot_strategy: Suggests pivot strategies for high-risk ideas
- validation_summary: Synthesizes validation findings
- mvp_scope: Defines MVP boundaries
- capability_model: Creates capability models
- build_buy_analyzer: Analyzes build vs buy decisions
- story_generator: Generates implementation stories
- idea_gatekeeper: Validates input ideas (planned)

Note: The legacy CEOAgentWorkflow class has been removed.
Use the Burr workflow engine instead for orchestration.
"""

from haytham.agents.factory.agent_factory import (
    create_agent_by_name,
)

__all__ = [
    "create_agent_by_name",
]
