---
name: done
description: Finish the current task of MH Ultimate Collection - run the checks, commit, push and open a pull request that closes the issue. Use when the user says done, /done, or the issue's "Done when" is met.
---

# Finish the task

1. Check the work against the issue's "Done when". If something is missing, say what and stop.
2. Run the checks in each repository you changed, and stop on any failure:
   - mod: `python3 -m pytest` and `ruff check .`;
   - fork: `tests/uc/run`, and `git diff --stat upstream/main` touches only the fork's own files or the hooks they need.
3. Update the docs that describe what changed (README.md, docs/architecture.md, specs/, reference/README.md) in the same commits. Write no report, status file or session notes.
4. Commit in small commits: the subject says what, the body says why. Push the branch.
5. Open a pull request whose body starts with `Closes #<number>`, says what changed and how it was tested, and names anything left undone. Results the issue asked for go in the docs it names, not in the pull request alone.
6. Follow-up work the task uncovered becomes issues, through `/plan`.
7. End with the pull request's link in one line. Merging is the maintainer's.
