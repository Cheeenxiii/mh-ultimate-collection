---
name: handoff
description: Close a session in the MH Ultimate Collection workspace so the next one can start cold - update STATUS.md, write the session report, run every check, commit, and ask before pushing. Use when the user says handoff, wrap up, end the session, or "save where we are".
---

# Hand off to the next session

Work through these in order. Stop and tell the user if a check fails; don't commit around it.

1. **Take stock.** `python3 mh-ultimate-collection/tools/doctor.py`, and `git log --oneline` on the current branch of each repo since the last report. List what this session did, what it couldn't do or check, and what it learned that changes the plan.
2. **Report** (skip for a session that changed nothing of substance): write `mh-ultimate-collection/docs/reports/YYYY-MM-DD-<short-name>.md` in the style of the earlier ones: Done (table), what it changes for the plan, Not done, Checklist for the next session. Counts and words only, never bytes from the files.
3. **STATUS.md:** rewrite `mh-ultimate-collection/STATUS.md` (don't append):
   - "Updated:" today's date and the session in a few words;
   - "Where we are": the phase and the findings that steer the next steps, linking the new report;
   - "Branches": every branch that isn't merged, in both repos, with its push and PR state as it will be after step 5;
   - "Next tasks": 3 to 5, in order, each with what counts as done; drop finished ones;
   - "Waiting on the maintainer": decisions and dumps only they can provide.
   Keep it under a screen.
4. **Checks**, in each repo you changed, with `game_files/work/venv/bin/python`:
   - content repo: `-m pytest -q`, `-m ruff check .`, `tools/check_specs.py`, `tools/check_no_game_data.py`;
   - fork: `-m pytest -q`, `tools/check_no_game_data.py --staged` after staging.
5. **Commit** in small focused commits with one-sentence subjects (CLAUDE.md conventions), the report and STATUS.md in their own commit. Push the session's branches and open a PR for each one that has none (sessions open PRs as they go; merging is the maintainer's). Name the PRs in the final lines.
6. **Workspace files:** if this session changed anything under `mh-ultimate-collection/tools/workspace/`, run `doctor.py --install` so the workspace copies match.
7. Run the doctor again and finish with its result plus the first next task, in two lines.
