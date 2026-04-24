# AGENTS.md

This file governs `subject_teacher/` and all child paths.
Use it together with the repository-level `AGENTS.md`; this file only adds tighter rules for the subject-teacher app.

## Scope

`subject_teacher` is the separate app for subject teachers.
It is not the homeroom-teacher GUI flow in `interface_teacher.py`.

Primary responsibilities in this package:

- Google OAuth + Drive `appDataFolder` persistence
- DPAPI-backed local token/password storage
- Subject-attendance NEIS Selenium automation
- Subject-teacher GUI and helper scripts

Shared root modules still matter here:

- `regions.py`
- `utils.py`
- `logger_config.py`
- `config.py`

Prefer changing `subject_teacher/*` first.
Only edit shared root modules when the task truly affects both apps.

## Run And Debug

- Runtime assumption: this app is Windows-oriented and expects GUI/OAuth dependencies from `requirements.txt` to be installed.
- GUI launch: `python -m subject_teacher.main`
- OAuth bootstrap: `python -m subject_teacher.scripts.authorize`
- Seed sample Drive data: `python -m subject_teacher.scripts.seed_sample --date 2026-04-20 --region 경기`
- Manual one-day sync: `python -m subject_teacher.scripts.run_day_manually --date 2026-04-20 --neis-password <PW> --region 경기 --close`

## Code Map

- `main.py`: GUI entry point
- `gui/app.py`: top-level CustomTkinter shell
- `gui/setup_tab.py`: settings, timetable, and student roster editing
- `gui/run_tab.py`: OAuth refresh, summary view, and threaded NEIS execution
- `app_service.py`: run orchestration, Selenium driver creation, Drive-to-NEIS preparation, sync-flag updates
- `state.py`: store factory, local password helpers, TSV serialization/parsing, daily summary helpers
- `auth/`: Google OAuth and DPAPI token storage
- `drive/`: appDataFolder client, schemas, migrations, persistence
- `neis/runner.py`: per-day orchestration with per-slot failure isolation
- `neis/subject_commands.py`: low-level selectors and button/cell interactions
- `scripts/`: manual bootstrap and operator utilities

## Data And Security Rules

- Drive JSON contracts use camelCase aliases via Pydantic models in `drive/schemas.py`; keep stored field compatibility unless a migration is added.
- If schema shape changes, update `drive/migrations.py` and the corresponding tests in `tests/test_drive_*`.
- Never store the NEIS certificate password or Google tokens in Drive JSON.
- Local secrets belong under `%LOCALAPPDATA%/NeisSubject` through `paths.py` and `auth/token_store.py`.
- In tests or non-Windows shells, set `LOCALAPPDATA` to a writable temp path before calling path/token helpers directly.
- Do not commit `client_secrets.json`, `token.bin`, `password.bin`, or ad-hoc debug dumps such as `tmp_student_candidates.json`.

## Change Guidance

- Keep the subject-teacher app separate from the homeroom app; avoid coupling new logic back into `interface_teacher.py` unless explicitly requested.
- Preserve background execution for long-running Drive/NEIS work so the GUI does not block.
- Prefer small helper additions over large abstraction layers; this package is still compact and task-oriented.
- When touching Selenium selectors or click flows, keep fallbacks and failure diagnostics intact because NEIS markup is brittle.
- When touching `build_day_input`, sync flags, or summary logic, verify both unchecked-slot behavior and re-run/idempotency behavior.

## Verification

Run the smallest relevant test set first, then widen only if your change crosses boundaries.

- State/service flow: `pytest tests/test_subject_teacher_state.py tests/test_app_service.py tests/test_neis_runner.py`
- Selectors: `pytest tests/test_subject_commands_selectors.py`
- Drive/auth/path contracts: `pytest tests/test_drive_client.py tests/test_drive_store.py tests/test_drive_schemas.py tests/test_drive_migrations.py tests/test_google_oauth.py tests/test_token_store.py tests/test_password_crypto.py tests/test_paths.py`

If you change GUI behavior, add at least targeted logic coverage where possible and note any manual-only verification gaps in the final report.
