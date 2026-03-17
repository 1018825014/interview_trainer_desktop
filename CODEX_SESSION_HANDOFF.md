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
- Persistent desktop library panel:
  - multi-workspace / multi-project / multi-overlay / multi-preset navigation
  - project / overlay / preset editors
  - compile, local repo import, bundle summary, and session activation

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

- Backend tests: `57/57` passing (excluding `test_library_api`, which still needs `httpx` in the venv)
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
- Desktop library UX is now usable, but still lacks:
  - copy-from-compiled shortcuts and multi-project templates on top of the new batch authoring pack flow
  - more polished workspace-level artifact browsing for very large libraries
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
  - Stage 2 backend library CRUD API
  - Stage 3 answer-oriented library compile layer
  - Stage 4 overlays, presets, bundles, and session-payload activation
  - Stage 5 runtime answer-plan integration
  - Stage 6 retrieval-unit-first and evidence-aware runtime routing
  - Stage 7 desktop persistent library UX and session activation flow
  - Stage 8 normalized document assets and repo reindex
  - Stage 9 manual evidence / metric / retrieval-unit authoring
  - Stage 10 compiled preview inspection
  - Stage 11 bundle history compare and reuse
  - Stage 12 hook-aware retrieval and artifact diffs
  - Stage 13 workspace preview filters and direct document CRUD
  - Stage 14 project authoring-pack batch editing and validation
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
- Stage 2 implemented:
  - `WorkspaceManager` now exposes project-level CRUD methods:
    - list/create/get/update/delete project
    - list project repos
    - import repo into a selected project
  - imported existing workspaces are auto-upgraded to include:
    - `project_id`
    - `repo_summaries`
  - FastAPI now exposes `/api/library/...` endpoints for:
    - workspace list/create/get/update
    - project list/create/get/update/delete
    - project repo list
    - project repo `import-path`
  - `create_app()` now supports `workspace_storage_root` for isolated test storage
- Stage 2 verification:
  - targeted API tests:
    - `test_library_api.py`
  - regression tests:
    - `test_library_store.py`
    - `test_library_repository.py`
    - `test_workspace.py`
  - full backend unittest: `37/37` passing
- Stage 3 implemented:
  - added typed library compile artifacts:
    - `ModuleCardPlus`
    - `EvidenceCard`
    - `MetricEvidence`
    - `RetrievalUnit`
    - `CompiledBundlePayload`
  - added `LibraryCompiler` that reuses `KnowledgeCompiler` output and builds:
    - project intro / architecture / tradeoff / performance / module deep-dive units
    - document/code evidence cards
    - metric evidence extracted from library documents
  - `KnowledgeCompiler` now preserves incoming `project_id` when provided
- New backend files added in Stage 3:
  - `backend/src/interview_trainer/library_types.py`
  - `backend/src/interview_trainer/library_compile.py`
  - `backend/tests/test_library_compile.py`
- Stage 3 verification:
  - targeted compile tests:
    - `test_library_compile.py`
    - `test_knowledge.py`
  - full backend unittest: `38/38` passing
- Stage 4 implemented:
  - added `LibrarySessionBuilder` to bridge:
    - selected library projects
    - overlay metadata
    - compiled bundle stats
    - session-ready `knowledge + briefing + activation_summary`
  - `WorkspaceManager` now persists and manages:
    - richer project answer fields such as `pitch_30`, `tradeoffs`, `key_metrics`
    - overlays
    - presets
    - compiled bundle summaries
  - FastAPI now exposes library endpoints for:
    - overlay list/create/get/update
    - preset list/create/get/update
    - bundle list/get
    - preset `build-session-payload`
- New backend files added in Stage 4:
  - `backend/src/interview_trainer/library_session.py`
- Stage 4 verification:
  - targeted API tests:
    - `test_library_api.py`
    - `test_service.py`
  - full backend unittest: `39/39` passing
- Stage 5 implemented:
  - added `AnswerController` with runtime objects:
    - `AnswerPlan`
    - `AnswerState`
  - service now builds and stores plan/state for each generated answer turn
  - current plan/state snapshots are returned inside answer payloads
  - router can now bias pack assembly with `answer_plan`, including forcing code evidence when needed
  - prompt builder now includes intent, retrieval priority, template, and active follow-up state in prompt context
  - generation layer now accepts structured `answer_plan` and `answer_state` inputs end-to-end
- New backend files added in Stage 5:
  - `backend/src/interview_trainer/answer_control.py`
  - `backend/tests/test_answer_control.py`
- Stage 5 verification:
  - targeted control tests:
    - `test_answer_control.py`
    - `test_routing.py`
    - `test_service.py`
  - full backend unittest: `42/42` passing
