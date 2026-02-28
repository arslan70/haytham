"""Zip utility for directory tree exporters."""

from __future__ import annotations

import zipfile
from io import BytesIO


def tree_to_zip(tree: dict[str, str]) -> bytes:
    """Convert a path-to-content dict into a zip archive.

    Args:
        tree: Dict mapping relative file paths to string content.

    Returns:
        Zip archive as bytes, suitable for st.download_button.
    """
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in sorted(tree.items()):
            zf.writestr(path, content)
    return buffer.getvalue()
