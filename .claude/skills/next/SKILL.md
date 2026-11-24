---
name: next
description: Start the next task of MH Ultimate Collection - pick an open GitHub issue in the current milestone and work on it. Use when the user says next, /next, "what's next", or names an issue to work on.
---

# Start the next task

1. Read `CLAUDE.md`, `README.md` and `docs/architecture.md`.
2. Pick the issue:
   - if the user named one, take it;
   - otherwise, in `Cheeenxiii/mh-ultimate-collection`, take the open milestone with the earliest due date (or the lowest number), and in it the lowest-numbered open issue that isn't blocked by another open issue.

   If no issue fits (all blocked, or each needs game files this machine doesn't have), say so and stop.
3. Say in two lines which issue you take and what its "Done when" asks. Then start without waiting.
4. Work on a branch named `issue-<number>` from `main` (from `uc/main` in the fork, for engine work). Keep to the issue: if you find other work, add it with `/plan` instead of doing it.
5. When the issue's "Done when" is met, run `/done`.
