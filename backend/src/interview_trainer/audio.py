from __future__ import annotations

import base64
import copy
import io
import json
import os
import subprocess
import sys
import threading
import time
import wave
from collections import deque
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Protocol
from uuid import uuid4

from .types import AudioFrame, AudioSource


class NativeAudioWorker(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...


@dataclass(slots=True)
class AudioDeviceInfo:
    name: str
    index: int
    max_input_channels: int
    max_output_channels: int
    hostapi: str
    default_samplerate: float
    is_loopback_candidate: bool


@dataclass(slots=True)
class AudioCapabilities:
    backend: str
    python_package_available: bool
    platform_supported: bool
    supports_loopback: bool
    supports_microphone_capture: bool
    devices: list[AudioDeviceInfo]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "python_package_available": self.python_package_available,
            "platform_supported": self.platform_supported,
            "supports_loopback": self.supports_loopback,
            "supports_microphone_capture": self.supports_microphone_capture,
            "devices": [asdict(item) for item in self.devices],
            "notes": self.notes,
        }


@dataclass(slots=True)
class AudioCapturePlan:
    ready: bool
    backend: str
    system_device: AudioDeviceInfo | None
    mic_device: AudioDeviceInfo | None
    sample_rate: int
    chunk_ms: int
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "backend": self.backend,
            "system_device": asdict(self.system_device) if self.system_device else None,
            "mic_device": asdict(self.mic_device) if self.mic_device else None,
            "sample_rate": self.sample_rate,
            "chunk_ms": self.chunk_ms,
            "notes": self.notes,
        }


@dataclass(slots=True)
class AudioCaptureConfig:
    transport: str
    backend: str
    sample_rate: int
    chunk_ms: int
    channels: int = 1
    sample_width_bytes: int = 2
    max_queue_frames: int = 128
    system_device: AudioDeviceInfo | None = None
    mic_device: AudioDeviceInfo | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "transport": self.transport,
            "backend": self.backend,
            "sample_rate": self.sample_rate,
            "chunk_ms": self.chunk_ms,
            "channels": self.channels,
            "sample_width_bytes": self.sample_width_bytes,
            "max_queue_frames": self.max_queue_frames,
            "system_device": asdict(self.system_device) if self.system_device else None,
            "mic_device": asdict(self.mic_device) if self.mic_device else None,
        }


@dataclass(slots=True)
class AudioFrameEnvelope:
    frame_id: str
    frame: AudioFrame
    sample_rate: int
    chunk_ms: int

    def to_dict(self, *, include_payload: bool = False) -> dict[str, Any]:
        payload = {
            "frame_id": self.frame_id,
            "source": self.frame.source.value,
            "ts": self.frame.ts,
            "num_bytes": len(self.frame.pcm),
            "sample_rate": self.sample_rate,
            "chunk_ms": self.chunk_ms,
        }
        if include_payload:
            payload["pcm_base64"] = base64.b64encode(self.frame.pcm).decode("ascii")
        return payload


@dataclass(slots=True)
class AudioCaptureSession:
    session_id: str
    status: str
    config: AudioCaptureConfig
    plan: AudioCapturePlan
    created_at: float
    notes: list[str] = field(default_factory=list)
    started_at: float | None = None
    stopped_at: float | None = None
    last_frame_ts: float | None = None
    total_frames: int = 0
    dropped_frames: int = 0
    queued_frames: int = 0
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "status": self.status,
            "config": self.config.to_dict(),
            "plan": self.plan.to_dict(),
            "created_at": self.created_at,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "last_frame_ts": self.last_frame_ts,
            "total_frames": self.total_frames,
            "dropped_frames": self.dropped_frames,
            "queued_frames": self.queued_frames,
            "notes": self.notes,
            "error": self.error,
        }


