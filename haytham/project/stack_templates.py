"""Stack templates for the Story-to-Implementation Pipeline.

Predefined technology stacks that users can choose from during
the Stack Selection phase. For POC, users select from these templates
rather than customizing individual components.

Reference: ADR-001b: Platform & Stack Proposal
"""

from .state_models import BackendStack, FrontendStack, Stack, TestingStack

# ========== Stack Templates ==========

STACK_TEMPLATES: dict[str, Stack] = {
    # ========== Web Application Stacks ==========
    "web-python-react": Stack(
        platform="web_application",
        backend=BackendStack(
            language="python",
            language_version="3.11+",
            framework="fastapi",
            orm="sqlalchemy",
            database="sqlite",
        ),
        frontend=FrontendStack(
            language="typescript",
            framework="react",
            framework_version="18+",
            bundler="vite",
            styling="tailwindcss",
        ),
        testing=TestingStack(
            backend="pytest",
            frontend="vitest",
        ),
        project_structure={
            "backend_dir": "backend/",
            "frontend_dir": "frontend/",
            "shared_dir": "shared/",
        },
    ),
    "web-python-htmx": Stack(
        platform="web_application",
        backend=BackendStack(
            language="python",
            language_version="3.11+",
            framework="fastapi",
            orm="sqlalchemy",
            database="sqlite",
        ),
        frontend=None,  # HTMX is server-rendered
        testing=TestingStack(
            backend="pytest",
            frontend="playwright",
        ),
        project_structure={
            "backend_dir": "app/",
            "templates_dir": "app/templates/",
            "static_dir": "app/static/",
        },
    ),
    "web-node-react": Stack(
        platform="web_application",
        backend=BackendStack(
            language="typescript",
            language_version="5.0+",
            framework="express",
            orm="prisma",
            database="sqlite",
        ),
        frontend=FrontendStack(
            language="typescript",
            framework="react",
            framework_version="18+",
            bundler="vite",
            styling="tailwindcss",
        ),
        testing=TestingStack(
            backend="jest",
            frontend="vitest",
        ),
        project_structure={
            "backend_dir": "server/",
            "frontend_dir": "client/",
        },
    ),
    # ========== CLI Application Stacks ==========
    "cli-python": Stack(
        platform="cli",
        backend=BackendStack(
            language="python",
            language_version="3.11+",
            framework="typer",
            orm="sqlalchemy",
            database="sqlite",
        ),
        frontend=None,
        testing=TestingStack(
            backend="pytest",
            frontend="",
        ),
        project_structure={
            "src_dir": "src/",
            "tests_dir": "tests/",
        },
    ),
    "cli-node": Stack(
        platform="cli",
        backend=BackendStack(
            language="typescript",
            language_version="5.0+",
            framework="commander",
            orm="prisma",
            database="sqlite",
        ),
        frontend=None,
        testing=TestingStack(
            backend="jest",
            frontend="",
        ),
        project_structure={
            "src_dir": "src/",
            "tests_dir": "tests/",
        },
    ),
    # ========== API-Only Stacks ==========
    "api-python": Stack(
        platform="api",
        backend=BackendStack(
            language="python",
            language_version="3.11+",
            framework="fastapi",
            orm="sqlalchemy",
            database="sqlite",
        ),
        frontend=None,
        testing=TestingStack(
            backend="pytest",
            frontend="",
        ),
        project_structure={
            "src_dir": "app/",
            "tests_dir": "tests/",
        },
    ),
    "api-node": Stack(
        platform="api",
        backend=BackendStack(
            language="typescript",
            language_version="5.0+",
            framework="express",
            orm="prisma",
            database="sqlite",
        ),
        frontend=None,
        testing=TestingStack(
            backend="jest",
            frontend="",
        ),
        project_structure={
            "src_dir": "src/",
            "tests_dir": "tests/",
        },
    ),
}


# ========== Helper Functions ==========


def get_stack_template(template_id: str) -> Stack | None:
    """Get a stack template by ID.

    Args:
        template_id: Template ID (e.g., "web-python-react")

    Returns:
        Stack template or None if not found
    """
    return STACK_TEMPLATES.get(template_id)


def get_templates_for_platform(platform: str) -> dict[str, Stack]:
    """Get all stack templates for a platform type.

    Args:
        platform: Platform type (web_application, cli, api)

    Returns:
        Dict of template_id -> Stack for matching templates
    """
    return {tid: stack for tid, stack in STACK_TEMPLATES.items() if stack.platform == platform}


