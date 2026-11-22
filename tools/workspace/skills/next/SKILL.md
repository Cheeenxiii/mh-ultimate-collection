---
name: next
description: Orient a fresh session in the MH Ultimate Collection workspace and propose the next task. Use at the start of a session, or when the user asks "where are we", "what's next" or "what should we do".
---

# Orient and pick the next task

1. Run `python3 mh-ultimate-collection/tools/doctor.py --fetch`. Note every `warn` and `FAIL`: unpushed branches, uncommitted changes, missing extractions, a stale venv.
2. Read `mh-ultimate-collection/STATUS.md` in full, and `mh-ultimate-collection/CLAUDE.md` for the ground rules.
3. If STATUS.md's "Updated" line is older than the newest file in `mh-ultimate-collection/docs/reports/`, or the branches it lists don't match what the doctor saw, say so: STATUS.md is stale. Read the newest report and reconcile before proposing anything.
4. Tell the user, in a few lines:
   - where the project stands (phase, last session's outcome);
   - anything the doctor flagged that needs handling first (for example: push the last session's branches);
   - the next task from STATUS.md, with what counts as done, and the one after it.
5. Ask which to start, then plan it with the task list. Don't start work that changes either repository before the user picks.

For a task needing game files, check the doctor showed the dumps it needs as extracted; if not, `doctor.py --fix` first (it can take several minutes per dump).
