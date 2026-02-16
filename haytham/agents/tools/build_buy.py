"""Build vs Buy tools for story/component analysis.

These tools allow an agent to search the service catalog and evaluate
build vs buy decisions using consistent business rules.
"""

import json
from pathlib import Path

from strands import tool


def _load_catalog_data() -> dict:
    """Load the service catalog YAML as a dictionary."""
    import yaml

    catalog_path = (
        Path(__file__).parent.parent.parent / "workflow" / "build_buy" / "service_catalog.yaml"
    )
    if not catalog_path.exists():
        return {"categories": {}, "build_categories": []}

    with open(catalog_path) as f:
        return yaml.safe_load(f)


@tool
def search_service_catalog(query: str) -> str:
    """Search the service catalog for solutions matching a story or component.

    Use this tool when analyzing a story to find existing services that could
    replace custom development. The tool searches category keywords and returns
    matching services with their details.

    Args:
        query: Search text - typically the story title and description combined.
               Example: "user authentication login password reset OAuth"

    Returns:
        JSON string with matching categories and services, or empty results if no match.
        Includes: category name, recommendation type (BUY/BUILD/HYBRID), rationale,
        and available services with pricing and integration effort.
    """
    data = _load_catalog_data()
    query_lower = query.lower()
    matches = []

    # Search buy/hybrid categories
    for category_name, category_data in data.get("categories", {}).items():
        keywords = category_data.get("keywords", [])
        for keyword in keywords:
            if keyword.lower() in query_lower:
                services = []
                for svc in category_data.get("services", []):
                    services.append(
                        {
                            "name": svc.get("name", ""),
                            "tier": svc.get("tier", "alternative"),
                            "pricing": svc.get("pricing", ""),
                            "integration_effort": svc.get("integration_effort", ""),
                            "best_for": svc.get("best_for", ""),
                        }
                    )

                matches.append(
                    {
                        "category": category_name,
                        "default_recommendation": category_data.get(
                            "default_recommendation", "BUY"
                        ),
                        "rationale": category_data.get("rationale", ""),
                        "if_you_must_build": category_data.get("if_you_must_build", ""),
                        "services": services,
                        "matched_keyword": keyword,
                    }
                )
                break  # Only match once per category

    # Search build categories
    for build_cat in data.get("build_categories", []):
        keywords = build_cat.get("keywords", [])
        for keyword in keywords:
            if keyword.lower() in query_lower:
                matches.append(
                    {
                        "category": build_cat.get("name", ""),
                        "default_recommendation": "BUILD",
                        "rationale": build_cat.get("rationale", ""),
                        "services": [],
                        "matched_keyword": keyword,
                    }
                )
                break

    return json.dumps(
        {
            "query": query,
            "matches_found": len(matches),
            "matches": matches,
        },
        indent=2,
    )


@tool
def evaluate_build_buy_decision(
    complexity_score: int,
    time_to_build_score: int,
    maintenance_burden_score: int,
    cost_at_scale_score: int,
    vendor_lock_in_score: int,
    differentiation_score: int,
) -> str:
    """Evaluate whether to BUILD, BUY, or use HYBRID approach for a component.

    Use this tool after you have assessed a component across all dimensions.
    Score each dimension from 1-5 based on the criteria below.

    Args:
        complexity_score: Technical/security complexity (1=simple CRUD, 5=security-critical like auth/payments)
        time_to_build_score: Time investment required (1=hours, 3=days, 5=weeks)
        maintenance_burden_score: Ongoing maintenance needs (1=set-and-forget, 5=constant updates needed)
        cost_at_scale_score: Cost of external service at scale (1=expensive at scale, 5=cheap/free at scale)
        vendor_lock_in_score: Risk of being locked to vendor (1=easy to switch, 5=very sticky)
        differentiation_score: How core this is to your product (1=core differentiator, 5=pure commodity)

    Returns:
        JSON with recommendation (BUILD/BUY/HYBRID), confidence, weighted score breakdown,
        and rationale explaining the decision.

    Scoring Guidelines:
        - High scores (4-5) favor BUY: complex, time-consuming, high maintenance, commodity
        - Low scores (1-2) favor BUILD: simple, quick, low maintenance, core differentiator
        - Mixed scores (2-4) often result in HYBRID approach
    """
    # Validate inputs
    scores = {
        "complexity": max(1, min(5, complexity_score)),
        "time_to_build": max(1, min(5, time_to_build_score)),
        "maintenance": max(1, min(5, maintenance_burden_score)),
        "cost_at_scale": max(1, min(5, cost_at_scale_score)),
        "lock_in_risk": max(1, min(5, vendor_lock_in_score)),
        "differentiation": max(1, min(5, differentiation_score)),
    }

    # Weights optimized for solo founders / small teams
    weights = {
        "complexity": 1.5,  # Security complexity matters most - don't DIY auth
        "time_to_build": 1.3,  # Time is precious for small teams
        "maintenance": 1.2,  # Ongoing burden adds up
        "cost_at_scale": 0.8,  # Less important at MVP stage
        "lock_in_risk": 0.7,  # Acceptable tradeoff for speed
        "differentiation": 1.5,  # Don't outsource your competitive advantage
    }

    # Calculate weighted score
    weighted_sum = sum(scores[dim] * weights[dim] for dim in scores)
    total_weight = sum(weights.values())
    weighted_score = weighted_sum / total_weight

    # Determine recommendation
    if weighted_score >= 3.5:
        recommendation = "BUY"
        confidence = "high" if weighted_score >= 4.0 else "medium"
        rationale = (
            "This component has high complexity, significant build time, and/or maintenance burden. "
            "Using an existing service will save substantial time and reduce risk. "
            "Focus your engineering effort on what differentiates your product."
        )
    elif weighted_score <= 2.0:
        recommendation = "BUILD"
        confidence = "high" if weighted_score <= 1.5 else "medium"
        rationale = (
            "This component is core to your product differentiation and/or relatively simple to build. "
            "Building it yourself gives you full control and avoids vendor dependencies. "
            "The investment is justified given its strategic importance."
        )
    else:
        recommendation = "HYBRID"
        confidence = "medium"
        rationale = (
            "This component benefits from using existing services as a foundation, "
            "but requires custom logic or integration. Use a service for the commodity parts "
            "and build your differentiated features on top."
        )

    return json.dumps(
        {
            "recommendation": recommendation,
            "confidence": confidence,
            "weighted_score": round(weighted_score, 2),
            "score_breakdown": {
                dim: {
                    "raw": scores[dim],
                    "weight": weights[dim],
                    "weighted": round(scores[dim] * weights[dim], 2),
                }
                for dim in scores
            },
            "rationale": rationale,
            "thresholds": {
                "BUY": ">= 3.5",
                "HYBRID": "2.0 - 3.5",
                "BUILD": "<= 2.0",
            },
        },
        indent=2,
    )


