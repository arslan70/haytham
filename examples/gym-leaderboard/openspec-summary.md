# OpenSpec Summary

This is a summary of the Phase 4 output. In a real Haytham run, the full OpenSpec lives in `.haytham/session/phase-4-specs/openspec/` as a directory tree with `config.yaml`, `project.md`, and individual domain spec files.

## Generated Domains

| Domain | Slug | Requirements | Scenarios |
|--------|------|-------------|-----------|
| Anonymous Profiles | `anonymous-profiles` | 3 | 7 |
| Workout Logging | `workout-logging` | 3 | 8 |
| Gym Leaderboards | `gym-leaderboards` | 3 | 7 |
| Social: Follow & Compare | `social-follow-compare` | 2 | 5 |
| Cross-Cutting Requirements | `cross-cutting` | 2 | 4 |
| **Total** | | **13** | **31** |

## Config

```yaml
name: gym-leaderboard
description: Anonymous gym community leaderboard where gym-goers compare workout performance using handles
appetite: Medium
generated_at: 2026-03-18T14:32:00Z
traits:
  interface: [browser, mobile_native]
  auth: multi_user
  deployment: [cloud_hosted]
  data_layer: remote_db
  realtime: false
  communication: none
  payments: none
  scheduling: none
```

## Example Domain Spec: Workout Logging

Below is one domain's spec to show the format. Each requirement has a SHALL statement and Gherkin scenarios with concrete values.

---

### Requirement: Log Workout Entry [CAP-F-004]

The system SHALL allow users to record a workout entry by selecting an exercise, entering sets, reps, and weight.

#### Scenario: Successful workout log

- **Given** an authenticated user with an anonymous profile
- **When** the user selects "Bench Press", enters 3 sets of 8 reps at 185 lbs, and submits
- **Then** the system stores the workout entry and displays a confirmation with the calculated estimated 1RM

#### Scenario: Incomplete entry rejected

- **Given** an authenticated user on the log workout screen
- **When** the user submits a workout with sets filled in but weight left blank
- **Then** the system displays an inline error on the weight field and does not save the entry

---

### Requirement: Calculate Estimated 1RM [CAP-F-005]

The system SHALL calculate an estimated one-rep max from the logged sets, reps, and weight using the Epley formula.

#### Scenario: Standard 1RM calculation

- **Given** a workout entry of 5 reps at 225 lbs for Squat
- **When** the system processes the entry
- **Then** the estimated 1RM is calculated as 225 x (1 + 5/30) = 262 lbs and stored alongside the entry

#### Scenario: Single-rep entry

- **Given** a workout entry of 1 rep at 315 lbs for Deadlift
- **When** the system processes the entry
- **Then** the estimated 1RM equals the entered weight (315 lbs) with no formula adjustment

---

### Requirement: View Workout History [CAP-F-006]

The system SHALL display a chronological list of a user's past workout entries grouped by exercise.

#### Scenario: User views history with entries

- **Given** a user who has logged 12 workout entries across 3 exercises over the past 2 weeks
- **When** the user navigates to their workout history
- **Then** the system displays entries grouped by exercise name, most recent first, with date, sets, reps, weight, and estimated 1RM for each

#### Scenario: User views history with no entries

- **Given** a newly registered user with no logged workouts
- **When** the user navigates to their workout history
- **Then** the system displays an empty state prompting them to log their first workout

---

## Tech Stack (from project.md)

The architecture decisions recommended:

- **Framework:** Next.js with TypeScript (progressive web app for mobile-first)
- **Database:** Supabase (Postgres + auth + realtime subscriptions)
- **Hosting:** Vercel
- **Auth:** Supabase Auth (anonymous sign-up with handle selection, no email required for browse-only)

Build/buy analysis marked Auth, Database, and Hosting as BUY. The only BUILD components are the workout logging UI, leaderboard calculation logic, and social follow/compare features.

## Full Output Location

In a real run, the complete spec tree would be:

```
.haytham/session/phase-4-specs/openspec/
  config.yaml
  project.md
  specs/
    anonymous-profiles/spec.md
    workout-logging/spec.md
    gym-leaderboards/spec.md
    social-follow-compare/spec.md
    cross-cutting/spec.md
```
