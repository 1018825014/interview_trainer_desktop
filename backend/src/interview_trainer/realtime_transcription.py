from __future__ import annotations

import base64
import json
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.parse import quote
from uuid import uuid4

try:  # pragma: no cover - optional dependency
    import websocket
except ImportError:  # pragma: no cover - optional dependency
    websocket = None

from .config import TranscriptionSettings
from .types import AudioSource, Speaker


@dataclass(slots=True)
class RealtimeChunkMetadata:
    source: AudioSource
    speaker: Speaker
    final: bool
    ts_start: float
    ts_end: float
    duration_ms: float
    num_frames: int
    language: str
    prompt: str
    session_snapshot: dict[str, Any]
    signal: dict[str, Any]
    interview_session_id: str
    auto_tick_offset_s: float
    turn_id: str
    enqueued_at: float = field(default_factory=time.perf_counter)


@dataclass(slots=True)
class RealtimeTranscriptEvent:
    provider: str
    model: str
    metadata: RealtimeChunkMetadata
    text: str
    confidence: float
    language: str
    notes: list[str]
    response_ms: float
    error: str = ""


@dataclass(slots=True)
class RealtimeTranscriptDeltaEvent:
    provider: str
    model: str
    metadata: RealtimeChunkMetadata
    item_id: str
    delta: str
    text: str
    language: str
    updated_at: float = field(default_factory=time.time)


class RealtimeTranscriptionStream(Protocol):
    provider_name: str
    model_name: str

    def start(self) -> None: ...

    def enqueue_chunk(
        self,
        *,
        pcm: bytes,
        sample_rate: int,
        channels: int,
        sample_width_bytes: int,
        metadata: RealtimeChunkMetadata,
    ) -> None: ...

    def poll_partials(self, *, limit: int = 8) -> list[RealtimeTranscriptDeltaEvent]: ...

    def poll_completed(self, *, limit: int = 8) -> list[RealtimeTranscriptEvent]: ...

    def close(self) -> None: ...


