以后启动后端就用这条（不怕 conda/base 混乱）
在 backend 目录下：

$env:PYTHONPATH="src"
.\.venv\Scripts\python -m interview_trainer --serve --host 127.0.0.1 --port 8000


# Interview Trainer Desktop

Windows desktop MVP for mock interviews or clearly disclosed AI-assisted practice.

This version already includes:

- Electron + React/TypeScript desktop shell with a visible floating panel
- Python backend for knowledge compilation, routing, overlap-aware turn management, and layered answers
- Knowledge workspace management for profile/project/role materials
- Async `starter` and `full` answer generation
- Audio capability probing and session management
- Manual and native audio transport (`WASAPI loopback + mic` via `PyAudioWPatch`)
- Chunked audio transcription pipeline
- Continuous live transcription bridge for `audio session -> transcript -> interview session`
- Optional OpenAI Realtime streaming transcription for live bridge sessions
- Partial transcript updates from Realtime `delta` events
- A development path from `audio session -> transcription -> interview answer`

The product scope stays inside visible training and disclosed assistance. It does not include any hidden, screen-share evasion, or recording evasion features.

## Structure

```text
interview_trainer_desktop/
|-- backend/
|   |-- src/interview_trainer/
|   |   |-- api.py
|   |   |-- audio.py
|   |   |-- briefing.py
|   |   |-- config.py
|   |   |-- corrections.py
|   |   |-- generation.py
|   |   |-- knowledge.py
|   |   |-- prompts.py
|   |   |-- routing.py
|   |   |-- service.py
|   |   |-- transcription.py
|   |   |-- turns.py
|   |   `-- types.py
|   |-- tests/
|   `-- pyproject.toml
`-- desktop/
    |-- electron/
    |-- src/
    |-- package.json
    `-- vite.config.ts
```

## Backend Highlights

### Interview memory model

Uploaded materials are compiled into interview-oriented layers instead of plain summary blobs:

- `ProfileCard`
- `ProjectInterviewPack`
- `ModuleCard`
- `RepoMap / CodebaseSummary`
- `DocChunk / CodeChunk`
- `RolePlaybook`

The answer flow is:

1. classify the question
2. route context
3. build a `KnowledgePack`
4. generate `starter` and `full`

### Knowledge workspaces

The backend now supports persistent in-memory workspaces for interview materials:

- create and list workspaces
- edit profile/project/role notes
- compile a workspace into interview-oriented memory
- import a local project path into a workspace as docs and code files

The desktop app exposes a minimal workspace editor so you can keep one reusable interview pack instead of relying only on hard-coded sample payloads.

### Turn management

`TurnManager` handles:

- interviewer-only speaking
- overlap and interruptions
- immediate candidate response after the interviewer stops
- silence-based question locking via `tick`

### Async answer generation

`starter` and `full` are generated in parallel:

- backend returns `pending` or `starter_ready`
- frontend polls `/api/sessions/{session_id}/answers/{turn_id}`
- final state becomes `complete`

### Audio capture

`AudioProbe` recommends a capture plan and checks package availability.

`AudioSessionManager` supports:

- create/start/stop audio sessions
- manual frame injection for development
- frame queue drain
- wav export
- native `WASAPI loopback + mic` capture when `PyAudioWPatch` is available

### Transcription pipeline

`AudioTranscriptionService` now connects audio chunks to ASR:

- drains frames from an audio session
- packages them as wav
- sends them to a transcription provider
- optionally forwards the resulting transcript into an interview session
- auto-runs a silence `tick` after interviewer chunks so answer generation can start immediately

It also includes a live bridge manager:

- start a background worker for a running audio session
- poll `system` and `mic` chunks continuously
- surface per-source partial transcript updates while a chunk is still streaming
- keep recent transcripts and last answer status
- update pending answer drafts until they reach `complete`

Default ASR is `template`. Real OpenAI chunked or realtime transcription can be enabled with env vars.

## Environment

### LLM generation

```powershell
set INTERVIEW_TRAINER_LLM_PROVIDER=openai
set INTERVIEW_TRAINER_LLM_API_KEY=sk-...
set INTERVIEW_TRAINER_LLM_BASE_URL=https://subrouter.ai/v1
set INTERVIEW_TRAINER_FAST_MODEL=gpt-4.1-mini
set INTERVIEW_TRAINER_SMART_MODEL=gpt-4.1
set INTERVIEW_TRAINER_LLM_ENABLE_THINKING=
set INTERVIEW_TRAINER_LLM_STARTER_STREAM=true
```

