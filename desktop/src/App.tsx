import { useEffect, useMemo, useState } from "react";
import {
  createLiveBridge,
  createAudioSession,
  createSession,
  fetchAudioCapabilities,
  fetchAudioRecommendation,
  getAnswer,
  getGenerationSettings,
  getLiveBridge,
  pingBackend,
  pushAudioFrame,
  sendTranscript,
  startAudioSession,
  stopLiveBridge,
  tickSession,
  transcribeAudioSession,
  updateGenerationSettings,
} from "./api/client";
import { LibraryPanel } from "./components/library/LibraryPanel";
import {
  demoTurnTranscript,
  sampleAnswer,
  sampleAudioRecommendation,
  sampleAudioSession,
  sampleBrief,
  sampleCorrections,
  sampleSessionPayload,
  sampleTranscripts,
} from "./mock/sample";
import {
  AnswerStatusView,
  AnswerView,
  AudioCapabilitiesPayload,
  AudioCapabilitiesView,
  AudioDeviceView,
  AudioRecommendationView,
  AudioSessionView,
  AudioTranscriptionView,
  CorrectionSuggestionView,
  GenerationSettingsView,
  LibrarySessionPayload,
  LiveBridgeView,
  PartialTranscriptView,
  PrewarmView,
  SessionBriefView,
  TranscriptFeedItem,
} from "./types";

type DemoStatus = "idle" | "creating_session" | "running_turn" | "ready" | "error";

