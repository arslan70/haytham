"""
Haytham Design System - Styling Utilities

Provides functions to inject custom CSS and design elements into Streamlit.
Based on the Interactive Startup Workspace V2 design.
"""

import base64
from pathlib import Path

import streamlit as st

# Asset paths
ASSETS_DIR = Path(__file__).parent.parent / "assets"
STYLE_CSS = ASSETS_DIR / "style.css"
WORKSPACE_ILLUSTRATION = ASSETS_DIR / "workspace_illustration.png"


def load_css() -> None:
    """Load and inject custom CSS styles into the Streamlit app."""
    if STYLE_CSS.exists():
        with open(STYLE_CSS) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def get_image_base64(image_path: Path) -> str:
    """Convert image to base64 for embedding in HTML."""
    if image_path.exists():
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


def workspace_card(
    title: str,
    subtitle: str = "Workspace",
    description: str = "",
    show_illustration: bool = True,
) -> None:
    """
    Render a workspace card styled like the design.

    Args:
        title: Main heading (e.g., "Interactive Startup Workspace V2")
        subtitle: Small label above title (e.g., "Workspace")
        description: Description text below title
        show_illustration: Whether to show the decorative illustration
    """
    illustration_html = ""
    if show_illustration and WORKSPACE_ILLUSTRATION.exists():
        img_b64 = get_image_base64(WORKSPACE_ILLUSTRATION)
        illustration_html = f"""
            <img src="data:image/png;base64,{img_b64}"
                 alt="Illustration"
                 style="position: absolute; top: 20px; right: 20px; width: 180px; opacity: 0.9;" />
        """

    st.markdown(
        f"""
        <div style="
            background-color: white;
            border-radius: 16px;
            padding: 40px 48px;
            box-shadow: 0 2px 12px rgba(107, 45, 139, 0.08);
            position: relative;
            overflow: hidden;
            max-width: 800px;
            margin: 20px auto;
        ">
            {illustration_html}
            <div style="color: #666; font-size: 14px; font-weight: 500; margin-bottom: 8px;">
                {subtitle}
            </div>
            <h1 style="
                color: #6B2D8B;
                font-size: 2.5rem;
                font-weight: 700;
                line-height: 1.2;
                margin: 0 0 16px 0;
                max-width: 70%;
            ">{title}</h1>
            <p style="
                color: #666;
                font-size: 1rem;
                line-height: 1.6;
                margin: 0;
                max-width: 65%;
            ">{description}</p>
        </div>
    """,
        unsafe_allow_html=True,
    )


def step_indicator(current_step: int, total_steps: int = 3) -> None:
    """
    Render a step progress indicator like "Step 1 of 3".

    Args:
        current_step: Current step number (1-indexed)
        total_steps: Total number of steps
    """
    progress_pct = (current_step / total_steps) * 100

    st.markdown(
        f"""
        <div style="
            display: flex;
            align-items: center;
            gap: 12px;
            color: #666;
            font-size: 14px;
            margin: 20px 0;
        ">
            <span>Step {current_step} of {total_steps}</span>
            <div style="
                width: 80px;
                height: 4px;
                background-color: #E0D5EE;
                border-radius: 9999px;
                overflow: hidden;
            ">
                <div style="
                    width: {progress_pct}%;
                    height: 100%;
                    background: linear-gradient(90deg, #6B2D8B, #8B5FAF);
                    border-radius: 9999px;
                "></div>
            </div>
        </div>
    """,
        unsafe_allow_html=True,
    )


def header_with_branding(title: str = "Haytham") -> None:
    """Render the Haytham brand header for the sidebar."""
    st.markdown(
        f"""
        <h1 style="
            color: #6B2D8B;
            font-size: 2rem;
            font-weight: 700;
            margin: 0 0 24px 0;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        ">{title}</h1>
    """,
        unsafe_allow_html=True,
    )


def nav_item(
    label: str,
    icon: str = "🔹",
    is_active: bool = False,
    step_number: int | None = None,
) -> None:
    """
    Render a navigation item styled like the sidebar design.

    Args:
        label: Navigation label text
        icon: Emoji or icon character
        is_active: Whether this item is currently active
        step_number: Optional step number to display
    """
    active_style = (
        """
        background-color: #E8DCF5;
        color: #6B2D8B;
        font-weight: 600;
    """
        if is_active
        else """
        background-color: transparent;
        color: #333;
        font-weight: 500;
    """
    )

    step_prefix = f"{step_number}. " if step_number else ""

    st.markdown(
        f"""
        <div style="
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            border-radius: 9999px;
            {active_style}
            font-size: 14px;
            cursor: pointer;
            transition: all 150ms ease;
            margin-bottom: 4px;
        ">
            <span style="font-size: 16px;">{icon}</span>
            <span>{step_prefix}{label}</span>
        </div>
    """,
        unsafe_allow_html=True,
    )


def info_card(content: str, variant: str = "info") -> None:
    """
    Render a styled info card.

    Args:
        content: Card content (supports HTML)
        variant: One of "info", "success", "warning", "error"
    """
    colors = {
        "info": ("#E8DCF5", "#6B2D8B"),
        "success": ("#E8F5E9", "#4CAF50"),
        "warning": ("#FFF3E0", "#FF9800"),
        "error": ("#FFEBEE", "#F44336"),
    }

    bg_color, border_color = colors.get(variant, colors["info"])

    st.markdown(
        f"""
        <div style="
            background-color: {bg_color};
            border-radius: 8px;
            padding: 16px;
            border-left: 4px solid {border_color};
            font-size: 1rem;
            line-height: 1.6;
            color: #333;
        ">{content}</div>
    """,
        unsafe_allow_html=True,
    )


def footer_trust_indicator(text: str = "Trusted by 100+ startups") -> None:
    """Render the footer trust indicator."""
    st.markdown(
        f"""
        <div style="
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 20px;
            margin-top: 24px;
            border-top: 1px solid #E0D5EE;
        ">
            <span style="color: #666; font-size: 14px;">{text}</span>
            <a href="#" style="
                color: #6B2D8B;
                font-size: 14px;
                font-weight: 500;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 4px;
            ">How it works →</a>
        </div>
    """,
        unsafe_allow_html=True,
    )


# Color palette constants for programmatic use
class HaythamColors:
    """Haytham design system color constants."""

    # Primary Colors
    PURPLE_DARK = "#6B2D8B"
    PURPLE_MEDIUM = "#8B5FAF"
    PURPLE_LIGHT = "#D4C4E8"
    LAVENDER = "#C9B8E0"
    LAVENDER_PALE = "#E8DCF5"

    # Accent Colors
    CORAL = "#EB5E55"
    CORAL_HOVER = "#D94E45"
    ORANGE = "#F5A623"

    # Neutrals
    WHITE = "#FFFFFF"
    GRAY_100 = "#F8F6FA"
    GRAY_200 = "#E0D5EE"
    GRAY_500 = "#666666"
    GRAY_900 = "#333333"

    # Status Colors
    SUCCESS = "#4CAF50"
    WARNING = "#FF9800"
    ERROR = "#F44336"
    INFO = "#2196F3"
