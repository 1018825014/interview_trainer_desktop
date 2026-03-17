# Persistent Knowledge Library Design

> Scope: This design covers only the local persistent multi-project knowledge library line for `interview_trainer_desktop`. It does not extend audio capture, ASR, or live bridge behavior except where the existing session pipeline needs a library-backed payload.

## Goal

Upgrade the current in-memory single-workspace editor into a persistent local knowledge library that can:

- maintain long-lived user background, multiple projects, multiple repos, and multiple documents
- keep long-term library data separate from interview-specific overlays
- precompile interview-oriented answer units so runtime answers are fast, natural, and guided
- feed the existing interview session pipeline with a reusable compiled payload instead of ad hoc sample knowledge

## Product Direction

This module is not a generic file vault and not a generic code RAG demo.
It is an interview-answer-oriented knowledge system optimized for:

1. fast starter latency
2. natural spoken Chinese answers
3. answers that sound like a strong candidate
4. guided hooks that steer interviewers toward prepared strengths

All imported repos are treated as the user's own work. The system does not model git authorship or git evolution.

## Non-Goals

- no changes to audio capture architecture
- no changes to realtime ASR architecture
- no changes to live bridge logic unless a session payload adapter is required
- no hidden overlay, screen-share evasion, or recording evasion features
- no git history or contributor attribution modeling

## Current State

The current codebase already provides:

- `WorkspaceManager` with in-memory CRUD
- path import into a single project's `documents` and `code_files`
- `KnowledgeCompiler` that builds:
  - `ProfileCard`
  - `ProjectInterviewPack`
  - `ModuleCard`
  - `RepoMap`
  - `CodebaseSummary`
  - `DocChunk`
  - `CodeChunk`
  - `RolePlaybook`
- a desktop workspace form inside `desktop/src/App.tsx`

The main limitations today are:

- workspace data disappears after restart
- the UI and backend are effectively single-project oriented
- imported repos and docs are stored as raw content blobs with no true library model
- there is no explicit overlay, preset, answer-plan, or retrieval-unit layer

## Architecture Overview

The persistent knowledge library introduces four layers:

1. storage layer
2. library domain layer
3. compilation and retrieval layer
4. runtime answer-control layer

### 1. Storage Layer

Use a hybrid local store:

- `SQLite` for metadata, relationships, activation state, retrieval units, evidence, and compiled bundle indexes
- `library_objects/` for large extracted text, code snapshots, compiled bundle JSON, and cache artifacts

Recommended local paths:

- `backend/data/library/library.db`
- `backend/data/library/objects/...`

This gives:

- fast lookup and filtering through SQL
- clean handling of large artifacts through filesystem storage
- a durable base for presets, bundles, overlays, and answer-control metadata

### 2. Library Domain Layer

The domain model is answer-oriented, not repository-oriented.

#### Core entities

- `LibraryWorkspace`
  - one long-lived library for a user
- `WorkspaceProfile`
  - the user's stable background and target roles
- `Project`
  - the main interview storytelling unit
- `Repo`
  - a local code directory attached to a project
- `DocumentAsset`
  - a profile/project/overlay document
- `InterviewOverlay`
  - one interview-specific layer for company, JD, emphasis, and style
- `ActivationPreset`
  - reusable activation configuration for one interview context
- `CompiledBundle`
  - a compiled payload ready for session creation

#### Project fields

Projects should persist both technical facts and candidate-friendly framing:

- `name`
- `business_value`
- `architecture`
- `pitch_30`
- `pitch_90`
- `tradeoffs`
- `failure_cases`
- `limitations`
- `upgrade_plan`
- `interviewer_hooks`

### 3. Compilation and Retrieval Layer

The system should not rely on raw chunk retrieval alone.
It must precompile interview-ready answer units.

#### Index entities

- `ModuleCardPlus`
  - extends the current `ModuleCard`
  - adds:
    - `upstream_modules`
    - `downstream_modules`
    - `key_call_paths`
    - `failure_surface`
    - `risky_interfaces`
    - `key_files`
- `RepoMap`
- `DocChunk`
- `CodeChunk`
- `EvidenceCard`
- `MetricEvidence`
- `RetrievalUnit`

#### RetrievalUnit

`RetrievalUnit` is the key runtime artifact.
It is not a loose summary chunk.
It is a strongly typed interview-answer unit with fields such as:

- `unit_type`
- `question_forms`
- `short_answer`
- `long_answer`
- `key_points`
- `supporting_refs`
- `safe_claims`
- `hooks`

Typical `unit_type` values:

