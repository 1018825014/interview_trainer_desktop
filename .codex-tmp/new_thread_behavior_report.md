# New Thread Behavior Report

## 1. AGENTS / skills / workflow constraints currently visible

- The active repository and user-level AGENTS guidance both prefer direct implementation for routine work over heavy process.
- For normal coding work, I should not proactively switch into Superpowers or other formal skill workflows unless the user explicitly asks for that or the task is unusually risky, unclear, architectural, or hard to debug.
- Routine small features, small bugfixes, and simple refactors should not default to brainstorming, TDD, or a written plan.
- If overlapping instructions exist, I should prefer the least process-heavy interpretation that still preserves correctness, safety, and verification.
- Changes should stay focused on the task, respect in-progress local work, and avoid reverting user changes unless explicitly asked.
- Before claiming implementation work is complete, I should run the narrowest realistic verification for the area touched. For backend work, prefer targeted `pytest` from `backend/` with `PYTHONPATH=src`; for desktop work, prefer the narrowest relevant build or smoke check from `desktop/`.
- Repo-specific product constraints include keeping the product inside visible interview practice, clearly disclosing AI assistance, avoiding hidden monitoring/evasion/stealth behavior, and preserving backend/desktop contracts.
- A skills catalog is available, and the prompt says if the user explicitly names a skill or a task clearly matches a skill trigger, that skill should be used for that turn. However, the higher-level collaboration preferences and interpretation sections explicitly say not to proactively use heavy workflows for straightforward work.

## 2. Default behavior for a routine small feature, small bugfix, or simple refactor

I would default to direct implementation, not first switch into a formal workflow such as brainstorming, TDD, or a written plan.

## 3. Main responsibility of `backend/src/interview_trainer/library_session.py`

`backend/src/interview_trainer/library_session.py` is responsible for assembling a library interview session payload from workspace knowledge plus a selected preset and optional overlay.

More specifically, `LibrarySessionBuilder`:

- selects the relevant knowledge subset from the workspace, especially which projects and role documents to include;
- normalizes project data into a consistent payload shape;
- calls `LibraryCompiler` to compile that selected knowledge into retrieval units, evidence, metrics, terminology, and compiled knowledge;
- calls `BriefingBuilder` to produce the user-facing briefing text/data using the compiled knowledge and overlay context;
- returns one combined payload containing:
  - `knowledge`
  - `briefing`
  - `activation_summary`
  - `artifact_index`

In short, this module is the backend assembly layer that turns stored library knowledge into the structured payload needed to activate a practice session.

## 4. Formal skill usage during this task

none

## 5. Files changed and verification

- Files changed: `E:\qqbroDownload\interview_trainer_desktop-knowledge\.codex-tmp\new_thread_behavior_report.md`
- Verification commands run: none beyond read-only inspection commands, because this was a behavior check and no application code was modified.