class AudioProbe:
    """Probe local Python audio backends without hard-failing when packages are missing."""

    def probe(self) -> list[AudioCapabilities]:
        return [self._probe_pyaudiowpatch(), self._probe_sounddevice()]

    def recommend(
        self,
        capabilities: list[AudioCapabilities] | None = None,
        *,
        sample_rate: int | None = None,
        chunk_ms: int = 250,
    ) -> AudioCapturePlan:
        capabilities = capabilities or self.probe()
        notes: list[str] = []
        ranked = sorted(
            capabilities,
            key=lambda item: (
                not item.python_package_available,
                not item.supports_loopback,
                item.backend != "pyaudiowpatch",
            ),
        )
        selected = ranked[0] if ranked else None
        if selected is None:
            return AudioCapturePlan(
                ready=False,
                backend="none",
                system_device=None,
                mic_device=None,
                sample_rate=sample_rate,
                chunk_ms=chunk_ms,
                notes=["No usable Python audio backend was detected."],
            )

        system_device = self._select_system_device(selected.devices)
        mic_device = self._select_mic_device(
            selected.devices,
            preferred_hostapi=system_device.hostapi if system_device else "",
            preferred_samplerate=system_device.default_samplerate if system_device else None,
        )
        effective_sample_rate = self._select_sample_rate(
            requested_sample_rate=sample_rate,
            system_device=system_device,
            mic_device=mic_device,
        )
        if not selected.python_package_available:
            notes.append(f"{selected.backend} is not installed yet, so native capture cannot start.")
        if not system_device:
            notes.append("No suitable system loopback device was detected.")
        if not mic_device:
            notes.append("No dedicated microphone input device was detected.")
        if not notes:
            notes.append("Use headphones so system audio and microphone remain separated.")
        notes.extend(selected.notes[:2])
        ready = selected.python_package_available and system_device is not None and mic_device is not None
        return AudioCapturePlan(
            ready=ready,
            backend=selected.backend,
            system_device=system_device,
            mic_device=mic_device,
            sample_rate=effective_sample_rate,
            chunk_ms=chunk_ms,
            notes=notes,
        )

    def _select_system_device(self, devices: list[AudioDeviceInfo]) -> AudioDeviceInfo | None:
        for device in devices:
            if device.is_loopback_candidate and device.max_input_channels > 0:
                return device
        return None

    def _select_mic_device(
        self,
        devices: list[AudioDeviceInfo],
        *,
        preferred_hostapi: str = "",
        preferred_samplerate: float | None = None,
    ) -> AudioDeviceInfo | None:
        candidates = [
            device
            for device in devices
            if device.max_input_channels > 0 and not device.is_loopback_candidate
        ]
        if not candidates:
            return None
        if preferred_hostapi and preferred_samplerate is not None:
            for device in candidates:
                if device.hostapi == preferred_hostapi and int(device.default_samplerate) == int(preferred_samplerate):
                    return device
        if preferred_hostapi:
            for device in candidates:
                if device.hostapi == preferred_hostapi:
                    return device
        return candidates[0]

    def _select_sample_rate(
        self,
        *,
        requested_sample_rate: int | None,
        system_device: AudioDeviceInfo | None,
        mic_device: AudioDeviceInfo | None,
    ) -> int:
        if requested_sample_rate and requested_sample_rate > 0:
            return int(requested_sample_rate)
        if system_device and mic_device and int(system_device.default_samplerate) == int(mic_device.default_samplerate):
            return int(system_device.default_samplerate)
        if system_device and system_device.default_samplerate > 0:
            return int(system_device.default_samplerate)
        if mic_device and mic_device.default_samplerate > 0:
            return int(mic_device.default_samplerate)
        return 16000

    def _probe_pyaudiowpatch(self) -> AudioCapabilities:
        try:
            import pyaudiowpatch as pyaudio  # type: ignore
        except ImportError:
            return AudioCapabilities(
                backend="pyaudiowpatch",
                python_package_available=False,
                platform_supported=True,
                supports_loopback=False,
                supports_microphone_capture=False,
                devices=[],
                notes=[
                    "Install PyAudioWPatch to enumerate WASAPI loopback devices.",
                    "This is the preferred backend for Windows system-audio capture.",
                ],
            )

        devices: list[AudioDeviceInfo] = []
        pa = pyaudio.PyAudio()
        try:
            host_api_count = pa.get_host_api_count()
            hostapi_names: dict[int, str] = {}
            for index in range(host_api_count):
                info = pa.get_host_api_info_by_index(index)
                hostapi_names[index] = info.get("name", f"hostapi-{index}")

            for index in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(index)
                name = str(info.get("name", "device"))
                hostapi_name = hostapi_names.get(info.get("hostApi", -1), "unknown")
                devices.append(
                    AudioDeviceInfo(
                        name=name,
                        index=index,
                        max_input_channels=int(info.get("maxInputChannels", 0)),
                        max_output_channels=int(info.get("maxOutputChannels", 0)),
                        hostapi=hostapi_name,
                        default_samplerate=float(info.get("defaultSampleRate", 0)),
                        is_loopback_candidate="loopback" in name.lower(),
                    )
                )
        finally:
            pa.terminate()

        return AudioCapabilities(
            backend="pyaudiowpatch",
            python_package_available=True,
            platform_supported=True,
            supports_loopback=any(device.is_loopback_candidate for device in devices),
            supports_microphone_capture=any(device.max_input_channels > 0 for device in devices),
            devices=devices,
            notes=[
                "Prefer a WASAPI loopback device for interviewer/system audio.",
                "Use a dedicated microphone input for the candidate channel.",
            ],
        )

    def _probe_sounddevice(self) -> AudioCapabilities:
        try:
            import sounddevice as sd  # type: ignore
        except ImportError:
            return AudioCapabilities(
                backend="sounddevice",
                python_package_available=False,
                platform_supported=True,
                supports_loopback=False,
                supports_microphone_capture=False,
                devices=[],
                notes=[
                    "Install sounddevice if you want an extra device probe backend.",
                    "Windows loopback support still needs explicit WASAPI configuration.",
                ],
            )

        hostapis = sd.query_hostapis()
        devices: list[AudioDeviceInfo] = []
        for index, info in enumerate(sd.query_devices()):
            hostapi_index = int(info.get("hostapi", -1))
            hostapi_name = hostapis[hostapi_index]["name"] if 0 <= hostapi_index < len(hostapis) else "unknown"
            name = str(info.get("name", "device"))
            devices.append(
                AudioDeviceInfo(
                    name=name,
                    index=index,
                    max_input_channels=int(info.get("max_input_channels", 0)),
                    max_output_channels=int(info.get("max_output_channels", 0)),
                    hostapi=hostapi_name,
                    default_samplerate=float(info.get("default_samplerate", 0)),
                    is_loopback_candidate="loopback" in name.lower(),
                )
            )

        return AudioCapabilities(
            backend="sounddevice",
            python_package_available=True,
            platform_supported=True,
            supports_loopback=any(device.is_loopback_candidate for device in devices),
            supports_microphone_capture=any(device.max_input_channels > 0 for device in devices),
            devices=devices,
            notes=[
                "sounddevice is useful for probing devices, but the real Windows loopback path still prefers PyAudioWPatch.",
            ],
        )


