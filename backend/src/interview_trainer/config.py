from __future__ import annotations

import os
from dataclasses import dataclass, field


def _first_non_empty(*values: str) -> str:
    for value in values:
        text = value.strip()
        if text:
            return text
    return ""


def _split_csv(raw_value: str) -> list[str]:
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _parse_optional_bool(raw_value: str) -> bool | None:
    text = raw_value.strip().lower()
    if not text:
        return None
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {raw_value!r}")


def _is_dashscope_compatible_base_url(base_url: str) -> bool:
    return "dashscope.aliyuncs.com/compatible-mode" in base_url.strip().lower()


def _default_fast_model_for_base_url(base_url: str) -> str:
    if _is_dashscope_compatible_base_url(base_url):
        return "qwen3.5-flash"
    return "gpt-4.1-mini"


def _default_fast_enable_thinking(*, base_url: str, model: str) -> bool | None:
    if _is_dashscope_compatible_base_url(base_url) and model.strip().lower().startswith("qwen3.5-"):
        return False
    return None


@dataclass(frozen=True, slots=True)
class FastModelPreset:
    name: str
    model: str
    enable_thinking: bool | None = None


_FAST_MODEL_PRESETS: dict[str, FastModelPreset] = {
    "qwen3.5-flash": FastModelPreset(
        name="qwen3.5-flash",
        model="qwen3.5-flash",
        enable_thinking=False,
    ),
    "qwen3.5-plus": FastModelPreset(
        name="qwen3.5-plus",
        model="qwen3.5-plus",
        enable_thinking=False,
    ),
}


_FAST_MODEL_PRESET_ALIASES = {
    "dashscope_flash": "qwen3.5-flash",
    "qwen3_5_flash": "qwen3.5-flash",
    "dashscope_plus": "qwen3.5-plus",
    "qwen3_5_plus": "qwen3.5-plus",
}


def list_fast_model_presets() -> list[FastModelPreset]:
    return [
        _FAST_MODEL_PRESETS["qwen3.5-flash"],
        _FAST_MODEL_PRESETS["qwen3.5-plus"],
    ]


def _resolve_fast_model_preset(raw_value: str) -> FastModelPreset | None:
    normalized = raw_value.strip().lower().replace("-", "_").replace(".", "_")
    if not normalized:
        return None
    preset_name = _FAST_MODEL_PRESET_ALIASES.get(normalized)
    preset = _FAST_MODEL_PRESETS.get(preset_name or "")
    if preset is None:
        raise ValueError(
            f"Invalid fast preset: {raw_value!r}. "
            "Supported values: dashscope-flash, qwen3.5-flash, dashscope-plus, qwen3.5-plus."
        )
    return preset


@dataclass(slots=True)
class GenerationLaneSettings:
    provider: str = "template"
    api_key: str = ""
    base_url: str = "https://subrouter.ai/v1"
    model: str = ""
    request_timeout_s: float = 30.0
    temperature: float = 0.7
    stream_enabled: bool = False
    enable_thinking: bool | None = None

    @property
    def use_openai(self) -> bool:
        return self.provider == "openai" and bool(self.api_key)


