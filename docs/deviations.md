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

## 2026-10-10 · Phase 3 · `ruff.toml` introduced early with an explicit `select`

- **What**: The guide defines `ruff.toml` (line-length 120, target-version py311) in
  Phase 6.1. We wrote it in Phase 3, adding `[lint] select = ["E4", "E7", "E9", "F"]`.
- **Why**: Gate 3 requires `ruff check services scripts` to be clean. With the pinned
  ruff 0.17.0 and NO repo config, ruff's built-in defaults enable a much broader rule
  set than the classic E4/E7/E9/F defaults — it flagged 6 findings in guide-written code
  (EXE001, I001 x4, SIM114) and would keep flagging guide code in later phases
  (`except Exception` patterns etc.). Pinning the selection makes the gate's meaning
  stable and matches the guide's evident assumption. No guide file content was altered.
- **Evidence**: `ruff check --show-settings` lists YTT*/ASYNC*/SIM*/I* rules as
  `linter.rules.enabled` with no user or repo config present
  (`ls ~/.config/ruff/` → nothing); findings reproduced in the gate-3 run logged in
  docs/PROGRESS.md.

## 2026-10-10 · Phase 6 · loop-controller requirements gain numpy==2.4.6

- **What**: Added `numpy==2.4.6` to `services/loop-controller/requirements.txt`
  (guide 5.1 lists the file without numpy).
- **Why**: The Docker runtime stage installs every wheel in /wheels with
  `pip install --no-index --find-links=/wheels`, and `fareops-common` declares
  `dependencies = ["numpy", "requests"]` (guide 3.1). No other loop-controller pin
  pulls numpy, so no numpy wheel was built and the offline install failed:
  `ERROR: Could not find a version that satisfies the requirement numpy
  (from fareops-common) (from versions: none)`. Caught by a local `docker build`
  smoke test of all four images before CI ran; the CI build (same Dockerfile, same
  offline install) would fail identically.
- **Evidence**: `/tmp/build-loop-controller.log` (docker buildx failure at the
  runtime `pip install` step); fare-api and trainer built OK because their own
  requirements already pin numpy. The CI **test** job is unaffected (it installs
  all three requirements files together, so numpy was present there).
