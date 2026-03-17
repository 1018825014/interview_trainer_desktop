export interface LibraryCompileSummaryRecord {
  projects: string[];
  rolePlaybooks: string[];
  terminologyCount: number;
  modules: number;
  docChunks: number;
  codeChunks: number;
}

export interface LibraryProfileRecord {
  headline: string;
  summary: string;
  strengths: string[];
  targetRoles: string[];
  introMaterial: string[];
}

export interface LibraryRoleDocumentRecord {
  documentId: string;
  scope: "role";
  title: string;
  path: string;
  content: string;
  sourceKind: string;
  sourcePath: string;
  repoId: string;
  updatedAt: number;
}

export interface LibraryDocumentRecord {
  documentId: string;
  scope: "project";
  title: string;
  path: string;
  content: string;
  sourceKind: string;
  sourcePath: string;
  repoId: string;
  updatedAt: number;
}

export interface LibraryCodeFileRecord {
  path: string;
  content: string;
  sourceKind: string;
  sourcePath: string;
  repoId: string;
}

export interface LibraryRepoSummaryRecord {
  repoId: string;
  label: string;
  rootPath: string;
  status: string;
  lastScannedAt: number;
  importedDocs: number;
  importedCodeFiles: number;
}

export interface LibraryProjectRecord {
  projectId: string;
  name: string;
  pitch30: string;
  pitch90: string;
  businessValue: string;
  architecture: string;
  keyMetrics: string[];
  tradeoffs: string[];
  failureCases: string[];
  limitations: string[];
  upgradePlan: string[];
  interviewerHooks: string[];
  repoSummaries: LibraryRepoSummaryRecord[];
  documents: LibraryDocumentRecord[];
  codeFiles: LibraryCodeFileRecord[];
}

export interface LibraryOverlayRecord {
  overlayId: string;
  name: string;
  company: string;
  jobDescription: string;
  businessContext: string;
  focusProjectIds: string[];
  emphasisPoints: string[];
  styleProfile: string[];
  depthPolicy: string;
  createdAt: number;
  updatedAt: number;
}

export interface LibraryPresetRecord {
  presetId: string;
  name: string;
  overlayId: string;
  projectIds: string[];
  includeRoleDocuments: boolean;
  createdAt: number;
  updatedAt: number;
}

export interface LibraryBundleSummaryRecord {
  bundleId: string;
  presetId: string;
  presetName: string;
  overlayId: string;
  overlayName: string;
  projectIds: string[];
  projectNames: string[];
  projectCount: number;
  retrievalUnitCount: number;
  metricEvidenceCount: number;
  terminologyCount: number;
  builtAt: number;
}

export interface LibraryKnowledgeRecord {
  profile: LibraryProfileRecord;
  projects: LibraryProjectRecord[];
  roleDocuments: LibraryRoleDocumentRecord[];
}

export interface LibraryWorkspaceRecord {
  workspaceId: string;
  name: string;
  createdAt: number | null;
  updatedAt: number | null;
  knowledge: LibraryKnowledgeRecord;
  overlays: LibraryOverlayRecord[];
  presets: LibraryPresetRecord[];
  compiledBundles: LibraryBundleSummaryRecord[];
  compileSummary: LibraryCompileSummaryRecord | null;
}

export interface LibraryImportSummary {
  projectName: string;
  importedDocs: number;
  importedCodeFiles: number;
  sourcePath: string;
}

export interface LibraryBriefingPayload {
  company: string;
  businessContext: string;
  jobDescription: string;
  priorityProjects: string[];
  focusTopics: string[];
  styleBias: string[];
  likelyQuestions: string[];
}

export interface LibrarySessionPayload {
  knowledge: Record<string, unknown>;
  briefing: LibraryBriefingPayload;
  activationSummary: LibraryBundleSummaryRecord;
}

export interface LibraryEntitySelection {
  type: "workspace" | "project" | "overlay" | "preset" | "bundle";
  id: string;
}