For a split fast/smart setup, you can override each lane independently:

```powershell
set INTERVIEW_TRAINER_FAST_PROVIDER=openai
set INTERVIEW_TRAINER_FAST_API_KEY=your-fast-key
set INTERVIEW_TRAINER_FAST_BASE_URL=https://fast-provider.example/v1
set INTERVIEW_TRAINER_FAST_PRESET=
set INTERVIEW_TRAINER_FAST_MODEL=your-fast-model
set INTERVIEW_TRAINER_FAST_ENABLE_THINKING=
set INTERVIEW_TRAINER_FAST_TIMEOUT_S=12
set INTERVIEW_TRAINER_SMART_PROVIDER=openai
set INTERVIEW_TRAINER_SMART_API_KEY=your-smart-key
set INTERVIEW_TRAINER_SMART_BASE_URL=https://smart-provider.example/v1
set INTERVIEW_TRAINER_SMART_MODEL=your-smart-model
set INTERVIEW_TRAINER_SMART_ENABLE_THINKING=
set INTERVIEW_TRAINER_SMART_TIMEOUT_S=45
```

If you want an instant local starter while a slower remote model works on `full`, use a mixed setup:

```powershell
set INTERVIEW_TRAINER_FAST_PROVIDER=template
set INTERVIEW_TRAINER_FAST_MODEL=template-fast
set INTERVIEW_TRAINER_SMART_PROVIDER=openai
set INTERVIEW_TRAINER_SMART_API_KEY=your-smart-key
set INTERVIEW_TRAINER_SMART_BASE_URL=https://your-provider.example/v1
set INTERVIEW_TRAINER_SMART_MODEL=your-smart-model
set INTERVIEW_TRAINER_SMART_TIMEOUT_S=45
```

Notes:

- generation now prefers `INTERVIEW_TRAINER_LLM_API_KEY` and `INTERVIEW_TRAINER_LLM_BASE_URL`
- if those are missing, it falls back to `OPENAI_API_KEY` and `OPENAI_BASE_URL`
- this lets you run answer generation on an OpenAI-compatible provider while keeping ASR on a separate OpenAI setup
- `INTERVIEW_TRAINER_FAST_*` and `INTERVIEW_TRAINER_SMART_*` override the shared generation settings per lane
- if a lane does not define its own provider/key/base URL, it falls back to the shared `INTERVIEW_TRAINER_LLM_*` values
- a lane can also be forced back to `template`, which is useful when you want an instant local starter while a slower remote model handles `full`
- `INTERVIEW_TRAINER_LLM_ENABLE_THINKING`, `INTERVIEW_TRAINER_FAST_ENABLE_THINKING`, and `INTERVIEW_TRAINER_SMART_ENABLE_THINKING` are optional; leave them empty to preserve provider defaults
- lane-specific `*_ENABLE_THINKING` values override the shared `INTERVIEW_TRAINER_LLM_ENABLE_THINKING`
- this is especially useful for DashScope Qwen 3.5 models when you want `enable_thinking=false` on the fast lane
- if the fast lane points at DashScope compatible mode and you do not set a fast model, the backend now defaults the fast lane to `qwen3.5-flash`
- in that DashScope fast-lane default, `enable_thinking=false` is applied automatically so the starter path stays latency-oriented
- `INTERVIEW_TRAINER_FAST_PRESET` is an optional shortcut for fast-lane model switching; supported values are `dashscope-flash`, `qwen3.5-flash`, `dashscope-plus`, and `qwen3.5-plus`
- when `INTERVIEW_TRAINER_FAST_PRESET` is set, it overrides `INTERVIEW_TRAINER_FAST_MODEL`; `INTERVIEW_TRAINER_FAST_ENABLE_THINKING` can still override the preset's default thinking mode
- when `INTERVIEW_TRAINER_LLM_STARTER_STREAM=true`, starter drafts use streaming chat completions when the provider supports SSE
- the backend will surface `starter_streaming` with a partial starter draft before the final starter is complete
- `answer.metrics.starter_stream_ms` records when the first visible starter fragment appeared, so you can compare first-token latency against final starter latency

### ASR transcription

