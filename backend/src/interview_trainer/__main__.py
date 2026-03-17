from __future__ import annotations

import argparse
import base64
import json
import time

from .api import create_app
from .audio import AudioProbe, AudioSessionManager
from .config import GenerationSettings, TranscriptionSettings
from .service import InterviewTrainerService
from .transcription import AudioTranscriptionService


def _demo_pcm(*, amplitude: int = 1200, samples: int = 4000, switch_every: int = 12) -> bytes:
    payload = bytearray()
    for index in range(samples):
        sign = 1 if ((index // switch_every) % 2 == 0) else -1
        sample = amplitude * sign
        payload.extend(int(sample).to_bytes(2, byteorder="little", signed=True))
    return bytes(payload)


def _demo_payload() -> dict:
    return {
        "profile": {
            "headline": "Agent application engineer focused on retrieval, orchestration, and evaluation.",
            "summary": "Strong at breaking business problems into retrieval, tool use, execution, and observability layers.",
            "strengths": ["system design", "latency tradeoffs", "truthful project storytelling"],
        },
        "projects": [
            {
                "name": "AgentOps Console",
                "business_value": "Help internal operators configure AI workflows with retrieval and tool calling.",
                "architecture": "React console + Python orchestration service + retrieval + tracing and evaluation.",
                "documents": [
                    {
                        "content": (
                            "This project serves internal business users and lets them configure agent workflows "
                            "without writing much code. The hard part was balancing latency, reliability, tracing, "
                            "and fallback behavior."
                        )
                    }
                ],
                "code_files": [
                    {
                        "path": "src/orchestrator/workflow.py",
                        "content": "class WorkflowOrchestrator:\n    def run(self, state):\n        return state\n",
                    },
                    {
                        "path": "src/retrieval/reranker.py",
                        "content": "def rerank(chunks):\n    return chunks[:5]\n",
                    },
                ],
            }
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Interview trainer backend")
    parser.add_argument("--demo", action="store_true", help="Run a local deterministic demo")
    parser.add_argument("--serve", action="store_true", help="Start the FastAPI app with uvicorn")
    parser.add_argument("--audio-info", action="store_true", help="Inspect local audio capture capabilities")
    parser.add_argument("--audio-plan", action="store_true", help="Show the recommended Windows capture plan")
    parser.add_argument("--audio-session-demo", action="store_true", help="Run a manual audio session demo")
    parser.add_argument("--transcription-demo", action="store_true", help="Run an audio to transcript to answer demo")
    parser.add_argument("--live-bridge-demo", action="store_true", help="Run a continuous live transcription bridge demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()

    if args.audio_info:
        probe = AudioProbe()
        print(json.dumps({"capabilities": [item.to_dict() for item in probe.probe()]}, ensure_ascii=False, indent=2))
        return

    if args.audio_plan:
        probe = AudioProbe()
        capabilities = probe.probe()
        print(
            json.dumps(
                {
                    "capabilities": [item.to_dict() for item in capabilities],
                    "recommendation": probe.recommend(capabilities).to_dict(),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.audio_session_demo:
        manager = AudioSessionManager()
        session = manager.create_session({"transport": "manual", "sample_rate": 16000, "chunk_ms": 200})
        session_id = session["session_id"]
        manager.start_session(session_id)
        manager.push_frame(
            session_id,
            {
                "source": "system",
                "pcm_base64": base64.b64encode(_demo_pcm(samples=3200)).decode("ascii"),
                "ts": 1.0,
            },
        )
        manager.push_frame(
            session_id,
            {
                "source": "mic",
                "pcm_base64": base64.b64encode(_demo_pcm(amplitude=1800, samples=3200, switch_every=10)).decode("ascii"),
                "ts": 1.2,
            },
        )
        drained = manager.drain_frames(session_id, max_frames=10, include_payload=False, as_wav=True)
        print(json.dumps({"session": session, "drained": drained}, ensure_ascii=False, indent=2))
        return

    if args.demo:
        settings = GenerationSettings.from_env()
        service = InterviewTrainerService(settings=settings)
        session = service.create_session(
            {
                "knowledge": _demo_payload(),
                "briefing": {
                    "company": "Mock AI Company",
                    "business_context": "Build a practical LLM application platform.",
                    "job_description": "Need strong agent, RAG, evaluation, and latency optimization skills.",
                },
            }
        )
        session_id = session["session_id"]
        print("Generation lanes:")
        print("  fast:", settings.fast_provider, settings.fast_model)
        print("  smart:", settings.smart_provider, settings.smart_model)
        print("Session:", json.dumps(session, ensure_ascii=False, indent=2))
        result = service.handle_transcript(
            session_id,
            {
                "speaker": "interviewer",
                "text": "Walk me through one agent project you built and explain the design tradeoffs.",
                "final": True,
                "confidence": 0.97,
                "ts_start": 0.0,
                "ts_end": 4.2,
                "turn_id": "",
            },
        )
        if "answer" not in result or result["answer"]["status"] == "pending":
            result = service.tick_session(session_id, 5.4)
        print("Answer:", json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.transcription_demo:
        generation_settings = GenerationSettings.from_env()
        transcription_settings = TranscriptionSettings.from_env()
        service = InterviewTrainerService(settings=generation_settings)
        audio_sessions = AudioSessionManager()
        transcriber = AudioTranscriptionService(
            audio_sessions,
            interview_service=service,
            settings=transcription_settings,
        )
        session = service.create_session(
            {
                "knowledge": _demo_payload(),
                "briefing": {
                    "company": "Mock AI Company",
                    "business_context": "Build a practical LLM application platform.",
                    "job_description": "Need strong agent, RAG, evaluation, and latency optimization skills.",
                },
            }
        )
        interview_session_id = session["session_id"]
        audio_session = audio_sessions.create_session({"transport": "manual", "sample_rate": 16000, "chunk_ms": 300})
        audio_session_id = audio_session["session_id"]
        audio_sessions.start_session(audio_session_id)
        audio_sessions.push_frame(
            audio_session_id,
            {
                "source": "system",
                "pcm_base64": base64.b64encode(_demo_pcm(samples=4800)).decode("ascii"),
                "ts": 1.0,
            },
        )
        result = transcriber.transcribe_audio_session(
            audio_session_id,
            {
                "source": "system",
                "session_id": interview_session_id,
                "text_override": "Walk me through one agent project you built and explain the design tradeoffs.",
            },
        )
        if "interview" in result and "answer" in result["interview"]:
            answer = result["interview"]["answer"]
            if answer["status"] == "pending":
                result["interview"] = service.tick_session(interview_session_id, result["transcript"]["ts_end"] + 1.2)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.live_bridge_demo:
        generation_settings = GenerationSettings.from_env()
        transcription_settings = TranscriptionSettings.from_env()
        service = InterviewTrainerService(settings=generation_settings)
        audio_sessions = AudioSessionManager()
        transcriber = AudioTranscriptionService(
            audio_sessions,
            interview_service=service,
            settings=transcription_settings,
        )
        session = service.create_session(
            {
                "knowledge": _demo_payload(),
                "briefing": {
                    "company": "Mock AI Company",
                    "business_context": "Build a practical LLM application platform.",
                    "job_description": "Need strong agent, RAG, evaluation, and latency optimization skills.",
                },
            }
        )
        interview_session_id = session["session_id"]
        audio_session = audio_sessions.create_session({"transport": "manual", "sample_rate": 16000, "chunk_ms": 250})
        audio_session_id = audio_session["session_id"]
        audio_sessions.start_session(audio_session_id)
        bridge = transcriber.create_live_bridge(
            {
                "audio_session_id": audio_session_id,
                "session_id": interview_session_id,
                "sources": ["system", "mic"],
                "poll_interval_ms": 120,
                "max_frames_per_chunk": 2,
                "auto_start": True,
            }
        )
        audio_sessions.push_frame(
            audio_session_id,
            {
                "source": "system",
                "pcm_base64": base64.b64encode(_demo_pcm(samples=4000)).decode("ascii"),
                "ts": 1.0,
            },
        )
        audio_sessions.push_frame(
            audio_session_id,
            {
                "source": "mic",
                "pcm_base64": base64.b64encode(_demo_pcm(amplitude=1800, samples=4000, switch_every=10)).decode("ascii"),
                "ts": 1.4,
            },
        )
        time.sleep(0.45)
        result = transcriber.stop_live_bridge(bridge["bridge_id"])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.serve:
        try:
            import uvicorn
        except ImportError as exc:  # pragma: no cover
            raise SystemExit("Install uvicorn from backend/requirements.txt first.") from exc
        uvicorn.run(create_app(), host=args.host, port=args.port)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
