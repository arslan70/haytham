"""Tests for agent output quality - validates principles, not specific content.

These tests validate that agent outputs follow the structural rules defined in prompts:
- Capability model traceability to MVP scope
- Build/Buy recommendations exclude frameworks
- Services map to capabilities
- No duplicates across sections
- Deployment infrastructure matches project type

These are schema-based validation tests that work with any agent output,
not tied to specific test fixtures. They enforce PRINCIPLES, not PRESCRIPTIONS.
"""

import re

import pytest

# =============================================================================
# Helper Functions
# =============================================================================


def extract_in_scope_items(mvp_scope: dict | str) -> list[str]:
    """Extract IN SCOPE items from MVP scope output."""
    if isinstance(mvp_scope, str):
        # Parse from markdown format
        items = []
        in_scope_section = False
        for line in mvp_scope.split("\n"):
            if "IN SCOPE" in line.upper():
                in_scope_section = True
                continue
            if in_scope_section and line.strip().startswith(("-", "|")):
                # Extract item text
                item = line.strip().lstrip("-|").split("|")[0].strip()
                if item and item not in ("IN SCOPE", "IN SCOPE (MVP v1)"):
                    items.append(item)
            if in_scope_section and "OUT OF SCOPE" in line.upper():
                break
        return items
    elif isinstance(mvp_scope, dict):
        return mvp_scope.get("in_scope", [])
    return []


def extract_out_of_scope_items(mvp_scope: dict | str) -> list[str]:
    """Extract OUT OF SCOPE items from MVP scope output."""
    if isinstance(mvp_scope, str):
        items = []
        out_scope_section = False
        for line in mvp_scope.split("\n"):
            if "OUT OF SCOPE" in line.upper():
                out_scope_section = True
                continue
            if out_scope_section and line.strip().startswith(("-", "|")):
                item = line.strip().lstrip("-|").split("|")[0].strip()
                if item and item not in ("OUT OF SCOPE", "OUT OF SCOPE (Future)"):
                    items.append(item)
            if out_scope_section and "SUCCESS" in line.upper():
                break
        return items
    elif isinstance(mvp_scope, dict):
        return mvp_scope.get("out_of_scope", [])
    return []


def extract_flow_count(mvp_scope: dict | str) -> int:
    """Count the number of flows defined in MVP scope."""
    if isinstance(mvp_scope, str):
        # Count "Flow N:" or "### Flow N" patterns
        flow_pattern = r"(?:###\s*)?Flow\s*(\d+)"
        matches = re.findall(flow_pattern, mvp_scope)
        if matches:
            return max(int(m) for m in matches)
        return 0
    elif isinstance(mvp_scope, dict):
        flows = mvp_scope.get("flows", [])
        return len(flows)
    return 0