- Stage 6 implemented:
  - added `LibraryRetriever` for bundle-aware runtime retrieval selection
  - `KnowledgePack` now carries:
    - `retrieval_refs`
    - `evidence_refs`
  - `ContextRouter.build_pack_for_plan()` now prioritizes:
    - retrieval units
    - evidence cards / metric evidence
    - project/module refs
    - code refs only when needed by plan
  - `InterviewTrainerService` now stores session-level compiled bundles and uses them to build plan-aware packs at answer time
  - prompt formatting and generation evidence refs now include retrieval/evidence items before code
- New backend files added in Stage 6:
  - `backend/src/interview_trainer/library_retriever.py`
- Stage 6 verification:
  - targeted retrieval tests:
    - `test_routing.py`
    - `test_generation.py`
    - `test_service.py`
  - full backend unittest: `44/44` passing
- Stage 7 implemented:
  - added dedicated frontend library types and `/api/library/...` API client:
    - `desktop/src/types/library.ts`
    - `desktop/src/api/library.ts`
  - split the old single-workspace form out of `App.tsx` into dedicated components:
    - `LibraryPanel`
    - `WorkspaceNav`
    - `ProjectEditor`
    - `OverlayEditor`
    - `PresetEditor`
    - `StatusRail`
  - desktop app now supports:
    - browsing persistent workspaces, projects, overlays, presets, and bundle summaries
    - editing project answer fields, overlay focus/style, and preset project selection
    - compiling the active workspace
    - importing a local repo into the selected project
    - building preset-backed session payloads
    - attaching a preset directly to the current interview session via existing `create_session`
  - `App.tsx` now keeps audio / ASR / live bridge sections intact while delegating knowledge-library UX to the new panel
- Stage 7 verification:
  - desktop build:
    - `npm run build`
  - full backend unittest:
    - `44/44` passing
- Stage 8 implemented:
  - unified project documents and role documents into document assets with stable metadata:
    - `document_id`
    - `scope`
    - `source_kind`
    - `source_path`
    - `repo_id`
    - `updated_at`
  - added backend asset APIs for:
    - project document list/create
    - role document list/create
    - document update/delete
    - repo reindex by `repo_id`
  - repo reindex now refreshes only repo-managed imported docs/code and preserves manual assets in the same project
  - frontend library panel now supports:
    - editing multiple role documents in the workspace editor
    - editing multiple project documents with per-asset metadata visible
    - showing code snapshot provenance in project assets
    - reindexing any imported repo from the status rail
  - sample/mock library data and frontend type mappings now use the normalized asset shape
- Stage 8 verification:
  - targeted backend asset tests:
    - `test_library_api.py`
    - `test_workspace.py`
    - `test_library_compile.py`
  - desktop build:
    - `npm run build`
  - full backend unittest:
    - `46/46` passing
- Stage 9 implemented:
  - added persistent project-level authoring fields for:
    - `manual_evidence`
    - `manual_metrics`
    - `manual_retrieval_units`
  - project CRUD now round-trips those fields through the library API and workspace serializer
  - `LibrarySessionBuilder` now carries authored materials into selected project payloads
  - `LibraryCompiler` now merges authored materials with auto-generated compile artifacts:
    - manual evidence cards are prepended and deduped by `evidence_id`
    - manual metric evidence is prepended and deduped by `evidence_id`
    - manual retrieval units are prepended and deduped by `unit_id`
  - desktop `ProjectEditor` now has dedicated authoring surfaces for:
    - manual evidence cards
    - manual metric evidence
    - manual retrieval units
  - frontend project serialization and mock workspace data were updated to carry the new authored-material shapes end-to-end
- Stage 9 verification:
  - targeted backend tests:
    - `test_library_compile.py`
    - `test_library_api.py`
  - desktop build:
    - `npm run build`
  - full backend unittest:
    - `48/48` passing
- Stage 10 implemented:
  - workspace compile now stores a lightweight compiled preview bundle alongside the existing `compiled_knowledge` summary
  - added preview APIs for compiled artifacts:
    - `GET /api/library/workspaces/{workspace_id}/compiled-preview`
    - `GET /api/library/projects/{project_id}/compiled-preview`
  - project compiled preview returns:
    - `module_cards`
    - `evidence_cards`
    - `metric_evidence`
    - `retrieval_units`
    - `terminology`
    - `compiled_at`
  - preview includes both auto-generated artifacts and previously authored manual evidence / metrics / retrieval units after compile
  - desktop `ProjectEditor` now fetches and renders the current project's compiled preview, so authored material can be compared against actual compile output in one place
