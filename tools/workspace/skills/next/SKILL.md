---
name: next
description: Orient a fresh session in the MH Ultimate Collection workspace and start the next area of work, carrying it far unattended. Use at the start of a session, or when the user asks "where are we", "what's next" or "what should we do".
---

# Orient and start working

The maintainer leaves sessions unattended. A session takes **one coherent area of work** (the monster port's next stage, say) and carries it as far as it goes: several pieces, one PR each. Don't stop to ask which task, or which way to go after each finding. Don't hop to an unrelated task either: a new area gets a new session.

1. Run `python3 mh-ultimate-collection/tools/doctor.py --fetch`. Note every `warn` and `FAIL`: unpushed branches, uncommitted changes, missing extractions, a stale venv. Fix what you can fix yourself (`doctor.py --fix` for missing extractions or a stale venv, a local `main` behind `origin`). Leave pushes and merges for the maintainer.
2. Read `mh-ultimate-collection/STATUS.md` in full, and `mh-ultimate-collection/CLAUDE.md` for the ground rules.
3. If STATUS.md's "Updated" line is older than the newest file in `mh-ultimate-collection/docs/reports/`, or the branches it lists don't match what the doctor saw (a merged PR, say), STATUS.md is stale. Read the newest report and reconcile in your head before starting. The session's `/handoff` rewrites STATUS.md anyway.
4. Say in a few lines where the project stands, what the doctor flagged, and which task you're starting, with what counts as done. Then **start it at once**, without waiting for an answer. If the user named a task, take that one instead.
5. Skip a task only if it needs the maintainer: an in-game check, a dump or key not on the machine, or an open decision (rule 6). Then take the next one, and say why you skipped.
6. Plan the area's steps, as far as they go, with the task list. Branch both repos as needed and work through them. Run big jobs in the background under the 6 GB cap, and write docs and tests while they run. When a finding changes the plan, record it in the design doc and adjust the plan. Don't stop to ask unless the choice is really the maintainer's.
7. When a piece is done (code, tests, docs, checks passing), commit it, push its branch and open its PR. Then branch the next piece from it and keep going, so review never blocks work; merging stays the maintainer's. Go on to the area's follow-ups (the next steps its own findings named) in the same session.
8. Stop when the area is done, or only steps that need the maintainer are left. Don't start an unrelated STATUS task: run `/handoff` instead, and the next session starts the next area.

For a task needing game files, check the doctor showed the dumps it needs as extracted; if not, `doctor.py --fix` first (it can take several minutes per dump).