```powershell
set INTERVIEW_TRAINER_ASR_PROVIDER=openai
set OPENAI_API_KEY=sk-...
set INTERVIEW_TRAINER_ASR_MODEL=gpt-4o-mini-transcribe
set INTERVIEW_TRAINER_ASR_LANGUAGE=zh
set INTERVIEW_TRAINER_ASR_PROMPT=Technical interview about AI agents and LLM applications.
set INTERVIEW_TRAINER_ASR_ENERGY_GATE=true
set INTERVIEW_TRAINER_ASR_ENERGY_THRESHOLD=0.003
set INTERVIEW_TRAINER_ASR_MIN_DURATION_MS=120
set INTERVIEW_TRAINER_ASR_ADAPTIVE_GATE=true
set INTERVIEW_TRAINER_ASR_ADAPTIVE_MULTIPLIER=2.5
set INTERVIEW_TRAINER_ASR_ADAPTIVE_FLOOR_RATIO=0.5
set INTERVIEW_TRAINER_ASR_NOISE_ALPHA=0.18
set INTERVIEW_TRAINER_BRIDGE_TARGET_MS=450
set INTERVIEW_TRAINER_BRIDGE_MAX_BUFFER_MS=1200
set INTERVIEW_TRAINER_VAD_FRAME_MS=30
set INTERVIEW_TRAINER_VAD_MIN_RATIO=0.25
set INTERVIEW_TRAINER_VAD_MIN_FRAMES=2
set INTERVIEW_TRAINER_VAD_MAX_ZCR=0.35
set INTERVIEW_TRAINER_VAD_MIN_DELTA=0.0005
set INTERVIEW_TRAINER_VAD_HANGOVER_FRAMES=1
set OPENAI_BASE_URL=https://subrouter.ai/v1
```

For live bridge streaming via the Realtime API:

```powershell
set INTERVIEW_TRAINER_ASR_PROVIDER=openai_realtime
set OPENAI_API_KEY=sk-...
set INTERVIEW_TRAINER_ASR_MODEL=gpt-4o-mini-transcribe
set INTERVIEW_TRAINER_ASR_REALTIME_SAMPLE_RATE=24000
set INTERVIEW_TRAINER_ASR_REALTIME_CONNECT_TIMEOUT_S=10
set INTERVIEW_TRAINER_ASR_REALTIME_RECV_TIMEOUT_S=0.05
set INTERVIEW_TRAINER_ASR_REALTIME_DRAIN_TIMEOUT_S=1.2
set INTERVIEW_TRAINER_ASR_REALTIME_BETA_HEADER=realtime=v1
set OPENAI_BASE_URL=https://subrouter.ai/v1
```

For live bridge streaming via Alibaba Cloud realtime ASR:

```powershell
set INTERVIEW_TRAINER_ASR_PROVIDER=alibaba_realtime
set INTERVIEW_TRAINER_ALIBABA_API_KEY=your-dashscope-key
set INTERVIEW_TRAINER_ALIBABA_WS_URL=wss://dashscope.aliyuncs.com/api-ws/v1/inference
set INTERVIEW_TRAINER_ASR_MODEL=fun-asr-realtime-2026-02-28
set INTERVIEW_TRAINER_ASR_LANGUAGE=zh
set INTERVIEW_TRAINER_ALIBABA_VOCABULARY_ID=your-agent-interview-vocabulary-id
set INTERVIEW_TRAINER_ASR_REALTIME_CONNECT_TIMEOUT_S=10
set INTERVIEW_TRAINER_ASR_REALTIME_RECV_TIMEOUT_S=0.05
set INTERVIEW_TRAINER_ASR_REALTIME_DRAIN_TIMEOUT_S=1.2
```

Notes:

- `ChatGPT Plus` does not provide API quota for these calls
- if the env vars are missing, the app falls back to template providers
- the default energy gate skips low-energy or too-short chunks before they hit ASR
- the live bridge also keeps a small per-source buffer and an adaptive threshold based on recent noise floor
- the VAD layer now looks at energy, zero-crossing rate, waveform delta, and a short hangover window instead of only RMS
- direct `POST /api/audio/sessions/{audio_session_id}/transcribe` stays on chunked transcription even when `INTERVIEW_TRAINER_ASR_PROVIDER=openai_realtime`
- the live bridge uses local VAD/buffering to decide chunk boundaries, then sends those chunks over a persistent Realtime WebSocket
- when Realtime is enabled, the bridge also exposes `partial_transcripts` so the UI can show live incremental text before the final transcript lands
- `INTERVIEW_TRAINER_ASR_PROVIDER=alibaba_realtime` now also covers direct chunk transcription and realtime fallback chunks by using a one-shot Alibaba realtime ASR call
- for interview terminology accuracy on Alibaba ASR, create a custom vocabulary in DashScope and set `INTERVIEW_TRAINER_ALIBABA_VOCABULARY_ID`

