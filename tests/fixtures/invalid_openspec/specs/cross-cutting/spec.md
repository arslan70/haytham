# Cross-Cutting Requirements

## Purpose

Non-functional requirements for the invalid fixture.

### Requirement: Performance [CAP-NF-01]

The system SHALL respond within 500 milliseconds.

#### Scenario: Page load

- **Given** the application is running
- **When** a user requests a page
- **Then** the server responds within 500 milliseconds
