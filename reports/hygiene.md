# Repository hygiene check

Checked 2026-10-17 over the working tree and every commit in the history (`git rev-list --all`). Nothing was pushed; the repository has no remote.

| Item | Finding | Where | Action taken |
|---|---|---|---|
| Personal email | Every commit's author and committer email is a personal address (an icloud.com address). | Git commit metadata, all commits | None. Removing it requires rewriting history (for example `git filter-repo --mailcallback` or a `.mailmap` plus a rewrite), which is irreversible; left for the owner to decide before publishing. Setting `git config user.email` to a GitHub noreply address would avoid it in future commits. |
| Personal email in files | No personal email in any tracked file, in any commit. The only email address ever committed is `t@example.com` in tests/test_guard.py. | | None needed. |
| Student ID, phone number | None found (searched for 9-digit IDs and phone-number patterns, excluding results CSV and JSON). | | None needed. |
| Name | The owner's full name appears once, in PREDICTIONS.md ("Written by ... before any data file was opened"). | PREDICTIONS.md line 3 | None: PREDICTIONS.md must not be edited. |
| Absolute paths with the username | Absolute paths under `/Users/<username>/` appear in the independent checkers' scripts, kept verbatim as records; one also contains a `/private/tmp/` scratch path that includes the username. They are present in 21 commits (main check) and 3 commits (post hoc check). | reports/independent_check/bootstrap.py, compare.py, recompute.py; reports/independent_check_posthoc/check.py | None, to keep the scripts verbatim. Before publishing, replace the paths with relative ones in a new commit (history would still contain them unless rewritten). |
| Credentials | No API keys, tokens, passwords or Kaggle credentials in any commit. The word "token" appears only in code (`src/trace.py`) and in the progress log line recording that no Kaggle token was found. | | None needed. |
| Data | No file under `data/` has ever been committed; `data/` is in .gitignore. No raw CSV is tracked outside `results/` and `results_posthoc/` (which hold aggregates only). | | None needed. |
| References to other projects | None. CLAUDE.md states the rule not to copy code from the owner's other projects without naming any. The two GitHub repositories named in reports/related_work.md belong to third parties and are cited as related work. | | None needed. |
