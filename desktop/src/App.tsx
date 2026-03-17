import { useEffect, useMemo, useState } from "react";
import {
  compileWorkspace,
  createWorkspace,
  createLiveBridge,
  createAudioSession,
  createSession,
  fetchAudioCapabilities,
  fetchAudioRecommendation,
  getWorkspace,
  getAnswer,
  getLiveBridge,
  importWorkspacePath,
  listWorkspaces,
  pingBackend,
  pushAudioFrame,
  sendTranscript,
  startAudioSession,
  stopLiveBridge,
  updateWorkspace,
  tickSession,
  transcribeAudioSession,
} from "./api/client";
import {
  demoTurnTranscript,
  sampleAnswer,
  sampleAudioRecommendation,
  sampleAudioSession,
  sampleBrief,
  sampleCorrections,
  sampleKnowledgeWorkspace,
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
  KnowledgeWorkspaceView,
  LiveBridgeView,
  PartialTranscriptView,
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
  const [answer, setAnswer] = useState<AnswerView>(sampleAnswer);
  const [workspace, setWorkspace] = useState<KnowledgeWorkspaceView>(sampleKnowledgeWorkspace);
  const [workspaceImportPath, setWorkspaceImportPath] = useState("");
  const [workspaceStatus, setWorkspaceStatus] = useState("Draft only");
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
    const loadWorkspace = async () => {
      try {
        const payload = await listWorkspaces(backendBaseUrl);
        const first = Array.isArray(payload.workspaces) ? payload.workspaces[0] : null;
        if (!first || cancelled) {
          return;
        }
        const full = await getWorkspace(backendBaseUrl, String(first.workspace_id));
        if (!cancelled) {
          setWorkspace(mapWorkspace(full));
          setWorkspaceStatus("Loaded from backend");
        }
      } catch {
        // ignore and keep local draft
      }
    };
    void loadWorkspace();
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

  async function ensureWorkspaceSaved(): Promise<KnowledgeWorkspaceView> {
    const payload = buildWorkspacePayload(workspace);
    if (!workspace.workspaceId) {
      const created = await createWorkspace(backendBaseUrl, payload);
      const mapped = mapWorkspace(created);
      setWorkspace(mapped);
      setWorkspaceStatus("Workspace created");
      return mapped;
    }
    const updated = await updateWorkspace(backendBaseUrl, workspace.workspaceId, payload);
    const mapped = mapWorkspace(updated);
    setWorkspace(mapped);
    setWorkspaceStatus("Workspace saved");
    return mapped;
  }

  async function handleCreateWorkspace() {
    setErrorMessage("");
    try {
      const created = await createWorkspace(backendBaseUrl, buildWorkspacePayload(workspace));
      setWorkspace(mapWorkspace(created));
      setWorkspaceStatus("Workspace created");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "创建资料工作区失败");
    }
  }

  async function handleSaveWorkspace() {
    setErrorMessage("");
    try {
      await ensureWorkspaceSaved();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "保存资料工作区失败");
    }
  }

  async function handleCompileWorkspace() {
    setErrorMessage("");
    try {
      const saved = await ensureWorkspaceSaved();
      const compiled = await compileWorkspace(backendBaseUrl, saved.workspaceId);
      setWorkspace(mapWorkspace(compiled));
      setWorkspaceStatus("Workspace compiled");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "编译资料工作区失败");
    }
  }

  async function handleImportWorkspacePath() {
    setErrorMessage("");
    try {
      const saved = await ensureWorkspaceSaved();
      const imported = await importWorkspacePath(backendBaseUrl, saved.workspaceId, {
        path: workspaceImportPath,
        project_name: workspace.projectName || "Imported Project",
      });
      setWorkspace(mapWorkspace(imported));
      const importSummary = imported.import_summary;
      if (importSummary) {
        setWorkspaceStatus(
          `Imported ${importSummary.imported_docs} docs + ${importSummary.imported_code_files} code files`,
        );
      } else {
        setWorkspaceStatus("Project path imported");
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "导入项目路径失败");
    }
  }

  async function handleUseWorkspaceForSession() {
    setErrorMessage("");
    setDemoStatus("creating_session");
    try {
      const saved = await ensureWorkspaceSaved();
      const response = await createSession(backendBaseUrl, {
        knowledge: buildWorkspaceKnowledge(saved),
        briefing: {
          company: brief.company,
          business_context: brief.businessContext,
          job_description: brief.jobDescription,
        },
      });
      setSessionId(response.session_id);
      setDemoStatus("ready");
      setWorkspaceStatus("Workspace attached to live session");
    } catch (error) {
      setDemoStatus("error");
      setErrorMessage(error instanceof Error ? error.message : "用资料工作区创建会话失败");
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
        <section className="panel panel-workspace">
          <div className="panel-head">
            <span>资料工作区</span>
            <strong>{workspace.workspaceId ? "已保存" : "本地草稿"}</strong>
          </div>
          <label>
            工作区名称
            <input
              value={workspace.name}
              onChange={(event) => setWorkspace({ ...workspace, name: event.target.value })}
            />
          </label>
          <label>
            项目路径导入
            <input
              value={workspaceImportPath}
              onChange={(event) => setWorkspaceImportPath(event.target.value)}
              placeholder="E:\\path\\to\\your\\project"
            />
          </label>
          <div className="action-row">
            <button className="ghost accent small" disabled={!backendOnline} onClick={handleCreateWorkspace}>
              创建工作区
            </button>
            <button className="ghost small" disabled={!backendOnline} onClick={handleSaveWorkspace}>
              保存资料
            </button>
            <button className="ghost small" disabled={!backendOnline} onClick={handleCompileWorkspace}>
              编译资料
            </button>
            <button
              className="ghost small"
              disabled={!backendOnline || !workspaceImportPath.trim()}
              onClick={handleImportWorkspacePath}
            >
              导入路径
            </button>
            <button className="ghost small" disabled={!backendOnline} onClick={handleUseWorkspaceForSession}>
              用于会话
            </button>
          </div>
          <p className="backend-meta">{workspaceStatus}</p>
          {workspace.compileSummary ? (
            <div className="session-chip">
              <strong>{workspace.compileSummary.projects.join(", ") || "No project"}</strong>
              <span>{workspace.compileSummary.modules} modules</span>
              <span>{workspace.compileSummary.doc_chunks} docs</span>
              <span>{workspace.compileSummary.code_chunks} code chunks</span>
              <span>{workspace.compileSummary.terminology_count} terms</span>
            </div>
          ) : null}
          <label>
            背景标题
            <input
              value={workspace.profileHeadline}
              onChange={(event) => setWorkspace({ ...workspace, profileHeadline: event.target.value })}
            />
          </label>
          <label>
            背景摘要
            <textarea
              rows={4}
              value={workspace.profileSummary}
              onChange={(event) => setWorkspace({ ...workspace, profileSummary: event.target.value })}
            />
          </label>
          <label>
            个人强项（每行一个）
            <textarea
              rows={4}
              value={workspace.profileStrengths}
              onChange={(event) => setWorkspace({ ...workspace, profileStrengths: event.target.value })}
            />
          </label>
          <label>
            目标岗位（每行一个）
            <textarea
              rows={3}
              value={workspace.targetRoles}
              onChange={(event) => setWorkspace({ ...workspace, targetRoles: event.target.value })}
            />
          </label>
          <label>
            自我介绍素材
            <textarea
              rows={3}
              value={workspace.introMaterial}
              onChange={(event) => setWorkspace({ ...workspace, introMaterial: event.target.value })}
            />
          </label>
          <label>
            项目名称
            <input
              value={workspace.projectName}
              onChange={(event) => setWorkspace({ ...workspace, projectName: event.target.value })}
            />
          </label>
          <label>
            项目业务价值
            <textarea
              rows={3}
              value={workspace.projectBusinessValue}
              onChange={(event) => setWorkspace({ ...workspace, projectBusinessValue: event.target.value })}
            />
          </label>
          <label>
            项目架构
            <textarea
              rows={3}
              value={workspace.projectArchitecture}
              onChange={(event) => setWorkspace({ ...workspace, projectArchitecture: event.target.value })}
            />
          </label>
          <label>
            项目说明 / 面试素材
            <textarea
              rows={6}
              value={workspace.projectDocument}
              onChange={(event) => setWorkspace({ ...workspace, projectDocument: event.target.value })}
            />
          </label>
          <label>
            关键代码路径
            <input
              value={workspace.codePath}
              onChange={(event) => setWorkspace({ ...workspace, codePath: event.target.value })}
            />
          </label>
          <label>
            关键代码片段
            <textarea
              rows={7}
              value={workspace.codeContent}
              onChange={(event) => setWorkspace({ ...workspace, codeContent: event.target.value })}
            />
          </label>
          <label>
            岗位资料标题
            <input
              value={workspace.roleDocTitle}
              onChange={(event) => setWorkspace({ ...workspace, roleDocTitle: event.target.value })}
            />
          </label>
          <label>
            岗位资料内容
            <textarea
              rows={5}
              value={workspace.roleDocContent}
              onChange={(event) => setWorkspace({ ...workspace, roleDocContent: event.target.value })}
            />
          </label>
        </section>

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
                {liveBridge.status} | {liveBridge.poll_interval_ms}ms poll | {liveBridge.cycles} cycles |{" "}
                {liveBridge.transcripts_processed} transcripts
              </p>
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
    metrics: {
      starterStreamMs: raw.metrics?.starter_stream_ms ?? null,
      starterMs: raw.metrics?.starter_ms ?? null,
      fullMs: raw.metrics?.full_ms ?? null,
    },
    error: raw.error ?? "",
  };
}

