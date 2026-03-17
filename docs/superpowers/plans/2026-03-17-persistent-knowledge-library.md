# Persistent Knowledge Library Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking. Follow @test-driven-development and @verification-before-completion during execution.

**Goal:** Replace the current in-memory single-workspace editor with a persistent local multi-project knowledge library that can compile answer-oriented bundles and feed the existing interview session pipeline.

**Architecture:** Add a hybrid `SQLite + library_objects` backend store, layer a library repository and compiler on top of it, introduce preset-driven session payload generation plus runtime answer-control objects, then split the desktop workspace form into dedicated library management components.

**Tech Stack:** Python 3.11, FastAPI, `sqlite3`, unittest, React 18, TypeScript, Vite, Electron shell

---

## Chunk 1: Persistent Library Foundation

### Task 1: Bootstrap local storage and persistent workspace loading

**Files:**
- Create: `backend/src/interview_trainer/library_paths.py`
- Create: `backend/src/interview_trainer/library_store.py`
- Test: `backend/tests/test_library_store.py`
- Modify: `backend/src/interview_trainer/workspace.py`

- [ ] **Step 1: Write the failing storage persistence test**

```python
import tempfile
import unittest
from pathlib import Path

from interview_trainer.workspace import WorkspaceManager


class LibraryStoreTests(unittest.TestCase):
    def test_workspace_persists_across_manager_restarts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manager = WorkspaceManager(storage_root=root)
            created = manager.create_workspace(
                {
                    "name": "Persistent Library",
                    "knowledge": {"profile": {"headline": "AI engineer"}},
                }
            )

            reloaded = WorkspaceManager(storage_root=root)
            listing = reloaded.list_workspaces()

        self.assertEqual(len(listing["workspaces"]), 1)
        self.assertEqual(listing["workspaces"][0]["workspace_id"], created["workspace_id"])
        self.assertEqual(listing["workspaces"][0]["name"], "Persistent Library")
```

- [ ] **Step 2: Run the targeted test to confirm failure**

Run:

```powershell
cd backend
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p 'test_library_store.py' -v
```

Expected:

- `FAILED`
- missing `storage_root` support or missing persistent backing modules

- [ ] **Step 3: Implement library path resolution and SQLite bootstrap**

Create a storage helper with deterministic paths:

```python
from __future__ import annotations

from pathlib import Path


def resolve_library_root(storage_root: Path | None = None) -> Path:
    root = (storage_root or Path("backend/data/library")).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    (root / "objects").mkdir(parents=True, exist_ok=True)
    return root
```

Create a bootstrapper that always initializes `library.db` and core tables:

```python
CREATE TABLE IF NOT EXISTS workspaces (
    workspace_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    default_overlay_id TEXT,
    default_style_profile_id TEXT,
    latest_bundle_id TEXT
)
```

- [ ] **Step 4: Update `WorkspaceManager` to load and save through the store**

Expose:

```python
class WorkspaceManager:
    def __init__(self, compiler: KnowledgeCompiler | None = None, storage_root: Path | None = None) -> None:
        self.compiler = compiler or KnowledgeCompiler()
        self.store = LibraryStore(storage_root=storage_root)
```

Keep the public response shape compatible with the current `/api/workspaces` endpoints.

- [ ] **Step 5: Re-run the targeted test**

Run:

```powershell
cd backend
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p 'test_library_store.py' -v
```

Expected:

- `OK`

- [ ] **Step 6: Commit**

```powershell
git add backend/src/interview_trainer/library_paths.py backend/src/interview_trainer/library_store.py backend/src/interview_trainer/workspace.py backend/tests/test_library_store.py
git commit -m "feat: add persistent library storage bootstrap"
```

### Task 2: Persist multi-project, multi-repo, and multi-document workspace data

**Files:**
- Create: `backend/src/interview_trainer/library_repository.py`
- Test: `backend/tests/test_library_repository.py`
- Modify: `backend/src/interview_trainer/workspace.py`
- Modify: `backend/tests/test_workspace.py`

- [ ] **Step 1: Write failing tests for multi-project CRUD and import persistence**

