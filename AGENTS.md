# Project Collaboration Preferences

This repository contains a Python backend in `backend/` and an Electron/React desktop app in `desktop/`.

## Default Working Style

- Prefer direct implementation for routine coding work instead of heavy process.
- Treat brainstorming, TDD, written plans, and other formal workflows as optional tools unless the user explicitly asks for them or the task is unusually risky.
- Do not assume small features, routine bugfixes, or narrow refactors require a formal skill workflow.
- Keep changes focused on the task at hand and avoid unrelated cleanup unless it is necessary to finish safely.
- Respect in-progress local changes. Do not revert user work unless explicitly asked.

## Verification

- Before claiming a change is complete, run the narrowest realistic verification for the area you touched.
- For backend changes, prefer targeted `pytest` runs from `backend/` with `PYTHONPATH=src` set.
- For desktop changes, prefer the narrowest relevant build or smoke check from `desktop/`.
- If a change crosses backend and desktop boundaries, verify both sides as needed.
- If verification cannot be run, say so clearly and explain what remains unverified.

## Repo Notes

- Backend dev start command from `backend/`:
  - `$env:PYTHONPATH="src"`
  - `.\.venv\Scripts\python -m interview_trainer --serve --host 127.0.0.1 --port 8000`
- Keep the product inside visible interview practice and clearly disclosed AI assistance.
- Do not add hidden monitoring, evasion, or stealth-oriented behavior.
- Prefer meaningful increments that preserve the contract between backend APIs and the desktop client.