class OpenAIRealtimeTranscriptionStream:
    provider_name = "openai_realtime"

    def __init__(
        self,
        settings: TranscriptionSettings,
        *,
        source: AudioSource,
        language: str,
        prompt: str,
    ) -> None:
        self.settings = settings
        self.source = source
        self.language = language
        self.prompt = prompt
        self.model_name = settings.model
        self._socket: Any | None = None
        self._pending_commits: deque[RealtimeChunkMetadata] = deque()
        self._pending_by_item_id: dict[str, RealtimeChunkMetadata] = {}
        self._partial_text_by_item_id: dict[str, str] = {}
        self._partials: deque[RealtimeTranscriptDeltaEvent] = deque()
        self._completed: deque[RealtimeTranscriptEvent] = deque()

    def start(self) -> None:
        if self._socket is not None:
            return
        if websocket is None:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "websocket-client is not installed. Run `python -m pip install \".[realtime]\"` in backend."
            )

        headers = [f"Authorization: Bearer {self.settings.openai_api_key}"]
        if self.settings.realtime_beta_header:
            headers.append(f"OpenAI-Beta: {self.settings.realtime_beta_header}")
        try:  # pragma: no cover - network branch
            self._socket = websocket.create_connection(
                self._build_realtime_url(),
                header=headers,
                timeout=self.settings.realtime_connect_timeout_s,
                enable_multithread=True,
            )
            self._socket.settimeout(self.settings.realtime_receive_timeout_s)
            self._send_json(
                {
                    "type": "session.update",
                    "session": self._build_session_payload(),
                }
            )
            self._drain_socket(max_events=8, max_wait_s=0.25)
        except Exception as exc:  # pragma: no cover - network branch
            self.close()
            raise RuntimeError(f"OpenAI realtime connection failed: {exc}") from exc

    def enqueue_chunk(
        self,
        *,
        pcm: bytes,
        sample_rate: int,
        channels: int,
        sample_width_bytes: int,
        metadata: RealtimeChunkMetadata,
    ) -> None:
        self.start()
        encoded_audio = base64.b64encode(
            self._prepare_pcm_bytes(
                pcm,
                sample_rate=sample_rate,
                channels=channels,
                sample_width_bytes=sample_width_bytes,
                target_rate=self.settings.realtime_input_sample_rate,
            )
        ).decode("ascii")
        self._pending_commits.append(metadata)
        self._send_json({"type": "input_audio_buffer.append", "audio": encoded_audio})
        self._send_json({"type": "input_audio_buffer.commit"})
        self._drain_socket(max_events=4, max_wait_s=0.05)

    def poll_completed(self, *, limit: int = 8) -> list[RealtimeTranscriptEvent]:
        self.start()
        self._drain_socket(max_events=max(8, limit * 4), max_wait_s=0.05)
        results: list[RealtimeTranscriptEvent] = []
        while self._completed and len(results) < limit:
            results.append(self._completed.popleft())
        return results

    def poll_partials(self, *, limit: int = 8) -> list[RealtimeTranscriptDeltaEvent]:
        self.start()
        self._drain_socket(max_events=max(8, limit * 4), max_wait_s=0.05)
        results: list[RealtimeTranscriptDeltaEvent] = []
        while self._partials and len(results) < limit:
            results.append(self._partials.popleft())
        return results

    def close(self) -> None:
        socket = self._socket
        self._socket = None
        if socket is None:
            return
        try:  # pragma: no cover - cleanup branch
            socket.close()
        except Exception:
            pass

    def _build_session_payload(self) -> dict[str, Any]:
        transcription: dict[str, Any] = {"model": self.settings.model}
        if self.language:
            transcription["language"] = self.language
        if self.prompt:
            transcription["prompt"] = self.prompt
        return {
            "type": "transcription",
            "audio": {
                "input": {
                    "format": {
                        "type": "audio/pcm",
                        "rate": self.settings.realtime_input_sample_rate,
                    },
                    "transcription": transcription,
                    "noise_reduction": {
                        "type": "far_field" if self.source == AudioSource.SYSTEM else "near_field"
                    },
                }
            },
            "include": ["item.input_audio_transcription.logprobs"],
        }

    def _build_realtime_url(self) -> str:
        if self.settings.realtime_ws_url:
            if "{model}" in self.settings.realtime_ws_url:
                return self.settings.realtime_ws_url.format(model=quote(self.settings.model, safe=""))
            return self.settings.realtime_ws_url
        base = self.settings.openai_base_url.rstrip("/")
        if base.startswith("https://"):
            base = "wss://" + base[len("https://") :]
        elif base.startswith("http://"):
            base = "ws://" + base[len("http://") :]
        return f"{base}/realtime?model={quote(self.settings.model, safe='')}"

    def _send_json(self, payload: dict[str, Any]) -> None:
        if self._socket is None:
            raise RuntimeError("OpenAI realtime socket is not connected.")
        self._socket.send(json.dumps(payload))

    def _drain_socket(self, *, max_events: int, max_wait_s: float) -> None:
        if self._socket is None:
            return
        deadline = time.perf_counter() + max_wait_s
        seen = 0
        while seen < max_events:
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                break
            try:
                self._socket.settimeout(min(self.settings.realtime_receive_timeout_s, max(0.01, remaining)))
                raw = self._socket.recv()
            except Exception as exc:  # pragma: no cover - optional dependency / network branch
                timeout_exc = getattr(websocket, "WebSocketTimeoutException", None)
                if timeout_exc is not None and isinstance(exc, timeout_exc):
                    break
                raise RuntimeError(f"OpenAI realtime receive failed: {exc}") from exc
            if not raw:
                break
            seen += 1
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            self._handle_event(event)

    def _handle_event(self, event: dict[str, Any]) -> None:
        event_type = str(event.get("type") or "")
        if not event_type:
            return
        if event_type == "error":  # pragma: no cover - network branch
            error_payload = event.get("error") or {}
            raise RuntimeError(str(error_payload.get("message") or "unknown realtime error"))
        if event_type == "input_audio_buffer.committed":
            item_id = str(event.get("item_id") or "").strip()
            if item_id and self._pending_commits:
                self._pending_by_item_id[item_id] = self._pending_commits.popleft()
                self._emit_partial_event(item_id=item_id, delta="", force_existing=True)
            return
        if event_type == "conversation.item.input_audio_transcription.delta":
            item_id = str(event.get("item_id") or "").strip()
            delta = str(event.get("delta") or "")
            if item_id:
                self._partial_text_by_item_id[item_id] = self._partial_text_by_item_id.get(item_id, "") + delta
                self._emit_partial_event(item_id=item_id, delta=delta)
            return
        if event_type == "conversation.item.input_audio_transcription.completed":
            item_id = str(event.get("item_id") or "").strip()
            metadata = self._pending_by_item_id.pop(item_id, None)
            if metadata is None:
                return
            transcript_text = str(event.get("transcript") or "").strip()
            logprobs = event.get("logprobs")
            self._partial_text_by_item_id.pop(item_id, None)
            self._completed.append(
                RealtimeTranscriptEvent(
                    provider=self.provider_name,
                    model=self.model_name,
                    metadata=metadata,
                    text=transcript_text,
                    confidence=self._confidence_from_logprobs(logprobs),
                    language=str(event.get("language") or metadata.language or self.language or "unknown"),
                    notes=["Streaming transcription via OpenAI Realtime API."],
                    response_ms=(time.perf_counter() - metadata.enqueued_at) * 1000,
                )
            )
            return
        if event_type == "conversation.item.input_audio_transcription.failed":
            item_id = str(event.get("item_id") or "").strip()
            metadata = self._pending_by_item_id.pop(item_id, None)
            if metadata is None:
                return
            error_payload = event.get("error") or {}
            self._partial_text_by_item_id.pop(item_id, None)
            self._completed.append(
                RealtimeTranscriptEvent(
                    provider=self.provider_name,
                    model=self.model_name,
                    metadata=metadata,
                    text="",
                    confidence=0.0,
                    language=str(metadata.language or self.language or "unknown"),
                    notes=["OpenAI Realtime API returned a transcription failure."],
                    response_ms=(time.perf_counter() - metadata.enqueued_at) * 1000,
                    error=str(error_payload.get("message") or "realtime transcription failed"),
                )
            )

    def _emit_partial_event(self, *, item_id: str, delta: str, force_existing: bool = False) -> None:
        metadata = self._pending_by_item_id.get(item_id)
        current_text = self._partial_text_by_item_id.get(item_id, "").strip()
        if metadata is None:
            return
        if not force_existing and not delta:
            return
        if not current_text:
            return
        self._partials.append(
            RealtimeTranscriptDeltaEvent(
                provider=self.provider_name,
                model=self.model_name,
                metadata=metadata,
                item_id=item_id,
                delta=delta,
                text=current_text,
                language=metadata.language or self.language or "unknown",
            )
        )

    @staticmethod
    def _confidence_from_logprobs(logprobs: Any) -> float:
        if not isinstance(logprobs, list) or not logprobs:
            return 0.92
        values: list[float] = []
        for item in logprobs:
            if isinstance(item, dict) and "logprob" in item:
                try:
                    values.append(float(item["logprob"]))
                except (TypeError, ValueError):
                    continue
        if not values:
            return 0.92
        return min(0.99, max(0.01, math.exp(sum(values) / len(values))))

    @classmethod
    def _prepare_pcm_bytes(
        cls,
        pcm: bytes,
        *,
        sample_rate: int,
        channels: int,
        sample_width_bytes: int,
        target_rate: int,
    ) -> bytes:
        if sample_width_bytes == 2 and channels == 1 and sample_rate == target_rate:
            return pcm
        samples = cls._pcm_bytes_to_mono_floats(pcm, channels=channels, sample_width_bytes=sample_width_bytes)
        resampled = cls._resample_linear(samples, from_rate=sample_rate, to_rate=target_rate)
        return cls._floats_to_pcm16(resampled)

    @staticmethod
    def _pcm_bytes_to_mono_floats(pcm: bytes, *, channels: int, sample_width_bytes: int) -> list[float]:
        if not pcm:
            return []
        raw_samples: list[float] = []
        if sample_width_bytes == 2:
            usable = len(pcm) - (len(pcm) % 2)
            raw_samples = [
                int.from_bytes(pcm[index : index + 2], byteorder="little", signed=True) / 32768.0
                for index in range(0, usable, 2)
            ]
        elif sample_width_bytes == 1:
            raw_samples = [(value - 128) / 128.0 for value in pcm]
        if channels <= 1 or not raw_samples:
            return raw_samples
        mono: list[float] = []
        stride = max(1, channels)
        for index in range(0, len(raw_samples) - (len(raw_samples) % stride), stride):
            frame = raw_samples[index : index + stride]
            mono.append(sum(frame) / len(frame))
        return mono

    @staticmethod
    def _resample_linear(samples: list[float], *, from_rate: int, to_rate: int) -> list[float]:
        if not samples or from_rate <= 0 or to_rate <= 0 or from_rate == to_rate:
            return list(samples)
        target_length = max(1, int(round(len(samples) * to_rate / from_rate)))
        if len(samples) == 1:
            return [samples[0]] * target_length
        scale = (len(samples) - 1) / max(1, target_length - 1)
        output: list[float] = []
        for index in range(target_length):
            position = index * scale
            left = int(position)
            right = min(left + 1, len(samples) - 1)
            fraction = position - left
            output.append((samples[left] * (1.0 - fraction)) + (samples[right] * fraction))
        return output

    @staticmethod
    def _floats_to_pcm16(samples: list[float]) -> bytes:
        payload = bytearray()
        for sample in samples:
            clamped = max(-1.0, min(1.0, sample))
            payload.extend(int(clamped * 32767.0).to_bytes(2, byteorder="little", signed=True))
        return bytes(payload)


