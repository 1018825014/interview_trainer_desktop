# Codex Session Handoff

This file is a local snapshot of the current project state so a new Codex thread can resume work quickly.

Pair this file with:

- `FUTURE_DEVELOPMENT_SPEC.md`
- `PERSISTENT_KNOWLEDGE_THREAD_PROMPT.md`
- `MULTI_THREAD_WORKFLOW.md`
- `THREAD_OWNERSHIP.md`

The handoff file records current state.
The future spec records what still needs to be built next.

## Product scope

- Project: `interview_trainer_desktop`
- Positioning: visible Windows desktop app for mock interviews or clearly disclosed AI-assisted practice
- Explicitly out of scope: hidden overlays, screen-share evasion, recording evasion

## Current architecture

- Desktop shell: Electron + React + TypeScript
- Backend: Python
- Audio: Windows `WASAPI loopback + mic` support, with manual and native session modes
- ASR: chunked transcription and optional OpenAI Realtime bridge
- Answer pipeline:
  - overlap-aware turn manager
  - knowledge routing
  - layered `starter` / `full` answer generation
  - optional streaming `starter`

## Important implemented pieces

- Audio capability probing and recommendation
- Knowledge workspace management
- Audio session manager
- Native audio capture worker path
- Live bridge:
  - `audio session -> ASR -> interview session -> answer`
- Partial transcripts for Realtime ASR
- Adaptive gate + lightweight VAD
- Streaming starter answer state:
  - `pending`
  - `starter_streaming`
  - `starter_ready`
  - `complete`
  - `failed`
- Starter metrics:
  - `starter_stream_ms`
  - `starter_ms`
  - `full_ms`
- Split generation lanes:
  - `fast`
  - `smart`
- Workspace API:
  - create/list/update
  - compile
  - import local project path
- Minimal desktop workspace panel:
  - profile/project/role notes
  - local path import
  - compile and attach to session

## Generation config model

Shared generation env vars still work:

```powershell
set INTERVIEW_TRAINER_LLM_PROVIDER=openai
set INTERVIEW_TRAINER_LLM_API_KEY=...
set INTERVIEW_TRAINER_LLM_BASE_URL=...
set INTERVIEW_TRAINER_FAST_MODEL=...
set INTERVIEW_TRAINER_SMART_MODEL=...
```

Lane-specific overrides are now supported:

```powershell
set INTERVIEW_TRAINER_FAST_PROVIDER=template
set INTERVIEW_TRAINER_FAST_MODEL=template-fast
set INTERVIEW_TRAINER_SMART_PROVIDER=openai
set INTERVIEW_TRAINER_SMART_API_KEY=...
set INTERVIEW_TRAINER_SMART_BASE_URL=https://subrouter.ai/v1
set INTERVIEW_TRAINER_SMART_MODEL=gpt-5.4
set INTERVIEW_TRAINER_SMART_TIMEOUT_S=45
```

Recommended current setup:

- `fast`: template or a genuinely fast compatible model
- `smart`: stronger remote model

## Last real validation results

- Backend tests: `33/33` passing
- Desktop build: `npm run build` passing
- Real compatible generation smoke:
  - provider style: OpenAI-compatible chat completions
  - streaming starter observed
  - example timing:
    - `starter_stream_ms`: about `8102`
    - `starter_ms`: about `12332`
  - `gpt-5.4` is still too slow to be the true fast model
- Mixed lane smoke:
  - `fast=template`
  - `smart=gpt-5.4`
  - immediate starter works
  - `full` may still take longer than short debug windows

## Known gaps

- Multi-interviewer speaker separation inside the system stream is not implemented
- Minimal workspace UI exists, but richer upload/indexing UX still needs to be built
- Need more real-user testing on:
  - naturalness
  - latency tolerance
  - follow-up consistency
  - project-specific answer quality

## Knowledge-Library Thread Update

- Thread focus: `local persistent multi-project knowledge library`
- Current stage completed:
  - design alignment
  - Stage 1 persistent workspace foundation
- Design direction chosen:
  - local hybrid storage: `SQLite + library_objects/`
  - long-term library separated from interview-specific overlays
  - multiple workspaces, projects, repos, documents, presets, and compiled bundles
  - runtime answer-control layer built around:
    - `QuestionIntent`
    - `AnswerPlan`
    - `AnswerState`
    - typed `RetrievalUnit`
    - `EvidenceCard / MetricEvidence`
- Explicitly out of scope for this thread:
  - audio capture changes
  - ASR optimization
  - live bridge feature work
- Design spec written to:
  - `docs/superpowers/specs/2026-03-17-persistent-knowledge-library-design.md`
- Implementation plan written to:
  - `docs/superpowers/plans/2026-03-17-persistent-knowledge-library.md`
- Stage 1 implemented:
  - `WorkspaceManager` now supports persistent local storage via `SQLite`
  - workspace data survives manager restart
  - imported docs/code content now stores through `library_objects`
  - project-level `repo_summaries` metadata is persisted and restored
  - backend tests were updated to use temp storage instead of polluting the repo
- New backend files added in Stage 1:
  - `backend/src/interview_trainer/library_paths.py`
  - `backend/src/interview_trainer/library_store.py`
  - `backend/src/interview_trainer/library_repository.py`
  - `backend/tests/test_library_store.py`
  - `backend/tests/test_library_repository.py`
- Stage 1 verification:
  - backend unittest: `35/35` passing
  - targeted persistence tests:
    - `test_library_store.py`
    - `test_library_repository.py`
    - `test_workspace.py`
- Recommended next implementation order:
  1. expand Stage 1 storage into true library CRUD endpoints and schema surfaces
  2. compile and retrieval-unit generation
  3. preset / overlay session payload activation
  4. desktop library UI split and management flow

## Best next debugging tasks

1. Run the backend locally and verify API endpoints.
2. Run the desktop renderer and confirm UI state transitions.
3. Test one real interview-style question with your own project context.
4. Measure whether starter naturalness and latency are acceptable.
5. Decide whether the next build step should prioritize:
   - upload/indexing
   - answer quality tuning
   - a faster fast-model provider

## Commands

Backend tests:

```powershell
cd backend
set PYTHONPATH=src
python -m unittest discover -s tests -v
```

Backend demo:

```powershell
cd backend
set PYTHONPATH=src
python -m interview_trainer --demo
```

Live bridge demo:

```powershell
cd backend
set PYTHONPATH=src
python -m interview_trainer --live-bridge-demo
```

Start backend API:

```powershell
cd backend
set PYTHONPATH=src
python -m interview_trainer --serve --host 127.0.0.1 --port 8000
```

Build desktop:

```powershell
cd desktop
npm run build
```

Renderer dev:

```powershell
cd desktop
npm run dev:renderer
```

## Bootstrap prompt for a new Codex thread

Use this at the top of a fresh thread:

```text
Please continue from these files:
E:/qqbroDownload/interview_trainer_desktop/CODEX_SESSION_HANDOFF.md
E:/qqbroDownload/interview_trainer_desktop/FUTURE_DEVELOPMENT_SPEC.md

Project root:
E:/qqbroDownload/interview_trainer_desktop

First, read both files and inspect the current backend and desktop status.
Then follow the recommended order in the spec.
Respond in Chinese.
```
