from __future__ import annotations

import io
import math
import copy
import json
import threading
import time
import wave
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol
from urllib import error, request
from uuid import uuid4

from .audio import AudioCaptureConfig, AudioFrameEnvelope, AudioSessionManager
from .config import TranscriptionSettings
from .realtime_transcription import (
    AlibabaRealtimeTranscriptionStream,
    OpenAIRealtimeTranscriptionStream,
    RealtimeChunkMetadata,
    RealtimeTranscriptDeltaEvent,
    RealtimeTranscriptEvent,
    RealtimeTranscriptionStream,
)
from .service import InterviewTrainerService
from .types import AudioSource, Speaker


@dataclass(slots=True)
class ProviderTranscript:
    text: str
    confidence: float
    language: str
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TranscriptionResult:
    provider: str
    model: str
    source: AudioSource
    speaker: Speaker
    text: str
    confidence: float
    language: str
    final: bool
    ts_start: float
    ts_end: float
    duration_ms: float
    num_frames: int
    response_ms: float
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "source": self.source.value,
            "speaker": self.speaker.value,
            "text": self.text,
            "confidence": self.confidence,
            "language": self.language,
            "final": self.final,
            "ts_start": self.ts_start,
            "ts_end": self.ts_end,
            "duration_ms": round(self.duration_ms, 2),
            "num_frames": self.num_frames,
            "response_ms": round(self.response_ms, 2),
            "notes": self.notes,
        }


@dataclass(slots=True)
class SignalGateStats:
    avg_rms: float
    peak_rms: float
    voiced_frames: int
    total_frames: int
    voiced_ratio: float
    max_speech_run_frames: int
    duration_ms: float
    threshold: float
    noise_floor_rms: float
    avg_zcr: float
    peak_zcr: float
    avg_delta: float
    frame_ms: int
    passed: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "avg_rms": round(self.avg_rms, 6),
            "peak_rms": round(self.peak_rms, 6),
            "voiced_frames": self.voiced_frames,
            "total_frames": self.total_frames,
            "voiced_ratio": round(self.voiced_ratio, 4),
            "max_speech_run_frames": self.max_speech_run_frames,
            "duration_ms": round(self.duration_ms, 2),
            "threshold": round(self.threshold, 6),
            "noise_floor_rms": round(self.noise_floor_rms, 6),
            "avg_zcr": round(self.avg_zcr, 4),
            "peak_zcr": round(self.peak_zcr, 4),
            "avg_delta": round(self.avg_delta, 6),
            "frame_ms": self.frame_ms,
            "passed": self.passed,
            "reason": self.reason,
        }


@dataclass(slots=True)
class BridgeSourceState:
    source: AudioSource
    buffered_frames: list[AudioFrameEnvelope] = field(default_factory=list)
    noise_floor_rms: float = 0.0
    adaptive_threshold: float = 0.0
    buffered_duration_ms: float = 0.0
    recent_peak_rms: float = 0.0
    recent_avg_rms: float = 0.0
    partial_text: str = ""
    partial_updated_at: float | None = None
    last_gate: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source.value,
            "buffered_frames": len(self.buffered_frames),
            "buffered_duration_ms": round(self.buffered_duration_ms, 2),
            "noise_floor_rms": round(self.noise_floor_rms, 6),
            "adaptive_threshold": round(self.adaptive_threshold, 6),
            "recent_peak_rms": round(self.recent_peak_rms, 6),
            "recent_avg_rms": round(self.recent_avg_rms, 6),
            "partial_text": self.partial_text,
            "partial_updated_at": self.partial_updated_at,
            "last_gate": copy.deepcopy(self.last_gate),
        }


@dataclass(slots=True)
class PartialTranscriptView:
    provider: str
    model: str
    source: AudioSource
    speaker: Speaker
    item_id: str
    text: str
    language: str
    updated_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "source": self.source.value,
            "speaker": self.speaker.value,
            "item_id": self.item_id,
            "text": self.text,
            "language": self.language,
            "updated_at": self.updated_at,
        }


@dataclass(slots=True)
class LiveTranscriptionBridge:
    bridge_id: str
    audio_session_id: str
    interview_session_id: str
    sources: list[AudioSource]
    poll_interval_ms: int
    max_frames_per_chunk: int
    final: bool
    language: str
    prompt: str
    auto_tick_offset_s: float
    status: str = "created"
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    stopped_at: float | None = None
    cycles: int = 0
    transcripts_processed: int = 0
    skipped_polls: int = 0
    last_error: str = ""
    last_activity_at: float | None = None
    recent_transcripts: list[dict[str, Any]] = field(default_factory=list)
    last_answer: dict[str, Any] | None = None
    last_prewarm: dict[str, Any] | None = None
    pending_turn_ids: list[str] = field(default_factory=list)
    last_signal: dict[str, Any] | None = None
    last_skip_reason: str = ""
    source_state: dict[str, BridgeSourceState] = field(default_factory=dict)
    partial_transcripts: dict[str, PartialTranscriptView] = field(default_factory=dict)
    active_asr_mode: str = "chunk"
    realtime_fallback_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "bridge_id": self.bridge_id,
            "audio_session_id": self.audio_session_id,
            "interview_session_id": self.interview_session_id,
            "sources": [item.value for item in self.sources],
            "poll_interval_ms": self.poll_interval_ms,
            "max_frames_per_chunk": self.max_frames_per_chunk,
            "final": self.final,
            "language": self.language,
            "prompt": self.prompt,
            "auto_tick_offset_s": self.auto_tick_offset_s,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "cycles": self.cycles,
            "transcripts_processed": self.transcripts_processed,
            "skipped_polls": self.skipped_polls,
            "last_error": self.last_error,
            "last_activity_at": self.last_activity_at,
            "recent_transcripts": copy.deepcopy(self.recent_transcripts),
            "last_answer": copy.deepcopy(self.last_answer),
            "last_prewarm": copy.deepcopy(self.last_prewarm),
            "last_signal": copy.deepcopy(self.last_signal),
            "last_skip_reason": self.last_skip_reason,
            "source_state": {key: value.to_dict() for key, value in self.source_state.items()},
            "partial_transcripts": [item.to_dict() for item in self.partial_transcripts.values()],
            "active_asr_mode": self.active_asr_mode,
            "realtime_fallback_reason": self.realtime_fallback_reason,
        }


class TranscriptionProvider(Protocol):
    provider_name: str
    model_name: str

    def transcribe(
        self,
        *,
        wav_bytes: bytes,
        source: AudioSource,
        language: str,
        prompt: str,
        text_override: str,
    ) -> ProviderTranscript: ...


class TemplateTranscriptionProvider:
    provider_name = "template"
    model_name = "template-asr"

    def transcribe(
        self,
        *,
        wav_bytes: bytes,
        source: AudioSource,
        language: str,
        prompt: str,
        text_override: str,
    ) -> ProviderTranscript:
        del wav_bytes, prompt
        if text_override.strip():
            text = text_override.strip()
        elif source == AudioSource.SYSTEM:
            text = "Please walk me through one agent project you built and explain the design tradeoffs."
        else:
            text = "Sure. I built an agent workflow console and I can explain the business goal, architecture, and tradeoffs."
        return ProviderTranscript(
            text=text,
            confidence=0.61,
            language=language or "en",
            notes=[
                "Template ASR is active. Set INTERVIEW_TRAINER_ASR_PROVIDER=openai or alibaba_realtime for real transcription."
            ],
        )