- Stage 10 verification:
  - targeted backend tests:
    - `test_library_api.py`
  - desktop build:
    - `npm run build`
  - full backend unittest:
    - `49/49` passing
- Stage 11 implemented:
  - compiled bundle history is now persisted as snapshot records, not just summaries
  - each bundle record now keeps:
    - activation summary fields
    - saved `knowledge`
    - saved `briefing`
  - added bundle history APIs for:
    - bundle detail lookup
    - bundle-to-bundle comparison
    - reusing a historical bundle as a session payload snapshot
  - workspace serialization still exposes only lightweight bundle summaries, so the main library list does not become heavy
  - desktop bundle view now supports:
    - viewing saved briefing context for the selected bundle
    - comparing the current bundle with another bundle from history
    - activating the selected historical bundle directly into the current interview session
- Stage 11 verification:
  - targeted backend tests:
    - `test_library_api.py`
  - desktop build:
    - `npm run build`
  - full backend unittest:
    - `50/50` passing
- Stage 12 implemented:
  - runtime retrieval is now hook-aware:
    - `ContextRouter.build_pack_for_plan()` accepts `answer_state`
    - `LibraryRetriever` now prefers retrieval units with unused hooks when `allow_hook=true`
    - `KnowledgePack` now carries `hook_refs`
  - runtime answer state now persists used hook ids:
    - `AnswerController.advance_state()` records hook-bearing retrieval units already used in prior turns
    - prompts now expose used hook ids and selected hook refs to the model
  - bundle history compare is now artifact-aware, not only count-aware:
    - session-payload build now stores a lightweight bundle `artifact_index`
    - bundle compare API now reports added/removed:
      - retrieval units
      - evidence titles
      - hook texts
  - desktop bundle compare view now renders those detailed diffs directly in the bundle panel
- Stage 12 verification:
  - targeted backend tests:
    - `test_routing.py`
    - `test_generation.py`
    - `test_library_api.py`
  - desktop build:
    - `npm run build`
  - full backend unittest:
    - `51/51` passing
- Stage 13 implemented:
  - workspace-level compiled preview now supports backend filtering by:
    - `project_id`
    - `artifact_kind`
    - `search`
  - workspace preview API now returns lightweight `project_summaries` so the desktop app can browse artifact coverage per project
  - desktop workspace editor now includes a real workspace-level compiled preview panel with:
    - project filter
    - artifact-kind filter
    - keyword search
    - filtered module / evidence / metric / retrieval-unit cards
  - desktop document maintenance is now more direct:
    - project documents support explicit create / save / delete actions through document CRUD APIs
    - role documents support explicit create / save / delete actions through document CRUD APIs
  - these direct actions no longer require bundling document edits into a full workspace or project save every time
- Stage 13 verification:
  - targeted backend tests:
    - `test_library_api.py`
  - desktop build:
    - `npm run build`
  - full backend unittest:
    - `52/52` passing
- Stage 14 implemented:
  - added project-level authoring-pack APIs:
    - `GET /api/library/projects/{project_id}/authoring-pack`
    - `POST /api/library/projects/{project_id}/authoring-pack/preview`
    - `PUT /api/library/projects/{project_id}/authoring-pack`
  - backend authoring-pack preview now validates:
    - duplicate supporting-ref ids shared across manual evidence and manual metrics
    - duplicate retrieval-unit ids
    - missing `supporting_refs`
    - warnings for unused supporting refs or retrieval units missing question forms / refs
  - desktop `ProjectEditor` now includes a dedicated `Batch Authoring Pack` panel that can:
    - generate a JSON draft from the current project form
    - preview validation results before saving
    - show available supporting ref ids for retrieval-unit authoring
    - apply a validated pack atomically to manual evidence / metrics / retrieval units
  - applying a batch authoring pack now invalidates local compiled preview state until the next workspace compile
- Stage 14 verification:
  - targeted backend tests:
    - `test_library_api.py`
  - desktop build:
    - `npm run build`
  - full backend unittest:
    - `68/68` passing
- Stage 15 implemented:
  - added compiled-preview-to-authoring template API:
    - `POST /api/library/projects/{project_id}/authoring-pack/template`
  - backend template generation now supports:
    - `source=compiled_preview`
    - `mode=replace|append`
    - selecting specific `evidence_ids`
    - selecting specific `metric_ids`
    - selecting specific `retrieval_unit_ids`
  - when a selected retrieval unit references supporting refs, template generation now auto-includes the needed compiled evidence / metric entries
  - append mode now preserves existing manual authoring materials and upserts generated items by id instead of duplicating them
  - desktop `ProjectEditor` authoring-pack panel now supports:
    - `Draft From Compiled`
    - `Append From Compiled`
    - exporting the current authoring draft JSON
    - importing a saved authoring JSON file
  - compiled preview cards now expose direct shortcuts to append:
    - a single evidence card
    - a single metric card
    - a single retrieval unit
    into the current authoring draft
