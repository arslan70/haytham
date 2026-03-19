# MVP Scope

## 1. THE ONE THING

The MVP will enable gym-goers to compare workout performance on anonymous local leaderboards so they can stay motivated through friendly competition.

## 2. PRIMARY USER SEGMENT

**Segment:** Gym-goers who track workouts and seek peer comparison
**Profile:** Goes to the gym 3+ times per week, already logs sets/reps in a notes app or spreadsheet, checks Reddit or forums to see how their lifts compare to others.
**Why First:** This segment already has the tracking habit. They don't need to be convinced to log workouts; they need a better place to see how they stack up.
**Key Need:** A low-friction way to compare gym performance with peers without exposing real identity.

## 3. PRIMARY INPUT METHOD

**Input Method:** Manual entry
**Why This Method:** Lowest technical complexity for MVP. Users already manually track workouts; this moves that behavior into the app rather than requiring new hardware or integrations.
**What This Excludes:** No device integrations (Apple Watch, Garmin, Fitbit), no camera-based form tracking, no gym equipment connections.

## 4. APPETITE

**Appetite:** Medium (3-4 weeks)
**If we had HALF the time:** Cut "Basic social (follow/compare)" and launch with leaderboards only (no follow, no direct comparison views). Users see the board but can't track specific handles.

## 5. MVP BOUNDARIES

| IN SCOPE (MVP v1) | Requires | OUT OF SCOPE (Future) |
|-------------------|----------|----------------------|
| Anonymous profiles (handle, avatar selection, no real name required) | Auth | Real identity verification, profile customization beyond handle/avatar |
| Manual workout logging (exercise, sets, reps, weight) | Anonymous profiles | Device integrations (Garmin, Apple Watch, Fitbit), auto-detection, real-time tracking |
| Gym-specific leaderboards (users join a gym, leaderboards scoped to that gym) | Workout logging | Cross-gym leaderboards, global rankings, league systems |
| Basic social: follow handles and compare stats | Anonymous profiles, Leaderboards | Direct messaging, comments, workout sharing to external platforms |
| | | Gym partnerships and B2B features |
| | | Paid tiers, premium features, monetization |
| | | Challenges, achievements, gamification beyond leaderboards |
| | | Admin tools, moderation dashboards |

## 6. SUCCESS CRITERIA

**Primary Metric:** Weekly active loggers (users who log at least 1 workout per week)
**Target:** 50 weekly active loggers per gym community within 6 weeks of launch -- realistic

**Validation Criteria:**
- [ ] 60%+ of users who complete onboarding log at least one workout in their first session
- [ ] 40%+ of week-1 users return and log in week 2 (D7 retention proxy)
- [ ] Average user checks the leaderboard 2+ times per week

**Failure Signals:**
- Weekly active loggers per gym drops below 20 after initial seeding (leaderboard feels dead)
- Less than 30% of registered users ever log a second workout (logging friction too high)

## 7. CORE USER FLOWS

### Flow 1: Log a Workout and See Your Rank

**Trigger:** User finishes a gym session and opens the app
**Steps:**
1. User selects "Log Workout"
2. User picks exercise from a preset list (e.g., Bench Press, Squat, Deadlift)
3. User enters sets, reps, and weight
4. System calculates estimated 1RM and updates the user's stats
5. System recalculates the gym leaderboard for that exercise
6. User sees their current rank on the leaderboard
**Success:** User sees an updated rank within 3 seconds of logging

### Flow 2: Follow a Handle and Compare

**Trigger:** User sees an interesting handle on the leaderboard and wants to track them
**Steps:**
1. User taps a handle on the leaderboard
2. System shows the handle's public stats (exercises logged, ranks, recent activity)
3. User taps "Follow"
4. System adds the handle to the user's following list
5. User can view a comparison overlay: their stats vs. followed handle's stats
**Success:** User can see a side-by-side comparison for any shared exercise

## 8. SCOPE METADATA

```
MVP_SCOPE_COMPLETE: true
PRIMARY_USER_SEGMENT: Gym-goers who track workouts and seek peer comparison
INPUT_METHOD: Manual entry
APPETITE: Medium
IN_SCOPE_COUNT: 4
OUT_SCOPE_COUNT: 8
FLOW_COUNT: 2
HALF_TIME_CUT: Basic social (follow/compare)
```