class OpenAITranscriptionProvider:
    provider_name = "openai"

    def __init__(self, settings: TranscriptionSettings) -> None:
        self.settings = settings
        self.model_name = settings.model

    def transcribe(
        self,
        *,
        wav_bytes: bytes,
        source: AudioSource,
        language: str,
        prompt: str,
        text_override: str,
    ) -> ProviderTranscript:
        del source, text_override
        fields = {
            "model": self.settings.model,
            "response_format": "json",
        }
        if language:
            fields["language"] = language
        if prompt:
            fields["prompt"] = prompt
        body, content_type = self._build_multipart_form_data(
            fields=fields,
            file_field_name="file",
            filename="chunk.wav",
            file_bytes=wav_bytes,
            mime_type="audio/wav",
        )
        endpoint = f"{self.settings.openai_base_url}/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": content_type,
        }
        req = request.Request(endpoint, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=self.settings.request_timeout_s) as response:
                payload = response.read().decode("utf-8")
        except error.HTTPError as exc:  # pragma: no cover - network branch
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"OpenAI transcription failed: {exc.code} {detail}") from exc
        except error.URLError as exc:  # pragma: no cover - network branch
            raise RuntimeError(f"OpenAI transcription failed: {exc.reason}") from exc

        parsed = self._parse_response(payload)
        return ProviderTranscript(
            text=parsed.get("text", "").strip(),
            confidence=0.92,
            language=str(parsed.get("language") or language or self.settings.language or "unknown"),
            notes=["Chunked transcription via OpenAI audio/transcriptions."],
        )

    @staticmethod
    def _build_multipart_form_data(
        *,
        fields: dict[str, str],
        file_field_name: str,
        filename: str,
        file_bytes: bytes,
        mime_type: str,
    ) -> tuple[bytes, str]:
        boundary = f"----InterviewTrainerBoundary{uuid4().hex}"
        body: list[bytes] = []

        for name, value in fields.items():
            body.append(f"--{boundary}\r\n".encode("utf-8"))
            body.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
            body.append(str(value).encode("utf-8"))
            body.append(b"\r\n")

        body.append(f"--{boundary}\r\n".encode("utf-8"))
        body.append(
            (
                f'Content-Disposition: form-data; name="{file_field_name}"; filename="{filename}"\r\n'
                f"Content-Type: {mime_type}\r\n\r\n"
            ).encode("utf-8")
        )
        body.append(file_bytes)
        body.append(b"\r\n")
        body.append(f"--{boundary}--\r\n".encode("utf-8"))
        return b"".join(body), f"multipart/form-data; boundary={boundary}"

    @staticmethod
    def _parse_response(payload: str) -> dict[str, Any]:
        payload = payload.strip()
        if not payload:
            return {"text": ""}
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return {"text": payload}
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, str):
            return {"text": parsed}
        return {"text": str(parsed)}


class AlibabaRealtimeChunkTranscriptionProvider:
    provider_name = "alibaba_realtime"

    def __init__(
        self,
        settings: TranscriptionSettings,
        realtime_stream_factory: Callable[
            [TranscriptionSettings, AudioSource, str, str],
            RealtimeTranscriptionStream,
        ],
    ) -> None:
        self.settings = settings
        self.model_name = settings.model
        self._realtime_stream_factory = realtime_stream_factory

    def transcribe(
        self,
        *,
        wav_bytes: bytes,
        source: AudioSource,
        language: str,
        prompt: str,
        text_override: str,
    ) -> ProviderTranscript:
        del text_override
        pcm, sample_rate, channels, sample_width_bytes = self._extract_wav_pcm(wav_bytes)
        stream = self._realtime_stream_factory(self.settings, source, language, prompt)
        try:
            stream.start()
            texts: list[str] = []
            confidences: list[float] = []
            language_hint = language or self.settings.language or "unknown"
            for segment in self._split_pcm_segments(
                pcm=pcm,
                sample_rate=sample_rate,
                channels=channels,
                sample_width_bytes=sample_width_bytes,
            ):
                metadata = RealtimeChunkMetadata(
                    source=source,
                    speaker=Speaker.INTERVIEWER if source == AudioSource.SYSTEM else Speaker.CANDIDATE,
                    final=True,
                    ts_start=segment["ts_start"],
                    ts_end=segment["ts_end"],
                    duration_ms=segment["duration_ms"],
                    num_frames=1,
                    language=language or self.settings.language,
                    prompt=prompt,
                    session_snapshot={},
                    signal={},
                    interview_session_id="",
                    auto_tick_offset_s=0.0,
                    turn_id="",
                )
                stream.enqueue_chunk(
                    pcm=segment["pcm"],
                    sample_rate=sample_rate,
                    channels=channels,
                    sample_width_bytes=sample_width_bytes,
                    metadata=metadata,
                )
                event = self._wait_for_completed_event(stream, expected_duration_ms=segment["duration_ms"])
                if event.error:
                    raise RuntimeError(event.error)
                if event.text.strip():
                    texts.append(event.text.strip())
                confidences.append(event.confidence)
                if event.language:
                    language_hint = event.language
            return ProviderTranscript(
                text=" ".join(texts).strip(),
                confidence=(sum(confidences) / len(confidences)) if confidences else 0.0,
                language=language_hint,
                notes=["Chunk transcription via Alibaba realtime ASR (segmented for stability)."],
            )
        except Exception as exc:
            raise RuntimeError(f"Alibaba transcription failed: {exc}") from exc
        finally:
            stream.close()

    @staticmethod
    def _extract_wav_pcm(wav_bytes: bytes) -> tuple[bytes, int, int, int]:
        with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
            return (
                wav_file.readframes(wav_file.getnframes()),
                wav_file.getframerate(),
                wav_file.getnchannels(),
                wav_file.getsampwidth(),
            )

    def _split_pcm_segments(
        self,
        *,
        pcm: bytes,
        sample_rate: int,
        channels: int,
        sample_width_bytes: int,
    ) -> list[dict[str, Any]]:
        bytes_per_frame = max(1, channels * sample_width_bytes)
        if not pcm:
            return [
                {
                    "pcm": b"",
                    "ts_start": 0.0,
                    "ts_end": 0.0,
                    "duration_ms": 0.0,
                }
            ]
        target_duration_ms = max(3000.0, self.settings.bridge_target_duration_ms)
        frames_per_segment = max(1, int(sample_rate * target_duration_ms / 1000.0))
        segments: list[dict[str, Any]] = []
        total_frames = len(pcm) // bytes_per_frame
        cursor_frames = 0
        while cursor_frames < total_frames:
            next_cursor_frames = min(total_frames, cursor_frames + frames_per_segment)
            start_byte = cursor_frames * bytes_per_frame
            end_byte = next_cursor_frames * bytes_per_frame
            duration_ms = ((next_cursor_frames - cursor_frames) / max(sample_rate, 1)) * 1000.0
            segments.append(
                {
                    "pcm": pcm[start_byte:end_byte],
                    "ts_start": cursor_frames / max(sample_rate, 1),
                    "ts_end": next_cursor_frames / max(sample_rate, 1),
                    "duration_ms": duration_ms,
                }
            )
            cursor_frames = next_cursor_frames
        return segments

    def _wait_for_completed_event(
        self,
        stream: RealtimeTranscriptionStream,
        *,
        expected_duration_ms: float,
    ) -> RealtimeTranscriptEvent:
        deadline = time.perf_counter() + max(
            self.settings.realtime_drain_timeout_s,
            2.0,
            (expected_duration_ms / 1000.0) + 1.0,
        )
        completed: list[RealtimeTranscriptEvent] = []
        while time.perf_counter() < deadline:
            completed = stream.poll_completed(limit=1)
            if completed:
                return completed[0]
            time.sleep(0.05)
        raise RuntimeError("Alibaba chunk transcription timed out waiting for a result.")


