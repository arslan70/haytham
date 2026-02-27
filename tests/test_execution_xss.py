"""Tests for XSS prevention in Streamlit execution view."""
import html


def test_html_escape_prevents_xss():
    """Verify html.escape sanitizes XSS payloads."""
    malicious = '<img src=x onerror=alert(1)>'
    escaped = html.escape(malicious)
    assert "<" not in escaped
    assert ">" not in escaped
    assert "&lt;" in escaped


def test_html_escape_preserves_normal_text():
    """Verify html.escape doesn't mangle normal startup ideas."""
    normal = "A gym leaderboard app for CrossFit athletes"
    assert html.escape(normal) == normal
