import subprocess

import pytest

from src.guard import GuardError, predictions_commit


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "t")
    (tmp_path / "README.md").write_text("x")
    git(tmp_path, "add", "README.md")
    git(tmp_path, "commit", "-q", "-m", "init")
    return tmp_path


def _commit_predictions(repo, text="p"):
    (repo / "PREDICTIONS.md").write_text(text)
    git(repo, "add", "PREDICTIONS.md")
    git(repo, "commit", "-q", "-m", "Pre-register predictions")
    return git(repo, "rev-parse", "HEAD")


def test_refuses_when_predictions_missing(repo):
    with pytest.raises(GuardError, match="not committed"):
        predictions_commit(repo)


def test_returns_hash_of_the_committing_commit(repo):
    h = _commit_predictions(repo)
    (repo / "other.txt").write_text("later")
    git(repo, "add", "other.txt")
    git(repo, "commit", "-q", "-m", "later work")
    assert predictions_commit(repo) == h


def test_refuses_uncommitted_edit(repo):
    _commit_predictions(repo)
    (repo / "PREDICTIONS.md").write_text("edited")
    with pytest.raises(GuardError, match="modified"):
        predictions_commit(repo)


def test_refuses_committed_edit(repo):
    _commit_predictions(repo)
    (repo / "PREDICTIONS.md").write_text("edited")
    git(repo, "commit", "-q", "-am", "edit")
    with pytest.raises(GuardError, match="more than one commit"):
        predictions_commit(repo)
