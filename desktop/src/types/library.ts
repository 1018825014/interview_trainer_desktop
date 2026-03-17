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

export interface LibraryManualEvidenceRecord {
  evidenceId: string;
  moduleId: string;
  evidenceType: string;
  title: string;
  summary: string;
  sourceKind: string;
  sourceRef: string;
  confidence: string;
}

export interface LibraryManualMetricRecord {
  evidenceId: string;
  moduleId: string;
  metricName: string;
  metricValue: string;
  baseline: string;
  method: string;
  environment: string;
  sourceNote: string;
  confidence: string;
}

export interface LibraryManualRetrievalUnitRecord {
  unitId: string;
  unitType: string;
  moduleId: string;
  questionForms: string[];
  shortAnswer: string;
  longAnswer: string;
  keyPoints: string[];
  supportingRefs: string[];
  hooks: string[];
  safeClaims: string[];
}

export interface LibraryCompiledModuleCardRecord {
  moduleId: string;
  projectId: string;
  repoId: string;
  name: string;
  responsibility: string;
  interfaces: string[];
  dependencies: string[];
  designRationale: string;
  upstreamModules: string[];
  downstreamModules: string[];
  keyCallPaths: string[];
  failureSurface: string[];
  riskyInterfaces: string[];
  keyFiles: string[];
}

export interface LibraryCompiledEvidenceCardRecord {
  evidenceId: string;
  projectId: string;
  moduleId: string;
  evidenceType: string;
  title: string;
  summary: string;
  sourceKind: string;
  sourceRef: string;
  confidence: string;
}

export interface LibraryCompiledMetricEvidenceRecord {
  evidenceId: string;
  projectId: string;
  moduleId: string;
  metricName: string;
  metricValue: string;
  baseline: string;
  method: string;
  environment: string;
  sourceNote: string;
  confidence: string;
}

export interface LibraryCompiledRetrievalUnitRecord {
  unitId: string;
  unitType: string;
  projectId: string;
  moduleId: string;
  questionForms: string[];
  shortAnswer: string;
  longAnswer: string;
  keyPoints: string[];
  supportingRefs: string[];
  hooks: string[];
  safeClaims: string[];
}

export interface LibraryProjectCompiledPreviewRecord {
  compiled: boolean;
  projectId: string;
  projectName: string;
  moduleCards: LibraryCompiledModuleCardRecord[];
  evidenceCards: LibraryCompiledEvidenceCardRecord[];
  metricEvidence: LibraryCompiledMetricEvidenceRecord[];
  retrievalUnits: LibraryCompiledRetrievalUnitRecord[];
  terminology: string[];
  compiledAt: number;
}

export interface LibraryWorkspaceCompiledPreviewSummaryRecord {
  projectId: string;
  projectName: string;
  moduleCount: number;
  evidenceCount: number;
  metricCount: number;
  retrievalUnitCount: number;
}

export interface LibraryWorkspaceCompiledPreviewFiltersRecord {
  projectId: string;
  artifactKind: string;
  search: string;
}

export interface LibraryWorkspaceCompiledPreviewRecord {
  compiled: boolean;
  moduleCards: LibraryCompiledModuleCardRecord[];
  evidenceCards: LibraryCompiledEvidenceCardRecord[];
  metricEvidence: LibraryCompiledMetricEvidenceRecord[];
  retrievalUnits: LibraryCompiledRetrievalUnitRecord[];
  terminology: string[];
  compiledAt: number;
  filters: LibraryWorkspaceCompiledPreviewFiltersRecord;
  projectSummaries: LibraryWorkspaceCompiledPreviewSummaryRecord[];
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
  manualEvidence: LibraryManualEvidenceRecord[];
  manualMetrics: LibraryManualMetricRecord[];
  manualRetrievalUnits: LibraryManualRetrievalUnitRecord[];
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

export interface LibraryBundleDetailRecord extends LibraryBundleSummaryRecord {
  knowledge: Record<string, unknown>;
  briefing: LibraryBriefingPayload;
}

export interface LibraryBundleComparisonRecord {
  leftBundle: LibraryBundleSummaryRecord;
  rightBundle: LibraryBundleSummaryRecord;
  addedProjects: string[];
  removedProjects: string[];
  projectCountDelta: number;
  retrievalUnitDelta: number;
  metricEvidenceDelta: number;
  terminologyDelta: number;
  addedFocusTopics: string[];
  removedFocusTopics: string[];
  addedRetrievalUnits: string[];
  removedRetrievalUnits: string[];
  addedEvidenceTitles: string[];
  removedEvidenceTitles: string[];
  addedHookTexts: string[];
  removedHookTexts: string[];
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
