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
- Starter prewarm:
  - interviewer partial transcripts can prewarm a `starter`
  - locked questions can reuse the warmed fast-lane draft instead of always starting cold
  - backend now exposes serialized prewarm state for session/runtime polling
  - desktop UI now shows prewarm status, preview text, and warm-start metrics
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

- Backend tests: `35/35` passing
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
- Runtime prewarm regression:
  - partial interviewer transcript now prewarms the starter lane
  - locked question reuses the warmed starter when the partial and final question match
- Runtime prewarm visibility:
  - session responses now include `prewarm`
  - session snapshots include active `prewarms`
  - live bridge responses include `last_prewarm`
  - answer UI marks reused warm starts with `prewarmed starter`

## Known gaps

- Multi-interviewer speaker separation inside the system stream is not implemented
- Minimal workspace UI exists, but richer upload/indexing UX still needs to be built
- Need more real-user testing on:
  - naturalness
  - latency tolerance
  - follow-up consistency
  - project-specific answer quality

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

## Recovered Windows Desktop threads

Recovered on `2026-03-17` from local Codex Desktop session storage under `C:\Users\Administrator\.codex\sessions`.

Session reuse commands:

```powershell
codex resume --all
codex fork <SESSION_ID>
codex resume <SESSION_ID>
```

Thread map:

- `019cfaad-34b7-7a70-a683-7c1d30791ec1`
  - Thread title: `寻找国内 gpt-4o-mini-transcribe API`
  - CWD: `E:\qqbroDownload\interview_trainer_desktop`
  - What it established:
    - Alibaba realtime ASR smoke tests were run against local sample audio.
    - Report output was written to `run_logs/asr-live-postfix-report.json`.
    - `.vscode/alibaba.local.env` was updated with a tested Alibaba ASR key at that time.
    - The project still used an OpenAI-compatible chat provider for answer generation, not Alibaba text generation.
  - Practical takeaway:
    - ASR path and answer-generation path were still split.
    - If resuming this line of work, the next decision is whether to keep `ASR=Alibaba + LLM=OpenAI-compatible` or implement an Alibaba text-model provider.

- `019cfbe3-25e4-7f31-8486-d863a526c24d`
  - Thread title: `说明系统麦克风声音转文字设计和片段长度`
  - CWD: `E:\qqbroDownload\interview_trainer_desktop`
  - What it established:
    - This was mostly an architecture and runtime explanation thread.
    - It clarified the real-time pipeline:
      - `system/mic` split
      - chunked ASR
      - turn locking
      - `starter` / `full`
      - prewarm behavior
    - It also clarified that GPT sees the assembled locked interviewer question plus routed context, not raw tiny ASR chunks.
  - Practical takeaway:
    - Useful as the best “mental model” thread for understanding why the runtime behaves the way it does.

- `019cfbf1-f07f-7de3-913b-efdf5014758e`
  - Thread title in index: `测试阿里云 apikey 通信性好吗`
  - CWD: `E:\qqbroDownload\interview_trainer_desktop`
  - What it ended up doing:
    - It merged `origin/master` into the `interview_trainer_desktop-knowledge` worktree branch `codex/knowledge-library`.
    - It left a backup branch `codex/backup-knowledge-before-master-merge-20260317`.
    - Merge commit recorded there: `30ab7ae`.
    - It carried over the generation-settings UI/API path into the knowledge-library worktree.
    - Verification there was:
      - desktop build passing
      - backend `57/57` targeted tests passing
      - `tests.test_library_api` still blocked only by missing `httpx` in the venv
  - Practical takeaway:
    - This is the key thread if you need to continue work in `E:\qqbroDownload\interview_trainer_desktop-knowledge`.

- `019cf09a-2359-78b1-99db-b7a1b45b313a`
  - Original CWD: `e:\qqbroDownload\第二周：deep_research\deep_research`
  - This is not a current-project session by cwd, but it is an ancestor planning thread for the product direction.
  - What it established:
    - the Windows interview trainer MVP scope
    - visible training positioning
    - `system + mic` split
    - layered `starter` then `full`
    - project-aware knowledge packs
  - Later in the same long thread, work was also done directly in `E:\qqbroDownload\interview_trainer_desktop`:
    - serialized prewarm state was added to backend/runtime responses
    - desktop UI exposed prewarm status and metrics
    - commit recorded there: `feed280` with message `Expose starter prewarm state in runtime UI`
  - Practical takeaway:
    - Use this thread for product intent and early architecture rationale, not as the cleanest source of current repo status.

Recommended resume order:

1. For current `interview_trainer_desktop` runtime context, read this handoff first, then inspect `019cfaad` and `019cfbe3`.
2. For `interview_trainer_desktop-knowledge` branch/worktree context, inspect `019cfbf1`.
3. Only inspect `019cf09a` if you need the original MVP rationale or the early prewarm implementation history.

Most useful single bootstrap prompt for a recovered thread:

```text
Please continue from this recovered Codex Desktop context.

Project root:
E:/qqbroDownload/interview_trainer_desktop

First read:
E:/qqbroDownload/interview_trainer_desktop/CODEX_SESSION_HANDOFF.md

Then summarize:
1. what has already been completed
2. what still appears unfinished
3. which thread history is most relevant now
4. the next 3 concrete actions

Respond in Chinese and do not edit code until after the summary.
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