```python
class LibraryRepositoryTests(unittest.TestCase):
    def test_import_path_appends_repo_to_selected_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo = root / "agent-console"
            repo.mkdir()
            (repo / "README.md").write_text("Agent console docs", encoding="utf-8")

            manager = WorkspaceManager(storage_root=root / "library")
            workspace = manager.create_workspace(
                {
                    "name": "Library",
                    "knowledge": {
                        "projects": [
                            {"name": "Agent Console"},
                            {"name": "Ops Dashboard"},
                        ]
                    },
                }
            )

            imported = manager.import_path(
                workspace["workspace_id"],
                {"path": str(repo), "project_name": "Agent Console"},
            )

            project_names = [item["name"] for item in imported["knowledge"]["projects"]]
            self.assertEqual(project_names, ["Agent Console", "Ops Dashboard"])
            self.assertEqual(imported["knowledge"]["projects"][0]["documents"][0]["path"], "README.md")
```

- [ ] **Step 2: Run the focused repository tests**

Run:

```powershell
cd backend
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p 'test_library_repository.py' -v
```

Expected:

- `FAILED`
- missing repository methods or data not surviving round-trip

- [ ] **Step 3: Implement repository-backed workspace serialization**

Persist nested workspace data into normalized tables:

- `workspace_profiles`
- `projects`
- `repos`
- `documents`

Keep a compatibility serializer that still returns:

```python
{
    "workspace_id": "...",
    "name": "...",
    "knowledge": {
        "profile": {...},
        "projects": [...],
        "role_documents": [...]
    }
}
```

- [ ] **Step 4: Update `import_path` to attach repo/doc snapshots to the selected project**

Store:

- repo metadata in SQLite
- extracted text/code payloads under `backend/data/library/objects/...`
- compatibility `knowledge.projects[*].documents/code_files` in the serialized response

- [ ] **Step 5: Run repository tests and existing workspace tests**

Run:

```powershell
cd backend
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p 'test_library_repository.py' -v
python -m unittest discover -s tests -p 'test_workspace.py' -v
```

Expected:

- both commands end with `OK`

- [ ] **Step 6: Commit**

```powershell
git add backend/src/interview_trainer/library_repository.py backend/src/interview_trainer/workspace.py backend/tests/test_library_repository.py backend/tests/test_workspace.py
git commit -m "feat: persist multi-project library data"
```

## Chunk 2: Indexing and Compile Layer

### Task 3: Add answer-oriented library types and compile artifacts

**Files:**
- Create: `backend/src/interview_trainer/library_types.py`
- Create: `backend/src/interview_trainer/library_compile.py`
- Modify: `backend/src/interview_trainer/knowledge.py`
- Test: `backend/tests/test_library_compile.py`

- [ ] **Step 1: Write failing compile tests for retrieval units and evidence**

```python
from interview_trainer.library_compile import LibraryCompiler


class LibraryCompilerTests(unittest.TestCase):
    def test_compile_project_creates_retrieval_units_and_metric_evidence(self) -> None:
        compiler = LibraryCompiler()
        bundle = compiler.compile_workspace(
            {
                "profile": {"headline": "AI engineer"},
                "projects": [
                    {
                        "name": "Agent Console",
                        "business_value": "Help teams build agent workflows",
                        "architecture": "React UI + Python orchestrator + retrieval",
                        "pitch_30": "Agent Console is the project I use to explain orchestration tradeoffs.",
                        "tradeoffs": ["Chose modular orchestration over one giant workflow"],
                        "documents": [{"path": "README.md", "content": "Latency dropped from 1.8s to 900ms."}],
                        "code_files": [{"path": "src/orchestrator/workflow.py", "content": "def run():\n    return 'ok'\n"}],
                    }
                ],
            }
        )

        self.assertGreaterEqual(len(bundle.retrieval_units), 1)
        self.assertGreaterEqual(len(bundle.evidence_cards), 1)
        self.assertIn("project_intro", {item.unit_type for item in bundle.retrieval_units})
```

- [ ] **Step 2: Run the new compile test**

Run:

```powershell
cd backend
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p 'test_library_compile.py' -v
```

Expected:

- `FAILED`
- `LibraryCompiler` or typed artifacts missing

- [ ] **Step 3: Implement new library dataclasses**

Add explicit types such as:

```python
@dataclass(slots=True)
class RetrievalUnit:
    unit_id: str
    unit_type: str
    project_id: str
    module_id: str | None
    question_forms: list[str]
    short_answer: str
    long_answer: str
    key_points: list[str]
    supporting_refs: list[str]
    hooks: list[str]
```

