# Gym Leaderboard

## Tech Stack

- **Framework:** Next.js 14 with TypeScript
- **Database:** Supabase Postgres
- **Auth:** Supabase Auth
- **Hosting:** Vercel

## Architecture Decisions

### DEC-STACK-001: Technology Stack Selection

**Decision:** Use Next.js with TypeScript
**Rationale:** Fits the system traits (browser interface, cloud hosted)
**Trade-offs:** Vendor lock-in to Vercel for optimal deployment

### DEC-AUTH-001: Authentication Approach

**Decision:** Use Supabase Auth with anonymous handles
**Rationale:** From build/buy analysis (BUY recommendation). Supports pseudonymous profiles.
**Trade-offs:** Coupled to Supabase ecosystem

## Build/Buy Analysis

| Component | Recommendation | Service |
|-----------|---------------|---------|
| Auth | BUY | Supabase Auth |
| Database | BUY | Supabase Postgres |
| Hosting | BUY | Vercel |

## Dependencies

| Package | Version | Purpose | Dev Only |
|---------|---------|---------|----------|
| next | ^14.0.0 | Web framework | false |
| @supabase/supabase-js | ^2.0.0 | Database and auth client | false |
| typescript | ^5.0.0 | Type checking | true |
