import {
  AnswerView,
  AudioRecommendationView,
  AudioSessionView,
  CorrectionSuggestionView,
  LibraryWorkspaceRecord,
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

export const sampleLibraryWorkspace: LibraryWorkspaceRecord = {
  workspaceId: "workspace-sample",
  name: "Persistent Interview Library",
  createdAt: Date.now() / 1000 - 7200,
  updatedAt: Date.now() / 1000,
  knowledge: {
    profile: {
      headline: "LLM application engineer focused on agent systems",
      summary: "I build practical agent workflows with retrieval, orchestration, tracing, and evaluation.",
      strengths: ["agent orchestration", "latency tuning", "evaluation design"],
      targetRoles: ["AI Agent Engineer", "LLM Application Engineer"],
      introMaterial: ["I build pragmatic agent systems with clear tradeoffs."],
    },
    projects: [
      {
        projectId: "project-agentops",
        name: "AgentOps Console",
        pitch30: "一个面向内部团队的 Agent 工作流控制台，重点是低延迟和可调试性。",
        pitch90: "我会把它当成讲 agent orchestration、retrieval tradeoff 和 observability 的主项目。",
        businessValue: "Help operators configure AI workflows with retrieval and tool calling.",
        architecture: "React console + Python orchestration service + retrieval + tracing/evaluation.",
        keyMetrics: ["Latency dropped from 1.8s to 900ms", "Escalation fallback coverage reached 95%"],
        tradeoffs: ["优先做单 agent 稳定链路，再逐步引入 planner/worker。"],
        failureCases: ["上游检索抖动时，回答会偏空，需要 fallback 和 tracing。"],
        limitations: ["复杂任务弹性不如多 agent。"],
        upgradePlan: ["继续做 hybrid retrieval 和 cached evidence ranking。"],
        interviewerHooks: ["这个系统真正难的是索引和检索时延，而不是生成本身。"],
        repoSummaries: [
          {
            repoId: "repo-agentops",
            label: "AgentOps Console",
            rootPath: "E:/projects/agentops-console",
            status: "ready",
            lastScannedAt: Date.now() / 1000,
            importedDocs: 4,
            importedCodeFiles: 12,
          },
        ],
        documents: [
          {
            documentId: "doc-agentops-readme",
            scope: "project",
            title: "README.md",
            path: "README.md",
            content:
              "This project serves internal users and lets them configure agent workflows with lower engineering overhead.",
            sourceKind: "repo_import",
            sourcePath: "E:/projects/agentops-console",
            repoId: "repo-agentops",
            updatedAt: Date.now() / 1000,
          },
        ],
        codeFiles: [
          {
            path: "src/orchestrator/workflow.py",
            content: "class WorkflowOrchestrator:\n    def run(self, state):\n        return state\n",
            sourceKind: "repo_import",
            sourcePath: "E:/projects/agentops-console",
            repoId: "repo-agentops",
          },
        ],
      },
      {
        projectId: "project-retrieval",
        name: "Retrieval Ops Pipeline",
        pitch30: "一个多项目资料库与面试问答编译系统，强调 retrieval-unit-first。",
        pitch90: "我会用它讲 codebase indexing、evidence-aware answer planning 和 runtime routing。",
        businessValue: "Help the assistant answer technical interviews from a pre-maintained project library.",
        architecture: "SQLite metadata + local object storage + compile bundle + runtime answer control.",
        keyMetrics: ["Starter stream under 250ms", "Full draft under 2s on local retrieval path"],
        tradeoffs: ["把重计算前移到预编译阶段，现场只做 bounded retrieval。"],
        failureCases: ["意图误判会导致 starter 结构跑偏，需要 follow-up state 修正。"],
        limitations: ["暂时还没有代码图可视化。"],
        upgradePlan: ["补模块关系图和更细粒度的 evidence ranking。"],
        interviewerHooks: ["普通 RAG 不够，这里真正关键的是回答控制层。"],
        repoSummaries: [],
        documents: [],
        codeFiles: [],
      },
    ],
    roleDocuments: [
      {
        documentId: "role-doc-alibaba",
        scope: "role",
        title: "Alibaba Agent Platform",
        path: "role/alibaba.md",
        content: "Focus on agent systems, retrieval quality, evaluation, latency optimization, and observability.",
        sourceKind: "manual",
        sourcePath: "",
        repoId: "",
        updatedAt: Date.now() / 1000,
      },
    ],
  },
  overlays: [
    {
      overlayId: "overlay-alibaba",
      name: "Alibaba Agent Platform",
      company: "Alibaba",
      jobDescription: "agent platform, retrieval, evaluation, latency optimization",
      businessContext: "大型模型应用平台与 agent 工作流基础设施",
      focusProjectIds: ["project-retrieval", "project-agentops"],
      emphasisPoints: ["tradeoff", "latency", "ownership"],
      styleProfile: ["口语化", "先结论后展开", "引导追问"],
      depthPolicy: "deep",
      createdAt: Date.now() / 1000 - 3600,
      updatedAt: Date.now() / 1000,
    },
  ],
  presets: [
    {
      presetId: "preset-alibaba",
      name: "Alibaba 深挖版",
      overlayId: "overlay-alibaba",
      projectIds: ["project-retrieval", "project-agentops"],
      includeRoleDocuments: true,
      createdAt: Date.now() / 1000 - 1800,
      updatedAt: Date.now() / 1000,
    },
  ],
  compiledBundles: [
    {
      bundleId: "bundle-sample",
      presetId: "preset-alibaba",
      presetName: "Alibaba 深挖版",
      overlayId: "overlay-alibaba",
      overlayName: "Alibaba Agent Platform",
      projectIds: ["project-retrieval", "project-agentops"],
      projectNames: ["Retrieval Ops Pipeline", "AgentOps Console"],
      projectCount: 2,
      retrievalUnitCount: 9,
      metricEvidenceCount: 4,
      terminologyCount: 18,
      builtAt: Date.now() / 1000,
    },
  ],
  compileSummary: {
    projects: ["AgentOps Console", "Retrieval Ops Pipeline"],
    rolePlaybooks: ["Alibaba Agent Platform"],
    terminologyCount: 18,
    modules: 11,
    docChunks: 15,
    codeChunks: 21,
  },
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