def get_default_template_for_platform(platform: str) -> str | None:
    """Get the default/recommended template ID for a platform.

    Args:
        platform: Platform type (web_application, cli, api)

    Returns:
        Default template ID or None if no templates for platform
    """
    defaults = {
        "web_application": "web-python-react",
        "cli": "cli-python",
        "api": "api-python",
    }
    return defaults.get(platform)


def list_all_templates() -> list[dict]:
    """List all available templates with summary info.

    Returns:
        List of dicts with template_id, platform, and description
    """
    templates = []
    for tid, stack in STACK_TEMPLATES.items():
        backend_lang = stack.backend.language if stack.backend else "none"
        frontend_lang = stack.frontend.language if stack.frontend else "none"

        templates.append(
            {
                "id": tid,
                "platform": stack.platform,
                "backend": f"{backend_lang}/{stack.backend.framework}" if stack.backend else "none",
                "frontend": f"{frontend_lang}/{stack.frontend.framework}"
                if stack.frontend
                else "none",
            }
        )

    return templates


# ========== Platform Detection Signals ==========

PLATFORM_SIGNALS = {
    "web_application": {
        "keywords": [
            "dashboard",
            "page",
            "screen",
            "view",
            "navigate",
            "login",
            "register",
            "signup",
            "form",
            "button",
            "click",
            "display",
            "show",
            "list",
            "table",
            "card",
            "modal",
            "menu",
            "sidebar",
            "layout",
            "responsive",
            "browser",
            "web",
            "website",
            "webapp",
        ],
        "features": [
            "user authentication",
            "user interface",
            "data display",
            "interactive elements",
            "real-time updates",
            "file upload",
            "image display",
            "charts",
            "graphs",
            "notifications",
        ],
        "weight": 1.0,  # Default platform
    },
    "cli": {
        "keywords": [
            "terminal",
            "command",
            "command-line",
            "shell",
            "script",
            "batch",
            "automation",
            "pipeline",
            "cron",
            "scheduled",
            "background",
            "daemon",
            "console",
            "stdout",
            "stdin",
        ],
        "features": [
            "file processing",
            "data transformation",
            "batch operations",
            "system administration",
            "automation scripts",
            "no UI needed",
        ],
        "weight": 0.8,
    },
    "api": {
        "keywords": [
            "api",
            "endpoint",
            "rest",
            "graphql",
            "webhook",
            "integration",
            "headless",
            "microservice",
            "service",
            "backend-only",
        ],
        "features": [
            "third-party integration",
            "machine-to-machine",
            "data API",
            "webhooks",
            "no frontend needed",
            "mobile backend",
        ],
        "weight": 0.9,
    },
}


def detect_platform_signals(mvp_spec_text: str) -> dict[str, float]:
    """Detect platform signals from MVP spec text.

    Analyzes the text for keywords and features that suggest
    a particular platform type.

    Args:
        mvp_spec_text: MVP specification markdown text

    Returns:
        Dict of platform -> confidence score (0.0 to 1.0)
    """
    text_lower = mvp_spec_text.lower()
    scores: dict[str, float] = {}

    for platform, signals in PLATFORM_SIGNALS.items():
        keyword_count = sum(1 for kw in signals["keywords"] if kw in text_lower)
        feature_count = sum(1 for feat in signals["features"] if feat.lower() in text_lower)

        # Calculate score based on matches
        max_keywords = len(signals["keywords"])
        max_features = len(signals["features"])

        keyword_score = keyword_count / max_keywords if max_keywords > 0 else 0
        feature_score = feature_count / max_features if max_features > 0 else 0

        # Weighted average with platform weight
        raw_score = (keyword_score * 0.6 + feature_score * 0.4) * signals["weight"]
        scores[platform] = min(1.0, raw_score * 2)  # Scale up but cap at 1.0

    return scores


def recommend_platform(mvp_spec_text: str) -> tuple[str, dict[str, float]]:
    """Recommend a platform based on MVP spec analysis.

    Args:
        mvp_spec_text: MVP specification markdown text

    Returns:
        Tuple of (recommended_platform, all_scores)
    """
    scores = detect_platform_signals(mvp_spec_text)

    # If no clear signal, default to web_application
    if not scores or max(scores.values()) < 0.1:
        return "web_application", {"web_application": 0.5, "cli": 0.1, "api": 0.1}

    recommended = max(scores, key=lambda k: scores[k])
    return recommended, scores
