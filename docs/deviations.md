# Deviations from the implementation guide

Every change from `docs/implementation guide.pdf` is logged here: what, why, evidence.

Format: date · phase · what changed · why · evidence (command output or error).

---

## 2026-10-10 · Phase 0 · `.gitignore` contains one extra entry: `.venv-dev/`

- **What**: The guide's repository-layouts comment lists `.venv/ __pycache__/ *.parquet
  mlruns/ .pytest_cache/`; we also ignore `.venv-dev/`.
- **Why**: Guide step 3.0 creates a second virtualenv `.venv-dev/` in the repo root for
  local development. Without the entry, a later `git add -A` could commit thousands of
  venv files. Preventive, zero behavioural impact.
- **Evidence**: Guide step 3.0: `python3.11 -m venv .venv-dev`.

## 2026-10-10 · Phase 0 · Guide filename differs from the task description

- **What**: The task text refers to `docs/IMPLEMENTATION_GUIDE.md`; the repository
  actually contains `docs/implementation guide.pdf` (81 pages, 1,970,639 bytes).
- **Why**: The PDF is the only guide present; its text was extracted with
  `pdftotext -layout` and read in full. No content skipped; no file renamed.
- **Evidence**: `ls -la docs/` shows only `implementation guide.pdf` and `progress.md`.
