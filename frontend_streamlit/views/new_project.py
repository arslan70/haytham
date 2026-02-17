"""New Project View - Start fresh with a new idea.

Simplified landing page using native Streamlit components.
Maintains Haytham brand identity with minimal CSS.
"""

import streamlit as st
from lib.session_utils import clear_session

# =============================================================================
# Minimal CSS - Only essential overrides (~40 lines)
# =============================================================================

st.markdown(
    """
    <style>
    /* Hide Streamlit header/footer */
    header[data-testid="stHeader"] { display: none; }
    footer { display: none !important; }

    /* Form styling */
    [data-testid="stForm"] {
        border: none !important;
        background: transparent !important;
    }

    /* Feature card styling */
    .feature-card {
        background: white;
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 2px 12px rgba(107, 45, 139, 0.08);
        height: 100%;
    }

    .feature-card h4 {
        color: #6B2D8B;
        margin: 0 0 0.5rem 0;
        font-size: 1rem;
    }

    .feature-card p {
        color: #666;
        font-size: 0.875rem;
        line-height: 1.5;
        margin: 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# Page Layout
# =============================================================================

# Add vertical spacing at top
st.markdown("<br>", unsafe_allow_html=True)

# Header Section - Centered title and subtitle
st.markdown(
    """
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="font-size: clamp(3rem, 10vw, 5rem); font-weight: 800;
                   color: #6B2D8B; margin: 0; line-height: 1.1;">
            Haytham
        </h1>
        <p style="font-size: 1.125rem; color: #666; max-width: 560px;
                  margin: 1rem auto; line-height: 1.6;">
            Stop guessing, start validating. Transform your startup idea
            into a validated concept with AI-powered analysis.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Main Form Section - Centered with columns
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    with st.form("new_project_form", clear_on_submit=False, border=False):
        idea = st.text_area(
            "Describe your startup idea",
            placeholder="Describe your business idea in a few sentences...",
            height=120,
            label_visibility="collapsed",
        )

        # Centered submit button
        submitted = st.form_submit_button(
            "✨ Validate Your Idea",
            use_container_width=True,
            type="primary",
        )

        if submitted:
            if not idea or not idea.strip():
                st.error("Please enter your startup idea to continue.")
            else:
                clear_session()
                st.session_state.new_idea = idea.strip()
                st.rerun()

    # Trust indicators
    st.caption(
        "<div style='text-align: center; margin-top: 1rem;'>"
        "🔒 High-fidelity insights • ⚡ Results in ~30 seconds"
        "</div>",
        unsafe_allow_html=True,
    )

# Spacer
st.markdown("<br><br>", unsafe_allow_html=True)

# Features Section - Three columns
st.markdown("---")

features = [
    {
        "icon": "🏗️",
        "title": "Real Standards",
        "desc": "We validate against enterprise-grade architectural standards, not just surface-level checks.",
    },
    {
        "icon": "📊",
        "title": "Market Analysis",
        "desc": "Deep dive into market trends and competitor landscape using real-time AI analysis.",
    },
    {
        "icon": "🎯",
        "title": "Idea Scoring",
        "desc": "Get a comprehensive score on technical and commercial viability of your concept.",
    },
]

feat_cols = st.columns(3)

for i, feature in enumerate(features):
    with feat_cols[i]:
        st.markdown(
            f"""
            <div class="feature-card">
                <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">
                    {feature["icon"]}
                </div>
                <h4>{feature["title"]}</h4>
                <p>{feature["desc"]}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

# Footer
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")
st.caption(
    "<div style='text-align: center;'>Haytham AI • Built for builders • © 2024</div>",
    unsafe_allow_html=True,
)