def probe_audio_capabilities_safe(*, timeout_s: float = 6.0) -> list[AudioCapabilities]:
    """Probe audio backends in a subprocess to avoid native driver crashes taking down the API server.

    Some PortAudio / WASAPI configurations can trigger process-level crashes (e.g. heap corruption) that
    cannot be caught in Python. Running the probe out-of-process keeps the main server alive.
    """

    # Only do this on Windows by default; elsewhere direct probing is usually stable.
    # Allow override for debugging via env var.
    force_subprocess = os.getenv("INTERVIEW_TRAINER_AUDIO_PROBE_SUBPROCESS", "").strip().lower()
    use_subprocess = sys.platform.startswith("win") and force_subprocess != "0"
    if not use_subprocess:
        return AudioProbe().probe()

    src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    child_env = dict(os.environ)
    existing = child_env.get("PYTHONPATH", "")
    child_env["PYTHONPATH"] = src_dir if not existing else f"{src_dir}{os.pathsep}{existing}"

    code = (
        "import json\n"
        "from interview_trainer.audio import AudioProbe\n"
        "probe = AudioProbe()\n"
        "caps = probe.probe()\n"
        "print(json.dumps({'capabilities': [c.to_dict() for c in caps]}, ensure_ascii=False))\n"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            env=child_env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except Exception:
        # Fall back to in-process (best effort) if subprocess cannot run.
        return AudioProbe().probe()

    if result.returncode != 0:
        # Child crashed or failed; degrade gracefully to "no audio backend" to keep API alive.
        return [
            AudioCapabilities(
                backend="pyaudiowpatch",
                python_package_available=False,
                platform_supported=True,
                supports_loopback=False,
                supports_microphone_capture=False,
                devices=[],
                notes=[
                    "Audio probe failed in a subprocess. This can happen with unstable audio drivers or virtual devices.",
                    "Try selecting a different output/microphone device, or disable native audio capture.",
                ],
            )
        ]

    try:
        payload = json.loads(result.stdout.strip() or "{}")
        raw_caps = payload.get("capabilities", [])
    except Exception:
        raw_caps = []

    capabilities: list[AudioCapabilities] = []
    for item in raw_caps:
        try:
            devices = [
                AudioDeviceInfo(
                    name=str(d.get("name", "")),
                    index=int(d.get("index", -1)),
                    max_input_channels=int(d.get("max_input_channels", 0)),
                    max_output_channels=int(d.get("max_output_channels", 0)),
                    hostapi=str(d.get("hostapi", "")),
                    default_samplerate=float(d.get("default_samplerate", 0)),
                    is_loopback_candidate=bool(d.get("is_loopback_candidate", False)),
                )
                for d in (item.get("devices") or [])
            ]
            capabilities.append(
                AudioCapabilities(
                    backend=str(item.get("backend", "unknown")),
                    python_package_available=bool(item.get("python_package_available", False)),
                    platform_supported=bool(item.get("platform_supported", True)),
                    supports_loopback=bool(item.get("supports_loopback", False)),
                    supports_microphone_capture=bool(item.get("supports_microphone_capture", False)),
                    devices=devices,
                    notes=[str(n) for n in (item.get("notes") or [])],
                )
            )
        except Exception:
            continue

    return capabilities or AudioProbe().probe()


def recommend_audio_plan_safe(
    *,
    sample_rate: int | None = None,
    chunk_ms: int = 250,
    timeout_s: float = 6.0,
) -> AudioCapturePlan:
    capabilities = probe_audio_capabilities_safe(timeout_s=timeout_s)
    return AudioProbe().recommend(capabilities, sample_rate=sample_rate, chunk_ms=chunk_ms)


class PyAudioNativeWorker:
    """Native Windows audio capture using PyAudioWPatch and WASAPI loopback."""

    def __init__(
        self,
        *,
        config: AudioCaptureConfig,
        on_frame: Callable[[AudioSource, bytes, float], None],
        on_error: Callable[[str], None],
    ) -> None:
        self.config = config
        self.on_frame = on_frame
        self.on_error = on_error
        self._stop_event = threading.Event()
        self._started_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._startup_error: str = ""

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._started_event.clear()
        self._startup_error = ""
        self._thread = threading.Thread(target=self._run, name="audio-native-worker", daemon=True)
        self._thread.start()
        self._started_event.wait(timeout=3.0)
        if self._startup_error:
            raise RuntimeError(self._startup_error)
        if not self._started_event.is_set():
            raise RuntimeError("Native audio worker did not complete startup in time.")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

    def _run(self) -> None:
        try:
            import pyaudiowpatch as pyaudio  # type: ignore
        except ImportError:
            self._fail_startup("PyAudioWPatch is not installed.")
            return

        pa = pyaudio.PyAudio()
        try:
            system_info = self._resolve_loopback_device(pa)
            mic_info = self._resolve_mic_device(pa)
            frames_per_buffer = max(1, int(self.config.sample_rate * self.config.chunk_ms / 1000))

            system_stream = pa.open(
                format=pyaudio.paInt16,
                channels=self._resolve_channels(system_info, fallback_channels=self.config.channels),
                rate=int(self.config.sample_rate or system_info.get("defaultSampleRate", 16000)),
                frames_per_buffer=frames_per_buffer,
                input=True,
                input_device_index=int(system_info["index"]),
                stream_callback=self._make_callback(pyaudio, AudioSource.SYSTEM),
            )
            mic_stream = pa.open(
                format=pyaudio.paInt16,
                channels=self._resolve_channels(mic_info, fallback_channels=self.config.channels),
                rate=int(self.config.sample_rate or mic_info.get("defaultSampleRate", 16000)),
                frames_per_buffer=frames_per_buffer,
                input=True,
                input_device_index=int(mic_info["index"]),
                stream_callback=self._make_callback(pyaudio, AudioSource.MIC),
            )
        except Exception as exc:
            pa.terminate()
            self._fail_startup(str(exc))
            return

        try:
            self._started_event.set()
            while not self._stop_event.wait(0.1):
                if not system_stream.is_active():
                    system_stream.start_stream()
                if not mic_stream.is_active():
                    mic_stream.start_stream()
        except Exception as exc:
            self.on_error(str(exc))
        finally:
            for stream in (system_stream, mic_stream):
                try:
                    if stream.is_active():
                        stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            pa.terminate()

    def _make_callback(self, pyaudio_module: Any, source: AudioSource):
        def callback(in_data: bytes, frame_count: int, time_info: dict[str, Any], status_flags: int):
            del frame_count, time_info, status_flags
            if in_data:
                self.on_frame(source, in_data, time.time())
            return (in_data, pyaudio_module.paContinue)

        return callback

    def _resolve_loopback_device(self, pa: Any) -> dict[str, Any]:
        config_device = self.config.system_device
        if config_device and config_device.is_loopback_candidate:
            return pa.get_device_info_by_index(config_device.index)

        if config_device and hasattr(pa, "get_wasapi_loopback_analogue_by_index"):
            try:
                info = pa.get_wasapi_loopback_analogue_by_index(config_device.index)
                if info:
                    return info
            except Exception:
                pass

        if hasattr(pa, "get_default_wasapi_loopback"):
            try:
                info = pa.get_default_wasapi_loopback()
                if info:
                    return info
            except Exception:
                pass

        for index in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(index)
            name = str(info.get("name", ""))
            if "loopback" in name.lower():
                return info
        raise RuntimeError("Could not resolve a loopback device for system audio.")

    def _resolve_mic_device(self, pa: Any) -> dict[str, Any]:
        config_device = self.config.mic_device
        if config_device:
            return pa.get_device_info_by_index(config_device.index)

        for index in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(index)
            if int(info.get("maxInputChannels", 0)) > 0:
                name = str(info.get("name", ""))
                if "loopback" not in name.lower():
                    return info
        raise RuntimeError("Could not resolve a microphone input device.")

    def _resolve_channels(self, device_info: dict[str, Any], *, fallback_channels: int) -> int:
        available = int(device_info.get("maxInputChannels", 0))
        if available <= 0:
            raise RuntimeError(f"Device {device_info.get('name', 'unknown')} has no input channels.")
        return max(1, min(fallback_channels, available))

    def _fail_startup(self, message: str) -> None:
        self._startup_error = message
        self._started_event.set()
        self.on_error(message)


class SubprocessPyAudioWorker:
    """Run native capture in a subprocess to isolate driver crashes from the API server."""

    def __init__(
        self,
        *,
        config: AudioCaptureConfig,
        on_frame: Callable[[AudioSource, bytes, float], None],
        on_error: Callable[[str], None],
    ) -> None:
        self.config = config
        self.on_frame = on_frame
        self.on_error = on_error
        self._stop_event = threading.Event()
        self._started_event = threading.Event()
        self._startup_error: str = ""
        self._proc: subprocess.Popen[str] | None = None
        self._reader_thread: threading.Thread | None = None

    def start(self) -> None:
        if self._proc and self._proc.poll() is None:
            return
        self._stop_event.clear()
        self._started_event.clear()
        self._startup_error = ""

        src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        child_env = dict(os.environ)
        existing = child_env.get("PYTHONPATH", "")
        child_env["PYTHONPATH"] = src_dir if not existing else f"{src_dir}{os.pathsep}{existing}"

        payload = {
            "sample_rate": int(self.config.sample_rate),
            "chunk_ms": int(self.config.chunk_ms),
            "channels": int(self.config.channels),
            "system_device_index": int(self.config.system_device.index) if self.config.system_device else None,
            "mic_device_index": int(self.config.mic_device.index) if self.config.mic_device else None,
        }
        child_env["INTERVIEW_TRAINER_AUDIO_CAPTURE_CONFIG_JSON"] = json.dumps(payload, ensure_ascii=False)

        code = _SUBPROCESS_CAPTURE_CODE
        self._proc = subprocess.Popen(
            [sys.executable, "-u", "-c", code],
            env=child_env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        self._reader_thread = threading.Thread(target=self._read_loop, name="audio-subprocess-reader", daemon=True)
        self._reader_thread.start()

        self._started_event.wait(timeout=4.0)
        if self._startup_error:
            raise RuntimeError(self._startup_error)
        if not self._started_event.is_set():
            raise RuntimeError("Audio capture subprocess did not complete startup in time.")

    def stop(self) -> None:
        self._stop_event.set()
        proc = self._proc
        if proc is None:
            return
        try:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=2.5)
                except Exception:
                    proc.kill()
        except Exception:
            pass
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=2.5)
        self._proc = None

    def _read_loop(self) -> None:
        proc = self._proc
        if proc is None or proc.stdout is None or proc.stderr is None:
            self._startup_error = "Audio subprocess streams are unavailable."
            self._started_event.set()
            self.on_error(self._startup_error)
            return

        def drain_stderr() -> str:
            try:
                return proc.stderr.read() or ""
            except Exception:
                return ""

        try:
            for line in proc.stdout:
                if self._stop_event.is_set():
                    break
                line = line.strip()
                if not line:
                    continue
                if line.startswith("{") and "\"event\"" in line:
                    try:
                        msg = json.loads(line)
                    except Exception:
                        continue
                    event = msg.get("event")
                    if event == "ready":
                        self._started_event.set()
                        continue
                    if event == "error":
                        message = str(msg.get("message", "audio subprocess error"))
                        if not self._started_event.is_set():
                            self._startup_error = message
                            self._started_event.set()
                        self.on_error(message)
                        continue
                if line.startswith("{") and "\"frame\"" in line:
                    try:
                        msg = json.loads(line)
                        frame = msg.get("frame") or {}
                        source = AudioSource(str(frame.get("source", AudioSource.SYSTEM.value)))
                        ts = float(frame.get("ts", time.time()))
                        pcm_b64 = frame.get("pcm_base64", "")
                        if pcm_b64:
                            pcm = base64.b64decode(str(pcm_b64))
                            self.on_frame(source, pcm, ts)
                    except Exception:
                        continue
        finally:
            if not self._started_event.is_set():
                err = drain_stderr().strip()
                self._startup_error = err or "Audio capture subprocess exited before startup."
                self._started_event.set()
                self.on_error(self._startup_error)
            rc = proc.poll()
            if rc is None:
                return
            if rc != 0 and not self._stop_event.is_set():
                err = drain_stderr().strip()
                message = err or f"Audio capture subprocess exited with code {rc}."
                self.on_error(message)