function mapWorkspace(raw: any): KnowledgeWorkspaceView {
  const profile = raw.knowledge?.profile ?? {};
  const project = raw.knowledge?.projects?.[0] ?? {};
  const document = project.documents?.[0] ?? {};
  const codeFile = project.code_files?.[0] ?? {};
  const roleDocument = raw.knowledge?.role_documents?.[0] ?? {};
  return {
    workspaceId: raw.workspace_id ?? "",
    name: raw.name ?? "Interview Workspace",
    createdAt: raw.created_at ?? null,
    updatedAt: raw.updated_at ?? null,
    profileHeadline: profile.headline ?? "",
    profileSummary: profile.summary ?? "",
    profileStrengths: joinLines(profile.strengths ?? []),
    targetRoles: joinLines(profile.target_roles ?? []),
    introMaterial: joinLines(profile.intro_material ?? []),
    projectName: project.name ?? "",
    projectBusinessValue: project.business_value ?? "",
    projectArchitecture: project.architecture ?? "",
    projectDocument: document.content ?? "",
    codePath: codeFile.path ?? "src/main.py",
    codeContent: codeFile.content ?? "",
    roleDocTitle: roleDocument.title ?? "Role Notes",
    roleDocContent: roleDocument.content ?? "",
    compileSummary: raw.compile_summary ?? null,
  };
}