class AlibabaRealtimeTranscriptionStream:
    provider_name = "alibaba_realtime"

    def __init__(
        self,
        settings: TranscriptionSettings,
        *,
        source: AudioSource,
        language: str,
        prompt: str,
    ) -> None:
        self.settings = settings
        self.source = source
        self.language = language
        self.prompt = prompt
        self.model_name = settings.model
        self._socket: Any | None = None
        self._pending_by_task_id: dict[str, RealtimeChunkMetadata] = {}
        self._started_task_ids: set[str] = set()
        self._partial_text_by_task_id: dict[str, str] = {}
        self._partials: deque[RealtimeTranscriptDeltaEvent] = deque()
        self._completed: deque[RealtimeTranscriptEvent] = deque()

    def start(self) -> None:
        if self._socket is not None:
            return
        if websocket is None:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "websocket-client is not installed. Run `python -m pip install \".[realtime]\"` in backend."
            )

        headers = [f"Authorization: Bearer {self.settings.alibaba_api_key}"]
        if self.settings.alibaba_workspace:
            headers.append(f"X-DashScope-WorkSpace: {self.settings.alibaba_workspace}")
        try:  # pragma: no cover - network branch
            self._socket = websocket.create_connection(
                self.settings.alibaba_ws_url,
                header=headers,
                timeout=self.settings.realtime_connect_timeout_s,
                enable_multithread=True,
            )
            self._socket.settimeout(self.settings.realtime_receive_timeout_s)
        except Exception as exc:  # pragma: no cover - network branch
            self.close()
            raise RuntimeError(f"Alibaba realtime connection failed: {exc}") from exc

    def enqueue_chunk(
        self,
        *,
        pcm: bytes,
        sample_rate: int,
        channels: int,
        sample_width_bytes: int,
        metadata: RealtimeChunkMetadata,
    ) -> None:
        self.start()
        task_id = str(uuid4())
        prepared_pcm, target_rate = self._prepare_audio_payload(
            pcm,
            sample_rate=sample_rate,
            channels=channels,
            sample_width_bytes=sample_width_bytes,
        )
        self._pending_by_task_id[task_id] = metadata
        self._send_json(self._build_run_task_payload(task_id=task_id, sample_rate=target_rate))
        self._wait_for_task_started(task_id)
        self._send_binary(prepared_pcm)
        self._send_json(
            {
                "header": {
                    "action": "finish-task",
                    "task_id": task_id,
                    "streaming": "duplex",
                },
                "payload": {
                    "input": {},
                },
            }
        )
        self._drain_socket(max_events=6, max_wait_s=0.05)

    def poll_completed(self, *, limit: int = 8) -> list[RealtimeTranscriptEvent]:
        self.start()
        self._drain_socket(max_events=max(8, limit * 4), max_wait_s=0.05)
        results: list[RealtimeTranscriptEvent] = []
        while self._completed and len(results) < limit:
            results.append(self._completed.popleft())
        return results

    def poll_partials(self, *, limit: int = 8) -> list[RealtimeTranscriptDeltaEvent]:
        self.start()
        self._drain_socket(max_events=max(8, limit * 4), max_wait_s=0.05)
        results: list[RealtimeTranscriptDeltaEvent] = []
        while self._partials and len(results) < limit:
            results.append(self._partials.popleft())
        return results

    def close(self) -> None:
        socket = self._socket
        self._socket = None
        if socket is None:
            return
        try:  # pragma: no cover - cleanup branch
            socket.close()
        except Exception:
            pass

    def _prepare_audio_payload(
        self,
        pcm: bytes,
        *,
        sample_rate: int,
        channels: int,
        sample_width_bytes: int,
    ) -> tuple[bytes, int]:
        target_rate = sample_rate if sample_rate in {8000, 16000} else 16000
        prepared_pcm = OpenAIRealtimeTranscriptionStream._prepare_pcm_bytes(
            pcm,
            sample_rate=sample_rate,
            channels=channels,
            sample_width_bytes=sample_width_bytes,
            target_rate=target_rate,
        )
        return prepared_pcm, target_rate

    def _build_run_task_payload(self, *, task_id: str, sample_rate: int) -> dict[str, Any]:
        parameters: dict[str, Any] = {
            "format": "pcm",
            "sample_rate": sample_rate,
            "semantic_punctuation_enabled": True,
        }
        if self.language:
            parameters["language_hints"] = [self.language]
        if self.settings.alibaba_vocabulary_id:
            parameters["vocabulary_id"] = self.settings.alibaba_vocabulary_id
        return {
            "header": {
                "action": "run-task",
                "task_id": task_id,
                "streaming": "duplex",
            },
            "payload": {
                "task_group": "audio",
                "task": "asr",
                "function": "recognition",
                "model": self.settings.model,
                "parameters": parameters,
                "input": {},
            },
        }

    def _wait_for_task_started(self, task_id: str) -> None:
        deadline = time.perf_counter() + 0.8
        while task_id not in self._started_task_ids:
            if task_id not in self._pending_by_task_id:
                raise RuntimeError("Alibaba realtime task ended before it was ready to stream audio.")
            if time.perf_counter() >= deadline:
                raise RuntimeError("Alibaba realtime task did not acknowledge start in time.")
            self._drain_socket(max_events=6, max_wait_s=0.05)

    def _send_json(self, payload: dict[str, Any]) -> None:
        if self._socket is None:
            raise RuntimeError("Alibaba realtime socket is not connected.")
        self._socket.send(json.dumps(payload))

    def _send_binary(self, payload: bytes) -> None:
        if self._socket is None:
            raise RuntimeError("Alibaba realtime socket is not connected.")
        send_binary = getattr(self._socket, "send_binary", None)
        if callable(send_binary):
            send_binary(payload)
            return
        opcode_binary = getattr(getattr(websocket, "ABNF", None), "OPCODE_BINARY", None)
        if opcode_binary is not None:
            self._socket.send(payload, opcode=opcode_binary)
            return
        self._socket.send(payload)

    def _drain_socket(self, *, max_events: int, max_wait_s: float) -> None:
        if self._socket is None:
            return
        deadline = time.perf_counter() + max_wait_s
        seen = 0
        while seen < max_events:
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                break
            try:
                self._socket.settimeout(min(self.settings.realtime_receive_timeout_s, max(0.01, remaining)))
                raw = self._socket.recv()
            except Exception as exc:  # pragma: no cover - optional dependency / network branch
                timeout_exc = getattr(websocket, "WebSocketTimeoutException", None)
                if timeout_exc is not None and isinstance(exc, timeout_exc):
                    break
                raise RuntimeError(f"Alibaba realtime receive failed: {exc}") from exc
            if not raw:
                break
            seen += 1
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="ignore")
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            self._handle_event(event)

    def _handle_event(self, event: dict[str, Any]) -> None:
        header = event.get("header") or {}
        event_type = str(header.get("event") or "").strip()
        if not event_type:
            return
        task_id = str(header.get("task_id") or "").strip()
        if event_type == "task-started":
            if task_id:
                self._started_task_ids.add(task_id)
            return
        if event_type == "task-failed":
            self._handle_failed_task(
                task_id=task_id,
                error_message=str(
                    header.get("error_message")
                    or header.get("error_msg")
                    or event.get("message")
                    or "realtime transcription failed"
                ).strip(),
            )
            return
        if event_type == "result-generated":
            self._handle_result_generated(task_id=task_id, event=event)
            return
        if event_type == "task-finished":
            self._started_task_ids.discard(task_id)
            metadata = self._pending_by_task_id.get(task_id)
            if metadata is None:
                return
            transcript_text = self._partial_text_by_task_id.get(task_id, "").strip()
            if transcript_text:
                self._pending_by_task_id.pop(task_id, None)
                self._partial_text_by_task_id.pop(task_id, None)
                self._completed.append(
                    RealtimeTranscriptEvent(
                        provider=self.provider_name,
                        model=self.model_name,
                        metadata=metadata,
                        text=transcript_text,
                        confidence=0.9,
                        language=metadata.language or self.language or "unknown",
                        notes=["Streaming transcription via Alibaba realtime ASR."],
                        response_ms=(time.perf_counter() - metadata.enqueued_at) * 1000,
                    )
                )

    def _handle_result_generated(self, *, task_id: str, event: dict[str, Any]) -> None:
        metadata = self._pending_by_task_id.get(task_id)
        if metadata is None:
            return
        sentence = (((event.get("payload") or {}).get("output") or {}).get("sentence") or {})
        text = str(sentence.get("text") or "").strip()
        if not text:
            return
        previous_text = self._partial_text_by_task_id.get(task_id, "")
        if text != previous_text:
            delta = text[len(previous_text) :] if previous_text and text.startswith(previous_text) else text
            self._partial_text_by_task_id[task_id] = text
            self._partials.append(
                RealtimeTranscriptDeltaEvent(
                    provider=self.provider_name,
                    model=self.model_name,
                    metadata=metadata,
                    item_id=task_id,
                    delta=delta,
                    text=text,
                    language=metadata.language or self.language or "unknown",
                )
            )

        sentence_end = bool(sentence.get("sentence_end"))
        end_time = sentence.get("end_time")
        if not sentence_end and end_time in {None, ""}:
            return

        self._started_task_ids.discard(task_id)
        self._pending_by_task_id.pop(task_id, None)
        self._partial_text_by_task_id.pop(task_id, None)
        self._completed.append(
            RealtimeTranscriptEvent(
                provider=self.provider_name,
                model=self.model_name,
                metadata=metadata,
                text=text,
                confidence=0.9,
                language=metadata.language or self.language or "unknown",
                notes=["Streaming transcription via Alibaba realtime ASR."],
                response_ms=(time.perf_counter() - metadata.enqueued_at) * 1000,
            )
        )

    def _handle_failed_task(self, *, task_id: str, error_message: str) -> None:
        self._started_task_ids.discard(task_id)
        metadata = self._pending_by_task_id.pop(task_id, None)
        self._partial_text_by_task_id.pop(task_id, None)
        if metadata is None:
            return
        self._completed.append(
            RealtimeTranscriptEvent(
                provider=self.provider_name,
                model=self.model_name,
                metadata=metadata,
                text="",
                confidence=0.0,
                language=metadata.language or self.language or "unknown",
                notes=["Alibaba realtime ASR returned a transcription failure."],
                response_ms=(time.perf_counter() - metadata.enqueued_at) * 1000,
                error=error_message or "realtime transcription failed",
            )
        )
