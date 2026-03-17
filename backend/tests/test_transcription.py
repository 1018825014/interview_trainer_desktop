import base64
import json
import time
import unittest
from unittest import mock

from interview_trainer.audio import AudioSessionManager
from interview_trainer.config import GenerationSettings, TranscriptionSettings
from interview_trainer.service import InterviewTrainerService
from interview_trainer.transcription import (
    AudioTranscriptionService,
    OpenAITranscriptionProvider,
    ProviderTranscript,
)
from interview_trainer.realtime_transcription import RealtimeChunkMetadata
from interview_trainer.realtime_transcription import RealtimeTranscriptEvent
from interview_trainer.realtime_transcription import RealtimeTranscriptDeltaEvent
from interview_trainer.types import AudioSource, Speaker


def _speech_pcm(*, amplitude: int = 1200, samples: int = 4000, switch_every: int = 12) -> bytes:
    payload = bytearray()
    for index in range(samples):
        sign = 1 if ((index // switch_every) % 2 == 0) else -1
        sample = amplitude * sign
        payload.extend(int(sample).to_bytes(2, byteorder="little", signed=True))
    return bytes(payload)


class _StaticProvider:
    provider_name = "stub"
    model_name = "stub-asr"

    def __init__(self, text: str) -> None:
        self.text = text
        self.call_count = 0

    def transcribe(self, **kwargs) -> ProviderTranscript:
        self.last_call = kwargs
        self.call_count += 1
        source = kwargs.get("source")
        text = self.text
        if source == AudioSource.MIC:
            text = "I designed the retrieval and orchestration layers around latency and debuggability."
        return ProviderTranscript(
            text=text,
            confidence=0.88,
            language="en",
            notes=["stub provider"],
        )


class _ImmediateRealtimeStream:
    provider_name = "openai_realtime"
    model_name = "gpt-4o-mini-transcribe"

    def __init__(self, source: AudioSource) -> None:
        self.source = source
        self.started = False
        self.closed = False
        self.partial_events: list[RealtimeTranscriptDeltaEvent] = []
        self.events: list[RealtimeTranscriptEvent] = []
        self._completion_hold = 1

    def start(self) -> None:
        self.started = True

    def enqueue_chunk(
        self,
        *,
        pcm: bytes,
        sample_rate: int,
        channels: int,
        sample_width_bytes: int,
        metadata,
    ) -> None:
        del pcm, sample_rate, channels, sample_width_bytes
        text = "Walk me through one agent project you built."
        if metadata.source == AudioSource.MIC:
            text = "I optimized retrieval, tool invocation, and evaluation around latency."
        self.partial_events.append(
            RealtimeTranscriptDeltaEvent(
                provider=self.provider_name,
                model=self.model_name,
                metadata=metadata,
                item_id=f"{metadata.source.value}-item",
                delta=text[:24],
                text=text[:24],
                language=metadata.language or "en",
            )
        )
        self.events.append(
            RealtimeTranscriptEvent(
                provider=self.provider_name,
                model=self.model_name,
                metadata=metadata,
                text=text,
                confidence=0.94,
                language=metadata.language or "en",
                notes=["fake realtime stream"],
                response_ms=35.0,
            )
        )

    def poll_partials(self, *, limit: int = 8) -> list[RealtimeTranscriptDeltaEvent]:
        ready = self.partial_events[:limit]
        self.partial_events = self.partial_events[limit:]
        return ready

    def poll_completed(self, *, limit: int = 8) -> list[RealtimeTranscriptEvent]:
        if not self.events:
            return []
        if self._completion_hold > 0:
            self._completion_hold -= 1
            return []
        ready = self.events[:limit]
        self.events = self.events[limit:]
        return ready

    def close(self) -> None:
        self.closed = True


class _AlibabaImmediateRealtimeStream(_ImmediateRealtimeStream):
    provider_name = "alibaba_realtime"
    model_name = "fun-asr-realtime-2026-02-28"


class _FakeResponse:
    def __init__(self, payload: str) -> None:
        self.payload = payload.encode("utf-8")

    def read(self) -> bytes:
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        del exc_type, exc, tb
        return False


class AudioTranscriptionServiceTests(unittest.TestCase):
    def test_transcribe_audio_session_can_forward_into_interview_flow(self) -> None:
        audio_sessions = AudioSessionManager()
        audio_session = audio_sessions.create_session({"transport": "manual", "sample_rate": 16000, "chunk_ms": 250})
        audio_session_id = audio_session["session_id"]
        audio_sessions.start_session(audio_session_id)
        audio_sessions.push_frame(
            audio_session_id,
            {
                "source": "system",
                "pcm_base64": base64.b64encode(_speech_pcm(samples=4000)).decode("ascii"),
                "ts": 2.0,
            },
        )

        interview_service = InterviewTrainerService(settings=GenerationSettings(provider="template"))
        interview_session = interview_service.create_session(
            {
                "knowledge": {
                    "projects": [
                        {
                            "name": "AgentOps Console",
                            "documents": [{"content": "Agent workflow builder with tracing and evaluation."}],
                            "code_files": [{"path": "src/workflow.py", "content": "def run():\n    return True\n"}],
                        }
                    ]
                },
                "briefing": {
                    "company": "Test AI",
                    "business_context": "Agent tooling",
                    "job_description": "Need agent system design and latency tradeoffs.",
                },
            }
        )

        provider = _StaticProvider("Walk me through one agent project you built.")
        transcriber = AudioTranscriptionService(
            audio_sessions,
            interview_service=interview_service,
            provider=provider,
        )
        result = transcriber.transcribe_audio_session(
            audio_session_id,
            {
                "source": "system",
                "session_id": interview_session["session_id"],
            },
        )

        self.assertFalse(result["skipped"])
        self.assertEqual(result["drained_frames"], 1)
        self.assertEqual(result["transcript"]["speaker"], "interviewer")
        self.assertEqual(result["transcript"]["text"], "Walk me through one agent project you built.")
        self.assertEqual(provider.last_call["source"], AudioSource.SYSTEM)
        self.assertIn("interview", result)
        self.assertIn("answer", result["interview"])
        self.assertIn(result["interview"]["answer"]["status"], {"pending", "starter_ready", "complete"})
        self.assertTrue(result["signal"]["passed"])

    def test_transcribe_audio_session_reports_skipped_when_no_frames_exist(self) -> None:
        audio_sessions = AudioSessionManager()
        audio_session = audio_sessions.create_session({"transport": "manual"})
        transcriber = AudioTranscriptionService(audio_sessions, provider=_StaticProvider("unused"))

        result = transcriber.transcribe_audio_session(audio_session["session_id"], {"source": "mic"})

        self.assertTrue(result["skipped"])
        self.assertIn("No mic frames", result["reason"])

    def test_transcribe_audio_session_gates_silent_chunks(self) -> None:
        audio_sessions = AudioSessionManager()
        audio_session = audio_sessions.create_session({"transport": "manual", "sample_rate": 16000, "chunk_ms": 250})
        audio_session_id = audio_session["session_id"]
        audio_sessions.start_session(audio_session_id)
        audio_sessions.push_frame(
            audio_session_id,
            {
                "source": "system",
                "pcm_base64": base64.b64encode(b"\x00\x00" * 200).decode("ascii"),
                "ts": 3.0,
            },
        )
        provider = _StaticProvider("unused")
        transcriber = AudioTranscriptionService(audio_sessions, provider=provider)

        result = transcriber.transcribe_audio_session(audio_session_id, {"source": "system"})

        self.assertTrue(result["skipped"])
        self.assertIn("gated", result["reason"])
        self.assertFalse(result["signal"]["passed"])
        self.assertEqual(provider.call_count, 0)

    def test_live_bridge_processes_system_and_mic_chunks(self) -> None:
        audio_sessions = AudioSessionManager()
        audio_session = audio_sessions.create_session({"transport": "manual", "sample_rate": 16000, "chunk_ms": 200})
        audio_session_id = audio_session["session_id"]
        audio_sessions.start_session(audio_session_id)

        interview_service = InterviewTrainerService(settings=GenerationSettings(provider="template"))
        interview_session = interview_service.create_session(
            {
                "knowledge": {
                    "projects": [
                        {
                            "name": "AgentOps Console",
                            "documents": [{"content": "Agent workflow builder with tracing and evaluation."}],
                            "code_files": [{"path": "src/workflow.py", "content": "def run():\n    return True\n"}],
                        }
                    ]
                },
                "briefing": {
                    "company": "Test AI",
                    "business_context": "Agent tooling",
                    "job_description": "Need agent system design and latency tradeoffs.",
                },
            }
        )
        provider = _StaticProvider("Walk me through one agent project you built.")
        transcriber = AudioTranscriptionService(
            audio_sessions,
            interview_service=interview_service,
            provider=provider,
        )
        bridge = transcriber.create_live_bridge(
            {
                "audio_session_id": audio_session_id,
                "session_id": interview_session["session_id"],
                "sources": ["system", "mic"],
                "poll_interval_ms": 220,
                "max_frames_per_chunk": 2,
                "auto_start": True,
            }
        )

        audio_sessions.push_frame(
            audio_session_id,
            {
                "source": "system",
                "pcm_base64": base64.b64encode(_speech_pcm(samples=3200)).decode("ascii"),
                "ts": 2.0,
            },
        )
        audio_sessions.push_frame(
            audio_session_id,
            {
                "source": "mic",
                "pcm_base64": base64.b64encode(_speech_pcm(amplitude=1800, samples=3200, switch_every=10)).decode("ascii"),
                "ts": 2.3,
            },
        )
        time.sleep(0.35)
        stopped = transcriber.stop_live_bridge(bridge["bridge_id"])

        self.assertEqual(stopped["status"], "stopped")
        self.assertGreaterEqual(stopped["transcripts_processed"], 2)
        self.assertTrue(any(item["source"] == "system" for item in stopped["recent_transcripts"]))
        self.assertTrue(any(item["source"] == "mic" for item in stopped["recent_transcripts"]))
        self.assertIsNotNone(stopped["last_answer"])
        self.assertTrue(stopped["last_signal"])

        session_state = interview_service.get_session(interview_session["session_id"])
        self.assertTrue(session_state["actual_candidate_history"])
        self.assertIn("retrieval and orchestration", session_state["actual_candidate_history"][-1])

    def test_live_bridge_flushes_quiet_short_speech_with_adaptive_gate(self) -> None:
        audio_sessions = AudioSessionManager()
        audio_session = audio_sessions.create_session({"transport": "manual", "sample_rate": 16000, "chunk_ms": 150})
        audio_session_id = audio_session["session_id"]
        audio_sessions.start_session(audio_session_id)

        interview_service = InterviewTrainerService(settings=GenerationSettings(provider="template"))
        interview_session = interview_service.create_session(
            {
                "knowledge": {
                    "projects": [
                        {
                            "name": "AgentOps Console",
                            "documents": [{"content": "Agent workflow builder with tracing and evaluation."}],
                            "code_files": [{"path": "src/workflow.py", "content": "def run():\n    return True\n"}],
                        }
                    ]
                },
                "briefing": {
                    "company": "Test AI",
                    "business_context": "Agent tooling",
                    "job_description": "Need agent system design and latency tradeoffs.",
                },
            }
        )
        provider = _StaticProvider("Walk me through one agent project you built.")
        transcriber = AudioTranscriptionService(
            audio_sessions,
            interview_service=interview_service,
            settings=TranscriptionSettings(
                energy_threshold=0.01,
                adaptive_gate_enabled=True,
                adaptive_floor_ratio=0.3,
                bridge_target_duration_ms=450.0,
                min_duration_ms=120.0,
            ),
            provider=provider,
        )
        bridge = transcriber.create_live_bridge(
            {
                "audio_session_id": audio_session_id,
                "session_id": interview_session["session_id"],
                "sources": ["system"],
                "poll_interval_ms": 80,
                "max_frames_per_chunk": 1,
                "auto_start": True,
            }
        )

        audio_sessions.push_frame(
            audio_session_id,
            {
                "source": "system",
                "pcm_base64": base64.b64encode(_speech_pcm(amplitude=160, samples=2400)).decode("ascii"),
                "ts": 4.0,
            },
        )
        time.sleep(0.35)
        stopped = transcriber.stop_live_bridge(bridge["bridge_id"])

        self.assertGreaterEqual(stopped["transcripts_processed"], 1)
        self.assertGreaterEqual(stopped["skipped_polls"], 1)
        self.assertLess(stopped["source_state"]["system"]["adaptive_threshold"], 0.01)
        self.assertTrue(stopped["last_signal"]["passed"])
        self.assertEqual(provider.call_count, 1)

    def test_live_bridge_can_use_realtime_streams(self) -> None:
        audio_sessions = AudioSessionManager()
        audio_session = audio_sessions.create_session({"transport": "manual", "sample_rate": 16000, "chunk_ms": 200})
        audio_session_id = audio_session["session_id"]
        audio_sessions.start_session(audio_session_id)

        interview_service = InterviewTrainerService(settings=GenerationSettings(provider="template"))
        interview_session = interview_service.create_session(
            {
                "knowledge": {
                    "projects": [
                        {
                            "name": "AgentOps Console",
                            "documents": [{"content": "Agent workflow builder with tracing and evaluation."}],
                            "code_files": [{"path": "src/workflow.py", "content": "def run():\n    return True\n"}],
                        }
                    ]
                },
                "briefing": {
                    "company": "Test AI",
                    "business_context": "Agent tooling",
                    "job_description": "Need agent system design and latency tradeoffs.",
                },
            }
        )

        provider = _StaticProvider("unused chunk provider")
        created_streams: dict[str, _ImmediateRealtimeStream] = {}

        def realtime_factory(settings, source, language, prompt):
            del settings, language, prompt
            stream = _ImmediateRealtimeStream(source)
            created_streams[source.value] = stream
            return stream

        transcriber = AudioTranscriptionService(
            audio_sessions,
            interview_service=interview_service,
            settings=TranscriptionSettings(provider="openai_realtime", openai_api_key="test-key"),
            provider=provider,
            realtime_stream_factory=realtime_factory,
        )
        bridge = transcriber.create_live_bridge(
            {
                "audio_session_id": audio_session_id,
                "session_id": interview_session["session_id"],
                "sources": ["system", "mic"],
                "poll_interval_ms": 80,
                "max_frames_per_chunk": 2,
                "auto_start": True,
            }
        )

        audio_sessions.push_frame(
            audio_session_id,
            {
                "source": "system",
                "pcm_base64": base64.b64encode(_speech_pcm(samples=3200)).decode("ascii"),
                "ts": 8.0,
            },
        )
        audio_sessions.push_frame(
            audio_session_id,
            {
                "source": "mic",
                "pcm_base64": base64.b64encode(_speech_pcm(amplitude=1800, samples=3200, switch_every=10)).decode("ascii"),
                "ts": 8.3,
            },
        )
        deadline = time.time() + 1.0
        running = transcriber.get_live_bridge(bridge["bridge_id"])
        while time.time() < deadline and not running["partial_transcripts"]:
            time.sleep(0.05)
            running = transcriber.get_live_bridge(bridge["bridge_id"])
        self.assertTrue(running["partial_transcripts"])
        self.assertTrue(any(item["text"] for item in running["partial_transcripts"]))
        time.sleep(0.35)
        stopped = transcriber.stop_live_bridge(bridge["bridge_id"])

        self.assertGreaterEqual(stopped["transcripts_processed"], 2)
        self.assertEqual(provider.call_count, 0)
        self.assertIn("openai_realtime", {item["provider"] for item in stopped["recent_transcripts"]})
        self.assertFalse(stopped["partial_transcripts"])
        self.assertTrue(created_streams["system"].started)
        self.assertTrue(created_streams["system"].closed)
        self.assertTrue(created_streams["mic"].closed)

    def test_live_bridge_falls_back_to_chunk_when_realtime_stream_fails(self) -> None:
        audio_sessions = AudioSessionManager()
        audio_session = audio_sessions.create_session({"transport": "manual", "sample_rate": 16000, "chunk_ms": 200})
        audio_session_id = audio_session["session_id"]
        audio_sessions.start_session(audio_session_id)

        interview_service = InterviewTrainerService(settings=GenerationSettings(provider="template"))
        interview_session = interview_service.create_session(
            {
                "knowledge": {
                    "projects": [
                        {
                            "name": "AgentOps Console",
                            "documents": [{"content": "Agent workflow builder with tracing and evaluation."}],
                            "code_files": [{"path": "src/workflow.py", "content": "def run():\n    return True\n"}],
                        }
                    ]
                },
                "briefing": {
                    "company": "Test AI",
                    "business_context": "Agent tooling",
                    "job_description": "Need agent system design and latency tradeoffs.",
                },
            }
        )

        provider = _StaticProvider("Walk me through one agent project you built.")

        def failing_realtime_factory(settings, source, language, prompt):
            del settings, source, language, prompt
            raise RuntimeError("realtime socket timed out")

        transcriber = AudioTranscriptionService(
            audio_sessions,
            interview_service=interview_service,
            settings=TranscriptionSettings(provider="openai_realtime", openai_api_key="test-key"),
            provider=provider,
            realtime_stream_factory=failing_realtime_factory,
        )
        bridge = transcriber.create_live_bridge(
            {
                "audio_session_id": audio_session_id,
                "session_id": interview_session["session_id"],
                "sources": ["system"],
                "poll_interval_ms": 80,
                "max_frames_per_chunk": 2,
                "auto_start": True,
            }
        )

        audio_sessions.push_frame(
            audio_session_id,
            {
                "source": "system",
                "pcm_base64": base64.b64encode(_speech_pcm(samples=3200)).decode("ascii"),
                "ts": 11.0,
            },
        )
        time.sleep(0.35)
        stopped = transcriber.stop_live_bridge(bridge["bridge_id"])

        self.assertEqual(stopped["status"], "stopped")
        self.assertEqual(stopped["active_asr_mode"], "chunk")
        self.assertIn("timed out", stopped["realtime_fallback_reason"])
        self.assertGreaterEqual(stopped["transcripts_processed"], 1)
        self.assertEqual(provider.call_count, 1)

    def test_live_bridge_can_use_alibaba_realtime_streams(self) -> None:
        audio_sessions = AudioSessionManager()
        audio_session = audio_sessions.create_session({"transport": "manual", "sample_rate": 16000, "chunk_ms": 200})
        audio_session_id = audio_session["session_id"]
        audio_sessions.start_session(audio_session_id)

        interview_service = InterviewTrainerService(settings=GenerationSettings(provider="template"))
        interview_session = interview_service.create_session(
            {
                "knowledge": {
                    "projects": [
                        {
                            "name": "AgentOps Console",
                            "documents": [{"content": "Agent workflow builder with tracing and evaluation."}],
                            "code_files": [{"path": "src/workflow.py", "content": "def run():\n    return True\n"}],
                        }
                    ]
                },
                "briefing": {
                    "company": "Test AI",
                    "business_context": "Agent tooling",
                    "job_description": "Need agent system design and latency tradeoffs.",
                },
            }
        )

        provider = _StaticProvider("unused chunk provider")
        created_streams: dict[str, _AlibabaImmediateRealtimeStream] = {}

        def realtime_factory(settings, source, language, prompt):
            del settings, language, prompt
            stream = _AlibabaImmediateRealtimeStream(source)
            created_streams[source.value] = stream
            return stream

        transcriber = AudioTranscriptionService(
            audio_sessions,
            interview_service=interview_service,
            settings=TranscriptionSettings(provider="alibaba_realtime", alibaba_api_key="test-key"),
            provider=provider,
            realtime_stream_factory=realtime_factory,
        )
        bridge = transcriber.create_live_bridge(
            {
                "audio_session_id": audio_session_id,
                "session_id": interview_session["session_id"],
                "sources": ["system", "mic"],
                "poll_interval_ms": 80,
                "max_frames_per_chunk": 2,
                "auto_start": True,
            }
        )

        self.assertEqual(bridge["active_asr_mode"], "realtime")

        audio_sessions.push_frame(
            audio_session_id,
            {
                "source": "system",
                "pcm_base64": base64.b64encode(_speech_pcm(samples=3200)).decode("ascii"),
                "ts": 12.0,
            },
        )
        audio_sessions.push_frame(
            audio_session_id,
            {
                "source": "mic",
                "pcm_base64": base64.b64encode(_speech_pcm(amplitude=1800, samples=3200, switch_every=10)).decode("ascii"),
                "ts": 12.3,
            },
        )
        deadline = time.time() + 1.0
        running = transcriber.get_live_bridge(bridge["bridge_id"])
        while time.time() < deadline and not running["partial_transcripts"]:
            time.sleep(0.05)
            running = transcriber.get_live_bridge(bridge["bridge_id"])
        self.assertTrue(running["partial_transcripts"])
        time.sleep(0.35)
        stopped = transcriber.stop_live_bridge(bridge["bridge_id"])

        self.assertGreaterEqual(stopped["transcripts_processed"], 2)
        self.assertEqual(provider.call_count, 0)
        self.assertIn("alibaba_realtime", {item["provider"] for item in stopped["recent_transcripts"]})
        self.assertTrue(created_streams["system"].started)
        self.assertTrue(created_streams["system"].closed)
        self.assertTrue(created_streams["mic"].closed)


class OpenAITranscriptionProviderTests(unittest.TestCase):
    def test_provider_posts_multipart_audio_to_openai_endpoint(self) -> None:
        settings = TranscriptionSettings(
            provider="openai",
            openai_api_key="test-key",
            openai_base_url="https://api.openai.com/v1",
            model="gpt-4o-mini-transcribe",
            language="en",
        )
        provider = OpenAITranscriptionProvider(settings)

        captured_request = {}

        def fake_urlopen(req, timeout):
            captured_request["url"] = req.full_url
            captured_request["method"] = req.get_method()
            captured_request["timeout"] = timeout
            captured_request["content_type"] = req.get_header("Content-type")
            captured_request["authorization"] = req.get_header("Authorization")
            captured_request["body"] = req.data
            return _FakeResponse(json.dumps({"text": "hello world", "language": "en"}))

        with mock.patch("interview_trainer.transcription.request.urlopen", side_effect=fake_urlopen):
            result = provider.transcribe(
                wav_bytes=b"RIFFfakeWAVE",
                source=AudioSource.SYSTEM,
                language="en",
                prompt="technical interview",
                text_override="",
            )

        self.assertEqual(result.text, "hello world")
        self.assertEqual(result.language, "en")
        self.assertEqual(captured_request["url"], "https://api.openai.com/v1/audio/transcriptions")
        self.assertEqual(captured_request["method"], "POST")
        self.assertIn("multipart/form-data", captured_request["content_type"])
        self.assertEqual(captured_request["authorization"], "Bearer test-key")
        self.assertIn(b'name="model"', captured_request["body"])
        self.assertIn(b"gpt-4o-mini-transcribe", captured_request["body"])
        self.assertIn(b'name="prompt"', captured_request["body"])
        self.assertIn(b"technical interview", captured_request["body"])
        self.assertIn(b'filename="chunk.wav"', captured_request["body"])


class RealtimeStreamFactoryTests(unittest.TestCase):
    def test_default_realtime_stream_factory_returns_alibaba_stream_for_alibaba_provider(self) -> None:
        settings = TranscriptionSettings(
            provider="alibaba_realtime",
            alibaba_api_key="test-key",
            model="fun-asr-realtime-2026-02-28",
        )

        stream = AudioTranscriptionService._default_realtime_stream_factory(
            settings,
            AudioSource.SYSTEM,
            "zh",
            "",
        )

        self.assertEqual(stream.provider_name, "alibaba_realtime")
        self.assertEqual(stream.model_name, "fun-asr-realtime-2026-02-28")

    def test_alibaba_realtime_stream_translates_result_generated_events(self) -> None:
        settings = TranscriptionSettings(
            provider="alibaba_realtime",
            alibaba_api_key="test-key",
            model="fun-asr-realtime-2026-02-28",
        )
        stream = AudioTranscriptionService._default_realtime_stream_factory(
            settings,
            AudioSource.SYSTEM,
            "zh",
            "",
        )
        metadata = RealtimeChunkMetadata(
            source=AudioSource.SYSTEM,
            speaker=Speaker.INTERVIEWER,
            final=True,
            ts_start=0.0,
            ts_end=1.0,
            duration_ms=1000.0,
            num_frames=4,
            language="zh",
            prompt="",
            session_snapshot={},
            signal={},
            interview_session_id="session-1",
            auto_tick_offset_s=1.0,
            turn_id="turn-1",
        )

        stream._socket = object()
        stream._drain_socket = lambda **kwargs: None
        stream._pending_by_task_id["task-1"] = metadata
        stream._handle_event(
            {
                "header": {"event": "result-generated", "task_id": "task-1"},
                "payload": {
                    "output": {
                        "sentence": {
                            "text": "请介绍一下你的RAG项目",
                            "sentence_end": False,
                            "begin_time": 0,
                            "end_time": None,
                        }
                    }
                },
            }
        )

        partials = stream.poll_partials(limit=4)
        self.assertEqual(len(partials), 1)
        self.assertEqual(partials[0].text, "请介绍一下你的RAG项目")
        self.assertEqual(partials[0].delta, "请介绍一下你的RAG项目")

        stream._handle_event(
            {
                "header": {"event": "result-generated", "task_id": "task-1"},
                "payload": {
                    "output": {
                        "sentence": {
                            "text": "请介绍一下你的RAG项目",
                            "sentence_end": True,
                            "begin_time": 0,
                            "end_time": 1320,
                        }
                    }
                },
            }
        )

        completed = stream.poll_completed(limit=4)
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0].provider, "alibaba_realtime")
        self.assertEqual(completed[0].text, "请介绍一下你的RAG项目")
        self.assertEqual(completed[0].language, "zh")


if __name__ == "__main__":
    unittest.main()
