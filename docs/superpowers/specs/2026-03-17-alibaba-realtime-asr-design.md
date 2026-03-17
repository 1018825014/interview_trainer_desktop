# Alibaba Realtime ASR Design

**Date:** 2026-03-17

**Goal:** Add Alibaba Cloud realtime ASR to the backend for live interview transcription, while keeping the existing chunked transcription path as the fallback path.

## Context

The backend currently supports:

- Chunked transcription through `OpenAITranscriptionProvider`
- Realtime streaming transcription through `OpenAIRealtimeTranscriptionStream`
- Live bridge orchestration in `AudioTranscriptionService`

The user wants a production-oriented ASR path that is usable in mainland China, prioritizes low latency, and can recognize LLM interview terminology accurately.

## Recommended Approach

Use Alibaba Cloud realtime ASR as a new realtime provider and keep the current chunked path unchanged for fallback.

Why this approach:

- It targets the highest-value path first: low-latency live interviews.
- It minimizes risk by avoiding a simultaneous rewrite of chunked transcription.
- It leaves a safe fallback path in place when realtime setup or connectivity fails.

## Scope

In scope:

- New transcription config for Alibaba realtime credentials, endpoint, app key, model, and hotwords
- New realtime stream implementation for Alibaba
- Realtime stream factory selection based on transcription provider
- Live bridge compatibility with Alibaba partial and final transcript events
- Tests covering config parsing, realtime provider selection, and fallback behavior
- Developer-facing setup notes

Out of scope for this phase:

- Replacing chunked transcription with Alibaba batch ASR
- Frontend settings UI
- Secret storage beyond environment variables

## Architecture

### Provider model

`AudioTranscriptionService` will continue to own the live bridge workflow. The change is to make realtime stream creation provider-aware.

- `provider=template` keeps the current deterministic local mode
- `provider=openai_realtime` keeps the current OpenAI realtime mode
- `provider=alibaba_realtime` uses a new Alibaba realtime stream implementation

Chunked fallback remains unchanged:

- If realtime stream initialization fails, the bridge falls back to chunk mode
- Chunk mode continues to use `TemplateTranscriptionProvider` or `OpenAITranscriptionProvider` based on existing settings

### Alibaba realtime stream

Create a new realtime stream class that implements the existing `RealtimeTranscriptionStream` protocol:

- `start()`
- `enqueue_chunk(...)`
- `poll_partials(...)`
- `poll_completed(...)`
- `close()`

The stream should adapt Alibaba websocket events into the project's existing event types:

- `RealtimeTranscriptDeltaEvent`
- `RealtimeTranscriptEvent`

This keeps the rest of the bridge logic unchanged.

### Configuration

Extend `TranscriptionSettings` with Alibaba-specific env-backed settings, including:

- API key or token
- WebSocket URL
- model name
- app key if required by the chosen API variant
- hotwords string/list
- optional sample rate override

The existing `provider` field remains the top-level switch.

### Hotword strategy

Support a simple environment-variable-based hotword list in phase one. This is the main accuracy lever for interview terminology.

Expected examples:

- `RAG`
- `MCP`
- `embedding`
- `reranker`
- `tool calling`
- `prompt caching`
- `context window`
- `agent orchestration`

## Error Handling

- Realtime connection/setup failure should not crash the bridge startup path
- On realtime failure, the bridge should switch to `active_asr_mode="chunk"` and record a human-readable fallback reason
- Provider-specific parsing failures should surface as runtime errors with clear context

## Testing

Add tests for:

- Alibaba env parsing in `TranscriptionSettings`
- Realtime stream factory/provider selection
- Live bridge initialization with Alibaba realtime
- Realtime fallback behavior when Alibaba stream creation fails

## Success Criteria

- Backend can start with `INTERVIEW_TRAINER_ASR_PROVIDER=alibaba_realtime`
- Live bridge emits partial and final transcripts through the same API shape as today
- Realtime failures fall back cleanly to chunk mode
- Hotwords can be configured without code changes