function App() {
  const [alwaysOnTop, setAlwaysOnTop] = useState(true);
  const [backendOnline, setBackendOnline] = useState(false);
  const [audioFetchedAt, setAudioFetchedAt] = useState<number>(0);
  const [sessionId, setSessionId] = useState<string>("");
  const [demoStatus, setDemoStatus] = useState<DemoStatus>("idle");
  const [brief, setBrief] = useState<SessionBriefView>(sampleBrief);
  const [audioPlan, setAudioPlan] = useState<AudioRecommendationView>(sampleAudioRecommendation);
  const [audioCapabilities, setAudioCapabilities] = useState<AudioCapabilitiesView[]>([]);
  const [selectedSystemDeviceIndex, setSelectedSystemDeviceIndex] = useState<number | null>(null);
  const [selectedMicDeviceIndex, setSelectedMicDeviceIndex] = useState<number | null>(null);
  const [audioSession, setAudioSession] = useState<AudioSessionView | null>(sampleAudioSession);
  const [liveBridge, setLiveBridge] = useState<LiveBridgeView | null>(null);
  const [lastTranscription, setLastTranscription] = useState<AudioTranscriptionView | null>(null);
  const [transcripts, setTranscripts] = useState<TranscriptFeedItem[]>(sampleTranscripts);
  const [partialTranscripts, setPartialTranscripts] = useState<PartialTranscriptView[]>([]);
  const [prewarm, setPrewarm] = useState<PrewarmView | null>(null);
  const [answer, setAnswer] = useState<AnswerView>(sampleAnswer);
  const [generationSettings, setGenerationSettings] = useState<GenerationSettingsView | null>(null);
  const [selectedFastPreset, setSelectedFastPreset] = useState("qwen3.5-flash");
  const [fastThinkingEnabled, setFastThinkingEnabled] = useState(false);
  const [generationStatus, setGenerationStatus] = useState("Waiting for backend");
  const [generationSaving, setGenerationSaving] = useState(false);
  const [corrections, setCorrections] = useState<CorrectionSuggestionView[]>(sampleCorrections);
  const [errorMessage, setErrorMessage] = useState("");
  const backendBaseUrl = window.interviewTrainer?.backendBaseUrl ?? "http://127.0.0.1:8000";
  const platform = window.interviewTrainer?.platform ?? "web";

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      const online = await pingBackend(backendBaseUrl);
      if (!cancelled) {
        setBackendOnline(online);
      }
    };
    void tick();
    const timer = window.setInterval(tick, 1500);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [backendBaseUrl]);

  useEffect(() => {
    if (!backendOnline) {
      return;
    }
    if (Date.now() - audioFetchedAt < 1200) {
      return;
    }
    let cancelled = false;
    const refresh = async () => {
      try {
        const capsPayload = (await fetchAudioCapabilities(backendBaseUrl)) as AudioCapabilitiesPayload;
        if (!cancelled) {
          setAudioCapabilities(capsPayload.capabilities ?? []);
        }
      } catch {
        // ignore
      }
      try {
        const recPayload = await fetchAudioRecommendation(backendBaseUrl);
        const recommendation = recPayload.recommendation as AudioRecommendationView;
        if (!cancelled) {
          setAudioPlan(recommendation);
          setSelectedSystemDeviceIndex((prev) => (prev === null ? recommendation.system_device?.index ?? null : prev));
          setSelectedMicDeviceIndex((prev) => (prev === null ? recommendation.mic_device?.index ?? null : prev));
          setAudioFetchedAt(Date.now());
        }
      } catch {
        // ignore
      }
    };
    void refresh();
    return () => {
      cancelled = true;
    };
  }, [backendOnline, backendBaseUrl, audioFetchedAt]);

  useEffect(() => {
    if (!backendOnline) {
      return;
    }
    let cancelled = false;
    const loadGenerationSettings = async () => {
      try {
        const payload = (await getGenerationSettings(backendBaseUrl)) as GenerationSettingsView;
        if (cancelled) {
          return;
        }
        setGenerationSettings(payload);
        setSelectedFastPreset(resolveFastPresetSelection(payload));
        setFastThinkingEnabled(Boolean(payload.fast_enable_thinking));
        setGenerationStatus("Synced from backend");
      } catch {
        if (!cancelled) {
          setGenerationStatus("Backend settings unavailable");
        }
      }
    };
    void loadGenerationSettings();
    return () => {
      cancelled = true;
    };
  }, [backendOnline, backendBaseUrl]);

  const deviceCatalog = useMemo(() => {
    const byBackend = new Map<string, AudioDeviceView[]>();
    for (const capability of audioCapabilities) {
      byBackend.set(capability.backend, capability.devices ?? []);
    }
    return byBackend;
  }, [audioCapabilities]);

  const devicesForPlanBackend = useMemo(() => {
    return deviceCatalog.get(audioPlan.backend) ?? [];
  }, [deviceCatalog, audioPlan.backend]);

  const systemDeviceOptions = useMemo(() => {
    return devicesForPlanBackend.filter((device) => device.is_loopback_candidate && device.max_input_channels > 0);
  }, [devicesForPlanBackend]);

  const micDeviceOptions = useMemo(() => {
    return devicesForPlanBackend.filter((device) => device.max_input_channels > 0 && !device.is_loopback_candidate);
  }, [devicesForPlanBackend]);

  useEffect(() => {
    if (!backendOnline || !liveBridge?.bridge_id || liveBridge.status !== "running") {
      return;
    }

    let cancelled = false;
    const poll = async () => {
      try {
        const latest = (await getLiveBridge(backendBaseUrl, liveBridge.bridge_id)) as LiveBridgeView;
        if (cancelled) {
          return;
        }
        setLiveBridge(latest);
        if (latest.last_error) {
          setErrorMessage(latest.last_error);
        }
        setPartialTranscripts(latest.partial_transcripts ?? []);
        setPrewarm(mapBackendPrewarm(latest.last_prewarm));
        if (latest.recent_transcripts.length > 0) {
          const recent = latest.recent_transcripts.slice(-6);
          setTranscripts(
            recent.map((item) => ({
              speaker: item.speaker,
              text: item.text,
              confidence: item.confidence,
              ts: formatClock(item.ts_end),
            })),
          );
          setLastTranscription(recent[recent.length - 1]);
        }
        if (latest.last_answer) {
          setAnswer(mapBackendAnswer(latest.last_answer));
        }
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(error instanceof Error ? error.message : "Failed to poll live bridge");
        }
      }
    };

    void poll();
    const timer = window.setInterval(poll, Math.max(300, liveBridge.poll_interval_ms));
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [backendOnline, backendBaseUrl, liveBridge?.bridge_id, liveBridge?.status, liveBridge?.poll_interval_ms]);

  const statusText = useMemo(() => {
    if (!backendOnline) {
      return "后端未连接（本地演示模式）";
    }
    if (demoStatus === "creating_session") {
      return "正在创建会话";
    }
    if (demoStatus === "running_turn") {
      return "正在运行演示回合";
    }
    if (demoStatus === "ready" && sessionId) {
      return `会话 ${sessionId.slice(0, 8)}`;
    }
    if (demoStatus === "error") {
      return "后端错误";
    }
    return "后端已连接";
  }, [backendOnline, demoStatus, sessionId]);

  async function handleAlwaysOnTopChange() {
    const nextValue = !alwaysOnTop;
    if (window.interviewTrainer?.setAlwaysOnTop) {
      const actual = await window.interviewTrainer.setAlwaysOnTop(nextValue);
      setAlwaysOnTop(actual);
      return;
    }
    setAlwaysOnTop(nextValue);
  }

  async function handleSaveGenerationSettings() {
    setErrorMessage("");
    setGenerationSaving(true);
    try {
      const updated = (await updateGenerationSettings(backendBaseUrl, {
        fast_preset: selectedFastPreset,
        fast_enable_thinking: fastThinkingEnabled,
      })) as GenerationSettingsView;
      setGenerationSettings(updated);
      setSelectedFastPreset(resolveFastPresetSelection(updated));
      setFastThinkingEnabled(Boolean(updated.fast_enable_thinking));
      setGenerationStatus("Fast lane updated");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to update fast lane settings");
    } finally {
      setGenerationSaving(false);
    }
  }

  async function handleActivateLibrarySession(payload: LibrarySessionPayload) {
    setErrorMessage("");
    setDemoStatus("creating_session");
    try {
      const response = await createSession(backendBaseUrl, {
        knowledge: payload.knowledge,
        briefing: {
          company: payload.briefing.company,
          business_context: payload.briefing.businessContext,
          job_description: payload.briefing.jobDescription,
        },
      });
      setSessionId(response.session_id);
      setBrief({
        company: payload.briefing.company,
        businessContext: payload.briefing.businessContext,
        jobDescription: payload.briefing.jobDescription,
        focusTopics: payload.briefing.focusTopics,
        priorityProjects: payload.briefing.priorityProjects,
        likelyQuestions: payload.briefing.likelyQuestions,
      });
      setDemoStatus("ready");
    } catch (error) {
      setDemoStatus("error");
      setErrorMessage(error instanceof Error ? error.message : "用资料库 preset 创建会话失败");
    }
  }

  async function handleCreateDemoSession() {
    setErrorMessage("");
    setDemoStatus("creating_session");
    try {
      const response = await createSession(backendBaseUrl, sampleSessionPayload);
      setSessionId(response.session_id);
      setDemoStatus("ready");
    } catch (error) {
      setDemoStatus("error");
      setErrorMessage(error instanceof Error ? error.message : "创建会话失败");
    }
  }

  async function handleCreateAudioSession() {
    setErrorMessage("");
    try {
      const created = await createAudioSession(backendBaseUrl, {
        transport: audioPlan.ready ? "native" : "manual",
        sample_rate: audioPlan.sample_rate,
        chunk_ms: audioPlan.chunk_ms,
        system_device_index: selectedSystemDeviceIndex ?? undefined,
        mic_device_index: selectedMicDeviceIndex ?? undefined,
      });
      const started = await startAudioSession(backendBaseUrl, created.session_id);
      setAudioSession(started as AudioSessionView);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "创建音频会话失败");
    }
  }

  async function handleInjectAudioFrame() {
    setErrorMessage("");
    try {
      let current = audioSession;
      if (!current || current.config.transport !== "manual") {
        const created = await createAudioSession(backendBaseUrl, {
          transport: "manual",
          sample_rate: audioPlan.sample_rate,
          chunk_ms: audioPlan.chunk_ms,
        });
        current = (await startAudioSession(backendBaseUrl, created.session_id)) as AudioSessionView;
      }
      const pushed = await pushAudioFrame(backendBaseUrl, current.session_id, {
        source: "system",
        pcm_text: "manual-dev-frame",
      });
      setAudioSession(pushed.session as AudioSessionView);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "注入演示音频帧失败");
    }
  }

  async function handleStartLiveBridge() {
    setErrorMessage("");
    try {
      let currentAudioSession = audioSession;
      if (!currentAudioSession) {
        const created = await createAudioSession(backendBaseUrl, {
          transport: audioPlan.ready ? "native" : "manual",
          sample_rate: audioPlan.sample_rate,
          chunk_ms: audioPlan.chunk_ms,
          system_device_index: selectedSystemDeviceIndex ?? undefined,
          mic_device_index: selectedMicDeviceIndex ?? undefined,
        });
        currentAudioSession = (await startAudioSession(backendBaseUrl, created.session_id)) as AudioSessionView;
        setAudioSession(currentAudioSession);
      } else if (currentAudioSession.status !== "running") {
        currentAudioSession = (await startAudioSession(backendBaseUrl, currentAudioSession.session_id)) as AudioSessionView;
        setAudioSession(currentAudioSession);
      }

      let activeSessionId = sessionId;
      if (!activeSessionId) {
        const response = await createSession(backendBaseUrl, sampleSessionPayload);
        activeSessionId = response.session_id;
        setSessionId(activeSessionId);
      }

      const createdBridge = (await createLiveBridge(backendBaseUrl, {
        audio_session_id: currentAudioSession.session_id,
        session_id: activeSessionId,
        sources: ["system", "mic"],
        poll_interval_ms: Math.max(350, audioPlan.chunk_ms + 100),
        max_frames_per_chunk: currentAudioSession.config.transport === "native" ? 4 : 2,
        auto_start: true,
      })) as LiveBridgeView;
      setLiveBridge(createdBridge);
      setPartialTranscripts(createdBridge.partial_transcripts ?? []);
      setPrewarm(mapBackendPrewarm(createdBridge.last_prewarm));
      setDemoStatus("ready");
    } catch (error) {
      setDemoStatus("error");
      setErrorMessage(error instanceof Error ? error.message : "启动实时桥接失败");
    }
  }

  async function handleStopLiveBridge() {
    if (!liveBridge?.bridge_id) {
      return;
    }
    setErrorMessage("");
    try {
      const stopped = (await stopLiveBridge(backendBaseUrl, liveBridge.bridge_id)) as LiveBridgeView;
      setLiveBridge(stopped);
      setPartialTranscripts(stopped.partial_transcripts ?? []);
      setPrewarm(mapBackendPrewarm(stopped.last_prewarm));
      if (stopped.last_answer) {
        const mapped = mapBackendAnswer(stopped.last_answer);
        setAnswer(mapped);
        if (
          stopped.interview_session_id &&
          stopped.last_answer.turn_id &&
          (mapped.status === "pending" || mapped.status === "starter_ready")
        ) {
          await pollAnswerUntilSettled(
            backendBaseUrl,
            stopped.interview_session_id,
            stopped.last_answer.turn_id,
            setAnswer,
          );
        }
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "停止实时桥接失败");
    }
  }

  async function handleTranscribeSystemAudio() {
    setErrorMessage("");
    try {
      let current = audioSession;
      let textOverride = "";

      if (!current || current.queued_frames === 0) {
        const created = await createAudioSession(backendBaseUrl, {
          transport: "manual",
          sample_rate: audioPlan.sample_rate,
          chunk_ms: audioPlan.chunk_ms,
        });
        current = (await startAudioSession(backendBaseUrl, created.session_id)) as AudioSessionView;
        const pushed = await pushAudioFrame(backendBaseUrl, current.session_id, {
          source: "system",
          pcm_text: "manual-dev-frame",
        });
        current = pushed.session as AudioSessionView;
        textOverride = demoTurnTranscript.text;
      }

      let activeSessionId = sessionId;
      if (!activeSessionId) {
        const response = await createSession(backendBaseUrl, sampleSessionPayload);
        activeSessionId = response.session_id;
        setSessionId(activeSessionId);
      }

      const result = await transcribeAudioSession(backendBaseUrl, current.session_id, {
        source: "system",
        session_id: activeSessionId,
        text_override: textOverride,
      });

      setAudioSession(result.session as AudioSessionView);
      if (result.skipped) {
        setErrorMessage(result.reason ?? "No audio frames available to transcribe");
        return;
      }

      const transcription = result.transcript as AudioTranscriptionView;
      setLastTranscription(transcription);
      setTranscripts([
        {
          speaker: transcription.speaker,
          text: transcription.text,
          confidence: transcription.confidence,
          ts: formatClock(transcription.ts_end),
        },
      ]);

      if (result.interview) {
        setCorrections((result.interview.corrections ?? []) as CorrectionSuggestionView[]);
        setPrewarm(mapBackendPrewarm(result.interview.prewarm));
        if (result.interview.answer) {
          const mapped = mapBackendAnswer(result.interview.answer);
          setAnswer(mapped);
          if (result.interview.answer.turn_id) {
            await pollAnswerUntilSettled(backendBaseUrl, activeSessionId, result.interview.answer.turn_id, setAnswer);
          }
        }
      }
      setDemoStatus("ready");
    } catch (error) {
      setDemoStatus("error");
      setErrorMessage(error instanceof Error ? error.message : "音频转写失败");
    }
  }

  async function handleRunDemoTurn() {
    setErrorMessage("");
    setDemoStatus("running_turn");

    try {
      let activeSessionId = sessionId;
      if (!activeSessionId) {
        const response = await createSession(backendBaseUrl, sampleSessionPayload);
        activeSessionId = response.session_id;
        setSessionId(activeSessionId);
      }

      const transcriptResponse = await sendTranscript(backendBaseUrl, activeSessionId, demoTurnTranscript);
      const immediateAnswer =
        transcriptResponse.answer ??
        (await tickSession(backendBaseUrl, activeSessionId, demoTurnTranscript.ts_end + 1.2)).answer;

      setTranscripts([
        {
          speaker: demoTurnTranscript.speaker,
          text: demoTurnTranscript.text,
          confidence: demoTurnTranscript.confidence,
          ts: "00:04",
        },
      ]);
      setCorrections((transcriptResponse.corrections ?? []) as CorrectionSuggestionView[]);
      setPrewarm(mapBackendPrewarm(transcriptResponse.prewarm));

      if (immediateAnswer) {
        setAnswer(mapBackendAnswer(immediateAnswer));
        if (immediateAnswer.turn_id) {
          await pollAnswerUntilSettled(backendBaseUrl, activeSessionId, immediateAnswer.turn_id, setAnswer);
        }
      }
      setDemoStatus("ready");
    } catch (error) {
      setDemoStatus("error");
      setErrorMessage(error instanceof Error ? error.message : "运行演示回合失败");
    }
  }

  return (
    <div className="shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Windows 面试训练助手</p>
          <h1>用于实时模拟面试的可见悬浮面板</h1>
          <p className="lede">
            用于模拟面试训练：JD/公司简报、实时转写轨道、starter/full 分层回答、术语纠错与证据引用。
          </p>
        </div>
        <div className="hero-actions">
          <button className="ghost" onClick={handleAlwaysOnTopChange}>
            {alwaysOnTop ? "取消置顶" : "保持置顶"}
          </button>
          <button className="ghost accent" disabled={!backendOnline || demoStatus === "creating_session"} onClick={handleCreateDemoSession}>
            创建演示会话
          </button>
          <button className="ghost accent" disabled={!backendOnline || demoStatus === "running_turn"} onClick={handleRunDemoTurn}>
            运行演示回合
          </button>
          <span className="platform-tag">{platform}</span>
          <span className={`status ${demoStatus === "error" ? "offline" : backendOnline ? "online" : "offline"}`}>
            {statusText}
          </span>
          <small className="backend-meta">{backendBaseUrl}</small>
          {errorMessage ? <small className="backend-error">{errorMessage}</small> : null}
        </div>
      </header>

      <main className="grid">
        <section className="panel panel-generation">
          <div className="panel-head">
            <span>Answer Engine</span>
            <strong>{generationSettings?.fast_model ?? "Not loaded"}</strong>
          </div>
          <div className="meta-card">
            <div className="panel-head compact">
              <span>Fast Lane</span>
              <strong>{generationSettings?.fast_provider ?? "template"}</strong>
            </div>
            <p>
              Base URL: <strong>{generationSettings?.fast_base_url ?? backendBaseUrl}</strong>
            </p>
            <p>
              Current model: <strong>{generationSettings?.fast_model ?? "qwen3.5-flash"}</strong> | Thinking:{" "}
              <strong>{formatThinkingMode(generationSettings?.fast_enable_thinking ?? null)}</strong>
            </p>
            <label>
              Fast preset
              <select value={selectedFastPreset} onChange={(event) => setSelectedFastPreset(event.target.value)}>
                {(generationSettings?.fast_preset_options ?? defaultFastPresetOptions()).map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.model}
                  </option>
                ))}
              </select>
            </label>
            <label className="toggle-row">
              <input
                type="checkbox"
                checked={fastThinkingEnabled}
                onChange={(event) => setFastThinkingEnabled(event.target.checked)}
              />
              <span>Enable thinking for fast lane</span>
            </label>
            <div className="action-row">
              <button
                className="ghost accent small"
                disabled={!backendOnline || generationSaving}
                onClick={handleSaveGenerationSettings}
              >
                {generationSaving ? "Saving..." : "Apply fast lane"}
              </button>
            </div>
            <p className="backend-meta">{generationStatus}</p>
            <ul className="note-list">
              <li>Preset switching only updates the fast lane. Provider and base URL stay unchanged.</li>
              <li>Changes apply to new answer jobs after the backend accepts the update.</li>
            </ul>
          </div>
        </section>

        <LibraryPanel
          backendBaseUrl={backendBaseUrl}
          backendOnline={backendOnline}
          onActivateSession={handleActivateLibrarySession}
        />

        <section className="panel panel-brief">
          <div className="panel-head">
            <span>会话简报</span>
            <strong>{brief.company}</strong>
          </div>
          <label>
            公司 / 团队
            <input
              value={brief.company}
              onChange={(event) => setBrief({ ...brief, company: event.target.value })}
            />
          </label>
          <label>
            业务背景
            <textarea
              rows={4}
              value={brief.businessContext}
              onChange={(event) => setBrief({ ...brief, businessContext: event.target.value })}
            />
          </label>
          <label>
            职位描述
            <textarea
              rows={7}
              value={brief.jobDescription}
              onChange={(event) => setBrief({ ...brief, jobDescription: event.target.value })}
            />
          </label>

          <div className="meta-card">
            <div className="panel-head compact">
              <span>音频方案</span>
              <strong>{audioPlan.ready ? "可用" : "需要配置"}</strong>
            </div>
            <p>
              后端：<strong>{audioPlan.backend}</strong> | 采样率：<strong>{audioPlan.sample_rate}Hz</strong> | 分片：{" "}
              <strong>{audioPlan.chunk_ms}ms</strong>
            </p>
            <p>
              系统：<strong>{audioPlan.system_device?.name ?? "未找到"}</strong>
            </p>
            <p>
              麦克风：<strong>{audioPlan.mic_device?.name ?? "未找到"}</strong>
            </p>
            <label>
              系统输出（Loopback）
              <select
                value={selectedSystemDeviceIndex === null ? "" : String(selectedSystemDeviceIndex)}
                onChange={(event) => {
                  const next = event.target.value ? Number(event.target.value) : null;
                  setSelectedSystemDeviceIndex(Number.isFinite(next as number) ? (next as number) : null);
                }}
              >
                <option value="">跟随推荐</option>
                {systemDeviceOptions.map((device) => (
                  <option key={device.index} value={String(device.index)}>
                    {device.name} (#{device.index}, {device.hostapi})
                  </option>
                ))}
              </select>
            </label>
            <label>
              麦克风输入
              <select
                value={selectedMicDeviceIndex === null ? "" : String(selectedMicDeviceIndex)}
                onChange={(event) => {
                  const next = event.target.value ? Number(event.target.value) : null;
                  setSelectedMicDeviceIndex(Number.isFinite(next as number) ? (next as number) : null);
                }}
              >
                <option value="">跟随推荐</option>
                {micDeviceOptions.map((device) => (
                  <option key={device.index} value={String(device.index)}>
                    {device.name} (#{device.index}, {device.hostapi})
                  </option>
                ))}
              </select>
            </label>
            <p className="backend-meta">
              使用顺序：先“创建原生会话”，再“启动实时桥接”。如果点“创建原生会话”后出现崩溃，请优先换一个非虚拟声卡的
              Loopback/麦克风设备再试。
            </p>
            <ul className="note-list">
              {audioPlan.notes.map((note) => (
                <li key={note}>{mapAudioNote(note)}</li>
              ))}
            </ul>
            <div className="action-row">
              <button className="ghost accent small" disabled={!backendOnline} onClick={handleCreateAudioSession}>
                {audioPlan.ready ? "创建原生会话" : "创建音频演示会话"}
              </button>
              <button className="ghost small" disabled={!backendOnline} onClick={handleInjectAudioFrame}>
                注入演示帧
              </button>
              <button className="ghost small" disabled={!backendOnline} onClick={handleTranscribeSystemAudio}>
                转写系统音频分片
              </button>
              <button
                className="ghost small"
                disabled={!backendOnline || liveBridge?.status === "running"}
                onClick={handleStartLiveBridge}
              >
                启动实时桥接
              </button>
              <button
                className="ghost small"
                disabled={!backendOnline || liveBridge?.status !== "running"}
                onClick={handleStopLiveBridge}
              >
                停止实时桥接
              </button>
            </div>
            {audioSession ? (
              <div className="session-chip">
                <strong>{audioSession.status}</strong>
                <span>{audioSession.config.transport}</span>
                <span>队列 {audioSession.queued_frames}</span>
                <span>累计 {audioSession.total_frames}</span>
              </div>
            ) : null}
            {lastTranscription ? (
              <div className="session-chip">
                <strong>{lastTranscription.provider}</strong>
                <span>{lastTranscription.model}</span>
                <span>{Math.round(lastTranscription.response_ms)}ms</span>
                <span>{lastTranscription.num_frames} frames</span>
              </div>
            ) : null}
            {liveBridge ? (
              <div className="session-chip">
                <strong>{liveBridge.status}</strong>
                <span>{liveBridge.sources.join(" + ")}</span>
                <span>转写 {liveBridge.transcripts_processed}</span>
                <span>跳过 {liveBridge.skipped_polls}</span>
              </div>
            ) : null}
          </div>

          <div className="token-group">
            <span>重点方向</span>
            <div className="tokens">
              {brief.focusTopics.map((topic) => (
                <span key={topic} className="token">
                  {topic}
                </span>
              ))}
            </div>
          </div>

          <div className="token-group">
            <span>优先项目</span>
            <div className="tokens">
              {brief.priorityProjects.map((project) => (
                <span key={project} className="token token-warm">
                  {project}
                </span>
              ))}
            </div>
          </div>

          <div className="list-block">
            <span>可能追问</span>
            <ul>
              {brief.likelyQuestions.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </section>

        <section className="panel panel-live">
          <div className="panel-head">
            <span>实时轨道</span>
            <strong>{answer.route.mode}</strong>
          </div>

          <div className="route-banner">
            <span>路由</span>
            <p>{answer.route.reason}</p>
          </div>

          {lastTranscription ? (
            <div className="route-banner">
              <span>最近一次转写</span>
              <p>
                {lastTranscription.speaker} via {lastTranscription.provider}:{lastTranscription.model} |{" "}
                {Math.round(lastTranscription.duration_ms)}ms audio | {lastTranscription.language}
              </p>
            </div>
          ) : null}

          {liveBridge ? (
            <div className="route-banner">
              <span>实时桥接</span>
              <p>
                {liveBridge.status} | mode {liveBridge.active_asr_mode} | {liveBridge.poll_interval_ms}ms poll |{" "}
                {liveBridge.cycles} cycles | {liveBridge.transcripts_processed} transcripts
              </p>
            </div>
          ) : null}

          {liveBridge?.realtime_fallback_reason ? (
            <div className="route-banner">
              <span>ASR 回退</span>
              <p>{liveBridge.realtime_fallback_reason}</p>
            </div>
          ) : null}

          {partialTranscripts.length > 0 ? (
            <div className="route-banner">
              <span>实时片段</span>
              <p>
                {partialTranscripts
                  .map((item) => `${item.source}: ${item.text || "（监听中…）"}`)
                  .join(" | ")}
              </p>
            </div>
          ) : null}

          {prewarm ? (
            <div className="route-banner">
              <span>Starter Prewarm</span>
              <p>
                {prewarm.status} | turn {prewarm.turnId.slice(0, 8)} | stream {formatMetric(prewarm.starterStreamMs)} |
                starter {formatMetric(prewarm.starterMs)} | {prewarm.textPreview || prewarm.question}
                {prewarm.error ? ` | ${prewarm.error}` : ""}
              </p>
            </div>
          ) : null}

          {liveBridge?.last_signal ? (
            <div className="route-banner">
              <span>信号门控</span>
              <p>
                {liveBridge.last_signal.passed ? "通过" : "拦截"} | peak {liveBridge.last_signal.peak_rms.toFixed(4)} /
                threshold {liveBridge.last_signal.threshold.toFixed(4)} | ratio {liveBridge.last_signal.voiced_ratio.toFixed(2)} |
                zcr {liveBridge.last_signal.avg_zcr.toFixed(2)} | {Math.round(liveBridge.last_signal.duration_ms)}ms /
                {liveBridge.last_signal.frame_ms}ms frames
                {liveBridge.last_skip_reason ? ` | ${liveBridge.last_skip_reason}` : ""}
              </p>
            </div>
          ) : null}

          {liveBridge && Object.values(liveBridge.source_state ?? {}).length > 0 ? (
            <div className="route-banner">
              <span>桥接来源</span>
              <p>
                {Object.values(liveBridge.source_state)
                  .map(
                    (item) =>
                      `${item.source}: buffer ${Math.round(item.buffered_duration_ms)}ms, threshold ${item.adaptive_threshold.toFixed(4)}, noise ${item.noise_floor_rms.toFixed(4)}${item.partial_text ? `, partial "${item.partial_text}"` : ""}`,
                  )
                  .join(" | ")}
              </p>
            </div>
          ) : null}

          <div className="transcript-list">
            {transcripts.map((item, index) => (
              <article key={`${item.ts}-${index}`} className={`utterance ${item.speaker}`}>
                <div className="utterance-head">
                  <strong>{item.speaker === "interviewer" ? "面试官" : "候选人"}</strong>
                  <span>{item.ts}</span>
                </div>
                <p>{item.text}</p>
                <small>置信度 {item.confidence.toFixed(2)}</small>
              </article>
            ))}
          </div>

          <div className="correction-strip">
            <span>ASR 快速纠错</span>
            {corrections.length === 0 ? (
              <div className="correction-card">
                <strong>暂无纠错建议</strong>
                <p>当实时转写出现低置信度术语时，会在这里提示替换建议。</p>
              </div>
            ) : (
              corrections.map((item) => (
                <div key={item.source_term} className="correction-card">
                  <strong>{item.source_term}</strong>
                  <p>{item.reason}</p>
                  <div className="tokens">
                    {item.replacements.map((replacement) => (
                      <span key={replacement} className="token token-dark">
                        {replacement}
                      </span>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="panel panel-answer">
          <div className="panel-head">
            <span>回答栈</span>
            <strong>{answer.status}</strong>
          </div>

          <div className="metrics-row">
            <span className="token token-outline">stream {formatMetric(answer.metrics.starterStreamMs)}</span>
            <span className="token token-outline">starter {formatMetric(answer.metrics.starterMs)}</span>
            <span className="token token-outline">full {formatMetric(answer.metrics.fullMs)}</span>
            {answer.prewarmedStarter ? (
              <span className="token token-outline">prewarmed starter</span>
            ) : null}
            {answer.status === "starter_streaming" ? (
              <span className="token token-outline">starter 流式输出中</span>
            ) : null}
          </div>

          <article className="answer-card starter">
            <small>{answer.starter.streaming ? "Starter（流式）" : "Starter"}</small>
            <p>{answer.starter.text || "正在生成 starter 草稿…"}</p>
            <ul>
              {answer.starter.bullets.map((bullet) => (
                <li key={bullet}>{bullet}</li>
              ))}
            </ul>
          </article>

          <article className="answer-card full">
            <small>Full</small>
            <p>{answer.full.text || "正在生成 full 草稿…"}</p>
            <ul>
              {answer.full.bullets.map((bullet) => (
                <li key={bullet}>{bullet}</li>
              ))}
            </ul>
          </article>

          {answer.error ? <p className="backend-error">{answer.error}</p> : null}

          <div className="evidence-block">
            <span>证据视图</span>
            <div className="tokens">
              {answer.evidence.map((ref) => (
                <span key={ref} className="token token-outline">
                  {ref}
                </span>
              ))}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

function formatMetric(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "--";
  }
  return `${value.toFixed(0)}ms`;
}

function mapAudioNote(note: string): string {
  const trimmed = note.trim();
  const mapping: Array<[string, string]> = [
    [
      "Use headphones so system audio and microphone remain separated.",
      "建议使用耳机，避免系统声与麦克风互相串音。",
    ],
    [
      "Prefer a WASAPI loopback device for interviewer/system audio.",
      "系统声（面试官/会议声音）优先选择 WASAPI 的 Loopback 设备。",
    ],
    [
      "Use a dedicated microphone input for the candidate channel.",
      "麦克风通道请使用独立的麦克风输入设备。",
    ],
    [
      "pyaudiowpatch is not installed yet, so native capture cannot start.",
      "尚未安装 pyaudiowpatch，无法启动原生采集。",
    ],
    ["No suitable system loopback device was detected.", "未检测到可用的系统 Loopback 设备。"],
    ["No dedicated microphone input device was detected.", "未检测到可用的麦克风输入设备。"],
    [
      "Install PyAudioWPatch to enumerate WASAPI loopback devices.",
      "请安装 PyAudioWPatch 以枚举 WASAPI Loopback 设备。",
    ],
    [
      "This is the preferred backend for Windows system-audio capture.",
      "这是 Windows 系统音频采集的推荐后端。",
    ],
  ];
  for (const [en, zh] of mapping) {
    if (trimmed === en) {
      return zh;
    }
  }
  return trimmed;
}

function formatClock(tsSeconds: number): string {
  const total = Math.max(0, Math.floor(tsSeconds));
  const minutes = Math.floor(total / 60)
    .toString()
    .padStart(2, "0");
  const seconds = (total % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}

async function pollAnswerUntilSettled(
  baseUrl: string,
  sessionId: string,
  turnId: string,
  onUpdate: (value: AnswerView) => void,
) {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    await sleep(attempt < 20 ? 150 : 250);
    const latest = await getAnswer(baseUrl, sessionId, turnId);
    const mapped = mapBackendAnswer(latest);
    onUpdate(mapped);
    if (
      mapped.status === "complete" ||
      mapped.status === "failed" ||
      (mapped.status === "starter_ready" && Boolean(mapped.error))
    ) {
      return;
    }
  }
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function mapBackendAnswer(raw: any): AnswerView {
  const starter = raw.drafts?.starter;
  const full = raw.drafts?.full;
  const evidenceIds = new Set<string>();
  for (const item of [...(starter?.evidence_refs ?? []), ...(full?.evidence_refs ?? [])]) {
    evidenceIds.add(String(item));
  }

  return {
    turnId: raw.turn_id ?? "turn-demo",
    status: (raw.status ?? "pending") as AnswerStatusView,
    route: {
      mode: raw.route?.mode ?? "generic",
      reason: raw.route?.reason ?? "No route reason available.",
    },
    starter: {
      level: "starter",
      text: starter?.text ?? "",
      bullets: starter?.bullets ?? [],
      evidenceRefs: starter?.evidence_refs ?? [],
      streaming: Boolean(starter?.streaming),
    },
    full: {
      level: "full",
      text: full?.text ?? "",
      bullets: full?.bullets ?? [],
      evidenceRefs: full?.evidence_refs ?? [],
    },
    evidence: Array.from(evidenceIds),
    prewarmedStarter: Boolean(raw.prewarmed_starter),
    metrics: {
      starterStreamMs: raw.metrics?.starter_stream_ms ?? null,
      starterMs: raw.metrics?.starter_ms ?? null,
      fullMs: raw.metrics?.full_ms ?? null,
    },
    error: raw.error ?? "",
  };
}

function mapBackendPrewarm(raw: any): PrewarmView | null {
  if (!raw) {
    return null;
  }

  return {
    turnId: String(raw.turn_id ?? ""),
    question: String(raw.question ?? ""),
    status: String(raw.status ?? "warming") as PrewarmView["status"],
    textPreview: String(raw.text_preview ?? ""),
    starterStreamMs: raw.starter_stream_ms ?? null,
    starterMs: raw.starter_ms ?? null,
    error: String(raw.error ?? ""),
  };
}

function defaultFastPresetOptions(): GenerationSettingsView["fast_preset_options"] {
  return [
    {
      value: "qwen3.5-flash",
      model: "qwen3.5-flash",
      enable_thinking: false,
    },
    {
      value: "qwen3.5-plus",
      model: "qwen3.5-plus",
      enable_thinking: false,
    },
  ];
}

function resolveFastPresetSelection(settings: GenerationSettingsView): string {
  const options = settings.fast_preset_options ?? defaultFastPresetOptions();
  if (settings.fast_preset && options.some((option) => option.value === settings.fast_preset)) {
    return settings.fast_preset;
  }
  const matched = options.find((option) => option.model === settings.fast_model);
  return matched?.value ?? options[0]?.value ?? "qwen3.5-flash";
}

function formatThinkingMode(value: boolean | null): string {
  if (value === true) {
    return "enabled";
  }
  if (value === false) {
    return "disabled";
  }
  return "inherit";
}

export default App;
