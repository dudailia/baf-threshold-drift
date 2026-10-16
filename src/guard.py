"""Refuse to train or evaluate unless PREDICTIONS.md is committed and never changed since.

Run with: python -m src.guard   (prints the commit hash, exits non-zero on failure)
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class GuardError(Exception):
    pass


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def predictions_commit(repo=ROOT):
    commits = _git(repo, "log", "--format=%H", "--", "PREDICTIONS.md").split()
    if not commits:
        raise GuardError("PREDICTIONS.md is not committed")
    if len(commits) > 1:
        raise GuardError(f"PREDICTIONS.md was changed in more than one commit: {commits}")
    if _git(repo, "status", "--porcelain", "--", "PREDICTIONS.md"):
        raise GuardError("PREDICTIONS.md is modified since its commit")
    return commits[0]


if __name__ == "__main__":
    try:
        print(predictions_commit())
    except GuardError as e:
        sys.exit(f"guard: {e}")
