#!/usr/bin/env python3
"""Where the workspace stands: dumps, extractions, the venv, both repositories, Claude's files.

The workspace is the folder holding this repository, the engine fork and game_files/:

    <workspace>/
      mh-ultimate-collection/   this repository
      MH4UltimateDC-fork/       the engine fork
      game_files/               the maintainer's dumps (never in git)
        work/                   extractions, the venv, scratch output
      CLAUDE.md, .claude/       installed from tools/workspace/ (doctor --install)

usage: doctor.py [--workspace DIR] [--fix] [--install] [--fetch] [--tests] [--session-start]

  --fix            extract missing dumps (the fork's extract_ncch.py), create the venv, and set
                   both repos' git identity to the project's
  --install        copy tools/workspace/ files into the workspace (CLAUDE.md, .claude/)
  --fetch          git fetch both repositories first (network)
  --tests          run both test suites (the fork's takes about a minute)
  --session-start  short report followed by STATUS.md, for the SessionStart hook; never fails

It prints one line per check, "ok", "warn" or "FAIL". Exit status 1 if anything FAILs
(except with --session-start). Standard library only; nothing it prints comes from the dumps.
"""
from __future__ import annotations

import argparse
import filecmp
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.basename(REPO)
FORK = "MH4UltimateDC-fork"
WORKSPACE_FILES = os.path.join(REPO, "tools", "workspace")
# installed path in the workspace -> source under tools/workspace/
INSTALL = {
    "CLAUDE.md": "CLAUDE.md",
    ".claude/settings.json": "settings.json",
    ".claude/skills/next/SKILL.md": "skills/next/SKILL.md",
    ".claude/skills/handoff/SKILL.md": "skills/handoff/SKILL.md",
}
VENV_MODULES = ("pytest", "ruff", "unicorn", "capstone", "elftools", "numpy")
# the project's git identity: both repos set it locally so the machine's global identity never leaks
GIT_NAME = "Cheeenxiii"
GIT_EMAIL = "342393699+Cheeenxiii@users.noreply.github.com"


@dataclass
class Result:
    level: str   # ok, warn, FAIL
    area: str
    text: str

    def line(self) -> str:
        return f"{self.level:<4}  {self.area:<10} {self.text}"


def _run(cmd: list[str], cwd: str | None = None, timeout: int = 60) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)
    return p.returncode, (p.stdout + p.stderr).strip()


# ── dumps and extractions ──────────────────────────────────────────────────

def load_dumps(path: str = os.path.join(WORKSPACE_FILES, "dumps.json")) -> dict:
    with open(path) as f:
        return json.load(f)["dumps"]


def extraction_state(workdir: str, kind: str = "3ds") -> str:
    """'ok', 'missing', 'partial' or 'encrypted' for one work/<name>/ folder.

    kind "3ds": extract_ncch.py's output. kind "switch": extract_nsp.py's (code only).
    """
    if not os.path.isdir(workdir):
        return "missing"
    needed = ("main.text.bin", "main.rodata.bin", "main.data.bin", "info.txt") if kind == "switch" \
        else ("exheader.bin", "code.bin", "romfs.bin", "info.txt")
    if not all(os.path.isfile(os.path.join(workdir, n)) for n in needed):
        return "partial"
    with open(os.path.join(workdir, "info.txt")) as f:
        info = f.read()
    if kind == "switch":
        return "ok" if "hash blocks verified" in info else "partial"
    return "ok" if "none (decrypted)" in info else "encrypted"