class AudioTranscriptionService:
    def __init__(
        self,
        audio_sessions: AudioSessionManager,
        *,
        interview_service: InterviewTrainerService | None = None,
        settings: TranscriptionSettings | None = None,
        provider: TranscriptionProvider | None = None,
        realtime_stream_factory: Callable[
            [TranscriptionSettings, AudioSource, str, str],
            RealtimeTranscriptionStream,
        ]
        | None = None,
    ) -> None:
        self.audio_sessions = audio_sessions
        self.interview_service = interview_service
        self.settings = settings or TranscriptionSettings.from_env()
        self._realtime_stream_factory = realtime_stream_factory or self._default_realtime_stream_factory
        self.provider = provider or self._build_provider(self.settings, self._realtime_stream_factory)
        self._lock = threading.RLock()
        self.bridges: dict[str, LiveTranscriptionBridge] = {}
        self._bridge_events: dict[str, threading.Event] = {}
        self._bridge_threads: dict[str, threading.Thread] = {}
        self._bridge_streams: dict[str, dict[str, RealtimeTranscriptionStream]] = {}

    def transcribe_audio_session(self, audio_session_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        source = AudioSource(str(payload.get("source", AudioSource.SYSTEM.value)))
        speaker = self._resolve_speaker(payload.get("speaker"), source)
        max_frames = max(1, int(payload.get("max_frames", 12)))
        final = bool(payload.get("final", True))
        language = str(payload.get("language") or self.settings.language).strip()
        prompt = str(payload.get("prompt") or self.settings.prompt).strip()
        text_override = str(payload.get("text_override", "")).strip()
        enable_gate = self._coerce_bool(payload.get("enable_gate"), self.settings.energy_gate_enabled)

        session_snapshot, config_snapshot, frames = self.audio_sessions.drain_frame_batch(
            audio_session_id,
            max_frames=max_frames,
            source=source.value,
        )
        if not frames:
            return {
                "session": session_snapshot,
                "skipped": True,
                "reason": f"No {source.value} frames are available to transcribe.",
            }

        ts_start, ts_end, duration_ms = self._frame_window(frames, config_snapshot)
        signal = self._analyze_signal(
            frames,
            config_snapshot,
            duration_ms=duration_ms,
            threshold=self.settings.energy_threshold,
            min_duration_ms=self.settings.min_duration_ms,
            noise_floor_rms=0.0,
        )
        if enable_gate and not text_override and not signal.passed:
            return {
                "session": session_snapshot,
                "skipped": True,
                "reason": signal.reason,
                "drained_frames": len(frames),
                "signal": signal.to_dict(),
            }

        return self._transcribe_frames(
            session_snapshot=session_snapshot,
            config_snapshot=config_snapshot,
            frames=frames,
            source=source,
            speaker=speaker,
            final=final,
            language=language,
            prompt=prompt,
            text_override=text_override,
            signal=signal,
            interview_session_id=str(payload.get("session_id") or payload.get("interview_session_id", "")).strip(),
            auto_tick_offset_s=float(payload.get("auto_tick_offset_s", 1.0)),
            turn_id=str(payload.get("turn_id", "")),
        )

    def _transcribe_frames(
        self,
        *,
        session_snapshot: dict[str, Any],
        config_snapshot: AudioCaptureConfig,
        frames: list[AudioFrameEnvelope],
        source: AudioSource,
        speaker: Speaker,
        final: bool,
        language: str,
        prompt: str,
        text_override: str,
        signal: SignalGateStats,
        interview_session_id: str,
        auto_tick_offset_s: float,
        turn_id: str,
    ) -> dict[str, Any]:
        wav_bytes = self.audio_sessions.build_wav_bytes(
            frames=[item.frame for item in frames],
            sample_rate=config_snapshot.sample_rate,
            channels=config_snapshot.channels,
            sample_width_bytes=config_snapshot.sample_width_bytes,
        )
        ts_start, ts_end, duration_ms = self._frame_window(frames, config_snapshot)
        started_at = time.perf_counter()
        provider_result = self.provider.transcribe(
            wav_bytes=wav_bytes,
            source=source,
            language=language,
            prompt=prompt,
            text_override=text_override,
        )
        response_ms = (time.perf_counter() - started_at) * 1000

        transcript = TranscriptionResult(
            provider=self.provider.provider_name,
            model=self.provider.model_name,
            source=source,
            speaker=speaker,
            text=provider_result.text,
            confidence=provider_result.confidence,
            language=provider_result.language,
            final=final,
            ts_start=ts_start,
            ts_end=ts_end,
            duration_ms=duration_ms,
            num_frames=len(frames),
            response_ms=response_ms,
            notes=provider_result.notes,
        )
        return self._finalize_transcript_result(
            session_snapshot=session_snapshot,
            transcript=transcript,
            signal=signal.to_dict(),
            drained_frames=len(frames),
            interview_session_id=interview_session_id,
            auto_tick_offset_s=auto_tick_offset_s,
            turn_id=turn_id,
        )

    def _finalize_transcript_result(
        self,
        *,
        session_snapshot: dict[str, Any],
        transcript: TranscriptionResult,
        signal: dict[str, Any],
        drained_frames: int,
        interview_session_id: str,
        auto_tick_offset_s: float,
        turn_id: str,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "session": session_snapshot,
            "skipped": False,
            "drained_frames": drained_frames,
            "transcript": transcript.to_dict(),
            "signal": signal,
        }

        if interview_session_id and self.interview_service is not None:
            interview_result = self.interview_service.handle_transcript(
                interview_session_id,
                {
                    "speaker": transcript.speaker.value,
                    "text": transcript.text,
                    "final": transcript.final,
                    "confidence": transcript.confidence,
                    "ts_start": transcript.ts_start,
                    "ts_end": transcript.ts_end,
                    "turn_id": turn_id,
                },
            )
            if (
                transcript.speaker == Speaker.INTERVIEWER
                and transcript.final
                and auto_tick_offset_s >= 0.0
                and "answer" not in interview_result
            ):
                interview_result = self.interview_service.tick_session(
                    interview_session_id,
                    transcript.ts_end + auto_tick_offset_s,
                )
            result["interview"] = interview_result
        return result

    def create_live_bridge(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        audio_session_id = str(payload["audio_session_id"])
        self.audio_sessions.get_session(audio_session_id)
        interview_session_id = str(payload.get("session_id") or payload.get("interview_session_id", "")).strip()
        if interview_session_id and self.interview_service is not None:
            self.interview_service.get_session(interview_session_id)
        bridge = LiveTranscriptionBridge(
            bridge_id=str(uuid4()),
            audio_session_id=audio_session_id,
            interview_session_id=interview_session_id,
            sources=self._parse_sources(payload.get("sources")),
            poll_interval_ms=max(100, int(payload.get("poll_interval_ms", 600))),
            max_frames_per_chunk=max(1, int(payload.get("max_frames_per_chunk", 6))),
            final=bool(payload.get("final", True)),
            language=str(payload.get("language") or self.settings.language).strip(),
            prompt=str(payload.get("prompt") or self.settings.prompt).strip(),
            auto_tick_offset_s=float(payload.get("auto_tick_offset_s", 1.0)),
            active_asr_mode="realtime" if self.settings.use_realtime_stream else "chunk",
        )
        bridge.source_state = {
            source.value: BridgeSourceState(
                source=source,
                adaptive_threshold=self.settings.energy_threshold,
            )
            for source in bridge.sources
        }
        with self._lock:
            self.bridges[bridge.bridge_id] = bridge
        if bool(payload.get("auto_start", False)):
            return self.start_live_bridge(bridge.bridge_id)
        return bridge.to_dict()

    def list_live_bridges(self) -> dict[str, Any]:
        with self._lock:
            return {"bridges": [bridge.to_dict() for bridge in self.bridges.values()]}

    def get_live_bridge(self, bridge_id: str) -> dict[str, Any]:
        with self._lock:
            return self.bridges[bridge_id].to_dict()

    def start_live_bridge(self, bridge_id: str) -> dict[str, Any]:
        with self._lock:
            bridge = self.bridges[bridge_id]
            if bridge.status == "running":
                return bridge.to_dict()
            stop_event = threading.Event()
            worker = threading.Thread(
                target=self._run_live_bridge,
                args=(bridge_id, stop_event),
                name=f"transcription-bridge-{bridge_id[:8]}",
                daemon=True,
            )
            bridge.status = "running"
            bridge.started_at = time.time()
            bridge.stopped_at = None
            bridge.last_error = ""
            self._bridge_events[bridge_id] = stop_event
            self._bridge_threads[bridge_id] = worker
            snapshot = bridge.to_dict()
        worker.start()
        return snapshot

    def stop_live_bridge(self, bridge_id: str) -> dict[str, Any]:
        with self._lock:
            bridge = self.bridges[bridge_id]
            stop_event = self._bridge_events.pop(bridge_id, None)
            worker = self._bridge_threads.pop(bridge_id, None)
            if stop_event is None or worker is None:
                if bridge.status == "running":
                    bridge.status = "stopped"
                    bridge.stopped_at = time.time()
                return bridge.to_dict()

        stop_event.set()
        worker.join(timeout=2.0)

        with self._lock:
            bridge = self.bridges[bridge_id]
            if bridge.status != "failed":
                bridge.status = "stopped"
            bridge.stopped_at = bridge.stopped_at or time.time()
            return bridge.to_dict()

    def _run_live_bridge(self, bridge_id: str, stop_event: threading.Event) -> None:
        try:
            self._maybe_prepare_realtime_streams(bridge_id)
            while not stop_event.is_set():
                poll_interval_s = self._run_live_bridge_cycle(bridge_id)
                self._collect_pending_answers(bridge_id)
                if stop_event.wait(poll_interval_s):
                    break
        except Exception as exc:  # pragma: no cover - defensive worker branch
            with self._lock:
                bridge = self.bridges.get(bridge_id)
                if bridge is not None:
                    bridge.status = "failed"
                    bridge.last_error = str(exc)
                    bridge.stopped_at = time.time()
        finally:
            for result in self._flush_live_bridge_buffers(bridge_id):
                self._record_bridge_result(bridge_id, result)
            for result in self._drain_bridge_streams(bridge_id, timeout_s=self.settings.realtime_drain_timeout_s):
                self._record_bridge_result(bridge_id, result)
            self._close_bridge_streams(bridge_id)
            self._collect_pending_answers(bridge_id)
            with self._lock:
                bridge = self.bridges.get(bridge_id)
                self._bridge_events.pop(bridge_id, None)
                self._bridge_threads.pop(bridge_id, None)
                if bridge is not None and bridge.status == "running":
                    bridge.status = "stopped"
                    bridge.stopped_at = time.time()

    def _run_live_bridge_cycle(self, bridge_id: str) -> float:
        with self._lock:
            bridge = self.bridges[bridge_id]
            bridge.cycles += 1
            sources = list(bridge.sources)
            poll_interval_s = bridge.poll_interval_ms / 1000.0

        for result in self._poll_bridge_streams(bridge_id):
            self._record_bridge_result(bridge_id, result)
        for source in sources:
            result = self._process_live_bridge_source(bridge_id, source)
            self._record_bridge_result(bridge_id, result)
        for result in self._poll_bridge_streams(bridge_id):
            self._record_bridge_result(bridge_id, result)
        return poll_interval_s

    def _record_bridge_result(self, bridge_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            bridge = self.bridges[bridge_id]
            if result.get("failed"):
                bridge.last_error = str(result.get("reason", ""))
                if result.get("signal") is not None:
                    bridge.last_signal = copy.deepcopy(result.get("signal"))
                return
            if result.get("queued"):
                bridge.last_activity_at = time.time()
                if result.get("signal") is not None:
                    bridge.last_signal = copy.deepcopy(result.get("signal"))
                bridge.last_skip_reason = ""
                return
            if result.get("partial"):
                partial = dict(result["transcript"])
                partial_updated_at = float(partial.get("updated_at", time.time()))
                bridge.partial_transcripts[partial["source"]] = PartialTranscriptView(
                    provider=str(partial["provider"]),
                    model=str(partial["model"]),
                    source=AudioSource(str(partial["source"])),
                    speaker=Speaker(str(partial["speaker"])),
                    item_id=str(partial.get("item_id", "")),
                    text=str(partial["text"]),
                    language=str(partial.get("language", "")),
                    updated_at=partial_updated_at,
                )
                source_state = bridge.source_state.get(partial["source"])
                if source_state is not None:
                    source_state.partial_text = str(partial["text"])
                    source_state.partial_updated_at = partial_updated_at
                bridge.last_activity_at = time.time()
                return
            if result.get("skipped"):
                bridge.skipped_polls += 1
                if result.get("signal") is not None:
                    bridge.last_signal = copy.deepcopy(result.get("signal"))
                bridge.last_skip_reason = str(result.get("reason", ""))
                return

            transcript = dict(result["transcript"])
            interview = result.get("interview", {})
            answer = interview.get("answer")
            prewarm = interview.get("prewarm")
            bridge.partial_transcripts.pop(transcript["source"], None)
            source_state = bridge.source_state.get(transcript["source"])
            if source_state is not None:
                source_state.partial_text = ""
                source_state.partial_updated_at = None
            bridge.last_prewarm = copy.deepcopy(prewarm) if prewarm else None
            if answer:
                transcript["answer_turn_id"] = answer.get("turn_id", "")
                transcript["answer_status"] = answer.get("status", "")
                bridge.last_answer = copy.deepcopy(answer)
                turn_id = answer.get("turn_id", "")
                if turn_id and answer.get("status") in {"pending", "starter_ready"}:
                    if turn_id not in bridge.pending_turn_ids:
                        bridge.pending_turn_ids.append(turn_id)

            bridge.transcripts_processed += 1
            bridge.last_activity_at = time.time()
            bridge.recent_transcripts.append(transcript)
            bridge.last_signal = copy.deepcopy(result.get("signal"))
            bridge.last_skip_reason = ""
            if len(bridge.recent_transcripts) > 12:
                bridge.recent_transcripts = bridge.recent_transcripts[-12:]

    def _process_live_bridge_source(self, bridge_id: str, source: AudioSource) -> dict[str, Any]:
        with self._lock:
            bridge = self.bridges[bridge_id]
            source_state = bridge.source_state[source.value]
            audio_session_id = bridge.audio_session_id
            interview_session_id = bridge.interview_session_id
            max_frames = bridge.max_frames_per_chunk
            final = bridge.final
            language = bridge.language
            prompt = bridge.prompt
            auto_tick_offset_s = bridge.auto_tick_offset_s
            use_realtime = bridge.active_asr_mode == "realtime"

        session_snapshot, config_snapshot, new_frames = self.audio_sessions.drain_frame_batch(
            audio_session_id,
            max_frames=max_frames,
            source=source.value,
        )
        if not new_frames and not source_state.buffered_frames:
            return {
                "session": session_snapshot,
                "skipped": True,
                "reason": f"No {source.value} frames are available to transcribe.",
            }

        self._update_noise_floor(source_state, new_frames, config_snapshot)

        candidate_frames = list(source_state.buffered_frames) + list(new_frames)
        candidate_duration_ms = self._buffer_duration_ms(candidate_frames, config_snapshot)
        threshold = self._effective_threshold(source_state)
        signal = self._analyze_signal(
            candidate_frames,
            config_snapshot,
            duration_ms=candidate_duration_ms,
            threshold=threshold,
            min_duration_ms=self.settings.min_duration_ms,
            noise_floor_rms=source_state.noise_floor_rms,
        )
        source_state.recent_avg_rms = signal.avg_rms
        source_state.recent_peak_rms = signal.peak_rms
        source_state.adaptive_threshold = threshold
        source_state.last_gate = signal.to_dict()

        if not new_frames and source_state.buffered_frames and signal.passed:
            source_state.buffered_frames = []
            source_state.buffered_duration_ms = 0.0
            if use_realtime:
                return self._enqueue_realtime_chunk(
                    bridge_id=bridge_id,
                    session_snapshot=session_snapshot,
                    config_snapshot=config_snapshot,
                    frames=candidate_frames,
                    source=source,
                    final=final,
                    language=language,
                    prompt=prompt,
                    signal=signal,
                    interview_session_id=interview_session_id,
                    auto_tick_offset_s=auto_tick_offset_s,
                    turn_id="",
                )
            return self._transcribe_frames(
                session_snapshot=session_snapshot,
                config_snapshot=config_snapshot,
                frames=candidate_frames,
                source=source,
                speaker=self._resolve_speaker(None, source),
                final=final,
                language=language,
                prompt=prompt,
                text_override="",
                signal=signal,
                interview_session_id=interview_session_id,
                auto_tick_offset_s=auto_tick_offset_s,
                turn_id="",
            )

        if candidate_duration_ms < self.settings.bridge_target_duration_ms and signal.voiced_frames > 0:
            source_state.buffered_frames = candidate_frames
            source_state.buffered_duration_ms = candidate_duration_ms
            return {
                "session": session_snapshot,
                "skipped": True,
                "reason": (
                    f"buffering short speech chunk: {candidate_duration_ms:.1f}ms < "
                    f"{self.settings.bridge_target_duration_ms:.1f}ms"
                ),
                "drained_frames": len(new_frames),
                "signal": signal.to_dict(),
            }

        if not signal.passed:
            if candidate_duration_ms >= self.settings.bridge_max_buffer_ms:
                source_state.buffered_frames = []
                source_state.buffered_duration_ms = 0.0
                return {
                    "session": session_snapshot,
                    "skipped": True,
                    "reason": (
                        f"buffer dropped after {candidate_duration_ms:.1f}ms without passing the adaptive gate"
                    ),
                    "drained_frames": len(new_frames),
                    "signal": signal.to_dict(),
                }

            if signal.voiced_frames > 0:
                source_state.buffered_frames = candidate_frames
                source_state.buffered_duration_ms = candidate_duration_ms
            else:
                source_state.buffered_frames = []
                source_state.buffered_duration_ms = 0.0
            return {
                "session": session_snapshot,
                "skipped": True,
                "reason": signal.reason,
                "drained_frames": len(new_frames),
                "signal": signal.to_dict(),
            }

        source_state.buffered_frames = []
        source_state.buffered_duration_ms = 0.0
        if use_realtime:
            return self._enqueue_realtime_chunk(
                bridge_id=bridge_id,
                session_snapshot=session_snapshot,
                config_snapshot=config_snapshot,
                frames=candidate_frames,
                source=source,
                final=final,
                language=language,
                prompt=prompt,
                signal=signal,
                interview_session_id=interview_session_id,
                auto_tick_offset_s=auto_tick_offset_s,
                turn_id="",
            )
        return self._transcribe_frames(
            session_snapshot=session_snapshot,
            config_snapshot=config_snapshot,
            frames=candidate_frames,
            source=source,
            speaker=self._resolve_speaker(None, source),
            final=final,
            language=language,
            prompt=prompt,
            text_override="",
            signal=signal,
            interview_session_id=interview_session_id,
            auto_tick_offset_s=auto_tick_offset_s,
            turn_id="",
        )

    def _collect_pending_answers(self, bridge_id: str) -> None:
        if self.interview_service is None:
            return

        with self._lock:
            bridge = self.bridges.get(bridge_id)
            if bridge is None or not bridge.interview_session_id or not bridge.pending_turn_ids:
                return
            interview_session_id = bridge.interview_session_id
            pending_turn_ids = list(bridge.pending_turn_ids)

        completed_turn_ids: list[str] = []
        for turn_id in pending_turn_ids:
            try:
                answer = self.interview_service.get_answer(interview_session_id, turn_id)
            except KeyError:
                completed_turn_ids.append(turn_id)
                continue

            with self._lock:
                bridge = self.bridges.get(bridge_id)
                if bridge is None:
                    return
                bridge.last_answer = copy.deepcopy(answer)
                if answer.get("status") in {"complete", "failed"}:
                    completed_turn_ids.append(turn_id)

        if not completed_turn_ids:
            return

        with self._lock:
            bridge = self.bridges.get(bridge_id)
            if bridge is None:
                return
            bridge.pending_turn_ids = [item for item in bridge.pending_turn_ids if item not in completed_turn_ids]

    def _flush_live_bridge_buffers(self, bridge_id: str) -> list[dict[str, Any]]:
        with self._lock:
            bridge = self.bridges.get(bridge_id)
            if bridge is None:
                return []
            bridge_snapshot = {
                "audio_session_id": bridge.audio_session_id,
                "interview_session_id": bridge.interview_session_id,
                "language": bridge.language,
                "prompt": bridge.prompt,
                "final": bridge.final,
                "auto_tick_offset_s": bridge.auto_tick_offset_s,
                "source_state": dict(bridge.source_state),
                "use_realtime": bridge.active_asr_mode == "realtime",
            }

        results: list[dict[str, Any]] = []
        for source_key, source_state in bridge_snapshot["source_state"].items():
            if not source_state.buffered_frames:
                continue

            source = AudioSource(source_key)
            session_snapshot = self.audio_sessions.get_session(bridge_snapshot["audio_session_id"])
            config_dict = session_snapshot["config"]
            config_snapshot = AudioCaptureConfig(
                transport=str(config_dict["transport"]),
                backend=str(config_dict["backend"]),
                sample_rate=int(config_dict["sample_rate"]),
                chunk_ms=int(config_dict["chunk_ms"]),
                channels=int(config_dict.get("channels", 1)),
                sample_width_bytes=int(config_dict.get("sample_width_bytes", 2)),
                max_queue_frames=int(config_dict.get("max_queue_frames", 128)),
                system_device=None,
                mic_device=None,
            )
            candidate_frames = list(source_state.buffered_frames)
            duration_ms = self._buffer_duration_ms(candidate_frames, config_snapshot)
            signal = self._analyze_signal(
                candidate_frames,
                config_snapshot,
                duration_ms=duration_ms,
                threshold=self._effective_threshold(source_state),
                min_duration_ms=self.settings.min_duration_ms,
                noise_floor_rms=source_state.noise_floor_rms,
            )
            if not signal.passed:
                continue

            with self._lock:
                bridge = self.bridges.get(bridge_id)
                if bridge is None:
                    return results
                bridge.source_state[source.value].buffered_frames = []
                bridge.source_state[source.value].buffered_duration_ms = 0.0

            if bridge_snapshot["use_realtime"]:
                results.append(
                    self._enqueue_realtime_chunk(
                        bridge_id=bridge_id,
                        session_snapshot=session_snapshot,
                        config_snapshot=config_snapshot,
                        frames=candidate_frames,
                        source=source,
                        final=bool(bridge_snapshot["final"]),
                        language=str(bridge_snapshot["language"]),
                        prompt=str(bridge_snapshot["prompt"]),
                        signal=signal,
                        interview_session_id=str(bridge_snapshot["interview_session_id"]),
                        auto_tick_offset_s=float(bridge_snapshot["auto_tick_offset_s"]),
                        turn_id="",
                    )
                )
                continue

            results.append(
                self._transcribe_frames(
                    session_snapshot=session_snapshot,
                    config_snapshot=config_snapshot,
                    frames=candidate_frames,
                    source=source,
                    speaker=self._resolve_speaker(None, source),
                    final=bool(bridge_snapshot["final"]),
                    language=str(bridge_snapshot["language"]),
                    prompt=str(bridge_snapshot["prompt"]),
                    text_override="",
                    signal=signal,
                    interview_session_id=str(bridge_snapshot["interview_session_id"]),
                    auto_tick_offset_s=float(bridge_snapshot["auto_tick_offset_s"]),
                    turn_id="",
                )
            )
        return results

    def _ensure_realtime_streams(self, bridge_id: str) -> None:
        if not self.settings.use_realtime_stream:
            return
        with self._lock:
            if bridge_id in self._bridge_streams:
                return
            bridge = self.bridges[bridge_id]
            bridge_language = bridge.language
            bridge_prompt = bridge.prompt
            sources = list(bridge.sources)

        created_streams: dict[str, RealtimeTranscriptionStream] = {}
        try:
            for source in sources:
                stream = self._realtime_stream_factory(
                    self.settings,
                    source,
                    bridge_language,
                    bridge_prompt,
                )
                stream.start()
                created_streams[source.value] = stream
        except Exception:
            for stream in created_streams.values():
                stream.close()
            raise

        with self._lock:
            self._bridge_streams[bridge_id] = created_streams

    def _maybe_prepare_realtime_streams(self, bridge_id: str) -> None:
        if not self.settings.use_realtime_stream:
            return
        try:
            self._ensure_realtime_streams(bridge_id)
        except Exception as exc:
            self._fallback_bridge_to_chunk(bridge_id, str(exc))

    def _poll_bridge_streams(self, bridge_id: str) -> list[dict[str, Any]]:
        with self._lock:
            bridge = self.bridges.get(bridge_id)
            use_realtime = bridge is not None and bridge.active_asr_mode == "realtime"
        if not use_realtime:
            return []
        with self._lock:
            streams = list(self._bridge_streams.get(bridge_id, {}).values())
        results: list[dict[str, Any]] = []
        try:
            for stream in streams:
                for event in stream.poll_partials(limit=8):
                    results.append(self._build_realtime_partial_result(event))
                for event in stream.poll_completed(limit=6):
                    results.append(self._build_realtime_result(event))
        except Exception as exc:
            self._fallback_bridge_to_chunk(bridge_id, str(exc))
            return []
        return results

    def _drain_bridge_streams(self, bridge_id: str, *, timeout_s: float) -> list[dict[str, Any]]:
        with self._lock:
            bridge = self.bridges.get(bridge_id)
            use_realtime = bridge is not None and bridge.active_asr_mode == "realtime"
        if not use_realtime:
            return []
        deadline = time.perf_counter() + max(0.0, timeout_s)
        results: list[dict[str, Any]] = []
        while time.perf_counter() < deadline:
            cycle_results = self._poll_bridge_streams(bridge_id)
            if cycle_results:
                results.extend(cycle_results)
                continue
            time.sleep(0.05)
        results.extend(self._poll_bridge_streams(bridge_id))
        return results

    def _close_bridge_streams(self, bridge_id: str) -> None:
        with self._lock:
            streams = self._bridge_streams.pop(bridge_id, {})
        for stream in streams.values():
            stream.close()

    def _fallback_bridge_to_chunk(self, bridge_id: str, reason: str) -> None:
        self._close_bridge_streams(bridge_id)
        with self._lock:
            bridge = self.bridges.get(bridge_id)
            if bridge is None:
                return
            bridge.active_asr_mode = "chunk"
            bridge.realtime_fallback_reason = reason
            bridge.partial_transcripts.clear()
            for source_state in bridge.source_state.values():
                source_state.partial_text = ""
                source_state.partial_updated_at = None

    def _enqueue_realtime_chunk(
        self,
        *,
        bridge_id: str,
        session_snapshot: dict[str, Any],
        config_snapshot: AudioCaptureConfig,
        frames: list[AudioFrameEnvelope],
        source: AudioSource,
        final: bool,
        language: str,
        prompt: str,
        signal: SignalGateStats,
        interview_session_id: str,
        auto_tick_offset_s: float,
        turn_id: str,
    ) -> dict[str, Any]:
        self._ensure_realtime_streams(bridge_id)
        with self._lock:
            stream = self._bridge_streams[bridge_id][source.value]
        ts_start, ts_end, duration_ms = self._frame_window(frames, config_snapshot)
        metadata = RealtimeChunkMetadata(
            source=source,
            speaker=self._resolve_speaker(None, source),
            final=final,
            ts_start=ts_start,
            ts_end=ts_end,
            duration_ms=duration_ms,
            num_frames=len(frames),
            language=language,
            prompt=prompt,
            session_snapshot=copy.deepcopy(session_snapshot),
            signal=signal.to_dict(),
            interview_session_id=interview_session_id,
            auto_tick_offset_s=auto_tick_offset_s,
            turn_id=turn_id,
        )
        try:
            stream.enqueue_chunk(
                pcm=b"".join(item.frame.pcm for item in frames),
                sample_rate=config_snapshot.sample_rate,
                channels=config_snapshot.channels,
                sample_width_bytes=config_snapshot.sample_width_bytes,
                metadata=metadata,
            )
        except Exception as exc:
            return {
                "session": session_snapshot,
                "failed": True,
                "reason": str(exc),
                "drained_frames": len(frames),
                "signal": signal.to_dict(),
            }
        return {
            "session": session_snapshot,
            "queued": True,
            "drained_frames": len(frames),
            "signal": signal.to_dict(),
            "source": source.value,
        }

    def _build_realtime_result(self, event: RealtimeTranscriptEvent) -> dict[str, Any]:
        if event.error:
            return {
                "session": event.metadata.session_snapshot,
                "failed": True,
                "reason": event.error,
                "drained_frames": event.metadata.num_frames,
                "signal": copy.deepcopy(event.metadata.signal),
            }
        transcript = TranscriptionResult(
            provider=event.provider,
            model=event.model,
            source=event.metadata.source,
            speaker=event.metadata.speaker,
            text=event.text,
            confidence=event.confidence,
            language=event.language,
            final=event.metadata.final,
            ts_start=event.metadata.ts_start,
            ts_end=event.metadata.ts_end,
            duration_ms=event.metadata.duration_ms,
            num_frames=event.metadata.num_frames,
            response_ms=event.response_ms,
            notes=event.notes,
        )
        return self._finalize_transcript_result(
            session_snapshot=copy.deepcopy(event.metadata.session_snapshot),
            transcript=transcript,
            signal=copy.deepcopy(event.metadata.signal),
            drained_frames=event.metadata.num_frames,
            interview_session_id=event.metadata.interview_session_id,
            auto_tick_offset_s=event.metadata.auto_tick_offset_s,
            turn_id=event.metadata.turn_id,
        )

    def _build_realtime_partial_result(self, event: RealtimeTranscriptDeltaEvent) -> dict[str, Any]:
        return {
            "session": copy.deepcopy(event.metadata.session_snapshot),
            "partial": True,
            "signal": copy.deepcopy(event.metadata.signal),
            "transcript": {
                "provider": event.provider,
                "model": event.model,
                "source": event.metadata.source.value,
                "speaker": event.metadata.speaker.value,
                "item_id": event.item_id,
                "text": event.text,
                "language": event.language,
                "updated_at": event.updated_at,
            },
        }

    def _update_noise_floor(
        self,
        source_state: BridgeSourceState,
        frames: list[AudioFrameEnvelope],
        config: AudioCaptureConfig,
    ) -> None:
        if not frames:
            return
        energies = [self._frame_rms(item.frame.pcm, config.sample_width_bytes) for item in frames]
        avg_rms = sum(energies) / len(energies) if energies else 0.0
        peak_rms = max(energies) if energies else 0.0
        source_state.recent_avg_rms = avg_rms
        source_state.recent_peak_rms = peak_rms

        if not self.settings.adaptive_gate_enabled or avg_rms <= 0.0:
            source_state.adaptive_threshold = self.settings.energy_threshold
            return

        baseline_threshold = self._effective_threshold(source_state)
        if peak_rms < baseline_threshold:
            if source_state.noise_floor_rms <= 0.0:
                source_state.noise_floor_rms = avg_rms
            else:
                alpha = min(max(self.settings.noise_floor_alpha, 0.01), 0.95)
                source_state.noise_floor_rms = (
                    (1.0 - alpha) * source_state.noise_floor_rms
                    + alpha * avg_rms
                )
        source_state.adaptive_threshold = self._effective_threshold(source_state)

    def _effective_threshold(self, source_state: BridgeSourceState) -> float:
        if not self.settings.adaptive_gate_enabled:
            return self.settings.energy_threshold
        floor_threshold = self.settings.energy_threshold * self.settings.adaptive_floor_ratio
        return max(
            floor_threshold,
            source_state.noise_floor_rms * self.settings.adaptive_multiplier,
        )

    def _buffer_duration_ms(
        self,
        frames: list[AudioFrameEnvelope],
        config: AudioCaptureConfig,
    ) -> float:
        if not frames:
            return 0.0
        _, _, duration_ms = self._frame_window(frames, config)
        return duration_ms

    @staticmethod
    def _build_provider(
        settings: TranscriptionSettings,
        realtime_stream_factory: Callable[
            [TranscriptionSettings, AudioSource, str, str],
            RealtimeTranscriptionStream,
        ],
    ) -> TranscriptionProvider:
        if settings.use_alibaba_realtime:
            return AlibabaRealtimeChunkTranscriptionProvider(settings, realtime_stream_factory)
        if settings.use_openai:
            return OpenAITranscriptionProvider(settings)
        return TemplateTranscriptionProvider()

    @staticmethod
    def _default_realtime_stream_factory(
        settings: TranscriptionSettings,
        source: AudioSource,
        language: str,
        prompt: str,
    ) -> RealtimeTranscriptionStream:
        if settings.use_alibaba_realtime:
            return AlibabaRealtimeTranscriptionStream(
                settings,
                source=source,
                language=language,
                prompt=prompt,
            )
        return OpenAIRealtimeTranscriptionStream(
            settings,
            source=source,
            language=language,
            prompt=prompt,
        )

    @staticmethod
    def _parse_sources(raw_sources: Any) -> list[AudioSource]:
        if not raw_sources:
            raw_sources = [AudioSource.SYSTEM.value, AudioSource.MIC.value]
        if isinstance(raw_sources, str):
            raw_sources = [item.strip() for item in raw_sources.split(",") if item.strip()]
        sources: list[AudioSource] = []
        seen: set[AudioSource] = set()
        for item in raw_sources:
            source = AudioSource(str(item))
            if source not in seen:
                sources.append(source)
                seen.add(source)
        return sources or [AudioSource.SYSTEM, AudioSource.MIC]

    @staticmethod
    def _resolve_speaker(raw_speaker: Any, source: AudioSource) -> Speaker:
        if raw_speaker:
            return Speaker(str(raw_speaker))
        return Speaker.INTERVIEWER if source == AudioSource.SYSTEM else Speaker.CANDIDATE

    @staticmethod
    def _frame_window(frames: list[AudioFrameEnvelope], config: AudioCaptureConfig) -> tuple[float, float, float]:
        ts_start = frames[0].frame.ts
        ts_end = frames[-1].frame.ts + (config.chunk_ms / 1000.0)
        duration_ms = max(0.0, (ts_end - ts_start) * 1000)
        return ts_start, ts_end, duration_ms

    @staticmethod
    def _coerce_bool(raw_value: Any, default: bool) -> bool:
        if raw_value is None:
            return default
        if isinstance(raw_value, bool):
            return raw_value
        return str(raw_value).strip().lower() not in {"0", "false", "no", "off"}

    def _analyze_signal(
        self,
        frames: list[AudioFrameEnvelope],
        config: AudioCaptureConfig,
        *,
        duration_ms: float,
        threshold: float,
        min_duration_ms: float,
        noise_floor_rms: float,
    ) -> SignalGateStats:
        pcm = b"".join(item.frame.pcm for item in frames)
        samples = self._pcm_to_samples(pcm, config.sample_width_bytes)
        sample_frames = self._split_samples(
            samples,
            sample_rate=config.sample_rate,
            frame_ms=self.settings.vad_frame_ms,
        )
        if not sample_frames:
            sample_frames = [samples] if samples else []

        frame_rms: list[float] = []
        frame_zcr: list[float] = []
        frame_delta: list[float] = []
        voiced_flags: list[bool] = []
        active = False
        hangover_left = 0

        for frame_samples in sample_frames:
            rms = self._sequence_rms(frame_samples)
            zcr = self._sequence_zcr(frame_samples)
            delta = self._sequence_delta(frame_samples)
            voiced = (
                rms >= threshold
                and zcr <= self.settings.vad_max_zcr
                and delta >= self.settings.vad_min_delta
            )
            if voiced:
                active = True
                hangover_left = self.settings.vad_hangover_frames
            elif active and hangover_left > 0:
                voiced = True
                hangover_left -= 1
            else:
                active = False

            frame_rms.append(rms)
            frame_zcr.append(zcr)
            frame_delta.append(delta)
            voiced_flags.append(voiced)

        avg_rms = sum(frame_rms) / len(frame_rms) if frame_rms else 0.0
        peak_rms = max(frame_rms) if frame_rms else 0.0
        avg_zcr = sum(frame_zcr) / len(frame_zcr) if frame_zcr else 0.0
        peak_zcr = max(frame_zcr) if frame_zcr else 0.0
        avg_delta = sum(frame_delta) / len(frame_delta) if frame_delta else 0.0
        voiced_frames = sum(1 for item in voiced_flags if item)
        total_frames = len(voiced_flags)
        voiced_ratio = (voiced_frames / total_frames) if total_frames else 0.0
        max_speech_run_frames = self._max_true_run(voiced_flags)
        passed = (
            duration_ms >= min_duration_ms
            and voiced_frames >= self.settings.vad_min_speech_frames
            and voiced_ratio >= self.settings.vad_min_voiced_ratio
        )
        reason = "speech-like audio detected"
        if duration_ms < min_duration_ms:
            reason = f"chunk too short for ASR gate: {duration_ms:.1f}ms < {min_duration_ms:.1f}ms"
        elif voiced_frames < self.settings.vad_min_speech_frames:
            reason = (
                f"chunk gated by VAD speech frames: {voiced_frames} < "
                f"{self.settings.vad_min_speech_frames}"
            )
        elif voiced_ratio < self.settings.vad_min_voiced_ratio:
            reason = (
                f"chunk gated by VAD ratio: {voiced_ratio:.2f} < "
                f"{self.settings.vad_min_voiced_ratio:.2f}"
            )
        elif peak_rms < threshold:
            reason = f"chunk gated by low energy: peak_rms={peak_rms:.4f} < threshold={threshold:.4f}"
        elif peak_zcr > self.settings.vad_max_zcr:
            reason = f"chunk gated by noisy zero-crossing: peak_zcr={peak_zcr:.3f}"
        elif avg_delta < self.settings.vad_min_delta:
            reason = f"chunk gated by low waveform motion: avg_delta={avg_delta:.4f}"
        return SignalGateStats(
            avg_rms=avg_rms,
            peak_rms=peak_rms,
            voiced_frames=voiced_frames,
            total_frames=total_frames,
            voiced_ratio=voiced_ratio,
            max_speech_run_frames=max_speech_run_frames,
            duration_ms=duration_ms,
            threshold=threshold,
            noise_floor_rms=noise_floor_rms,
            avg_zcr=avg_zcr,
            peak_zcr=peak_zcr,
            avg_delta=avg_delta,
            frame_ms=self.settings.vad_frame_ms,
            passed=passed,
            reason=reason,
        )

    @staticmethod
    def _max_true_run(flags: list[bool]) -> int:
        best = 0
        current = 0
        for item in flags:
            if item:
                current += 1
                best = max(best, current)
            else:
                current = 0
        return best

    @staticmethod
    def _split_samples(samples: list[float], *, sample_rate: int, frame_ms: int) -> list[list[float]]:
        if not samples:
            return []
        frame_size = max(1, int(sample_rate * frame_ms / 1000))
        return [samples[index : index + frame_size] for index in range(0, len(samples), frame_size)]

    @staticmethod
    def _sequence_rms(samples: list[float]) -> float:
        if not samples:
            return 0.0
        return math.sqrt(sum(value * value for value in samples) / len(samples))

    @staticmethod
    def _sequence_zcr(samples: list[float]) -> float:
        if len(samples) < 2:
            return 0.0
        crossings = 0
        prev = samples[0]
        for current in samples[1:]:
            if (prev >= 0.0 and current < 0.0) or (prev < 0.0 and current >= 0.0):
                crossings += 1
            prev = current
        return crossings / (len(samples) - 1)

    @staticmethod
    def _sequence_delta(samples: list[float]) -> float:
        if len(samples) < 2:
            return 0.0
        return sum(abs(current - prev) for prev, current in zip(samples, samples[1:])) / (len(samples) - 1)

    @staticmethod
    def _pcm_to_samples(pcm: bytes, sample_width_bytes: int) -> list[float]:
        if not pcm:
            return []
        if sample_width_bytes == 2:
            usable = len(pcm) - (len(pcm) % 2)
            return [
                int.from_bytes(pcm[index : index + 2], byteorder="little", signed=True) / 32768.0
                for index in range(0, usable, 2)
            ]
        if sample_width_bytes == 1:
            return [(value - 128) / 128.0 for value in pcm]
        return []

    @staticmethod
    def _frame_rms(pcm: bytes, sample_width_bytes: int) -> float:
        if not pcm:
            return 0.0
        if sample_width_bytes == 2:
            usable = len(pcm) - (len(pcm) % 2)
            if usable <= 0:
                return 0.0
            total = 0.0
            count = 0
            for index in range(0, usable, 2):
                sample = int.from_bytes(pcm[index : index + 2], byteorder="little", signed=True)
                total += float(sample * sample)
                count += 1
            if count == 0:
                return 0.0
            return math.sqrt(total / count) / 32768.0
        if sample_width_bytes == 1:
            total = 0.0
            for value in pcm:
                centered = value - 128
                total += float(centered * centered)
            return math.sqrt(total / len(pcm)) / 128.0
        return 0.0
