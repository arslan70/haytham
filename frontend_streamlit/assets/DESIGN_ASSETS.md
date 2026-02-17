# Haytham Design Assets

This document describes the design assets extracted from the "Interactive Startup Workspace V2" design mockup for use in the Streamlit app.

## Design Overview

The design features:
- **Lavender purple gradient background** for the app
- **White card-based content areas** with soft shadows
- **Coral/orange primary buttons** for CTAs  
- **Purple accent colors** for headers and active states
- **Step-based navigation** in the sidebar
- **Decorative illustrations** with gears, lightbulbs, and innovation motifs

---

## Files Created

### 1. Theme Configuration
**File:** `.streamlit/config.toml`

Streamlit's native theme configuration with:
- Primary color: `#EB5E55` (Coral)
- Background: `#FFFFFF` (White)
- Secondary background: `#D4C4E8` (Lavender purple)
- Text color: `#333333` (Dark gray)

### 2. Custom CSS Stylesheet
**File:** `assets/style.css`

Comprehensive CSS design system including:
- CSS custom properties (variables) for all design tokens
- Google Fonts import (Inter)
- Sidebar styling
- Input field styling (chat bubble style)
- Button styling (coral primary, transparent secondary)
- Card components
- Navigation pills
- Step indicator
- Status cards (info, success, warning, error)
- Animations

### 3. Decorative Illustration
**File:** `assets/workspace_illustration.png`

AI-generated illustration featuring:
- Glowing lightbulb
- Purple and gray gears
- Rocket ship
- Connected nodes and dotted lines
- Decorative swirls

### 4. Styling Helper Module
**File:** `components/styling.py`

Python module with helper functions:
- `load_css()` - Inject custom CSS
- `workspace_card()` - Render styled workspace card
- `step_indicator()` - Render step progress
- `header_with_branding()` - Render brand header
- `nav_item()` - Render navigation items
- `info_card()` - Render status cards
- `footer_trust_indicator()` - Render footer
- `HaythamColors` class - Color constants

---

## Color Palette

| Name | Hex | Usage |
|------|-----|-------|
| Purple Dark | `#6B2D8B` | Headers, titles, active nav |
| Purple Medium | `#8B5FAF` | Accents, gradients |
| Purple Light | `#D4C4E8` | Sidebar background |
| Lavender | `#C9B8E0` | Background gradient |
| Lavender Pale | `#E8DCF5` | Active nav, info cards |
| Coral | `#EB5E55` | Primary buttons |
| Coral Hover | `#D94E45` | Button hover state |
| Orange | `#F5A623` | Accent color |
| White | `#FFFFFF` | Card backgrounds |
| Gray 100 | `#F8F6FA` | Light backgrounds |
| Gray 200 | `#E0D5EE` | Borders, dividers |
| Gray 500 | `#666666` | Muted text |
| Gray 900 | `#333333` | Primary text |

---

## Typography

- **Font Family:** Inter (Google Fonts), with system fallbacks
- **Font Sizes:**
  - XS: 0.75rem (12px)
  - SM: 0.875rem (14px)
  - Base: 1rem (16px)
  - LG: 1.125rem (18px)
  - XL: 1.5rem (24px)
  - 2XL: 2rem (32px)
  - 3XL: 2.5rem (40px)

---

## Usage

### Quick Start

```python
# In your Streamlit page
from components.styling import load_css, workspace_card, step_indicator

# Load custom CSS (call once at the top of your main app)
load_css()

# Render the workspace card
workspace_card(
    title="Interactive Startup Workspace V2",
    subtitle="Workspace",
    description="Transform your startup idea into implementation-ready user stories with AI.",
    show_illustration=True
)

# Show step indicator
step_indicator(current_step=1, total_steps=3)
```

### Using Color Constants

```python
from components.styling import HaythamColors

# Use in inline styles
st.markdown(f'''
    <div style="color: {HaythamColors.PURPLE_DARK}">
        Hello World
    </div>
''', unsafe_allow_html=True)
```

### Custom Info Cards

```python
from components.styling import info_card

# Info variant (purple)
info_card("This is an informational message.", variant="info")

# Success variant (green)
info_card("Operation completed!", variant="success")

# Warning variant (orange)
info_card("Please review before proceeding.", variant="warning")
```

---

## Design Patterns

### Main App Layout

The design follows this structure:
1. **Sidebar** (left): Haytham branding + stepped navigation
2. **Main Content** (center): White card with illustration overlay
3. **Footer** (bottom left): Step indicator with progress bar

### Content Cards

Use white backgrounds with:
- Border radius: 16px
- Padding: 40px 48px
- Box shadow: `0 2px 12px rgba(107, 45, 139, 0.08)`

### Buttons

- **Primary (CTA):** Coral background, white text, pill shape
- **Secondary:** Transparent, purple text, border

### Input Fields

- Light border (`#E0D5EE`)
- Rounded corners (12px)
- Purple focus ring
- Chat bubble aesthetic with speech tail (optional)

---

## Notes

- The CSS includes `@import` for Google Fonts which loads asynchronously
- All colors are accessible and follow contrast guidelines
- Animations are subtle to avoid distraction
- The design is optimized for wide layout (`layout="wide"`)
