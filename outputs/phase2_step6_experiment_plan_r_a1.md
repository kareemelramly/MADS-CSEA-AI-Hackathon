UNVALIDATED · FOUNDER OVERRIDE

# Validation experiment plan

**Locked target:** 100 real waitlist sign-ups in 14 days, with at least 200 real visitors.
Locked at 2026-11-17T20:35:01Z with SHA-256 `2d28b0835a8b8a66da2ee9f03b84e0b713e5bb9144fc5c775e8d0ef08ec2327f`. Changing it after this point makes the gate return `stop`.

Basis: ASSUMPTION: planning values set before any data (problem statement example: 100 sign-ups in 14 days)

## Steps
1. Publish the landing page yourself after approving it (publishing from this system is STUBBED).
2. Share it in channels where the segment already talks about the pain (see the evidence links in Phase 1).
3. Record visitors and sign-ups daily in the tracking sheet. Do not count friends or test entries.
4. When the 14 days end, enter `experiment_status: completed`, dates, visitors and sign-ups in the results form.

## How the gate will judge it
- Not started or running: `awaiting_evidence` (nothing decided).
- Completed with fewer than 200 visitors: `repeat` (too few people saw the page).
- Ratio sign-ups ÷ 100 at least 1: `go`. Between 0.5 and 1: `repeat` while attempts remain.
- Below 0.5: `pivot_back` while an alternative remains, else `stop`.

Waitlist: MOCKED in this prototype. Real counts come only from the founder.