def check_dumps(ws: str, fix: bool) -> list[Result]:
    out = []
    games = os.path.join(ws, "game_files")
    if not os.path.isdir(games):
        return [Result("warn", "dumps", "no game_files/ here: a web session, or dumps kept elsewhere")]
    extractor = os.path.join(ws, FORK, "tools", "extract_ncch.py")
    for name, d in load_dumps().items():
        src = os.path.join(games, d["file"])
        work = os.path.join(games, "work", name)
        kind = d.get("kind", "3ds")
        state = extraction_state(work, kind)
        if kind == "switch" and state != "ok":
            # Needs the maintainer's keys: never extracted automatically.
            out.append(Result("warn", "dumps", f"{name}: not extracted ({state}); needs the maintainer's keys, "
                              f"see extract_nsp.py in the fork"))
            continue
        if state != "ok" and fix and os.path.isfile(src) and os.path.isfile(extractor):
            code, msg = _run([sys.executable, extractor, src, "-o", work, "--romfs"], timeout=1800)
            state = extraction_state(work) if code == 0 else "encrypted" if "encrypted" in msg else "partial"
        if state == "ok":
            out.append(Result("ok", "dumps", f"{name}: extracted ({d['role']})"))
        elif not os.path.isfile(src):
            out.append(Result("warn", "dumps", f"{name}: dump not found ({d['file']})"))
        elif state == "encrypted":
            out.append(Result("FAIL", "dumps", f"{name}: still encrypted; decrypt it (GodMode9) before use"))
        else:
            out.append(Result("warn", "dumps", f"{name}: not extracted ({state}); doctor --fix extracts it"))
    return out


def check_venv(ws: str, fix: bool) -> list[Result]:
    work = os.path.join(ws, "game_files", "work")
    if not os.path.isdir(os.path.join(ws, "game_files")):
        return []
    py = os.path.join(work, "venv", "bin", "python")
    if not os.path.isfile(py) and fix:
        os.makedirs(work, exist_ok=True)
        _run([sys.executable, "-m", "venv", os.path.join(work, "venv")], timeout=300)
        req = os.path.join(ws, FORK, "requirements.txt")
        _run([py, "-m", "pip", "install", "-q", "-r", req, "ruff", "numpy"], timeout=900)   # numpy: MHGU-DE tools
    if not os.path.isfile(py):
        return [Result("warn", "venv", "game_files/work/venv missing; doctor --fix creates it")]
    code, msg = _run([py, "-c", "import " + ", ".join(VENV_MODULES)])
    if code:
        return [Result("warn", "venv", f"venv lacks modules ({msg.splitlines()[-1] if msg else '?'})")]
    return [Result("ok", "venv", "game_files/work/venv has " + ", ".join(VENV_MODULES))]


# ── repositories ───────────────────────────────────────────────────────────

def check_identity(path: str, fix: bool = False) -> Result:
    """The repo's own user.name/user.email must be the project's, not inherited from ~/.gitconfig."""
    name = os.path.basename(path)
    _, local_name = _run(["git", "config", "--local", "user.name"], cwd=path)
    _, local_email = _run(["git", "config", "--local", "user.email"], cwd=path)
    if (local_name, local_email) != (GIT_NAME, GIT_EMAIL) and fix:
        _run(["git", "config", "--local", "user.name", GIT_NAME], cwd=path)
        _run(["git", "config", "--local", "user.email", GIT_EMAIL], cwd=path)
        return Result("ok", "identity", f"{name}: set to {GIT_NAME}")
    if (local_name, local_email) == (GIT_NAME, GIT_EMAIL):
        return Result("ok", "identity", f"{name}: commits as {GIT_NAME}")
    return Result("FAIL", "identity", f"{name}: no repo-local {GIT_NAME} identity, commits would use the global one "
                  "(doctor --fix sets it)")