@dataclass(slots=True)
class GenerationSettings:
    provider: str = "template"
    openai_api_key: str = ""
    openai_base_url: str = "https://subrouter.ai/v1"
    enable_thinking: bool | None = None
    fast_provider: str = "template"
    fast_api_key: str = ""
    fast_base_url: str = "https://subrouter.ai/v1"
    fast_model: str = "gpt-4.1-mini"
    fast_preset: str = ""
    fast_request_timeout_s: float = 30.0
    fast_enable_thinking: bool | None = None
    smart_provider: str = "template"
    smart_api_key: str = ""
    smart_base_url: str = "https://subrouter.ai/v1"
    smart_model: str = "gpt-4.1"
    smart_request_timeout_s: float = 30.0
    smart_enable_thinking: bool | None = None
    starter_stream_enabled: bool = True
    request_timeout_s: float = 30.0
    temperature_starter: float = 0.7
    temperature_full: float = 0.45

    @classmethod
    def from_env(cls) -> "GenerationSettings":
        provider = os.getenv("INTERVIEW_TRAINER_LLM_PROVIDER", "template").strip().lower() or "template"
        api_key = _first_non_empty(
            os.getenv("INTERVIEW_TRAINER_LLM_API_KEY", ""),
            os.getenv("OPENAI_API_KEY", ""),
        )
        base_url = (
            _first_non_empty(
                os.getenv("INTERVIEW_TRAINER_LLM_BASE_URL", "https://subrouter.ai/v1"),
                os.getenv("OPENAI_BASE_URL", "https://subrouter.ai/v1"),
            )
            or "https://subrouter.ai/v1"
        ).rstrip("/")
        request_timeout_s = float(os.getenv("INTERVIEW_TRAINER_REQUEST_TIMEOUT_S", "30"))
        enable_thinking = _parse_optional_bool(os.getenv("INTERVIEW_TRAINER_LLM_ENABLE_THINKING", ""))
        fast_base_url = (
            _first_non_empty(os.getenv("INTERVIEW_TRAINER_FAST_BASE_URL", ""), base_url)
            or "https://subrouter.ai/v1"
        ).rstrip("/")
        fast_preset = _resolve_fast_model_preset(os.getenv("INTERVIEW_TRAINER_FAST_PRESET", ""))
        fast_model_default = _default_fast_model_for_base_url(fast_base_url)
        fast_model = (
            fast_preset.model
            if fast_preset is not None
            else (os.getenv("INTERVIEW_TRAINER_FAST_MODEL", fast_model_default).strip() or fast_model_default)
        )
        fast_enable_thinking = _parse_optional_bool(os.getenv("INTERVIEW_TRAINER_FAST_ENABLE_THINKING", ""))
        smart_enable_thinking = _parse_optional_bool(os.getenv("INTERVIEW_TRAINER_SMART_ENABLE_THINKING", ""))
        return cls(
            provider=provider,
            openai_api_key=api_key,
            openai_base_url=base_url,
            enable_thinking=enable_thinking,
            fast_provider=os.getenv("INTERVIEW_TRAINER_FAST_PROVIDER", "").strip().lower() or provider,
            fast_api_key=_first_non_empty(os.getenv("INTERVIEW_TRAINER_FAST_API_KEY", ""), api_key),
            fast_base_url=fast_base_url,
            fast_model=fast_model,
            fast_preset=fast_preset.name if fast_preset is not None else "",
            fast_request_timeout_s=float(
                os.getenv("INTERVIEW_TRAINER_FAST_TIMEOUT_S", str(request_timeout_s))
            ),
            fast_enable_thinking=(
                fast_enable_thinking
                if fast_enable_thinking is not None
                else (
                    fast_preset.enable_thinking
                    if fast_preset is not None and fast_preset.enable_thinking is not None
                    else (
                        enable_thinking
                        if enable_thinking is not None
                        else _default_fast_enable_thinking(base_url=fast_base_url, model=fast_model)
                    )
                )
            ),
            smart_provider=os.getenv("INTERVIEW_TRAINER_SMART_PROVIDER", "").strip().lower() or provider,
            smart_api_key=_first_non_empty(os.getenv("INTERVIEW_TRAINER_SMART_API_KEY", ""), api_key),
            smart_base_url=(
                _first_non_empty(os.getenv("INTERVIEW_TRAINER_SMART_BASE_URL", ""), base_url)
                or "https://subrouter.ai/v1"
            ).rstrip("/"),
            smart_model=os.getenv("INTERVIEW_TRAINER_SMART_MODEL", "gpt-4.1").strip() or "gpt-4.1",
            smart_request_timeout_s=float(
                os.getenv("INTERVIEW_TRAINER_SMART_TIMEOUT_S", str(request_timeout_s))
            ),
            smart_enable_thinking=smart_enable_thinking if smart_enable_thinking is not None else enable_thinking,
            starter_stream_enabled=(
                os.getenv("INTERVIEW_TRAINER_LLM_STARTER_STREAM", "true").strip().lower() != "false"
            ),
            request_timeout_s=request_timeout_s,
            temperature_starter=float(os.getenv("INTERVIEW_TRAINER_TEMP_STARTER", "0.7")),
            temperature_full=float(os.getenv("INTERVIEW_TRAINER_TEMP_FULL", "0.45")),
        )

    @property
    def use_openai(self) -> bool:
        return self.fast_lane.use_openai or self.smart_lane.use_openai

    @property
    def fast_lane(self) -> GenerationLaneSettings:
        return GenerationLaneSettings(
            provider=self.fast_provider,
            api_key=self.fast_api_key,
            base_url=self.fast_base_url,
            model=self.fast_model,
            request_timeout_s=self.fast_request_timeout_s,
            temperature=self.temperature_starter,
            stream_enabled=self.starter_stream_enabled,
            enable_thinking=self.fast_enable_thinking,
        )

    @property
    def smart_lane(self) -> GenerationLaneSettings:
        return GenerationLaneSettings(
            provider=self.smart_provider,
            api_key=self.smart_api_key,
            base_url=self.smart_base_url,
            model=self.smart_model,
            request_timeout_s=self.smart_request_timeout_s,
            temperature=self.temperature_full,
            stream_enabled=False,
            enable_thinking=self.smart_enable_thinking,
        )


