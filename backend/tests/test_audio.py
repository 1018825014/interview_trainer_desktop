import base64
import unittest

from interview_trainer.audio import (
    AudioCapabilities,
    AudioCapturePlan,
    AudioDeviceInfo,
    AudioProbe,
    AudioSessionManager,
)
from interview_trainer.types import AudioSource


class _FakeProbe:
    def __init__(self, *, ready: bool) -> None:
        self.system_device = AudioDeviceInfo(
            name="Speaker (loopback)",
            index=1,
            max_input_channels=2,
            max_output_channels=2,
            hostapi="Windows WASAPI",
            default_samplerate=48000,
            is_loopback_candidate=True,
        )
        self.mic_device = AudioDeviceInfo(
            name="USB Mic",
            index=2,
            max_input_channels=1,
            max_output_channels=0,
            hostapi="Windows WASAPI",
            default_samplerate=48000,
            is_loopback_candidate=False,
        )
        self.ready = ready
        self.capabilities = [
            AudioCapabilities(
                backend="pyaudiowpatch",
                python_package_available=ready,
                platform_supported=True,
                supports_loopback=ready,
                supports_microphone_capture=ready,
                devices=[self.system_device, self.mic_device] if ready else [],
                notes=["fake probe"],
            )
        ]

    def probe(self):
        return self.capabilities

    def recommend(self, capabilities=None, *, sample_rate: int | None = 16000, chunk_ms: int = 250):
        return AudioCapturePlan(
            ready=self.ready,
            backend="pyaudiowpatch",
            system_device=self.system_device if self.ready else None,
            mic_device=self.mic_device if self.ready else None,
            sample_rate=sample_rate or 16000,
            chunk_ms=chunk_ms,
            notes=["ready"] if self.ready else ["not ready"],
        )


class _FakeNativeWorker:
    def __init__(self, on_frame, on_error) -> None:
        self.on_frame = on_frame
        self.on_error = on_error
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True
        self.on_frame(AudioSource.SYSTEM, b"sys", 1.0)
        self.on_frame(AudioSource.MIC, b"mic", 1.1)

    def stop(self) -> None:
        self.stopped = True


class AudioProbeTests(unittest.TestCase):
    def test_probe_returns_capability_entries(self) -> None:
        capabilities = AudioProbe().probe()
        self.assertGreaterEqual(len(capabilities), 2)
        self.assertTrue(all(hasattr(item, "backend") for item in capabilities))

    def test_recommend_prefers_ready_loopback_backend(self) -> None:
        capabilities = [
            AudioCapabilities(
                backend="sounddevice",
                python_package_available=True,
                platform_supported=True,
                supports_loopback=False,
                supports_microphone_capture=True,
                devices=[],
                notes=[],
            ),
            AudioCapabilities(
                backend="pyaudiowpatch",
                python_package_available=True,
                platform_supported=True,
                supports_loopback=True,
                supports_microphone_capture=True,
                devices=[
                    AudioDeviceInfo(
                        name="Speaker (loopback)",
                        index=1,
                        max_input_channels=2,
                        max_output_channels=2,
                        hostapi="Windows WASAPI",
                        default_samplerate=48000,
                        is_loopback_candidate=True,
                    ),
                    AudioDeviceInfo(
                        name="USB Mic",
                        index=2,
                        max_input_channels=1,
                        max_output_channels=0,
                        hostapi="Windows WASAPI",
                        default_samplerate=48000,
                        is_loopback_candidate=False,
                    ),
                ],
                notes=[],
            ),
        ]
        recommendation = AudioProbe().recommend(capabilities)
        self.assertTrue(recommendation.ready)
        self.assertEqual(recommendation.backend, "pyaudiowpatch")
        self.assertEqual(recommendation.system_device.name, "Speaker (loopback)")
        self.assertEqual(recommendation.mic_device.name, "USB Mic")


class AudioSessionManagerTests(unittest.TestCase):
    def test_manual_session_can_queue_and_drain_frames(self) -> None:
        manager = AudioSessionManager()
        session = manager.create_session({"transport": "manual", "sample_rate": 16000, "chunk_ms": 200})
        session_id = session["session_id"]
        self.assertEqual(session["status"], "created")

        started = manager.start_session(session_id)
        self.assertEqual(started["status"], "running")

        pushed = manager.push_frame(
            session_id,
            {
                "source": "system",
                "pcm_base64": base64.b64encode(b"\x00\x01" * 160).decode("ascii"),
                "ts": 1.5,
            },
        )
        self.assertEqual(pushed["session"]["queued_frames"], 1)

        drained = manager.drain_frames(session_id, max_frames=10, include_payload=True, as_wav=True)
        self.assertEqual(len(drained["frames"]), 1)
        self.assertEqual(drained["session"]["queued_frames"], 0)
        self.assertTrue(drained["frames"][0]["pcm_base64"])
        self.assertTrue(drained["wav_base64"])

    def test_queue_respects_max_frame_limit(self) -> None:
        manager = AudioSessionManager()
        session = manager.create_session({"transport": "manual", "max_queue_frames": 1})
        session_id = session["session_id"]
        manager.push_frame(session_id, {"source": "system", "pcm_base64": base64.b64encode(b"a").decode("ascii")})
        manager.push_frame(session_id, {"source": "mic", "pcm_base64": base64.b64encode(b"b").decode("ascii")})
        snapshot = manager.get_session(session_id)
        self.assertEqual(snapshot["queued_frames"], 1)
        self.assertEqual(snapshot["dropped_frames"], 1)

    def test_build_wav_bytes_has_riff_header(self) -> None:
        manager = AudioSessionManager()
        wav_bytes = manager.build_wav_bytes(
            frames=[],
            sample_rate=16000,
            channels=1,
            sample_width_bytes=2,
        )
        self.assertTrue(wav_bytes.startswith(b"RIFF"))
        self.assertIn(b"WAVE", wav_bytes)

    def test_native_session_uses_worker_and_enqueues_frames(self) -> None:
        created_workers: list[_FakeNativeWorker] = []

        def factory(session, on_frame, on_error):
            del session
            worker = _FakeNativeWorker(on_frame, on_error)
            created_workers.append(worker)
            return worker

        manager = AudioSessionManager(probe=_FakeProbe(ready=True), worker_factory=factory)
        session = manager.create_session({})
        session_id = session["session_id"]
        self.assertEqual(session["config"]["transport"], "native")
        self.assertEqual(session["status"], "created")

        started = manager.start_session(session_id)
        self.assertEqual(started["status"], "running")
        self.assertEqual(started["queued_frames"], 2)
        self.assertTrue(created_workers[0].started)

        stopped = manager.stop_session(session_id)
        self.assertEqual(stopped["status"], "stopped")
        self.assertTrue(created_workers[0].stopped)

    def test_native_session_blocks_when_probe_is_not_ready(self) -> None:
        manager = AudioSessionManager(probe=_FakeProbe(ready=False))
        session = manager.create_session({"transport": "native"})
        self.assertEqual(session["status"], "blocked")
        with self.assertRaises(RuntimeError):
            manager.start_session(session["session_id"])


if __name__ == "__main__":
    unittest.main()