```python
@dataclass(slots=True)
class MetricEvidence:
    evidence_id: str
    metric_name: str
    metric_value: str
    baseline: str
    method: str
    environment: str
    source_note: str
```

- [ ] **Step 4: Implement a compiler that builds bundle-ready artifacts**

Build:

- `ModuleCardPlus`
- `EvidenceCard`
- `MetricEvidence`
- typed `RetrievalUnit`
- `CompiledBundlePayload`

Reuse existing chunking helpers from `knowledge.py` instead of duplicating them.

- [ ] **Step 5: Run compile tests plus existing knowledge tests**

Run:

```powershell
cd backend
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p 'test_library_compile.py' -v
python -m unittest discover -s tests -p 'test_knowledge.py' -v
```

Expected:

- both commands end with `OK`

- [ ] **Step 6: Commit**

```powershell
git add backend/src/interview_trainer/library_types.py backend/src/interview_trainer/library_compile.py backend/src/interview_trainer/knowledge.py backend/tests/test_library_compile.py
git commit -m "feat: compile answer-oriented library artifacts"
```

### Task 4: Add overlays, presets, bundles, and session-payload building endpoints

**Files:**
- Create: `backend/src/interview_trainer/library_session.py`
- Modify: `backend/src/interview_trainer/api.py`
- Modify: `backend/src/interview_trainer/workspace.py`
- Test: `backend/tests/test_library_api.py`

- [ ] **Step 1: Write failing API tests for preset payload generation**

```python
from fastapi.testclient import TestClient

from interview_trainer.api import create_app


class LibraryApiTests(unittest.TestCase):
    def test_build_session_payload_returns_knowledge_and_briefing(self) -> None:
        client = TestClient(create_app())
        workspace = client.post("/api/library/workspaces", json={"name": "Library"}).json()
        project = client.post(
            f"/api/library/workspaces/{workspace['workspace_id']}/projects",
            json={"name": "Agent Console", "pitch_30": "Short pitch"},
        ).json()
        overlay = client.post(
            f"/api/library/workspaces/{workspace['workspace_id']}/overlays",
            json={"name": "Alibaba", "company": "Alibaba", "job_description": "agent platform"},
        ).json()
        preset = client.post(
            f"/api/library/workspaces/{workspace['workspace_id']}/presets",
            json={"name": "Alibaba preset", "project_ids": [project['project_id']], "overlay_id": overlay['overlay_id']},
        ).json()

        payload = client.post(f"/api/library/presets/{preset['preset_id']}/build-session-payload").json()

        self.assertIn("knowledge", payload)
        self.assertIn("briefing", payload)
        self.assertIn("activation_summary", payload)
```

- [ ] **Step 2: Run the API test to verify failure**

Run:

```powershell
cd backend
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p 'test_library_api.py' -v
```

Expected:

- `FAILED`
- missing `/api/library/...` routes

- [ ] **Step 3: Implement library session payload building**

Create a bridge function:

```python
def build_session_payload(preset: ActivationPreset, bundle: CompiledBundlePayload) -> dict[str, Any]:
    return {
        "knowledge": bundle.knowledge_payload,
        "briefing": bundle.briefing_payload,
        "activation_summary": {
            "preset_id": preset.preset_id,
            "project_count": len(preset.project_ids),
            "overlay_id": preset.overlay_id,
        },
    }
```

- [ ] **Step 4: Add new `/api/library/...` routes while preserving `/api/workspaces`**

Backfill:

- workspace CRUD
- project CRUD
- repo import/reindex
- document CRUD
- overlay CRUD
- preset CRUD
- compile and bundle lookup
- preset session payload bridge

- [ ] **Step 5: Run library API tests and current backend smoke tests**

Run:

```powershell
cd backend
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p 'test_library_api.py' -v
python -m unittest discover -s tests -p 'test_service.py' -v
```

Expected:

- `OK`
- no regression in session creation tests

- [ ] **Step 6: Commit**

```powershell
git add backend/src/interview_trainer/library_session.py backend/src/interview_trainer/api.py backend/src/interview_trainer/workspace.py backend/tests/test_library_api.py
git commit -m "feat: add library presets and session payload API"
```