- `project_intro`
- `architecture_overview`
- `module_deep_dive`
- `tradeoff_reasoning`
- `failure_analysis`
- `performance_evidence`
- `optimization_plan`
- `project_compare`
- `role_fit`

#### Evidence

`EvidenceCard` and `MetricEvidence` are first-class entities, not only labels.
They support deeper answers such as:

- why a latency claim is credible
- what measurement method was used
- what logs, benchmark notes, or docs support a statement

### 4. Runtime Answer-Control Layer

The current `routing.py` route modes are too coarse for strong interview answers.
The new library will support:

- `QuestionIntent`
- `AnswerPlan`
- `AnswerState`
- `AnswerStyleProfile`
- `DepthPolicy`

#### QuestionIntent

Runtime question classification should use interview-oriented intent classes:

- `project_intro`
- `architecture_overview`
- `module_deep_dive`
- `tradeoff_reasoning`
- `failure_analysis`
- `performance_evidence`
- `optimization_plan`
- `project_compare`
- `role_fit`
- `generic_behavior`

#### AnswerPlan

`AnswerPlan` is a runtime object derived from the current question, active preset, overlay, and style.
It should contain:

- `intent`
- `target_project_ids`
- `target_module_ids`
- `retrieve_priority`
- `depth_policy`
- `style_profile`
- `answer_template`
- `max_sentences`
- `need_metrics`
- `need_code_evidence`
- `allow_hook`
- `preferred_hook_ids`

#### AnswerState

For follow-up consistency, runtime state should track:

- current primary project
- current primary module
- claims already spoken
- hooks already used
- current follow-up thread

This allows the system to continue a line of explanation instead of re-answering from scratch.

## Retrieval and Generation Flow

### Starter flow

The `starter` path must stay lightweight:

1. classify `QuestionIntent`
2. create a small `AnswerPlan`
3. retrieve one or two primary `RetrievalUnit`s
4. optionally attach one strong `EvidenceCard`
5. generate a short spoken answer
6. stream the first visible fragment when supported

Starter goals:

- 1-2 spoken sentences
- immediate usability
- natural spoken tone
- leave room for deeper follow-up

### Full flow

The `full` path can be heavier but must remain bounded:

1. reuse `QuestionIntent`
2. create a full `AnswerPlan`
3. retrieve primary `RetrievalUnit`
4. add `EvidenceCard / MetricEvidence`
5. add `ModuleCardPlus` when needed
6. add one or two `CodeChunk` or `DocChunk` references for deep dives
7. generate a complete spoken answer with talking points

The full answer structure should default to:

1. conclusion
2. real implementation
3. tradeoff reasoning
4. limitations or risks
5. upgrade direction or one controlled hook

## Hook Strategy

Hooks are useful, but must be controlled.

Rules:

- only use when `AnswerPlan.allow_hook` is true
- only use one hook per answer
- only use hooks that already have prepared follow-up units
- use hooks mainly in project, architecture, and tradeoff questions
- do not let hooks derail the current answer

This helps the assistant guide interviewers toward prepared strengths without sounding unnatural.

## Database Schema

The first implementation should use the following tables.

### Core tables

- `workspaces`
- `workspace_profiles`
- `projects`
- `repos`
- `documents`
- `overlays`
- `activation_presets`
- `compiled_bundles`

### Index and answer tables

- `module_cards`
- `doc_chunks`
- `code_chunks`
- `evidence_cards`
- `metric_evidence`
- `retrieval_units`

### Relationship tables

- `project_repo`
- `project_document`
- `retrieval_unit_evidence`
- `retrieval_unit_module`
- `retrieval_unit_code_chunk`
- `retrieval_unit_doc_chunk`
- `hook_prepared_unit`
- `preset_project`
- `preset_repo`
- `preset_document`

`SQLite` is sufficient. A graph database is unnecessary at this stage.
The relationship model should be explicit, but implemented with normal relational tables.

## API Design

Do not break the current `/api/workspaces` endpoints immediately.
Introduce a new library API surface and keep workspace endpoints as a compatibility layer during migration.

### New API surface

- `GET /api/library/workspaces`
- `POST /api/library/workspaces`
- `GET /api/library/workspaces/{workspace_id}`
- `PUT /api/library/workspaces/{workspace_id}`

- `GET /api/library/workspaces/{workspace_id}/projects`
- `POST /api/library/workspaces/{workspace_id}/projects`
- `GET /api/library/projects/{project_id}`
- `PUT /api/library/projects/{project_id}`
- `DELETE /api/library/projects/{project_id}`

- `GET /api/library/projects/{project_id}/repos`
- `POST /api/library/projects/{project_id}/repos/import-path`
- `GET /api/library/repos/{repo_id}`
- `POST /api/library/repos/{repo_id}/reindex`

