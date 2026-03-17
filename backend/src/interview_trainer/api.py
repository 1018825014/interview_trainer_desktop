from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:  # pragma: no cover
    FastAPI = None
    HTTPException = Exception
    CORSMiddleware = None

from .audio import AudioSessionManager, probe_audio_capabilities_safe, recommend_audio_plan_safe
from .service import InterviewTrainerService
from .transcription import AudioTranscriptionService
from .workspace import WorkspaceManager


def create_app(*, workspace_storage_root: Path | str | None = None) -> Any:
    if FastAPI is None:  # pragma: no cover
        raise RuntimeError("FastAPI is not installed. Install backend/requirements.txt first.")

    app = FastAPI(title="Interview Trainer MVP", version="0.5.0")
    if CORSMiddleware is not None:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "http://127.0.0.1:5173",
                "http://localhost:5173",
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    service = InterviewTrainerService()
    audio_sessions = AudioSessionManager()
    transcription_service = AudioTranscriptionService(audio_sessions, interview_service=service)
    workspace_manager = WorkspaceManager(
        service.knowledge_compiler,
        storage_root=workspace_storage_root,
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/audio/capabilities")
    def audio_capabilities() -> dict[str, Any]:
        capabilities = probe_audio_capabilities_safe()
        return {"capabilities": [item.to_dict() for item in capabilities]}

    @app.get("/api/audio/recommendation")
    def audio_recommendation() -> dict[str, Any]:
        capabilities = probe_audio_capabilities_safe()
        return {
            "capabilities": [item.to_dict() for item in capabilities],
            "recommendation": recommend_audio_plan_safe().to_dict(),
        }

    @app.post("/api/audio/sessions")
    def create_audio_session(payload: dict[str, Any]) -> dict[str, Any]:
        return audio_sessions.create_session(payload)

    @app.get("/api/audio/sessions/{audio_session_id}")
    def get_audio_session(audio_session_id: str) -> dict[str, Any]:
        try:
            return audio_sessions.get_session(audio_session_id)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="audio session not found") from exc

    @app.post("/api/audio/sessions/{audio_session_id}/start")
    def start_audio_session(audio_session_id: str) -> dict[str, Any]:
        try:
            return audio_sessions.start_session(audio_session_id)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="audio session not found") from exc
        except RuntimeError as exc:  # pragma: no cover
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/audio/sessions/{audio_session_id}/stop")
    def stop_audio_session(audio_session_id: str) -> dict[str, Any]:
        try:
            return audio_sessions.stop_session(audio_session_id)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="audio session not found") from exc

    @app.post("/api/audio/sessions/{audio_session_id}/frames")
    def push_audio_frame(audio_session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return audio_sessions.push_frame(audio_session_id, payload)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="audio session not found") from exc
        except RuntimeError as exc:  # pragma: no cover
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/audio/sessions/{audio_session_id}/drain")
    def drain_audio_frames(audio_session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return audio_sessions.drain_frames(
                audio_session_id,
                max_frames=int(payload.get("max_frames", 20)),
                include_payload=bool(payload.get("include_payload", False)),
                as_wav=bool(payload.get("as_wav", False)),
                source=str(payload["source"]) if "source" in payload and payload["source"] else None,
            )
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="audio session not found") from exc

    @app.post("/api/audio/sessions/{audio_session_id}/transcribe")
    def transcribe_audio_session(audio_session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return transcription_service.transcribe_audio_session(audio_session_id, payload)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="audio session not found") from exc
        except RuntimeError as exc:  # pragma: no cover
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/audio/live-bridges")
    def list_live_bridges() -> dict[str, Any]:
        return transcription_service.list_live_bridges()

    @app.post("/api/audio/live-bridges")
    def create_live_bridge(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return transcription_service.create_live_bridge(payload)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="audio session not found") from exc

    @app.get("/api/audio/live-bridges/{bridge_id}")
    def get_live_bridge(bridge_id: str) -> dict[str, Any]:
        try:
            return transcription_service.get_live_bridge(bridge_id)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="live bridge not found") from exc

    @app.post("/api/audio/live-bridges/{bridge_id}/start")
    def start_live_bridge(bridge_id: str) -> dict[str, Any]:
        try:
            return transcription_service.start_live_bridge(bridge_id)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="live bridge not found") from exc

    @app.post("/api/audio/live-bridges/{bridge_id}/stop")
    def stop_live_bridge(bridge_id: str) -> dict[str, Any]:
        try:
            return transcription_service.stop_live_bridge(bridge_id)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="live bridge not found") from exc

    @app.post("/api/knowledge/compile")
    def compile_knowledge(payload: dict[str, Any]) -> dict[str, Any]:
        return service.compile_knowledge(payload)

    @app.get("/api/workspaces")
    def list_workspaces() -> dict[str, Any]:
        return workspace_manager.list_workspaces()

    @app.post("/api/workspaces")
    def create_workspace(payload: dict[str, Any]) -> dict[str, Any]:
        return workspace_manager.create_workspace(payload)

    @app.get("/api/workspaces/{workspace_id}")
    def get_workspace(workspace_id: str) -> dict[str, Any]:
        try:
            return workspace_manager.get_workspace(workspace_id)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="workspace not found") from exc

    @app.put("/api/workspaces/{workspace_id}")
    def update_workspace(workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return workspace_manager.update_workspace(workspace_id, payload)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="workspace not found") from exc

    @app.get("/api/library/workspaces")
    def list_library_workspaces() -> dict[str, Any]:
        return workspace_manager.list_workspaces()

    @app.post("/api/library/workspaces")
    def create_library_workspace(payload: dict[str, Any]) -> dict[str, Any]:
        return workspace_manager.create_workspace(payload)

    @app.get("/api/library/workspaces/{workspace_id}")
    def get_library_workspace(workspace_id: str) -> dict[str, Any]:
        try:
            return workspace_manager.get_workspace(workspace_id)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="workspace not found") from exc

    @app.put("/api/library/workspaces/{workspace_id}")
    def update_library_workspace(workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return workspace_manager.update_workspace(workspace_id, payload)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="workspace not found") from exc

    @app.get("/api/library/workspaces/{workspace_id}/projects")
    def list_library_projects(workspace_id: str) -> dict[str, Any]:
        try:
            return workspace_manager.list_projects(workspace_id)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="workspace not found") from exc

    @app.post("/api/library/workspaces/{workspace_id}/projects")
    def create_library_project(workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return workspace_manager.create_project(workspace_id, payload)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="workspace not found") from exc

    @app.get("/api/library/projects/{project_id}")
    def get_library_project(project_id: str) -> dict[str, Any]:
        try:
            return workspace_manager.get_project(project_id)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="project not found") from exc

    @app.put("/api/library/projects/{project_id}")
    def update_library_project(project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return workspace_manager.update_project(project_id, payload)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="project not found") from exc

    @app.delete("/api/library/projects/{project_id}")
    def delete_library_project(project_id: str) -> dict[str, str]:
        try:
            return workspace_manager.delete_project(project_id)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="project not found") from exc

    @app.get("/api/library/projects/{project_id}/repos")
    def list_library_project_repos(project_id: str) -> dict[str, Any]:
        try:
            return workspace_manager.list_project_repos(project_id)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="project not found") from exc

    @app.post("/api/library/projects/{project_id}/repos/import-path")
    def import_library_project_repo(project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return workspace_manager.import_project_repo(project_id, payload)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="project not found") from exc
        except FileNotFoundError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/library/workspaces/{workspace_id}/overlays")
    def list_library_overlays(workspace_id: str) -> dict[str, Any]:
        try:
            return workspace_manager.list_overlays(workspace_id)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="workspace not found") from exc

    @app.post("/api/library/workspaces/{workspace_id}/overlays")
    def create_library_overlay(workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return workspace_manager.create_overlay(workspace_id, payload)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="workspace not found") from exc

    @app.get("/api/library/overlays/{overlay_id}")
    def get_library_overlay(overlay_id: str) -> dict[str, Any]:
        try:
            return workspace_manager.get_overlay(overlay_id)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="overlay not found") from exc

    @app.put("/api/library/overlays/{overlay_id}")
    def update_library_overlay(overlay_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return workspace_manager.update_overlay(overlay_id, payload)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="overlay not found") from exc

    @app.get("/api/library/workspaces/{workspace_id}/presets")
    def list_library_presets(workspace_id: str) -> dict[str, Any]:
        try:
            return workspace_manager.list_presets(workspace_id)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="workspace not found") from exc

    @app.post("/api/library/workspaces/{workspace_id}/presets")
    def create_library_preset(workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return workspace_manager.create_preset(workspace_id, payload)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="workspace not found") from exc

    @app.get("/api/library/presets/{preset_id}")
    def get_library_preset(preset_id: str) -> dict[str, Any]:
        try:
            return workspace_manager.get_preset(preset_id)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="preset not found") from exc

    @app.put("/api/library/presets/{preset_id}")
    def update_library_preset(preset_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return workspace_manager.update_preset(preset_id, payload)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="preset not found") from exc

    @app.post("/api/library/presets/{preset_id}/build-session-payload")
    def build_library_session_payload(preset_id: str) -> dict[str, Any]:
        try:
            return workspace_manager.build_preset_session_payload(preset_id)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="preset not found") from exc

    @app.get("/api/library/workspaces/{workspace_id}/bundles")
    def list_library_bundles(workspace_id: str) -> dict[str, Any]:
        try:
            return workspace_manager.list_bundles(workspace_id)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="workspace not found") from exc

    @app.get("/api/library/bundles/{bundle_id}")
    def get_library_bundle(bundle_id: str) -> dict[str, Any]:
        try:
            return workspace_manager.get_bundle(bundle_id)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="bundle not found") from exc

    @app.post("/api/workspaces/{workspace_id}/compile")
    def compile_workspace(workspace_id: str) -> dict[str, Any]:
        try:
            return workspace_manager.compile_workspace(workspace_id)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="workspace not found") from exc

    @app.post("/api/workspaces/{workspace_id}/import-path")
    def import_workspace_path(workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return workspace_manager.import_path(workspace_id, payload)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="workspace not found") from exc
        except FileNotFoundError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/sessions")
    def create_session(payload: dict[str, Any]) -> dict[str, Any]:
        return service.create_session(payload)

    @app.get("/api/sessions/{session_id}")
    def get_session(session_id: str) -> dict[str, Any]:
        try:
            return service.get_session(session_id)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="session not found") from exc

    @app.get("/api/sessions/{session_id}/answers/{turn_id}")
    def get_answer(session_id: str, turn_id: str) -> dict[str, Any]:
        try:
            return service.get_answer(session_id, turn_id)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="answer not found") from exc

    @app.post("/api/sessions/{session_id}/transcripts")
    def handle_transcript(session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return service.handle_transcript(session_id, payload)
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="session not found") from exc

    @app.post("/api/sessions/{session_id}/tick")
    def tick_session(session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return service.tick_session(session_id, float(payload["now_ts"]))
        except KeyError as exc:  # pragma: no cover
            raise HTTPException(status_code=404, detail="session not found") from exc

    return app