## Chunk 3: Runtime Answer Control

### Task 5: Introduce QuestionIntent, AnswerPlan, and AnswerState

**Files:**
- Create: `backend/src/interview_trainer/answer_control.py`
- Modify: `backend/src/interview_trainer/routing.py`
- Modify: `backend/src/interview_trainer/service.py`
- Modify: `backend/src/interview_trainer/prompts.py`
- Test: `backend/tests/test_answer_control.py`
- Modify: `backend/tests/test_service.py`

- [ ] **Step 1: Write failing intent and answer-plan tests**

```python
from interview_trainer.answer_control import AnswerController


class AnswerControlTests(unittest.TestCase):
    def test_tradeoff_question_builds_tradeoff_answer_plan(self) -> None:
        controller = AnswerController()
        plan = controller.build_plan(
            question="为什么这个项目这样设计，而不是做成一个一体化工作流？",
            route_mode="project",
            active_project_ids=["agent-console"],
        )

        self.assertEqual(plan.intent, "tradeoff_reasoning")
        self.assertTrue(plan.allow_hook)
        self.assertIn("RetrievalUnit", plan.retrieve_priority)
```

- [ ] **Step 2: Run the new answer-control test**

Run:

```powershell
cd backend
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p 'test_answer_control.py' -v
```

Expected:

- `FAILED`
- missing controller or missing `intent`/`plan` fields

- [ ] **Step 3: Implement runtime answer-control objects**

Use a bounded runtime model:

```python
@dataclass(slots=True)
class AnswerPlan:
    intent: str
    retrieve_priority: list[str]
    answer_template: list[str]
    max_sentences: int
    need_metrics: bool
    need_code_evidence: bool
    allow_hook: bool
```

```python
@dataclass(slots=True)
class AnswerState:
    active_project_id: str | None = None
    active_module_id: str | None = None
    spoken_claims: list[str] = field(default_factory=list)
    used_hook_ids: list[str] = field(default_factory=list)
    followup_thread: str = ""
```

- [ ] **Step 4: Thread `AnswerPlan` into routing, service, and prompts**

Update runtime flow so that:

- `ContextRouter` still decides high-level route
- `AnswerController` decides intent and plan
- `PromptBuilder` receives structured plan fields instead of only `style_bias`
- `InterviewTrainerService` stores and reuses `AnswerState`

- [ ] **Step 5: Run answer-control and service tests**

Run:

```powershell
cd backend
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p 'test_answer_control.py' -v
python -m unittest discover -s tests -p 'test_service.py' -v
```

Expected:

- both commands end with `OK`

- [ ] **Step 6: Commit**

```powershell
git add backend/src/interview_trainer/answer_control.py backend/src/interview_trainer/routing.py backend/src/interview_trainer/service.py backend/src/interview_trainer/prompts.py backend/tests/test_answer_control.py backend/tests/test_service.py
git commit -m "feat: add answer intent and planning layer"
```

### Task 6: Make runtime retrieval unit-first and evidence-aware

**Files:**
- Create: `backend/src/interview_trainer/library_retriever.py`
- Modify: `backend/src/interview_trainer/routing.py`
- Modify: `backend/src/interview_trainer/prompts.py`
- Modify: `backend/src/interview_trainer/generation.py`
- Test: `backend/tests/test_routing.py`
- Modify: `backend/tests/test_generation.py`

- [ ] **Step 1: Write failing retrieval-priority tests**

```python
class RoutingRetrievalTests(unittest.TestCase):
    def test_tradeoff_question_prefers_retrieval_unit_and_evidence_before_code(self) -> None:
        router = ContextRouter()
        pack = router.build_pack_for_plan(
            question="这个方案最大的 tradeoff 是什么？",
            plan=AnswerPlan(
                intent="tradeoff_reasoning",
                retrieve_priority=["RetrievalUnit", "EvidenceCard", "ModuleCard", "CodeChunk"],
                answer_template=["conclusion", "tradeoff", "reason", "upgrade"],
                max_sentences=6,
                need_metrics=False,
                need_code_evidence=False,
                allow_hook=True,
            ),
            compiled_bundle=sample_bundle(),
        )

        self.assertGreaterEqual(len(pack.project_refs), 1)
        self.assertGreaterEqual(len(pack.evidence_refs), 1)
        self.assertLessEqual(len(pack.code_refs), 1)
```