@tool
def estimate_integration_effort(
    service_name: str,
    story_context: str,
    has_existing_auth: bool = False,
    team_familiarity: str = "none",
) -> str:
    """Estimate the effort to integrate an external service for a story.

    Use this tool after finding a service via search_service_catalog to get
    a more refined effort estimate based on your specific context.

    Args:
        service_name: Name of the service (e.g., "Clerk", "Stripe", "Supabase")
        story_context: Description of what you need to implement
        has_existing_auth: Whether you already have authentication set up
        team_familiarity: Team's familiarity with this service ("none", "some", "expert")

    Returns:
        JSON with effort estimate (hours), breakdown of tasks, and considerations.
    """
    # Base effort by service type (heuristic)
    service_efforts = {
        # Auth services
        "clerk": {"base": 2, "category": "auth"},
        "auth0": {"base": 4, "category": "auth"},
        "supabase auth": {"base": 3, "category": "auth"},
        "firebase auth": {"base": 3, "category": "auth"},
        # Payment services
        "stripe": {"base": 6, "category": "payments"},
        "lemonsqueezy": {"base": 4, "category": "payments"},
        "paddle": {"base": 5, "category": "payments"},
        # Storage services
        "cloudflare r2": {"base": 2, "category": "storage"},
        "supabase storage": {"base": 2, "category": "storage"},
        "aws s3": {"base": 3, "category": "storage"},
        # Email services
        "resend": {"base": 2, "category": "email"},
        "sendgrid": {"base": 3, "category": "email"},
        "postmark": {"base": 2, "category": "email"},
        # Database
        "supabase": {"base": 3, "category": "database"},
        "planetscale": {"base": 4, "category": "database"},
        "neon": {"base": 3, "category": "database"},
    }

    service_lower = service_name.lower()
    service_info = service_efforts.get(service_lower, {"base": 4, "category": "general"})
    base_hours = service_info["base"]
    category = service_info["category"]

    # Adjust for familiarity
    familiarity_multiplier = {
        "none": 1.5,
        "some": 1.0,
        "expert": 0.7,
    }.get(team_familiarity, 1.0)

    # Adjust if auth already exists (reduces effort for many integrations)
    if has_existing_auth and category != "auth":
        base_hours = base_hours * 0.8

    estimated_hours = round(base_hours * familiarity_multiplier, 1)

    # Build task breakdown
    tasks = []
    if category == "auth":
        tasks = [
            "Set up service account and configure OAuth providers",
            "Install SDK and configure environment variables",
            "Implement sign-up / sign-in flows",
            "Add session management and protected routes",
            "Test edge cases (password reset, email verification)",
        ]
    elif category == "payments":
        tasks = [
            "Set up Stripe/service account and configure products",
            "Install SDK and configure webhooks",
            "Implement checkout flow",
            "Handle subscription lifecycle events",
            "Test with test cards and edge cases",
        ]
    elif category == "storage":
        tasks = [
            "Configure bucket and access policies",
            "Install SDK and configure credentials",
            "Implement upload/download functions",
            "Add file validation and error handling",
        ]
    elif category == "email":
        tasks = [
            "Set up service account and verify domain",
            "Install SDK and configure templates",
            "Implement send functions",
            "Add error handling and retry logic",
        ]
    else:
        tasks = [
            "Review service documentation",
            "Set up account and configure credentials",
            "Install SDK and implement integration",
            "Test and handle edge cases",
        ]

    return json.dumps(
        {
            "service": service_name,
            "estimated_hours": estimated_hours,
            "estimate_range": f"{max(1, estimated_hours - 1)}-{estimated_hours + 2} hours",
            "factors": {
                "base_effort": f"{base_hours} hours",
                "familiarity_adjustment": f"{familiarity_multiplier}x ({team_familiarity})",
                "has_existing_auth": has_existing_auth,
            },
            "task_breakdown": tasks,
            "considerations": [
                "Estimates assume modern framework (Next.js, etc.) with good SDK support",
                "Add 20-30% buffer for unexpected issues",
                "First-time setup takes longer; subsequent integrations are faster",
            ],
        },
        indent=2,
    )
