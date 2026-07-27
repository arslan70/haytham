# What we are building

A leaderboard for a single gym community. Members log workouts under an anonymous handle and see where they stand against everyone else training in the same room.

## What is in

- **User Registration**: a member claims a handle and joins the gym's board. Serves "members can join with an anonymous handle".
- **Workout Logging**: a member records a completed workout so it counts toward their standing. Serves "members can log workouts".

## What is out

Real-name profiles and social following are out. The scope asks for anonymity, and a follow graph would pull identity back in through the side door.

## Judgment calls

- Registration and handle selection are one capability, not two. A member does not experience picking a handle as a separate step from joining.
- Logging does not validate that a workout actually happened. Verification is a trust problem, not an MVP problem, and the scope does not ask for it.

## Open questions

- The scope does not say whether a handle can be changed after it is claimed. Assumed no, because a changing handle breaks the standing history.
