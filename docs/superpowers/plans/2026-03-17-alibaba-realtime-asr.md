# Alibaba Realtime ASR Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Alibaba realtime ASR support for live interview transcription while preserving the current chunk transcription fallback path.

**Architecture:** Extend transcription config with Alibaba-specific settings, add an Alibaba realtime stream that conforms to the existing realtime protocol, and make the live bridge choose the correct realtime stream based on provider. Keep chunked transcription unchanged so realtime failures degrade safely.

**Tech Stack:** Python 3.11+, FastAPI backend, websocket-client, unittest

---

## Chunk 1: Config and provider selection

### Task 1: Add Alibaba transcription settings

**Files:**
- Modify: `backend/src/interview_trainer/config.py`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

Add a test that sets Alibaba realtime env vars and asserts `TranscriptionSettings.from_env()` reads provider, websocket URL, model, app key, and hotwords correctly.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest backend.tests.test_config`
Expected: FAIL because Alibaba transcription fields do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Extend `TranscriptionSettings` and `from_env()` with Alibaba env-backed fields and helper properties for realtime provider detection.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest backend.tests.test_config`
Expected: PASS

- [ ] **Step 5: Commit**

Run:

```bash
git add backend/src/interview_trainer/config.py backend/tests/test_config.py
git commit -m "feat: add alibaba transcription settings"
```

### Task 2: Make realtime stream selection provider-aware

**Files:**
- Modify: `backend/src/interview_trainer/transcription.py`
- Test: `backend/tests/test_transcription.py`

- [ ] **Step 1: Write the failing test**

Add a test that builds `AudioTranscriptionService` with `provider="alibaba_realtime"` and asserts the default realtime stream factory creates the Alibaba stream type.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest backend.tests.test_transcription`
Expected: FAIL because the factory always returns the OpenAI realtime stream.

- [ ] **Step 3: Write minimal implementation**

Update realtime stream factory selection to branch on transcription provider.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest backend.tests.test_transcription`
Expected: PASS

- [ ] **Step 5: Commit**

Run:

```bash
git add backend/src/interview_trainer/transcription.py backend/tests/test_transcription.py
git commit -m "feat: route realtime transcription by provider"
```

## Chunk 2: Alibaba realtime stream

### Task 3: Add Alibaba realtime stream implementation

**Files:**
- Modify: `backend/src/interview_trainer/realtime_transcription.py`
- Test: `backend/tests/test_transcription.py`

- [ ] **Step 1: Write the failing test**

Add stream-level tests for Alibaba websocket event translation into partial and completed transcript events.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest backend.tests.test_transcription`
Expected: FAIL because Alibaba stream implementation does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `AlibabaRealtimeTranscriptionStream` implementing the existing protocol and adapting Alibaba websocket payloads into the shared event types.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest backend.tests.test_transcription`
Expected: PASS

- [ ] **Step 5: Commit**

Run:

```bash
git add backend/src/interview_trainer/realtime_transcription.py backend/tests/test_transcription.py
git commit -m "feat: add alibaba realtime transcription stream"
```

## Chunk 3: Bridge integration and fallback

### Task 4: Integrate Alibaba realtime into the live bridge

**Files:**
- Modify: `backend/src/interview_trainer/transcription.py`
- Test: `backend/tests/test_transcription.py`

- [ ] **Step 1: Write the failing test**

Add bridge tests that confirm:

- `provider="alibaba_realtime"` uses realtime mode
- stream startup works with stubbed Alibaba streams
- startup failure falls back to chunk mode with a readable reason

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest backend.tests.test_transcription`
Expected: FAIL because bridge preparation is only wired for OpenAI realtime semantics.

- [ ] **Step 3: Write minimal implementation**

Adjust realtime eligibility checks and bridge startup paths so Alibaba realtime is handled identically to OpenAI realtime at the bridge level.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest backend.tests.test_transcription`
Expected: PASS

- [ ] **Step 5: Commit**

Run:

```bash
git add backend/src/interview_trainer/transcription.py backend/tests/test_transcription.py
git commit -m "feat: support alibaba realtime bridge fallback"
```

## Chunk 4: Setup and verification

### Task 5: Document setup and run verification

**Files:**
- Modify: `.vscode/launch.json`
- Optional Modify: `README.md`

- [ ] **Step 1: Write the failing test**

No automated test required. Treat this as a verification and developer-experience task.

- [ ] **Step 2: Add Alibaba env examples**

Update local launch/debug config or docs with Alibaba realtime env vars and hotword examples.

- [ ] **Step 3: Run verification**

Run:

```bash
python -m unittest discover -s backend/tests
```

Expected: PASS

- [ ] **Step 4: Commit**

Run:

```bash
git add .vscode/launch.json README.md
git commit -m "docs: add alibaba realtime asr setup"
```