@dataclass(slots=True)
class TranscriptionSettings:
    provider: str = "template"
    openai_api_key: str = ""
    openai_base_url: str = "https://subrouter.ai/v1"
    alibaba_api_key: str = ""
    alibaba_ws_url: str = "wss://dashscope.aliyuncs.com/api-ws/v1/inference"
    alibaba_app_key: str = ""
    alibaba_workspace: str = ""
    alibaba_vocabulary_id: str = ""
    alibaba_hotwords: list[str] = field(default_factory=list)
    model: str = "gpt-4o-mini-transcribe"
    realtime_ws_url: str = ""
    realtime_input_sample_rate: int = 24000
    realtime_connect_timeout_s: float = 10.0
    realtime_receive_timeout_s: float = 0.05
    realtime_drain_timeout_s: float = 1.2
    realtime_beta_header: str = "realtime=v1"
    request_timeout_s: float = 30.0
    language: str = "zh"
    prompt: str = ""
    energy_gate_enabled: bool = True
    energy_threshold: float = 0.003
    min_duration_ms: float = 120.0
    adaptive_gate_enabled: bool = True
    adaptive_multiplier: float = 2.5
    adaptive_floor_ratio: float = 0.5
    noise_floor_alpha: float = 0.18
    bridge_target_duration_ms: float = 450.0
    bridge_max_buffer_ms: float = 1200.0
    vad_frame_ms: int = 30
    vad_min_voiced_ratio: float = 0.25
    vad_min_speech_frames: int = 2
    vad_max_zcr: float = 0.35
    vad_min_delta: float = 0.0005
    vad_hangover_frames: int = 1

    @classmethod
    def from_env(cls) -> "TranscriptionSettings":
        provider = os.getenv("INTERVIEW_TRAINER_ASR_PROVIDER", "template").strip().lower() or "template"
        bridge_target_raw = os.getenv("INTERVIEW_TRAINER_BRIDGE_TARGET_MS", "").strip()
        bridge_max_buffer_raw = os.getenv("INTERVIEW_TRAINER_BRIDGE_MAX_BUFFER_MS", "").strip()
        default_bridge_target_ms = 3000.0 if provider == "alibaba_realtime" else 450.0
        default_bridge_max_buffer_ms = 5000.0 if provider == "alibaba_realtime" else 1200.0
        return cls(
            provider=provider,
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            openai_base_url=os.getenv("OPENAI_BASE_URL", "https://subrouter.ai/v1").rstrip("/"),
            alibaba_api_key=_first_non_empty(
                os.getenv("INTERVIEW_TRAINER_ALIBABA_API_KEY", ""),
                os.getenv("DASHSCOPE_API_KEY", ""),
            ),
            alibaba_ws_url=(
                _first_non_empty(
                    os.getenv("INTERVIEW_TRAINER_ALIBABA_WS_URL", ""),
                    os.getenv("INTERVIEW_TRAINER_ASR_REALTIME_URL", ""),
                    "wss://dashscope.aliyuncs.com/api-ws/v1/inference",
                )
                or "wss://dashscope.aliyuncs.com/api-ws/v1/inference"
            ).rstrip("/"),
            alibaba_app_key=os.getenv("INTERVIEW_TRAINER_ALIBABA_APP_KEY", "").strip(),
            alibaba_workspace=os.getenv("INTERVIEW_TRAINER_ALIBABA_WORKSPACE", "").strip(),
            alibaba_vocabulary_id=os.getenv("INTERVIEW_TRAINER_ALIBABA_VOCABULARY_ID", "").strip(),
            alibaba_hotwords=_split_csv(os.getenv("INTERVIEW_TRAINER_ALIBABA_HOTWORDS", "")),
            model=(
                os.getenv("INTERVIEW_TRAINER_ASR_MODEL", "gpt-4o-mini-transcribe").strip()
                or "gpt-4o-mini-transcribe"
            ),
            realtime_ws_url=os.getenv("INTERVIEW_TRAINER_ASR_REALTIME_URL", "").strip(),
            realtime_input_sample_rate=int(os.getenv("INTERVIEW_TRAINER_ASR_REALTIME_SAMPLE_RATE", "24000")),
            realtime_connect_timeout_s=float(os.getenv("INTERVIEW_TRAINER_ASR_REALTIME_CONNECT_TIMEOUT_S", "10")),
            realtime_receive_timeout_s=float(os.getenv("INTERVIEW_TRAINER_ASR_REALTIME_RECV_TIMEOUT_S", "0.05")),
            realtime_drain_timeout_s=float(os.getenv("INTERVIEW_TRAINER_ASR_REALTIME_DRAIN_TIMEOUT_S", "1.2")),
            realtime_beta_header=os.getenv("INTERVIEW_TRAINER_ASR_REALTIME_BETA_HEADER", "realtime=v1").strip(),
            request_timeout_s=float(os.getenv("INTERVIEW_TRAINER_ASR_TIMEOUT_S", "30")),
            language=os.getenv("INTERVIEW_TRAINER_ASR_LANGUAGE", "zh").strip() or "zh",
            prompt=os.getenv("INTERVIEW_TRAINER_ASR_PROMPT", "").strip(),
            energy_gate_enabled=(os.getenv("INTERVIEW_TRAINER_ASR_ENERGY_GATE", "true").strip().lower() != "false"),
            energy_threshold=float(os.getenv("INTERVIEW_TRAINER_ASR_ENERGY_THRESHOLD", "0.003")),
            min_duration_ms=float(os.getenv("INTERVIEW_TRAINER_ASR_MIN_DURATION_MS", "120")),
            adaptive_gate_enabled=(os.getenv("INTERVIEW_TRAINER_ASR_ADAPTIVE_GATE", "true").strip().lower() != "false"),
            adaptive_multiplier=float(os.getenv("INTERVIEW_TRAINER_ASR_ADAPTIVE_MULTIPLIER", "2.5")),
            adaptive_floor_ratio=float(os.getenv("INTERVIEW_TRAINER_ASR_ADAPTIVE_FLOOR_RATIO", "0.5")),
            noise_floor_alpha=float(os.getenv("INTERVIEW_TRAINER_ASR_NOISE_ALPHA", "0.18")),
            bridge_target_duration_ms=float(bridge_target_raw or default_bridge_target_ms),
            bridge_max_buffer_ms=float(bridge_max_buffer_raw or default_bridge_max_buffer_ms),
            vad_frame_ms=int(os.getenv("INTERVIEW_TRAINER_VAD_FRAME_MS", "30")),
            vad_min_voiced_ratio=float(os.getenv("INTERVIEW_TRAINER_VAD_MIN_RATIO", "0.25")),
            vad_min_speech_frames=int(os.getenv("INTERVIEW_TRAINER_VAD_MIN_FRAMES", "2")),
            vad_max_zcr=float(os.getenv("INTERVIEW_TRAINER_VAD_MAX_ZCR", "0.35")),
            vad_min_delta=float(os.getenv("INTERVIEW_TRAINER_VAD_MIN_DELTA", "0.0005")),
            vad_hangover_frames=int(os.getenv("INTERVIEW_TRAINER_VAD_HANGOVER_FRAMES", "1")),
        )

    @property
    def use_openai(self) -> bool:
        return self.provider in {"openai", "openai_realtime"} and bool(self.openai_api_key)

    @property
    def use_openai_realtime(self) -> bool:
        return self.provider == "openai_realtime" and bool(self.openai_api_key)

    @property
    def use_alibaba_realtime(self) -> bool:
        return self.provider == "alibaba_realtime" and bool(self.alibaba_api_key)

    @property
    def use_realtime_stream(self) -> bool:
        return self.use_openai_realtime or self.use_alibaba_realtime
