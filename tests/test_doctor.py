"""tools/doctor.py on temporary folders and git repositories (no game data)."""
from __future__ import annotations

import os
import subprocess

import doctor
import pytest


@pytest.fixture(autouse=True)
def git_identity(monkeypatch):
    for k, v in (("GIT_AUTHOR_NAME", "t"), ("GIT_AUTHOR_EMAIL", "t@t"), ("GIT_COMMITTER_NAME", "t"),
                 ("GIT_COMMITTER_EMAIL", "t@t")):
        monkeypatch.setenv(k, v)


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _repo(path):
    os.makedirs(path)
    _git(path, "init", "-q", "-b", "main")
    (open(os.path.join(path, "a.txt"), "w")).write("a")
    _git(path, "add", "a.txt")
    _git(path, "commit", "-q", "-m", "first")
    return path


def _work(path, info="NCCH crypto   : none (decrypted)\n"):
    os.makedirs(path)
    for n in ("exheader.bin", "code.bin", "romfs.bin"):
        open(os.path.join(path, n), "wb").close()
    with open(os.path.join(path, "info.txt"), "w") as f:
        f.write(info)


def test_extraction_state(tmp_path):
    assert doctor.extraction_state(str(tmp_path / "none")) == "missing"
    _work(str(tmp_path / "ok"))
    assert doctor.extraction_state(str(tmp_path / "ok")) == "ok"
    _work(str(tmp_path / "enc"), "error: NCCH is encrypted\n")
    assert doctor.extraction_state(str(tmp_path / "enc")) == "encrypted"
    os.makedirs(tmp_path / "part")
    assert doctor.extraction_state(str(tmp_path / "part")) == "partial"


def test_check_dumps(tmp_path, monkeypatch):
    assert doctor.check_dumps(str(tmp_path), fix=False)[0].level == "warn"   # no game_files/
    games = tmp_path / "game_files"
    games.mkdir()
    (games / "a.3ds").write_bytes(b"")
    (games / "b.3ds").write_bytes(b"")
    _work(str(games / "work" / "a"))
    monkeypatch.setattr(doctor, "load_dumps", lambda: {
        "a": {"file": "a.3ds", "role": "r"}, "b": {"file": "b.3ds", "role": "r"}, "c": {"file": "c.3ds", "role": "r"}})
    res = {r.text.split(":")[0]: r.level for r in doctor.check_dumps(str(tmp_path), fix=False)}
    assert res == {"a": "ok", "b": "warn", "c": "warn"}


def test_dumps_json_names_known_work_folders():
    dumps = doctor.load_dumps()
    assert {"mh4u_usa_upd", "mh3u_usa", "mhxx_jpn"} <= set(dumps)
    assert all({"file", "role"} <= set(d) for d in dumps.values())


def test_repo_state(tmp_path):
    repo = _repo(str(tmp_path / "r"))
    res = doctor.repo_state(repo)
    assert res[0].level == "ok" and "on main, clean" in res[0].text
    assert any("not pushed" in r.text for r in res)          # no remote at all
    open(os.path.join(repo, "b.txt"), "w").write("b")
    assert "1 uncommitted" in doctor.repo_state(repo)[0].text
    assert doctor.repo_state(str(tmp_path))[0].level == "FAIL"   # not a repository


def test_repo_state_pushed(tmp_path):
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "-q", "--bare", str(remote))
    repo = _repo(str(tmp_path / "r"))
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-q", "-u", "origin", "main")
    assert [r.level for r in doctor.repo_state(repo)] == ["ok"]
    _git(repo, "checkout", "-q", "-b", "feature", "--track", "origin/main")
    open(os.path.join(repo, "c.txt"), "w").write("c")
    _git(repo, "add", "c.txt")
    _git(repo, "commit", "-q", "-m", "c")
    assert any("feature has 1 commit(s) on no remote" in r.text for r in doctor.repo_state(repo))


def test_check_install(tmp_path, monkeypatch):
    src = tmp_path / "src"
    for rel in doctor.INSTALL.values():
        p = src / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(rel)
    ws = tmp_path / "ws"
    ws.mkdir()
    assert all(r.level == "warn" for r in doctor.check_install(str(ws), False, str(src)))
    doctor.check_install(str(ws), True, str(src))
    assert [r.level for r in doctor.check_install(str(ws), False, str(src))] == ["ok"]
    (ws / "CLAUDE.md").write_text("edited")
    assert any("differs" in r.text for r in doctor.check_install(str(ws), False, str(src)))


def test_workspace_sources_exist():
    for rel in doctor.INSTALL.values():
        assert os.path.isfile(os.path.join(doctor.WORKSPACE_FILES, rel)), rel


def test_session_start_never_fails(tmp_path, capsys):
    assert doctor.main(["--workspace", str(tmp_path), "--session-start"]) == 0
    out = capsys.readouterr().out
    assert "Workspace doctor" in out and "# Status" in out   # STATUS.md follows the checks
