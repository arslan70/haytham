"""Pydantic models for structured system traits output.

Simple/flat schemas safe for LLM structured output. The model captures
trait values for downstream stages; human-readable explanations are
preserved in the markdown ``to_markdown()`` rendering.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SystemTraitsOutput(BaseModel):
    """Flat system traits classification.

    All fields are simple scalars — well within reliable structured output
    territory.  Multi-select traits are comma-separated strings to keep
    the schema flat (e.g. ``"browser, mobile_native"``).
    """

    interface: str = Field(
        description=(
            "Comma-separated interface types from: browser, terminal, "
            "mobile_native, desktop_gui, api_only, none"
        )
    )
    interface_explanation: str = Field(
        description="Plain-language explanation for the interface choice"
    )
    auth: str = Field(description="Authentication model: multi_user, single_user, or none")
    auth_explanation: str = Field(description="Plain-language explanation for the auth choice")
    deployment: str = Field(
        description=(
            "Comma-separated deployment targets from: cloud_hosted, "
            "app_store, package_registry, local_install, embedded"
        )
    )
    deployment_explanation: str = Field(
        description="Plain-language explanation for the deployment choice"
    )
    data_layer: str = Field(
        description="Primary data storage: remote_db, local_storage, file_system, or none"
    )
    data_layer_explanation: str = Field(
        description="Plain-language explanation for the data_layer choice"
    )
    realtime: str = Field(description="Whether realtime is needed: true or false")
    realtime_explanation: str = Field(
        description="Plain-language explanation for the realtime choice"
    )
    communication: str = Field(
        description="User-to-user communication: video, audio, text, async, or none"
    )
    communication_explanation: str = Field(
        description="Plain-language explanation for the communication choice"
    )
    payments: str = Field(description="Payment handling: required, optional, or none")
    payments_explanation: str = Field(
        description="Plain-language explanation for the payments choice"
    )
    scheduling: str = Field(description="Booking/scheduling: required, optional, or none")
    scheduling_explanation: str = Field(
        description="Plain-language explanation for the scheduling choice"
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def to_traits_dict(self) -> dict[str, str | list[str]]:
        """Convert to the dict format expected by extract_system_traits_processor.

        Multi-select traits (interface, deployment) are returned as lists.
        """
        traits: dict[str, str | list[str]] = {}

        for name in (
            "interface",
            "auth",
            "deployment",
            "data_layer",
            "realtime",
            "communication",
            "payments",
            "scheduling",
        ):
            raw = getattr(self, name, "").strip()
            # Multi-select fields: parse comma-separated into list
            if name in ("interface", "deployment"):
                values = [v.strip() for v in raw.split(",") if v.strip()]
                traits[name] = values if len(values) > 1 else (values[0] if values else raw)
            else:
                traits[name] = raw

        return traits

    def to_markdown(self) -> str:
        """Render as the same markdown format the downstream UI expects."""
        lines = ["## SYSTEM TRAITS", ""]

        trait_names = [
            "interface",
            "auth",
            "deployment",
            "data_layer",
            "realtime",
            "communication",
            "payments",
            "scheduling",
        ]
        multi_select = {"interface", "deployment"}

        for name in trait_names:
            value = getattr(self, name, "")
            explanation = getattr(self, f"{name}_explanation", "")

            # Format value with bracket notation for multi-select
            if name in multi_select:
                values = [v.strip() for v in value.split(",") if v.strip()]
                display = f"[{', '.join(values)}]" if values else value
            else:
                display = value

            lines.append(f"- **{name}:** {display}")
            if explanation:
                lines.append(f"  Explanation: {explanation}")
            lines.append("")

        return "\n".join(lines)
