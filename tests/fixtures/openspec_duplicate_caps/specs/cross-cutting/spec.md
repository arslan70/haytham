# Cross-Cutting Requirements

## Purpose

Non-functional requirements.

### Requirement: Response Time [CAP-NF-01]

The system SHALL respond within 500ms.

#### Scenario: Normal load

- **Given** the system is under normal load
- **When** a request is made
- **Then** the response arrives within 500ms
