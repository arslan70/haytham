# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Haytham, please report it responsibly.

**GitHub**: Use [GitHub's private vulnerability reporting](https://github.com/arslan70/haytham/security/advisories/new) to submit a report.

Please include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

**Do not** open a public GitHub issue for security vulnerabilities.

## Response Timeline

- **Acknowledgement**: Within 48 hours of report
- **Initial assessment**: Within 7 days
- **Fix or mitigation**: Best effort within 30 days
- **Public disclosure**: 90 days after report, or when a fix is released (whichever is first)

## Scope

### In scope

- Haytham core package (`haytham/`)
- Official integrations and provider adapters
- CLI and Streamlit interface
- Session data handling and file I/O

### Out of scope

- Third-party LLM provider APIs (Bedrock, Anthropic, OpenAI, Ollama)
- Streamlit framework vulnerabilities
- Issues in user-generated content or session data
- Denial-of-service attacks against LLM providers

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Credit

We appreciate responsible disclosure and will credit reporters in release notes (unless you prefer to remain anonymous).