- Stage 15 verification:
  - targeted backend tests:
    - `tests.test_library_api -v`
  - desktop build:
    - `npm run build`
  - full backend unittest:
    - `70/70` passing
- Stage 16 implemented:
  - added preset workflow APIs:
    - `POST /api/library/presets/{preset_id}/clone`
    - `GET /api/library/presets/{left_preset_id}/compare/{right_preset_id}`
  - backend preset compare now reports:
    - added projects
    - removed projects
    - shared projects
    - overlay name changes
    - role-document toggle changes
  - backend preset clone now creates a new preset record that preserves:
    - selected project ids
    - overlay id
    - include_role_documents
  - desktop `PresetEditor` was rewritten into a cleaner editor surface and now supports:
    - cloning the current preset
    - selecting another preset as compare target
    - viewing project / overlay / role-document differences inline
  - this makes multi-company preset iteration much faster because you can clone a baseline preset, tweak it, and immediately compare what changed
- Stage 16 verification:
  - targeted backend tests:
    - `tests.test_library_api -v`
  - desktop build:
    - `npm run build`
  - full backend unittest:
    - `71/71` passing
- Stage 17 implemented:
  - completed the first "spoken answer control" pass for the knowledge-library runtime
  - `AnswerPlan` now carries:
    - `delivery_style`
    - `opening_move`
    - `closing_move`
  - prompt building now forwards those controls into the runtime prompt so the model can see:
    - how to open
    - how to sound
    - how to close or invite follow-up
  - the local `TemplateLLMProvider` fallback was upgraded from a generic template into plan-aware spoken drafting:
    - tradeoff questions now open with answer-first language and explicit tradeoff framing
    - module deep-dive questions now open with responsibility-first framing and emphasize boundary / risk
    - follow-up-safe closing moves now differ by plan:
      - invite follow-up
      - risk boundary
      - evidence anchor
  - this means the no-network fallback path now behaves much more like a real interview copilot instead of a generic summary generator
- Stage 17 verification:
  - targeted backend tests:
    - `tests.test_answer_control -v`
    - `tests.test_generation -v`
  - full backend unittest:
    - `73/73` passing
- Stage 18 implemented:
  - added preset-vs-latest-bundle drift detection for the knowledge-library workflow
  - new backend API:
    - `GET /api/library/presets/{preset_id}/latest-bundle-status`
  - backend drift status now reports whether the preset is:
    - `missing`
    - `current`
    - `stale`
  - stale reasons currently include:
    - project selection changed
    - overlay changed
    - include-role-documents changed
    - project content updated after the bundle was built
    - overlay updated after the bundle was built
    - role documents updated after the bundle was built
  - project records now persist `updated_at`, which makes bundle staleness checks much more accurate for:
    - manual authoring edits
    - project document edits
    - repo reindex / import refreshes
  - desktop preset editing now shows a dedicated bundle-status panel:
    - current vs stale vs missing
    - human-readable stale reasons
    - the exact project names that changed after the latest bundle
  - this makes the preset workflow much safer before a live interview because you can tell immediately whether the current bundle is still trustworthy
- Stage 18 verification:
  - targeted backend tests:
    - `tests.test_library_api -v`
  - desktop build:
    - `npm run build`
  - full backend unittest:
    - `74/74` passing
- Recommended next implementation order:
  1. larger-library workspace preview UX polish
  2. preset workflow refinement:
     - saved preset families for one-click company switching
     - compare current preset against a non-latest historical bundle on demand
  3. authoring-pack refinement:
     - saved template presets across projects
     - smarter dedupe / rename suggestions when importing external templates
  4. deeper answer naturalness tuning:
     - transcript-informed rhythm / pacing
     - stronger spoken Chinese variation beyond plan-level control

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
E:/qqbroDownload/interview_trainer_desktop-knowledge/CODEX_SESSION_HANDOFF.md
E:/qqbroDownload/interview_trainer_desktop-knowledge/docs/superpowers/specs/2026-03-17-persistent-knowledge-library-design.md
E:/qqbroDownload/interview_trainer_desktop-knowledge/docs/superpowers/plans/2026-03-17-persistent-knowledge-library.md

Project root:
E:/qqbroDownload/interview_trainer_desktop-knowledge

First, read all three files and inspect the current backend and desktop status.
Then continue only the local persistent multi-project knowledge-library line.
Respond in Chinese.
```