_SUBPROCESS_CAPTURE_CODE = r"""
import base64
import json
import os
import signal
import sys
import threading
import time


def main():
    cfg_json = os.environ.get("INTERVIEW_TRAINER_AUDIO_CAPTURE_CONFIG_JSON", "{}")
    try:
        cfg = json.loads(cfg_json)
    except Exception:
        cfg = {}

    sample_rate = int(cfg.get("sample_rate", 16000))
    chunk_ms = int(cfg.get("chunk_ms", 250))
    channels = int(cfg.get("channels", 1))
    system_index = cfg.get("system_device_index", None)
    mic_index = cfg.get("mic_device_index", None)

    stop_event = threading.Event()

    def handle_signal(_sig, _frame):
        stop_event.set()

    for sig in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None)):
        if sig is not None:
            try:
                signal.signal(sig, handle_signal)
            except Exception:
                pass

    try:
        import pyaudiowpatch as pyaudio  # type: ignore
    except Exception as exc:
        print(json.dumps({"event": "error", "message": f"PyAudioWPatch import failed: {exc}"}, ensure_ascii=False), flush=True)
        return 2

    pa = pyaudio.PyAudio()
    frames_per_buffer = max(1, int(sample_rate * chunk_ms / 1000))

    def resolve_loopback():
        if isinstance(system_index, int):
            info = pa.get_device_info_by_index(system_index)
            name = str(info.get("name", "")).lower()
            if "loopback" in name:
                return info
        if hasattr(pa, "get_default_wasapi_loopback"):
            try:
                info = pa.get_default_wasapi_loopback()
                if info:
                    return info
            except Exception:
                pass
        for idx in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(idx)
            name = str(info.get("name", "")).lower()
            if "loopback" in name:
                return info
        raise RuntimeError("Could not resolve a loopback device.")

    def resolve_mic():
        if isinstance(mic_index, int):
            return pa.get_device_info_by_index(mic_index)
        for idx in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(idx)
            if int(info.get("maxInputChannels", 0)) > 0:
                name = str(info.get("name", "")).lower()
                if "loopback" not in name:
                    return info
        raise RuntimeError("Could not resolve a microphone device.")

    def run_reader(source, stream):
        while not stop_event.is_set():
            try:
                data = stream.read(frames_per_buffer, exception_on_overflow=False)
            except Exception:
                time.sleep(0.03)
                continue
            if not data:
                continue
            payload = {
                "frame": {
                    "source": source,
                    "ts": time.time(),
                    "pcm_base64": base64.b64encode(data).decode("ascii"),
                }
            }
            try:
                sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except Exception:
                # If stdout breaks, stop to avoid runaway.
                stop_event.set()

    try:
        system_info = resolve_loopback()
        mic_info = resolve_mic()
        system_stream = pa.open(
            format=pyaudio.paInt16,
            channels=max(1, min(channels, int(system_info.get("maxInputChannels", 1)))),
            rate=int(sample_rate or system_info.get("defaultSampleRate", 16000)),
            frames_per_buffer=frames_per_buffer,
            input=True,
            input_device_index=int(system_info["index"]),
        )
        mic_stream = pa.open(
            format=pyaudio.paInt16,
            channels=max(1, min(channels, int(mic_info.get("maxInputChannels", 1)))),
            rate=int(sample_rate or mic_info.get("defaultSampleRate", 16000)),
            frames_per_buffer=frames_per_buffer,
            input=True,
            input_device_index=int(mic_info["index"]),
        )
    except Exception as exc:
        try:
            pa.terminate()
        except Exception:
            pass
        print(json.dumps({"event": "error", "message": str(exc)}, ensure_ascii=False), flush=True)
        return 3

    print(json.dumps({"event": "ready"}, ensure_ascii=False), flush=True)

    t1 = threading.Thread(target=run_reader, args=("system", system_stream), daemon=True)
    t2 = threading.Thread(target=run_reader, args=("mic", mic_stream), daemon=True)
    t1.start()
    t2.start()

    try:
        while not stop_event.wait(0.15):
            pass
    finally:
        for s in (system_stream, mic_stream):
            try:
                s.stop_stream()
                s.close()
            except Exception:
                pass
        try:
            pa.terminate()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        try:
            print(json.dumps({"event": "error", "message": f"fatal: {exc}"}, ensure_ascii=False), flush=True)
        except Exception:
            pass
        raise
"""

