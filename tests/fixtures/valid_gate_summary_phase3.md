# How we are building it

A small web app with a hosted database behind it. Nothing runs on your own hardware, and there is no background processing to babysit.

## The stack

- **Supabase** (BUY): database, auth, and hosting in one service, so there is one bill and one thing to learn.
- **OpenAI API** (BUY): inference for the matching step. Building this in-house is a research project, not an MVP.

## Decisions that matter

- Standings are computed when the board is read, not on a schedule. Simpler to operate, and the numbers are never stale. The alternative, a nightly job, was rejected because it adds a scheduler to a system that otherwise has no background work.
- Handles live in the same database as workouts. Splitting anonymity into a separate store was rejected: it doubles the operational surface for a gym-sized member list.

## What this costs

$0 to $50 a month, and roughly 2 to 3 days of integration work. Supabase is free until the database passes its free-tier size, which this member count will not reach in the first year.

## Unknowns to resolve before building

- What ranking rule handles ties and recent activity fairly? This blocks the leaderboard capability.