def repo_state(path: str, fetch: bool = False) -> list[Result]:
    name = os.path.basename(path)
    if not os.path.isdir(os.path.join(path, ".git")):
        return [Result("FAIL", "git", f"{name}: not a git repository here")]
    if fetch:
        _run(["git", "fetch", "-q", "origin"], cwd=path, timeout=120)
    out = []
    _, branch = _run(["git", "branch", "--show-current"], cwd=path)
    _, dirty = _run(["git", "status", "--porcelain"], cwd=path)
    n_dirty = len([x for x in dirty.splitlines() if x.strip()])
    where = f"{name}: on {branch or '(detached)'}"
    out.append(Result("warn", "git", f"{where}, {n_dirty} uncommitted change(s)") if n_dirty
               else Result("ok", "git", f"{where}, clean"))
    _, refs = _run(["git", "for-each-ref", "--format=%(refname:short)\t%(upstream:short)\t%(upstream:track)",
                    "refs/heads"], cwd=path)
    for row in refs.splitlines():
        parts = (row.split("\t") + ["", ""])[:3]
        local, upstream, track = parts
        # commits that no remote branch contains: not pushed anywhere (as of the last fetch)
        code, ahead = _run(["git", "rev-list", "--count", local, "--not", "--remotes"], cwd=path)
        if code == 0 and ahead.strip() not in ("", "0"):
            n = ahead.strip()
            out.append(Result("warn", "git", f"{name}: {local} has {n} commit(s) on no remote (not pushed)"))
        if "behind" in track:
            out.append(Result("warn", "git", f"{name}: {local} {track.strip('[]')} vs {upstream}"))
        elif "gone" in track:
            out.append(Result("warn", "git", f"{name}: {local}'s upstream {upstream} is gone"))
    return out


# ── Claude's workspace files ───────────────────────────────────────────────

def check_install(ws: str, install: bool, source: str = WORKSPACE_FILES) -> list[Result]:
    out = []
    for dest_rel, src_rel in INSTALL.items():
        src, dest = os.path.join(source, src_rel), os.path.join(ws, dest_rel)
        same = os.path.isfile(dest) and filecmp.cmp(src, dest, shallow=False)
        if not same and install:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(src, dest)
            same = True
            out.append(Result("ok", "workspace", f"installed {dest_rel}"))
        elif not same:
            what = "differs from" if os.path.isfile(dest) else "missing; from"
            out.append(Result("warn", "workspace", f"{dest_rel} {what} tools/workspace/ (doctor --install)"))
    if not out:
        out.append(Result("ok", "workspace", "CLAUDE.md, hook and skills match tools/workspace/"))
    return out


def run_tests(ws: str) -> list[Result]:
    py = os.path.join(ws, "game_files", "work", "venv", "bin", "python")
    py = py if os.path.isfile(py) else sys.executable
    out = []
    for repo in (CONTENT, FORK):
        code, msg = _run([py, "-m", "pytest", "-q"], cwd=os.path.join(ws, repo), timeout=1800)
        last = msg.splitlines()[-1] if msg else "no output"
        out.append(Result("ok" if code == 0 else "FAIL", "tests", f"{repo}: {last}"))
    return out


def doctor(ws: str, fix=False, install=False, fetch=False, tests=False) -> list[Result]:
    results = check_install(ws, install)
    for repo in (CONTENT, FORK):
        results += repo_state(os.path.join(ws, repo), fetch)
        if os.path.isdir(os.path.join(ws, repo, ".git")):
            results.append(check_identity(os.path.join(ws, repo), fix))
    results += check_venv(ws, fix)
    results += check_dumps(ws, fix)
    if tests:
        results += run_tests(ws)
    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workspace", default=os.path.dirname(REPO))
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--tests", action="store_true")
    ap.add_argument("--session-start", action="store_true")
    a = ap.parse_args(argv)
    try:
        results = doctor(a.workspace, a.fix, a.install, a.fetch, a.tests)
    except Exception as e:  # the hook must never break a session
        if not a.session_start:
            raise
        results = [Result("FAIL", "doctor", f"crashed: {e}")]
    if a.session_start:
        shown = [r for r in results if r.level != "ok" or r.area in ("git", "identity")]
        n_ok = sum(r.level == "ok" for r in results)
        print("# Workspace doctor (tools/doctor.py)")
        print("\n".join(r.line() for r in shown))
        print(f"({n_ok} checks ok; run `python3 {CONTENT}/tools/doctor.py` for all of them)\n")
        status = os.path.join(REPO, "STATUS.md")
        if os.path.isfile(status):
            with open(status) as f:
                print(f.read())
        return 0
    print("\n".join(r.line() for r in results))
    return 1 if any(r.level == "FAIL" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