class AudioSessionManager:
    """Manage visible audio capture sessions and frame queues."""

    def __init__(
        self,
        probe: AudioProbe | None = None,
        *,
        worker_factory: Callable[[AudioCaptureSession, Callable[[AudioSource, bytes, float], None], Callable[[str], None]], NativeAudioWorker]
        | None = None,
    ) -> None:
        self.probe = probe or AudioProbe()
        self.worker_factory = worker_factory or self._build_native_worker
        self.sessions: dict[str, AudioCaptureSession] = {}
        self.frame_queues: dict[str, deque[AudioFrameEnvelope]] = {}
        self.workers: dict[str, NativeAudioWorker] = {}
        self._lock = threading.RLock()

    def create_session(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        sample_rate = int(payload["sample_rate"]) if payload.get("sample_rate") else 0
        chunk_ms = int(payload.get("chunk_ms", 250))
        capabilities = self.probe.probe()
        plan = self.probe.recommend(
            capabilities,
            sample_rate=sample_rate if sample_rate > 0 else None,
            chunk_ms=chunk_ms,
        )
        requested_transport = str(payload.get("transport", "")).strip().lower()
        transport = requested_transport or ("native" if plan.ready else "manual")
        backend = str(payload.get("backend", plan.backend)).strip() or plan.backend
        config = AudioCaptureConfig(
            transport=transport,
            backend=backend,
            sample_rate=plan.sample_rate,
            chunk_ms=chunk_ms,
            channels=int(payload.get("channels", 1)),
            sample_width_bytes=int(payload.get("sample_width_bytes", 2)),
            max_queue_frames=int(payload.get("max_queue_frames", 128)),
            system_device=self._resolve_device(capabilities, backend, payload.get("system_device_index"), plan.system_device),
            mic_device=self._resolve_device(capabilities, backend, payload.get("mic_device_index"), plan.mic_device),
        )
        notes = list(plan.notes)
        status = "created"
        if transport == "manual":
            notes.append("This session uses manual transport for local development and ASR integration work.")
        elif not plan.ready:
            status = "blocked"
            notes.append("Native transport is not ready yet on this machine. Install the backend and check devices first.")
        else:
            notes.append("Native transport is available and can be started from this session.")

        session = AudioCaptureSession(
            session_id=str(uuid4()),
            status=status,
            config=config,
            plan=plan,
            created_at=time.time(),
            notes=notes,
        )
        with self._lock:
            self.sessions[session.session_id] = session
            self.frame_queues[session.session_id] = deque()
        return session.to_dict()

    def get_session(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            session = self.sessions[session_id]
            session.queued_frames = len(self.frame_queues[session_id])
            return session.to_dict()

    def start_session(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            session = self.sessions[session_id]
            if session.status == "running":
                return session.to_dict()
            if session.status == "blocked":
                raise RuntimeError("Audio session is blocked. Check the recommendation notes first.")

            session.started_at = session.started_at or time.time()
            session.stopped_at = None
            session.error = ""

            if session.config.transport == "manual":
                session.status = "running"
                session.queued_frames = len(self.frame_queues[session_id])
                return session.to_dict()

            session.status = "running"
            worker = self.worker_factory(
                session,
                lambda source, pcm, ts: self._enqueue_frame(session_id, source, pcm, ts),
                lambda message: self._record_worker_error(session_id, message),
            )
            self.workers[session_id] = worker

        try:
            worker.start()
        except Exception as exc:
            with self._lock:
                self.workers.pop(session_id, None)
            self._record_worker_error(session_id, str(exc), failed=True)
            raise RuntimeError(str(exc)) from exc

        return self.get_session(session_id)

    def stop_session(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            session = self.sessions[session_id]
            worker = self.workers.pop(session_id, None)
            session.stopped_at = time.time()
            if worker is None:
                if session.status == "running":
                    session.status = "stopped"
                session.queued_frames = len(self.frame_queues[session_id])
                return session.to_dict()

        worker.stop()
        with self._lock:
            session = self.sessions[session_id]
            session.status = "stopped"
            session.stopped_at = time.time()
            session.queued_frames = len(self.frame_queues[session_id])
            return session.to_dict()

    def push_frame(self, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            session = self.sessions[session_id]
            if session.status == "blocked":
                raise RuntimeError("Audio session is blocked and cannot accept frames.")

        source = AudioSource(str(payload.get("source", AudioSource.SYSTEM.value)))
        ts = float(payload.get("ts", time.time()))
        if "pcm_base64" in payload:
            pcm = base64.b64decode(str(payload["pcm_base64"]))
        else:
            pcm = str(payload.get("pcm_text", "")).encode("utf-8")
        envelope = self._enqueue_frame(session_id, source, pcm, ts)
        return {
            "session": self.get_session(session_id),
            "frame": envelope.to_dict(),
        }

    def drain_frame_batch(
        self,
        session_id: str,
        *,
        max_frames: int = 20,
        source: str | None = None,
    ) -> tuple[dict[str, Any], AudioCaptureConfig, list[AudioFrameEnvelope]]:
        with self._lock:
            session = self.sessions[session_id]
            drained = self._drain_envelopes_locked(session, self.frame_queues[session_id], max_frames=max_frames, source=source)
            session_snapshot = session.to_dict()
            config_snapshot = copy.deepcopy(session.config)
        return session_snapshot, config_snapshot, drained

    def drain_frames(
        self,
        session_id: str,
        *,
        max_frames: int = 20,
        include_payload: bool = False,
        as_wav: bool = False,
        source: str | None = None,
    ) -> dict[str, Any]:
        session_snapshot, config_snapshot, drained = self.drain_frame_batch(
            session_id,
            max_frames=max_frames,
            source=source,
        )

        payload: dict[str, Any] = {
            "session": session_snapshot,
            "frames": [item.to_dict(include_payload=include_payload) for item in drained],
        }
        if as_wav and drained:
            wav_bytes = self.build_wav_bytes(
                frames=[item.frame for item in drained],
                sample_rate=config_snapshot.sample_rate,
                channels=config_snapshot.channels,
                sample_width_bytes=config_snapshot.sample_width_bytes,
            )
            payload["wav_base64"] = base64.b64encode(wav_bytes).decode("ascii")
            payload["wav_num_frames"] = len(drained)
        return payload

    def build_wav_bytes(
        self,
        *,
        frames: list[AudioFrame],
        sample_rate: int,
        channels: int = 1,
        sample_width_bytes: int = 2,
    ) -> bytes:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as handle:
            handle.setnchannels(channels)
            handle.setsampwidth(sample_width_bytes)
            handle.setframerate(sample_rate)
            handle.writeframes(b"".join(frame.pcm for frame in frames))
        return buffer.getvalue()

    def _build_native_worker(
        self,
        session: AudioCaptureSession,
        on_frame: Callable[[AudioSource, bytes, float], None],
        on_error: Callable[[str], None],
    ) -> NativeAudioWorker:
        if session.config.backend == "pyaudiowpatch":
            force_subprocess = os.getenv("INTERVIEW_TRAINER_AUDIO_CAPTURE_SUBPROCESS", "").strip().lower()
            use_subprocess = sys.platform.startswith("win") and force_subprocess != "0"
            if use_subprocess:
                return SubprocessPyAudioWorker(config=session.config, on_frame=on_frame, on_error=on_error)
            return PyAudioNativeWorker(config=session.config, on_frame=on_frame, on_error=on_error)
        raise RuntimeError(f"Native backend {session.config.backend} is not implemented yet.")

    def _enqueue_frame(self, session_id: str, source: AudioSource, pcm: bytes, ts: float) -> AudioFrameEnvelope:
        with self._lock:
            session = self.sessions[session_id]
            queue = self.frame_queues[session_id]
            envelope = AudioFrameEnvelope(
                frame_id=str(uuid4()),
                frame=AudioFrame(source=source, ts=ts, pcm=pcm),
                sample_rate=session.config.sample_rate,
                chunk_ms=session.config.chunk_ms,
            )
            if len(queue) >= session.config.max_queue_frames:
                queue.popleft()
                session.dropped_frames += 1
            queue.append(envelope)
            session.total_frames += 1
            session.last_frame_ts = ts
            session.queued_frames = len(queue)
            if session.status == "created":
                session.status = "running"
                session.started_at = session.started_at or time.time()
            return envelope

    def _drain_envelopes_locked(
        self,
        session: AudioCaptureSession,
        queue: deque[AudioFrameEnvelope],
        *,
        max_frames: int,
        source: str | None,
    ) -> list[AudioFrameEnvelope]:
        drained: list[AudioFrameEnvelope] = []
        held_back: list[AudioFrameEnvelope] = []

        while queue and len(drained) < max_frames:
            envelope = queue.popleft()
            if source and envelope.frame.source.value != source:
                held_back.append(envelope)
                continue
            drained.append(envelope)

        while held_back:
            queue.appendleft(held_back.pop())

        session.queued_frames = len(queue)
        return drained

    def _record_worker_error(self, session_id: str, message: str, *, failed: bool = False) -> None:
        with self._lock:
            session = self.sessions.get(session_id)
            if session is None:
                return
            session.error = message
            session.status = "failed" if failed or session.status != "stopped" else session.status

    def _resolve_device(
        self,
        capabilities: list[AudioCapabilities],
        backend: str,
        device_index: Any,
        fallback: AudioDeviceInfo | None,
    ) -> AudioDeviceInfo | None:
        if device_index is None:
            return fallback
        try:
            target_index = int(device_index)
        except (TypeError, ValueError):
            return fallback

        for capability in capabilities:
            if capability.backend != backend:
                continue
            for device in capability.devices:
                if device.index == target_index:
                    return device
        return fallback
