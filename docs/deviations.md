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

## 2026-10-10 · Phase 1 · YAML indentation reconstructed from the PDF text layer

- **What**: The guide's Phase 1 Ansible YAML is line-wrapped by the PDF layout (task
  keys, `when:` clauses and list items broken across lines with drifting indentation).
  Files were written with valid YAML indentation matching the guide's evident structure.
- **Why**: PDF-extracted indentation is not valid YAML; structure (task names, module
  args, conditions, order) is unchanged from the guide.
- **Evidence**: `make up` ran the playbook twice: first run `failed=0`, second run
  `changed=0` (idempotent) — both pasted in docs/PROGRESS.md.

## 2026-10-10 · Phase 3 · pyarrow stepped down 26.0.0 → 25.0.1 (guide rule: "If a pinned set fails pip install together...")

- **What**: `pyarrow==26.0.0` (newest on PyPI) replaced by `pyarrow==25.0.1` (newest < 26)
  in `versions.md`, `scripts/requirements-host.txt` and `services/trainer/requirements.txt`.
- **Why**: `pip install -r services/trainer/requirements.txt` failed with
  `ResolutionImpossible: Cannot install mlflow==3.17.0 ... and pyarrow==26.0.0`.
  mlflow 3.17.0 declares `pyarrow<26,>=4.0.0`; 25.0.1 is the newest satisfying it.
  The guide's rule names numpy, but the mechanism it defines (step the conflicting pin
  down to the newest mutually-acceptable version, record why here) applies to any pin.
- **Evidence**: `curl -s https://pypi.org/pypi/mlflow/3.17.0/json` →
  `['numpy<3', 'pandas<4', 'pyarrow<26,>=4.0.0', ...]`; pandas 3.0.6 requires
  `pyarrow>=13.0.0` (extras only) and lightgbm 4.7.0 `numpy>=1.21.3`, so 25.0.1 and
  numpy 2.4.6 remain acceptable to every other pin.