- [ ] **Step 2: Run focused routing and generation tests**

Run:

```powershell
cd backend
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p 'test_routing.py' -v
python -m unittest discover -s tests -p 'test_generation.py' -v
```

Expected:

- at least one failure caused by missing retrieval-unit-aware pack building

- [ ] **Step 3: Implement a library retriever that prioritizes precompiled answer units**

Pseudo-structure:

```python
class LibraryRetriever:
    def retrieve(self, plan: AnswerPlan, bundle: CompiledBundlePayload) -> RetrievalSelection:
        units = self._match_units(plan, bundle.retrieval_units)
        evidence = self._collect_evidence(plan, units, bundle.evidence_cards)
        modules = self._collect_modules(plan, units, bundle.module_cards)
        code = self._collect_code(plan, units, bundle.code_chunks)
        return RetrievalSelection(units=units, evidence=evidence, modules=modules, code=code)
```

- [ ] **Step 4: Update generation prompts to mention answer template and hook rules**

Include prompt lines like:

```text
Intent: tradeoff_reasoning
Answer template: conclusion -> real implementation -> tradeoff -> risk -> upgrade
Hook allowed: true
Need metrics: false
Need code evidence: false
```

- [ ] **Step 5: Re-run routing, generation, and service tests**

Run:

```powershell
cd backend
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p 'test_routing.py' -v
python -m unittest discover -s tests -p 'test_generation.py' -v
python -m unittest discover -s tests -p 'test_service.py' -v
```

Expected:

- all commands end with `OK`
- starter/full behavior still works

- [ ] **Step 6: Commit**

```powershell
git add backend/src/interview_trainer/library_retriever.py backend/src/interview_trainer/routing.py backend/src/interview_trainer/prompts.py backend/src/interview_trainer/generation.py backend/tests/test_routing.py backend/tests/test_generation.py
git commit -m "feat: prioritize retrieval units and evidence in answers"
```

## Chunk 4: Desktop Library UX

### Task 7: Add dedicated frontend types and library API client

**Files:**
- Create: `desktop/src/types/library.ts`
- Create: `desktop/src/api/library.ts`
- Modify: `desktop/src/types.ts`
- Modify: `desktop/src/api/client.ts`

- [ ] **Step 1: Write the failing TypeScript wiring**

Add type stubs such as:

```ts
export interface LibraryWorkspaceRecord {
  workspaceId: string;
  name: string;
  latestBundleId: string | null;
  updatedAt: number | null;
}
```

```ts
export interface LibraryPresetRecord {
  presetId: string;
  workspaceId: string;
  name: string;
  overlayId: string | null;
  styleProfileId: string | null;
  depthPolicy: string;
}
```

- [ ] **Step 2: Run the desktop build and confirm failure once imports start referencing the new modules**

Run:

```powershell
cd desktop
npm run build
```

Expected:

- `FAILED`
- missing modules or type errors

- [ ] **Step 3: Implement library API helpers**

Add request helpers for:

- list/create/update workspace
- list/create/update project
- repo import/reindex
- list/create/update overlay
- list/create/update preset
- compile and bundle lookup
- build preset session payload

- [ ] **Step 4: Re-run the desktop build**

Run:

```powershell
cd desktop
npm run build
```

Expected:

- `vite build` and `tsc -p tsconfig.node.json` succeed

- [ ] **Step 5: Commit**

```powershell
git add desktop/src/types/library.ts desktop/src/api/library.ts desktop/src/types.ts desktop/src/api/client.ts
git commit -m "feat: add frontend library client and types"
```

### Task 8: Split the library UI out of `App.tsx`

**Files:**
- Create: `desktop/src/components/library/LibraryPanel.tsx`
- Create: `desktop/src/components/library/WorkspaceNav.tsx`
- Create: `desktop/src/components/library/ProjectEditor.tsx`
- Create: `desktop/src/components/library/OverlayEditor.tsx`
- Create: `desktop/src/components/library/PresetEditor.tsx`
- Create: `desktop/src/components/library/StatusRail.tsx`
- Modify: `desktop/src/App.tsx`
- Modify: `desktop/src/styles.css`

- [ ] **Step 1: Move the current workspace form into a dedicated panel component with failing compile first**