def extract_flow_number(flow_ref: str) -> int:
    """Extract flow number from a flow reference string."""
    match = re.search(r"Flow\s*(\d+)", flow_ref, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 0


def infer_project_type(mvp_scope: dict | str) -> str:
    """Infer project type from MVP scope content."""
    content = mvp_scope if isinstance(mvp_scope, str) else str(mvp_scope)
    content_lower = content.lower()

    if any(kw in content_lower for kw in ["cli", "command line", "terminal", "package"]):
        return "cli_tool"
    elif any(kw in content_lower for kw in ["rest api", "api service", "api endpoint"]):
        return "api_service"
    elif any(kw in content_lower for kw in ["mobile app", "ios", "android"]):
        return "mobile_app"
    elif any(kw in content_lower for kw in ["iot", "embedded", "device", "sensor"]):
        return "iot_device"
    else:
        return "web_app"


def extract_flows(mvp_scope: dict | str) -> list[dict]:
    """Extract flow details from MVP scope."""
    if isinstance(mvp_scope, dict):
        return mvp_scope.get("flows", [])

    # Parse from markdown
    flows = []
    current_flow = None
    for line in mvp_scope.split("\n"):
        flow_match = re.match(r"(?:###\s*)?Flow\s*(\d+)", line)
        if flow_match:
            if current_flow:
                flows.append(current_flow)
            current_flow = {"number": int(flow_match.group(1)), "trigger": "", "steps": []}
        elif current_flow:
            if "trigger" in line.lower():
                current_flow["trigger"] = line.split(":", 1)[-1].strip()
            elif line.strip().startswith(("1.", "2.", "3.", "4.", "5.")):
                current_flow["steps"].append(line.strip())
    if current_flow:
        flows.append(current_flow)
    return flows


# =============================================================================
# Test Classes
# =============================================================================


class TestCapabilityModelQuality:
    """Validate capability model traceability and structure."""

    def test_capabilities_trace_to_scope(self, capability_model: dict, mvp_scope: dict | str):
        """Every capability must reference an actual IN SCOPE item."""
        in_scope_items = extract_in_scope_items(mvp_scope)
        if not in_scope_items:
            pytest.skip("No IN SCOPE items found in MVP scope")

        capabilities = capability_model.get("capabilities", {})
        functional = capabilities.get("functional", [])

        for cap in functional:
            serves = cap.get("serves_scope_item", "")
            if not serves:
                pytest.fail(
                    f"Capability '{cap.get('name', 'unknown')}' has empty serves_scope_item"
                )

            # Check that serves_scope_item relates to an IN SCOPE item
            # Allow partial matches since wording may differ slightly
            matched = any(
                item.lower() in serves.lower() or serves.lower() in item.lower()
                for item in in_scope_items
            )
            if not matched:
                # Check for keyword overlap
                serves_words = set(serves.lower().split())
                for item in in_scope_items:
                    item_words = set(item.lower().split())
                    overlap = serves_words & item_words
                    # Exclude common words
                    overlap -= {"the", "a", "an", "with", "and", "or", "to", "for", "of"}
                    if len(overlap) >= 2:
                        matched = True
                        break

            assert matched, (
                f"Capability '{cap.get('name')}' serves_scope_item '{serves}' "
                f"doesn't trace to any IN SCOPE item: {in_scope_items}"
            )

    def test_flow_references_exist(self, capability_model: dict, mvp_scope: dict | str):
        """Flow references must exist in MVP scope."""
        defined_flows = extract_flow_count(mvp_scope)
        if defined_flows == 0:
            pytest.skip("No flows defined in MVP scope")

        capabilities = capability_model.get("capabilities", {})
        functional = capabilities.get("functional", [])

        for cap in functional:
            flow_ref = cap.get("user_flow", "")
            if flow_ref:
                flow_num = extract_flow_number(flow_ref)
                assert flow_num <= defined_flows, (
                    f"Capability '{cap.get('name')}' references {flow_ref} "
                    f"but only {defined_flows} flows are defined"
                )

    def test_no_supporting_flow_references(self, capability_model: dict):
        """Capabilities must not use 'Supporting flow' as flow reference."""
        capabilities = capability_model.get("capabilities", {})
        functional = capabilities.get("functional", [])

        for cap in functional:
            flow_ref = cap.get("user_flow", "").lower()
            assert "supporting" not in flow_ref, (
                f"Capability '{cap.get('name')}' uses invalid flow reference: "
                f"'{cap.get('user_flow')}'. Must be Flow 1, Flow 2, or Flow 3."
            )

    def test_capability_count_proportional_to_scope(
        self, capability_model: dict, mvp_scope: dict | str
    ):
        """Capability count should be within ±2 of IN SCOPE count."""
        in_scope_items = extract_in_scope_items(mvp_scope)
        if not in_scope_items:
            pytest.skip("No IN SCOPE items found in MVP scope")

        capabilities = capability_model.get("capabilities", {})
        functional = capabilities.get("functional", [])

        diff = abs(len(functional) - len(in_scope_items))
        assert diff <= 2, (
            f"Capability count ({len(functional)}) differs significantly from "
            f"IN SCOPE count ({len(in_scope_items)}). Difference: {diff}"
        )


class TestBuildBuyQuality:
    """Validate build/buy recommendations."""

    # Framework keywords that should NOT be in build/buy recommendations
    FRAMEWORK_KEYWORDS = [
        "react",
        "vue",
        "angular",
        "svelte",
        "solid",  # Frontend frameworks
        "tailwind",
        "bootstrap",
        "material",
        "chakra",  # CSS frameworks
        "express",
        "fastapi",
        "django",
        "rails",
        "flask",
        "nestjs",  # Backend frameworks
        "vite",
        "webpack",
        "parcel",
        "esbuild",  # Build tools
        "next.js",
        "nextjs",
        "nuxt",
        "remix",  # Meta-frameworks (acceptable exception)
    ]

    # Future/deferral keywords that indicate non-MVP items
    FUTURE_KEYWORDS = ["future", "not needed", "v2", "phase 2", "later", "optional"]

    def test_no_framework_recommendations(self, build_buy_output: dict):
        """Frameworks are not infrastructure - should not be in recommendations."""
        recommended = build_buy_output.get("recommended_stack", [])

        for service in recommended:
            name_lower = service.get("name", "").lower()
            category_lower = service.get("category", "").lower()

            for fw in self.FRAMEWORK_KEYWORDS:
                # Allow meta-frameworks that include hosting (Next.js on Vercel, etc.)
                if fw in ("next.js", "nextjs", "nuxt", "remix"):
                    continue

                assert fw not in name_lower, (
                    f"Framework '{service.get('name')}' should not be in "
                    "build/buy recommendations. Frameworks are implementation choices."
                )

                # Also check category
                assert fw not in category_lower, (
                    f"Framework '{fw}' found in category for '{service.get('name')}'. "
                    "Build/buy is for infrastructure, not frameworks."
                )

    def test_all_services_serve_capabilities(self, build_buy_output: dict):
        """Every service must serve at least one capability."""
        recommended = build_buy_output.get("recommended_stack", [])

        for service in recommended:
            caps = service.get("capabilities_served", [])
            assert len(caps) > 0, (
                f"Service '{service.get('name')}' has empty capabilities_served. "
                "Every service must map to at least one capability."
            )

    def test_no_future_items_in_stack(self, build_buy_output: dict):
        """No 'future' or 'not needed for MVP' items in recommended stack."""
        recommended = build_buy_output.get("recommended_stack", [])

        for service in recommended:
            category = service.get("category", "").lower()
            rationale = service.get("rationale", "").lower()

            for kw in self.FUTURE_KEYWORDS:
                assert kw not in category, (
                    f"Service '{service.get('name')}' has '{kw}' in category. "
                    "Future items should not be in recommended_stack."
                )

            # Check rationale for "not needed for MVP"
            assert "not needed for mvp" not in rationale, (
                f"Service '{service.get('name')}' rationale says it's not needed. "
                "Remove items not needed for MVP from recommended_stack."
            )
            assert "not required for mvp" not in rationale, (
                f"Service '{service.get('name')}' rationale says it's not required. "
                "Remove items not required for MVP from recommended_stack."
            )

    def test_no_duplicates_across_sections(self, build_buy_output: dict):
        """Service cannot be in both recommended_stack and alternatives."""
        recommended = build_buy_output.get("recommended_stack", [])
        recommended_names = {s.get("name", "").lower() for s in recommended}

        alternatives = build_buy_output.get("alternatives", [])
        for alt_section in alternatives:
            for alt in alt_section.get("alternatives", []):
                alt_name = alt.get("name", "").lower()
                assert alt_name not in recommended_names, (
                    f"Service '{alt.get('name')}' appears in both recommended_stack "
                    "and alternatives. Remove from alternatives."
                )

    def test_deployment_infrastructure_present(self, build_buy_output: dict, mvp_scope: dict | str):
        """Appropriate deployment infrastructure for project type."""
        project_type = infer_project_type(mvp_scope)
        recommended = build_buy_output.get("recommended_stack", [])

        if project_type == "web_app":
            hosting_keywords = [
                "hosting",
                "deploy",
                "vercel",
                "netlify",
                "railway",
                "render",
                "fly",
                "heroku",
                "aws",
                "gcp",
                "azure",
            ]
            categories = [s.get("category", "").lower() for s in recommended]
            names = [s.get("name", "").lower() for s in recommended]

            has_hosting = any(
                any(kw in cat or kw in name for kw in hosting_keywords)
                for cat, name in zip(categories, names, strict=False)
            )
            assert has_hosting, (
                "Web app should have hosting/deployment infrastructure in recommendations"
            )

        elif project_type == "cli_tool":
            # CLI tools should NOT have web hosting
            web_hosting = ["vercel", "netlify", "heroku"]
            names = [s.get("name", "").lower() for s in recommended]
            for name in names:
                for kw in web_hosting:
                    assert kw not in name, (
                        f"CLI tool should not have web hosting '{kw}' in recommendations"
                    )


class TestMVPScopeConsistency:
    """Validate MVP scope internal consistency."""

    def test_flow_triggers_use_in_scope_features(self, mvp_scope: dict | str):
        """Flow triggers must not reference OUT OF SCOPE features."""
        out_scope = extract_out_of_scope_items(mvp_scope)
        flows = extract_flows(mvp_scope)

        if not flows or not out_scope:
            pytest.skip("No flows or out of scope items to check")

        for flow in flows:
            trigger = flow.get("trigger", "").lower()
            if not trigger:
                continue

            # Check that trigger doesn't require OUT OF SCOPE features
            for out_item in out_scope:
                # Check significant keywords (ignore common words)
                keywords = out_item.lower().split()
                significant_keywords = [
                    kw
                    for kw in keywords
                    if len(kw) > 4 and kw not in ("users", "basic", "simple", "other")
                ]

                for kw in significant_keywords:
                    if kw in trigger:
                        pytest.fail(
                            f"Flow trigger '{trigger}' may reference OUT OF SCOPE "
                            f"item '{out_item}' via keyword '{kw}'"
                        )


# =============================================================================
# Negative Tests — Verify validators catch real problems
# =============================================================================


class TestCapabilityModelNegative:
    """Verify validators catch invalid capability models."""

    def test_rejects_empty_serves_scope_item(self, mvp_scope):
        """Capability with empty serves_scope_item is caught."""
        bad_model = {
            "capabilities": {
                "functional": [
                    {
                        "id": "CAP-001",
                        "name": "Orphan Feature",
                        "serves_scope_item": "",
                        "user_flow": "Flow 1",
                    },
                ],
            }
        }
        errors = validate_capability_model(bad_model, mvp_scope)
        assert any("empty serves_scope_item" in e for e in errors)

    def test_rejects_supporting_flow_reference(self, mvp_scope):
        """'Supporting flow' reference is caught."""
        bad_model = {
            "capabilities": {
                "functional": [
                    {
                        "id": "CAP-001",
                        "name": "Background Sync",
                        "serves_scope_item": "User registration and login",
                        "user_flow": "Supporting flow",
                    },
                ],
            }
        }
        errors = validate_capability_model(bad_model, mvp_scope)
        assert any("Supporting flow" in e for e in errors)

    def test_rejects_nonexistent_flow_reference(self, mvp_scope):
        """Reference to Flow 99 when only 2 flows exist is caught."""
        bad_model = {
            "capabilities": {
                "functional": [
                    {
                        "id": "CAP-001",
                        "name": "Time Travel",
                        "serves_scope_item": "User registration and login",
                        "user_flow": "Flow 99",
                    },
                ],
            }
        }
        errors = validate_capability_model(bad_model, mvp_scope)
        assert any("Flow 99" in e for e in errors)


class TestBuildBuyNegative:
    """Verify validators catch invalid build/buy output."""

    def test_rejects_framework_in_stack(self):
        """Framework in recommended_stack is caught."""
        bad_output = {
            "recommended_stack": [
                {
                    "name": "React",
                    "category": "Frontend Framework",
                    "capabilities_served": ["CAP-001"],
                    "rationale": "Popular UI library.",
                },
            ],
            "alternatives": [],
        }
        errors = validate_build_buy(bad_output)
        assert any("react" in e.lower() for e in errors)

    def test_rejects_empty_capabilities_served(self):
        """Service with no capabilities_served is caught."""
        bad_output = {
            "recommended_stack": [
                {
                    "name": "RandomService",
                    "category": "Mystery",
                    "capabilities_served": [],
                    "rationale": "No clear purpose.",
                },
            ],
            "alternatives": [],
        }
        errors = validate_build_buy(bad_output)
        assert any("empty capabilities_served" in e for e in errors)

    def test_rejects_duplicate_across_sections(self):
        """Service in both recommended and alternatives is caught."""
        bad_output = {
            "recommended_stack": [
                {
                    "name": "Supabase",
                    "category": "Database",
                    "capabilities_served": ["CAP-001"],
                    "rationale": "Managed Postgres.",
                },
            ],
            "alternatives": [
                {
                    "alternatives": [
                        {"name": "Supabase", "rationale": "Also an alternative."},
                    ],
                },
            ],
        }
        errors = validate_build_buy(bad_output)
        assert any("both recommended and alternatives" in e.lower() for e in errors)


# =============================================================================
# Standalone Validation Functions (for use outside pytest)
# =============================================================================


def validate_capability_model(capability_model: dict, mvp_scope: dict | str) -> list[str]:
    """
    Validate capability model against MVP scope.
    Returns list of validation errors (empty if valid).
    """
    errors = []
    defined_flows = extract_flow_count(mvp_scope)

    capabilities = capability_model.get("capabilities", {})
    functional = capabilities.get("functional", [])

    for cap in functional:
        # Check serves_scope_item
        serves = cap.get("serves_scope_item", "")
        if not serves:
            errors.append(f"Capability '{cap.get('name')}' has empty serves_scope_item")

        # Check flow reference
        flow_ref = cap.get("user_flow", "")
        if "supporting" in flow_ref.lower():
            errors.append(f"Capability '{cap.get('name')}' uses invalid 'Supporting flow'")

        if flow_ref and defined_flows > 0:
            flow_num = extract_flow_number(flow_ref)
            if flow_num > defined_flows:
                errors.append(
                    f"Capability '{cap.get('name')}' references Flow {flow_num} "
                    f"but only {defined_flows} flows defined"
                )

    return errors


def validate_build_buy(build_buy_output: dict) -> list[str]:
    """
    Validate build/buy output structure.
    Returns list of validation errors (empty if valid).
    """
    errors = []
    recommended = build_buy_output.get("recommended_stack", [])
    recommended_names = {s.get("name", "").lower() for s in recommended}

    frameworks = [
        "react",
        "vue",
        "angular",
        "tailwind",
        "bootstrap",
        "express",
        "fastapi",
        "django",
    ]

    for service in recommended:
        name_lower = service.get("name", "").lower()

        # Check for frameworks
        for fw in frameworks:
            if fw in name_lower:
                errors.append(f"Framework '{service.get('name')}' in recommended_stack")

        # Check capabilities_served
        caps = service.get("capabilities_served", [])
        if not caps:
            errors.append(f"Service '{service.get('name')}' has empty capabilities_served")

    # Check for duplicates in alternatives
    alternatives = build_buy_output.get("alternatives", [])
    for alt_section in alternatives:
        for alt in alt_section.get("alternatives", []):
            if alt.get("name", "").lower() in recommended_names:
                errors.append(f"Service '{alt.get('name')}' in both recommended and alternatives")

    return errors