### Optional audio dependencies

```powershell
cd backend
python -m pip install ".[audio]"
```

### Optional realtime dependency

```powershell
cd backend
python -m pip install ".[realtime]"
```

## Run Backend

Install backend dependencies:

```powershell
cd backend
python -m pip install -r requirements.txt
```

Run the deterministic text-only demo:

```powershell
set PYTHONPATH=src
python -m interview_trainer --demo
```

Inspect local audio support:

```powershell
set PYTHONPATH=src
python -m interview_trainer --audio-info
```

Show the recommended Windows audio plan:

```powershell
set PYTHONPATH=src
python -m interview_trainer --audio-plan
```

Run a manual audio session demo:

```powershell
set PYTHONPATH=src
python -m interview_trainer --audio-session-demo
```

Run the new end-to-end transcription demo:

```powershell
set PYTHONPATH=src
python -m interview_trainer --transcription-demo
```

Run the continuous bridge demo:

```powershell
set PYTHONPATH=src
python -m interview_trainer --live-bridge-demo
```

Start the API:

```powershell
set PYTHONPATH=src
python -m interview_trainer --serve --host 127.0.0.1 --port 8000
```

## Tests

```powershell
cd backend
set PYTHONPATH=src
python -m unittest discover -s tests -v
```

## API

```text
GET  /health
GET  /api/audio/capabilities
GET  /api/audio/recommendation
POST /api/audio/sessions
GET  /api/audio/sessions/{audio_session_id}
POST /api/audio/sessions/{audio_session_id}/start
POST /api/audio/sessions/{audio_session_id}/stop
POST /api/audio/sessions/{audio_session_id}/frames
POST /api/audio/sessions/{audio_session_id}/drain
POST /api/audio/sessions/{audio_session_id}/transcribe
GET  /api/audio/live-bridges
POST /api/audio/live-bridges
GET  /api/audio/live-bridges/{bridge_id}
POST /api/audio/live-bridges/{bridge_id}/start
POST /api/audio/live-bridges/{bridge_id}/stop
POST /api/knowledge/compile
GET  /api/workspaces
POST /api/workspaces
GET  /api/workspaces/{workspace_id}
PUT  /api/workspaces/{workspace_id}
POST /api/workspaces/{workspace_id}/compile
POST /api/workspaces/{workspace_id}/import-path
POST /api/sessions
GET  /api/sessions/{session_id}
GET  /api/sessions/{session_id}/answers/{turn_id}
POST /api/sessions/{session_id}/transcripts
POST /api/sessions/{session_id}/tick
```

`POST /api/audio/sessions/{audio_session_id}/transcribe` example:

```json
{
  "source": "system",
  "session_id": "existing-interview-session-id",
  "max_frames": 12,
  "language": "zh",
  "prompt": "AI agent interview",
  "text_override": "",
  "auto_tick_offset_s": 1.0
}
```

`POST /api/audio/live-bridges` example:

```json
{
  "audio_session_id": "existing-audio-session-id",
  "session_id": "existing-interview-session-id",
  "sources": ["system", "mic"],
  "poll_interval_ms": 450,
  "max_frames_per_chunk": 4,
  "language": "zh",
  "prompt": "AI agent interview",
  "auto_tick_offset_s": 1.0,
  "auto_start": true
}
```

## Desktop

Current UI includes:

- knowledge workspace panel
- answer engine panel for switching the fast-lane Qwen preset and `enable_thinking`
- local path import input for project docs/code
- JD and company briefing panel
- audio plan card
- audio session controls
- live bridge controls
- live transcript rail
- live partial transcript banner
- ASR quick fix strip
- `starter` and `full` answer stack
- demo session and demo turn actions
- `Transcribe System Chunk` button for audio-to-answer integration testing
- `Start Live Bridge` / `Stop Live Bridge` controls for continuous polling

Build the renderer:

```powershell
cd desktop
npm install
npm run build
```

Renderer-only dev mode:

```powershell
cd desktop
npm install
npm run dev:renderer
```

## Current Gaps

- multi-interviewer speaker separation inside the system stream is not implemented
- full upload/indexing UI still needs to be built
- Electron runtime download remains an external environment issue on this machine