- `GET /api/library/projects/{project_id}/documents`
- `POST /api/library/projects/{project_id}/documents`
- `DELETE /api/library/documents/{document_id}`

- `GET /api/library/workspaces/{workspace_id}/overlays`
- `POST /api/library/workspaces/{workspace_id}/overlays`
- `PUT /api/library/overlays/{overlay_id}`

- `GET /api/library/projects/{project_id}/modules`
- `GET /api/library/projects/{project_id}/retrieval-units`
- `GET /api/library/projects/{project_id}/evidence`

- `POST /api/library/workspaces/{workspace_id}/compile`
- `GET /api/library/workspaces/{workspace_id}/bundles`
- `GET /api/library/bundles/{bundle_id}`

- `GET /api/library/workspaces/{workspace_id}/presets`
- `POST /api/library/workspaces/{workspace_id}/presets`
- `POST /api/library/presets/{preset_id}/build-session-payload`

### Session bridge

`POST /api/library/presets/{preset_id}/build-session-payload` should return:

- `knowledge`
- `briefing`
- `activation_summary`

The existing `create_session` path should keep consuming the same high-level payload shape.
This keeps the live interview path stable while the library becomes much more powerful.

## Frontend Interaction Design

The library should no longer live as a single big form inside `App.tsx`.
It should be split into dedicated UI units.

### Proposed navigation

- left column:
  - workspace list
  - current workspace sections:
    - projects
    - overlays
    - presets
    - bundles
- center column:
  - active object editor
- right column:
  - assets and status

### Active editors

#### Project editor

- project name
- business value
- architecture
- `pitch_30`
- `pitch_90`
- tradeoffs
- failure cases
- upgrade plan
- hooks

#### Overlay editor

- company
- JD
- business context
- focus projects
- emphasis points
- style and depth preferences

#### Preset editor

- active projects
- active repos
- active documents
- active overlay
- style profile
- depth policy

### Status rail

Show:

- repo list
- document list
- import/index status
- latest scan time
- retrieval unit count
- evidence count
- compile status
- latest bundle summary

### Session activation UX

Do not attach a whole workspace directly to a session.
Use:

1. choose preset
2. build interview bundle
3. attach bundle to current session

This is better for real interview switching across companies and JDs.

## Implementation Stages

### Stage 1: persistent library foundation

- add `SQLite + library_objects`
- replace in-memory-only workspace storage
- support multiple workspaces, projects, repos, and documents
- finish CRUD and path import

### Stage 2: indexing and compile layer

- generate `ModuleCardPlus`
- generate `DocChunk / CodeChunk`
- generate `EvidenceCard / MetricEvidence`
- generate typed `RetrievalUnit`
- generate `CompiledBundle`

### Stage 3: runtime answer integration

- add `QuestionIntent`
- add `AnswerPlan`
- add `AnswerState`
- route runtime answers through retrieval units and evidence
- connect preset-to-session payload generation

### Stage 4: desktop library UX

- split library UI out of `App.tsx`
- add workspace / project / overlay / preset management
- add compile/index/activation status surfaces
- optimize interview-prep switching flow

## Error Handling

- invalid import path must fail clearly without corrupting existing data
- failed indexing must preserve the last successful state
- failed compile must not replace the latest usable bundle
- repo-specific failure should not break the whole workspace
- status should be visible in the UI:
  - `idle`
  - `importing`
  - `indexing`
  - `compiled`
  - `failed`

## Validation Criteria

The design is successful when the system can:

- persist library data across restarts
- manage multiple projects, multiple repos, and multiple documents
- keep overlays separate from long-term data
- build reusable preset-driven session payloads
- produce clearly different answer framing under different overlays or presets
- keep `starter` fast while making `full` deeper and more resilient

## Design Decisions

### Why not stay file-only?

Pure file storage is simple, but weak for:

- multi-entity relationships
- presets and overlays
- filtered activation
- typed retrieval units
- compile status and version tracking

The quality target here is high enough that a hybrid `SQLite + object store` design is justified.

### Why not use heavy graph infrastructure?

The system needs graph-like relationships, but not a graph database.
`SQLite` plus explicit relation tables is enough and keeps local distribution simple.

### Why not do live deep repo search as the main path?

Because interview latency matters.
Fast runtime answers should mostly rely on precompiled answer units, then selectively enrich with evidence or code when needed.

## Next Step

After this spec is approved, the next work item is an implementation plan focused on:

1. persistent library storage
2. multi-project and multi-repo CRUD
3. compile pipeline upgrades
4. preset-driven session activation
5. desktop library management UI
