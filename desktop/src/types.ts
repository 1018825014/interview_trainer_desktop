export type TurnMode =
  | "listening"
  | "overlap"
  | "locked_question"
  | "candidate_answering";

export type AnswerStatusView = "pending" | "starter_streaming" | "starter_ready" | "complete" | "failed";
export type PrewarmStatusView = "warming" | "streaming" | "ready" | "failed" | "cancelled";

export interface TranscriptFeedItem {
  speaker: "interviewer" | "candidate";
  text: string;
  confidence: number;
  ts: string;
}

export interface AnswerDraftView {
  level: "starter" | "full";
  text: string;
  bullets: string[];
  evidenceRefs: string[];
  streaming?: boolean;
}

export interface CorrectionSuggestionView {
  source_term: string;
  replacements: string[];
  reason: string;
}

export interface SessionBriefView {
  company: string;
  businessContext: string;
  jobDescription: string;
  focusTopics: string[];
  priorityProjects: string[];
  likelyQuestions: string[];
}

export interface KnowledgeWorkspaceCompileSummaryView {
  projects: string[];
  role_playbooks: string[];
  terminology_count: number;
  modules: number;
  doc_chunks: number;
  code_chunks: number;
}

export interface KnowledgeWorkspaceView {
  workspaceId: string;
  name: string;
  createdAt: number | null;
  updatedAt: number | null;
  profileHeadline: string;
  profileSummary: string;
  profileStrengths: string;
  targetRoles: string;
  introMaterial: string;
  projectName: string;
  projectBusinessValue: string;
  projectArchitecture: string;
  projectDocument: string;
  codePath: string;
  codeContent: string;
  roleDocTitle: string;
  roleDocContent: string;
  compileSummary: KnowledgeWorkspaceCompileSummaryView | null;
}

export interface WorkspaceListPayload {
  workspaces: Array<Record<string, unknown>>;
}

export interface AudioDeviceView {
  name: string;
  index: number;
  max_input_channels: number;
  max_output_channels: number;
  hostapi: string;
  default_samplerate: number;
  is_loopback_candidate: boolean;
}

export interface AudioCapabilitiesView {
  backend: string;
  python_package_available: boolean;
  platform_supported: boolean;
  supports_loopback: boolean;
  supports_microphone_capture: boolean;
  devices: AudioDeviceView[];
  notes: string[];
}

export interface AudioCapabilitiesPayload {
  capabilities: AudioCapabilitiesView[];
}

export interface AudioRecommendationView {
  ready: boolean;
  backend: string;
  system_device: AudioDeviceView | null;
  mic_device: AudioDeviceView | null;
  sample_rate: number;
  chunk_ms: number;
  notes: string[];
}

export interface AudioSessionView {
  session_id: string;
  status: string;
  total_frames: number;
  queued_frames: number;
  dropped_frames: number;
  notes: string[];
  error: string;
  config: {
    transport: string;
    backend: string;
    sample_rate: number;
    chunk_ms: number;
  };
}

export interface AudioTranscriptionView {
  provider: string;
  model: string;
  source: "system" | "mic";
  speaker: "interviewer" | "candidate";
  text: string;
  confidence: number;
  language: string;
  final: boolean;
  ts_start: number;
  ts_end: number;
  duration_ms: number;
  num_frames: number;
  response_ms: number;
  notes: string[];
}

export interface SignalGateView {
  avg_rms: number;
  peak_rms: number;
  voiced_frames: number;
  total_frames: number;
  voiced_ratio: number;
  max_speech_run_frames: number;
  duration_ms: number;
  threshold: number;
  passed: boolean;
  noise_floor_rms: number;
  avg_zcr: number;
  peak_zcr: number;
  avg_delta: number;
  frame_ms: number;
  reason: string;
}

export interface BridgeSourceStateView {
  source: "system" | "mic";
  buffered_frames: number;
  buffered_duration_ms: number;
  noise_floor_rms: number;
  adaptive_threshold: number;
  recent_peak_rms: number;
  recent_avg_rms: number;
  partial_text: string;
  partial_updated_at: number | null;
  last_gate: SignalGateView | null;
}

export interface LiveBridgeTranscriptView extends AudioTranscriptionView {
  answer_turn_id?: string;
  answer_status?: AnswerStatusView | string;
}

export interface PartialTranscriptView {
  provider: string;
  model: string;
  source: "system" | "mic";
  speaker: "interviewer" | "candidate";
  item_id: string;
  text: string;
  language: string;
  updated_at: number;
}

export interface PrewarmView {
  turnId: string;
  question: string;
  status: PrewarmStatusView;
  textPreview: string;
  starterStreamMs: number | null;
  starterMs: number | null;
  error: string;
}

export interface LiveBridgeView {
  bridge_id: string;
  audio_session_id: string;
  interview_session_id: string;
  sources: Array<"system" | "mic">;
  poll_interval_ms: number;
  max_frames_per_chunk: number;
  final: boolean;
  language: string;
  prompt: string;
  auto_tick_offset_s: number;
  status: string;
  created_at: number;
  started_at: number | null;
  stopped_at: number | null;
  cycles: number;
  transcripts_processed: number;
  skipped_polls: number;
  last_error: string;
  last_activity_at: number | null;
  recent_transcripts: LiveBridgeTranscriptView[];
  last_answer: any | null;
  last_prewarm: PrewarmView | null;
  last_signal: SignalGateView | null;
  last_skip_reason: string;
  source_state: Record<string, BridgeSourceStateView>;
  partial_transcripts: PartialTranscriptView[];
}

export interface AnswerView {
  turnId: string;
  status: AnswerStatusView;
  route: {
    mode: "generic" | "project" | "role" | "hybrid";
    reason: string;
  };
  starter: AnswerDraftView;
  full: AnswerDraftView;
  evidence: string[];
  prewarmedStarter: boolean;
  metrics: {
    starterStreamMs: number | null;
    starterMs: number | null;
    fullMs: number | null;
  };
  error: string;
}

export interface SessionBootstrapPayload {
  knowledge: Record<string, unknown>;
  briefing: {
    company: string;
    business_context: string;
    job_description: string;
  };
}

export interface TranscriptPayload {
  speaker: "interviewer" | "candidate";
  text: string;
  final: boolean;
  confidence: number;
  ts_start: number;
  ts_end: number;
  turn_id?: string;
}
