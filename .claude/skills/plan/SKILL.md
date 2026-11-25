---
name: plan
description: Add tasks to MH Ultimate Collection's plan - create GitHub issues, and milestones when a new goal appears, in the project's style. Use when the user says plan, /plan, "add an issue", "add a milestone", or when work uncovers a follow-up task.
---

# Add issues and milestones

The plan lives in GitHub, in `Cheeenxiii/mh-ultimate-collection`: milestones for goals, issues for tasks. Use the GitHub tools available (`gh`, or the GitHub connector). The plan is public, so write for someone who has just found the repository.

## A milestone is a result people can see

- Its title names the result, not the work: "First new quest in game", not "Extra Data work".
- Its description says in one or two sentences what will be true when it is closed.
- Create one only when a new goal appears that no open milestone covers. Ask the maintainer first: goals are theirs to set.

## An issue is one session's work

- **Title:** imperative, short, the outcome in plain words. "Port Rathian's moves to MH4U". No check codes (Q17, R1), file names or counts in the title.
- **Body:**
  - one paragraph of context a newcomer can follow;
  - **Done when:** a concrete, checkable end, naming the doc where the result will be recorded;
  - what it waits for, as issue links (#14), and whether it needs game files.

  Check codes and file paths may appear in the body, as references to the docs.
- **Milestone:** the goal it serves, only if a milestone's result depends on it. If none fits, leave it without one and say so.
- **Labels:** one type and one need, always.
  - type: `research` (a format or the games' code, written up in specs/ or reference/), `tool` (code in mhuc, tools/ or a plugin that isn't a port), `port` (a monster, map or system brought into MH4U), `in-game check` (closed by watching the game, procedure in docs/checks.md), `docs`;
  - need: `needs: game files` (the maintainer's dumps, on the machine), `needs: game session` (someone has to play), `needs: missing files` (files the machine doesn't have, named in the body). None for work that needs only the repository.
- **Links:** set what the body says as GitHub relationships, so they show and filter:
  - each issue it waits for as "blocked by": `gh api repos/Cheeenxiii/mh-ultimate-collection/issues/<N>/dependencies/blocked_by -X POST -F issue_id=<id of the blocking issue>`;
  - a slice of a split issue as its sub-issue: `gh api repos/Cheeenxiii/mh-ultimate-collection/issues/<parent>/sub_issues -X POST -F sub_issue_id=<id of the slice>`.

  An issue's `id` (not its number) is `gh api repos/Cheeenxiii/mh-ultimate-collection/issues/<N> -q .id`.
- Before creating an issue, search the open ones. Don't duplicate, and don't open issues for open decisions (docs/decisions.md): those are the maintainer's.
- Too big for a session? Split it: the slices become sub-issues of the parent, and the parent's body says so.
- Not worth an issue: a detail left unknown. Mark it `unknown` in the spec with what was searched.

Report the links you created in one line each.
