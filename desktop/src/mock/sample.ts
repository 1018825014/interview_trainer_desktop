import {
  AnswerView,
  AudioRecommendationView,
  AudioSessionView,
  CorrectionSuggestionView,
  KnowledgeWorkspaceView,
  SessionBriefView,
  SessionBootstrapPayload,
  TranscriptFeedItem,
  TranscriptPayload,
} from "../types";

export const sampleBrief: SessionBriefView = {
  company: "Mock AI 应用团队",
  businessContext: "面向企业提供 Agent 工作流与知识检索能力",
  jobDescription:
    "需要熟悉 Agent、RAG、工具调用、评测、延迟优化、可观测性和落地交付。",
  focusTopics: ["agent", "latency", "evaluation", "tool"],
  priorityProjects: ["AgentOps Console", "Retrieval Ops Pipeline"],
  likelyQuestions: [
    "请你介绍一个你做过的 Agent 项目。",
    "你如何平衡效果、延迟和成本？",
    "当检索结果不稳定时，你怎么兜底？",
  ],
};

export const sampleAudioRecommendation: AudioRecommendationView = {
  ready: false,
  backend: "pyaudiowpatch",
  system_device: null,
  mic_device: null,
  sample_rate: 16000,
  chunk_ms: 250,
  notes: [
    "当前机器还没有安装可用的 Windows loopback 采集后端。",
    "后续接上 pyaudiowpatch 后，可以把腾讯会议声音映射到 system 通道。",
  ],
};

export const sampleAudioSession: AudioSessionView | null = null;

export const sampleTranscripts: TranscriptFeedItem[] = [
  {
    speaker: "interviewer",
    text: "介绍一下你做过的 Agent 项目，以及为什么没有一开始就做 multi-agent？",
    confidence: 0.97,
    ts: "00:12",
  },
  {
    speaker: "candidate",
    text: "我先从业务目标和为什么这样拆架构讲起。",
    confidence: 0.94,
    ts: "00:17",
  },
];

export const sampleAnswer: AnswerView = {
  turnId: "turn-demo",
  status: "complete",
  route: {
    mode: "hybrid",
    reason: "问题同时追问真实项目实现和岗位方法论。",
  },
  starter: {
    level: "starter",
    text:
      "这个问题我会先从 AgentOps Console 的真实取舍说起。先给结论，我当时没有直接做 multi-agent，核心是先把单 agent 链路做稳定、可观测、可复盘。",
    bullets: [
      "先讲业务目标和约束",
      "再讲为什么单 agent 更稳",
      "最后补升级路线",
    ],
    evidenceRefs: ["agentops-console", "llm-app-engineer"],
  },
  full: {
    level: "full",
    text:
      "如果完整回答，我会先说这个项目服务的是业务同学配置工作流的场景，所以当时最重要的是交付速度、可观测性和失败兜底。基于这个目标，我先做了单 agent 编排，把检索、工具调用、状态更新和 tracing 拆成清晰模块，而不是一上来做 multi-agent。这样做的好处是链路更短、问题更容易定位、线上延迟也更可控。它的不足是复杂任务的策略弹性没那么强，所以如果继续做，我会把复杂决策层升级成可控的 planner/worker 结构，但仍保留单 agent 模式作为默认稳定路径。",
    bullets: [
      "真实实现：单 agent + 检索 + tracing",
      "核心取舍：稳定性、可观测性、延迟优先",
      "限制：复杂任务弹性有限",
      "升级路线：按需引入 planner/worker",
    ],
    evidenceRefs: [
      "agentops-console",
      "AgentOps Console",
      "Orchestrator",
      "src/orchestrator/workflow.py",
    ],
  },
  evidence: [
    "AgentOps Console",
    "Orchestrator",
    "Retrieval",
    "src/orchestrator/workflow.py",
  ],
  metrics: {
    starterStreamMs: 210,
    starterMs: 420,
    fullMs: 1680,
  },
  error: "",
};

export const sampleKnowledgeWorkspace: KnowledgeWorkspaceView = {
  workspaceId: "",
  name: "My Interview Workspace",
  createdAt: null,
  updatedAt: null,
  profileHeadline: "LLM application engineer focused on agent systems",
  profileSummary: "I build practical agent workflows with retrieval, orchestration, tracing, and evaluation.",
  profileStrengths: "agent orchestration\nlatency tuning\nevaluation design",
  targetRoles: "AI Agent Engineer\nLLM Application Engineer",
  introMaterial: "I build pragmatic agent systems with clear tradeoffs.",
  projectName: "AgentOps Console",
  projectBusinessValue: "Help operators configure AI workflows with retrieval and tool calling.",
  projectArchitecture: "React console + Python orchestration service + retrieval + tracing/evaluation.",
  projectDocument:
    "This project serves internal users and lets them configure agent workflows with lower engineering overhead. The hard part is balancing latency, reliability, and debuggability.",
  codePath: "src/orchestrator/workflow.py",
  codeContent: "class WorkflowOrchestrator:\n    def run(self, state):\n        return state\n",
  roleDocTitle: "AI Agent Role Notes",
  roleDocContent: "Focus on latency, evaluation, tool calling, observability, and failure recovery.",
  compileSummary: null,
};

export const sampleCorrections: CorrectionSuggestionView[] = [
  {
    source_term: "mulit-agent",
    replacements: ["multi-agent", "single-agent", "agent orchestration"],
    reason: "这是低置信度术语，建议快速替换。",
  },
];

export const sampleSessionPayload: SessionBootstrapPayload = {
  knowledge: {
    profile: {
      headline: "候选人主要做大模型应用和 Agent 系统落地。",
      summary: "擅长把业务场景拆成检索、编排、执行、评测和观测几个稳定模块。",
      strengths: ["系统化拆解复杂问题", "兼顾效果与延迟", "会讲清真实取舍"],
    },
    projects: [
      {
        name: "AgentOps Console",
        business_value: "帮助运营团队快速搭建带检索和工具调用的 AI 工作流。",
        architecture: "前端控制台 + Python 编排服务 + 检索层 + tracing/评测层。",
        documents: [
          {
            content:
              "这个项目服务内部业务同学，让他们通过低代码配置 Agent 工作流。核心难点是既要保证响应速度，又要让 tracing 和失败兜底足够清晰。",
          },
        ],
        code_files: [
          {
            path: "src/orchestrator/workflow.py",
            content:
              "class WorkflowOrchestrator:\n    def run(self, state):\n        return state\n",
          },
          {
            path: "src/retrieval/reranker.py",
            content: "def rerank(chunks):\n    return chunks[:5]\n",
          },
        ],
      },
    ],
  },
  briefing: {
    company: "Mock AI Company",
    business_context: "做大模型应用平台",
    job_description: "需要熟悉 Agent、RAG、evaluation、latency optimization",
  },
};

export const demoTurnTranscript: TranscriptPayload = {
  speaker: "interviewer",
  text: "介绍一下你做过的 Agent 项目，以及为什么你没有一开始就做 multi-agent？",
  final: true,
  confidence: 0.97,
  ts_start: 0,
  ts_end: 4.2,
};