Start by changing `App.tsx` imports to a component that does not exist yet:

```tsx
import { LibraryPanel } from "./components/library/LibraryPanel";
```

- [ ] **Step 2: Run the build to verify the component split is required**

Run:

```powershell
cd desktop
npm run build
```

Expected:

- `FAILED`
- import resolution error for `LibraryPanel`

- [ ] **Step 3: Implement the split panel structure**

`LibraryPanel` should render:

- left nav for workspaces / projects / overlays / presets / bundles
- center editor based on selected entity
- right status rail for repos, docs, compile state, retrieval-unit counts

`App.tsx` should keep audio/transcript/live-session sections intact and mount the new library area.

- [ ] **Step 4: Re-run the build**

Run:

```powershell
cd desktop
npm run build
```

Expected:

- build succeeds

- [ ] **Step 5: Commit**

```powershell
git add desktop/src/components/library desktop/src/App.tsx desktop/src/styles.css
git commit -m "feat: split persistent library UI from app shell"
```

### Task 9: Connect presets, compile actions, and session activation UX

**Files:**
- Modify: `desktop/src/components/library/LibraryPanel.tsx`
- Modify: `desktop/src/components/library/PresetEditor.tsx`
- Modify: `desktop/src/App.tsx`
- Modify: `desktop/src/mock/sample.ts`

- [ ] **Step 1: Add failing wiring for preset-driven session activation**

Sketch the target integration:

```tsx
const payload = await buildPresetSessionPayload(backendBaseUrl, presetId);
const response = await createSession(backendBaseUrl, {
  knowledge: payload.knowledge,
  briefing: payload.briefing,
});
```

- [ ] **Step 2: Run the desktop build and confirm failure if helper imports are not yet wired**

Run:

```powershell
cd desktop
npm run build
```

Expected:

- `FAILED`
- missing preset activation helper or type mismatch

- [ ] **Step 3: Implement preset compile and activation controls**

Support:

- compile selected workspace/preset
- build session payload
- attach bundle to current interview session
- show latest bundle summary and activation result

- [ ] **Step 4: Re-run the build**

Run:

```powershell
cd desktop
npm run build
```

Expected:

- build succeeds

- [ ] **Step 5: Commit**

```powershell
git add desktop/src/components/library/LibraryPanel.tsx desktop/src/components/library/PresetEditor.tsx desktop/src/App.tsx desktop/src/mock/sample.ts
git commit -m "feat: connect library presets to interview sessions"
```

## Chunk 5: Final Documentation and Verification

### Task 10: Update docs and run full verification before completion

**Files:**
- Modify: `README.md`
- Modify: `CODEX_SESSION_HANDOFF.md`
- Optionally modify: `FUTURE_DEVELOPMENT_SPEC.md`

- [ ] **Step 1: Update README with the new library architecture and commands**

Add:

- library storage overview
- new `/api/library/...` endpoints
- session payload activation flow
- backend data directory notes

- [ ] **Step 2: Update handoff with completed implementation status**

Record:

- what was implemented
- what was verified
- remaining gaps
- touched shared files

- [ ] **Step 3: Run the full backend test suite**

Run:

```powershell
cd backend
$env:PYTHONPATH='src'
python -m unittest discover -s tests -v
```

Expected:

- all tests pass

- [ ] **Step 4: Run the desktop build**

Run:

```powershell
cd desktop
npm run build
```

Expected:

- renderer and electron shell build succeed

- [ ] **Step 5: Manual smoke checklist**

- start backend
- load desktop renderer
- create persistent workspace
- add two projects and at least one repo each
- create overlay and preset
- compile bundle
- build session payload
- attach to session and ask one project question

- [ ] **Step 6: Commit**

```powershell
git add README.md CODEX_SESSION_HANDOFF.md FUTURE_DEVELOPMENT_SPEC.md
git commit -m "docs: document persistent knowledge library rollout"
```

## Execution Notes

- Keep the audio, ASR, and live-bridge files untouched unless a session payload adapter requires a narrow interface change.
- Favor backward compatibility for existing `/api/workspaces` consumers until the new library UI is wired.
- Keep the runtime fast path bounded: retrieve precompiled answer units first, then selectively add evidence or code.
- Do not model git authorship or git history in this plan.