function buildWorkspacePayload(workspace: KnowledgeWorkspaceView) {
  return {
    name: workspace.name,
    knowledge: buildWorkspaceKnowledge(workspace),
  };
}

function buildWorkspaceKnowledge(workspace: KnowledgeWorkspaceView) {
  const projects =
    workspace.projectName || workspace.projectDocument || workspace.codeContent
      ? [
          {
            name: workspace.projectName || "Interview Project",
            business_value: workspace.projectBusinessValue,
            architecture: workspace.projectArchitecture,
            documents: workspace.projectDocument
              ? [{ path: "notes.md", content: workspace.projectDocument }]
              : [],
            code_files: workspace.codeContent
              ? [{ path: workspace.codePath || "src/main.py", content: workspace.codeContent }]
              : [],
          },
        ]
      : [];

  const roleDocuments = workspace.roleDocContent
    ? [
        {
          title: workspace.roleDocTitle || "Role Notes",
          content: workspace.roleDocContent,
        },
      ]
    : [];

  return {
    profile: {
      headline: workspace.profileHeadline,
      summary: workspace.profileSummary,
      strengths: splitLines(workspace.profileStrengths),
      target_roles: splitLines(workspace.targetRoles),
      intro_material: splitLines(workspace.introMaterial),
    },
    projects,
    role_documents: roleDocuments,
  };
}

function splitLines(value: string): string[] {
  return value
    .replace(/\r/g, "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function joinLines(value: unknown): string {
  if (!Array.isArray(value)) {
    return "";
  }
  return value.map((item) => String(item)).join("\n");
}

export default App;
