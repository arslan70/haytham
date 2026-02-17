"""Shared regex patterns for extracting validation metrics from markdown outputs.

Used by both the Streamlit discovery view and the PDF report config builder.
"""

import re

RE_RECOMMENDATION = re.compile(r"\*\*Recommendation:\*\*\s*(GO|NO-GO|PIVOT)", re.IGNORECASE)
RE_CONFIDENCE = re.compile(
    r"\*\*(?:Evidence Quality|Confidence):\*\*\s*(HIGH|MEDIUM|LOW)", re.IGNORECASE
)
RE_COMPOSITE = re.compile(r"\*\*Composite Score:\*\*\s*(\d+\.?\d*)\s*/\s*5\.0", re.IGNORECASE)
RE_RISK_LEVEL = re.compile(r"## Overall Risk Level:\s*(HIGH|MEDIUM|LOW)", re.IGNORECASE)
RE_CLAIMS = re.compile(
    r"\*\*Summary:\*\*\s*(\d+) claims analyzed:\s*(\d+) supported,\s*(\d+) partial",
    re.IGNORECASE,
)

# Plain-text (non-markdown) recommendation pattern used by workflow runner
# and entry validators to extract the verdict from uppercased output.
RE_RECOMMENDATION_PLAIN = re.compile(r"RECOMMENDATION:\s*(GO|NO-GO|PIVOT)")
