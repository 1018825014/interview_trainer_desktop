import { requestJson } from "./client";
import type {
  LibraryBundleSummaryRecord,
  LibraryCompiledEvidenceCardRecord,
  LibraryCompiledMetricEvidenceRecord,
  LibraryCompiledModuleCardRecord,
  LibraryCompiledRetrievalUnitRecord,
  LibraryProjectCompiledPreviewRecord,
  LibraryCodeFileRecord,
  LibraryCompileSummaryRecord,
  LibraryDocumentRecord,
  LibraryImportSummary,
  LibraryKnowledgeRecord,
  LibraryManualEvidenceRecord,
  LibraryManualMetricRecord,
  LibraryManualRetrievalUnitRecord,
  LibraryOverlayRecord,
  LibraryPresetRecord,
  LibraryProfileRecord,
  LibraryProjectRecord,
  LibraryRepoSummaryRecord,
  LibraryRoleDocumentRecord,
  LibrarySessionPayload,
  LibraryWorkspaceRecord,
} from "../types/library";

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item)).filter(Boolean) : [];
}

function mapProfile(raw: any): LibraryProfileRecord {
  return {
    headline: asString(raw?.headline),
    summary: asString(raw?.summary),
    strengths: asStringArray(raw?.strengths),
    targetRoles: asStringArray(raw?.target_roles),
    introMaterial: asStringArray(raw?.intro_material),
  };
}

function mapRoleDocument(raw: any): LibraryRoleDocumentRecord {
  return {
    documentId: asString(raw?.document_id),
    scope: "role",
    title: asString(raw?.title, "Role Notes"),
    path: asString(raw?.path),
    content: asString(raw?.content),
    sourceKind: asString(raw?.source_kind, "manual"),
    sourcePath: asString(raw?.source_path),
    repoId: asString(raw?.repo_id),
    updatedAt: asNumber(raw?.updated_at),
  };
}

function mapDocument(raw: any): LibraryDocumentRecord {
  return {
    documentId: asString(raw?.document_id),
    scope: "project",
    title: asString(raw?.title, "Project Document"),
    path: asString(raw?.path),
    content: asString(raw?.content),
    sourceKind: asString(raw?.source_kind, "manual"),
    sourcePath: asString(raw?.source_path),
    repoId: asString(raw?.repo_id),
    updatedAt: asNumber(raw?.updated_at),
  };
}

function mapCodeFile(raw: any): LibraryCodeFileRecord {
  return {
    path: asString(raw?.path, "src/main.py"),
    content: asString(raw?.content),
    sourceKind: asString(raw?.source_kind, "manual"),
    sourcePath: asString(raw?.source_path),
    repoId: asString(raw?.repo_id),
  };
}

function mapManualEvidence(raw: any): LibraryManualEvidenceRecord {
  return {
    evidenceId: asString(raw?.evidence_id),
    moduleId: asString(raw?.module_id),
    evidenceType: asString(raw?.evidence_type, "manual_note"),
    title: asString(raw?.title, "Evidence"),
    summary: asString(raw?.summary),
    sourceKind: asString(raw?.source_kind, "manual_note"),
    sourceRef: asString(raw?.source_ref),
    confidence: asString(raw?.confidence, "medium"),
  };
}

function mapManualMetric(raw: any): LibraryManualMetricRecord {
  return {
    evidenceId: asString(raw?.evidence_id),
    moduleId: asString(raw?.module_id),
    metricName: asString(raw?.metric_name),
    metricValue: asString(raw?.metric_value),
    baseline: asString(raw?.baseline),
    method: asString(raw?.method, "manual note"),
    environment: asString(raw?.environment, "workspace"),
    sourceNote: asString(raw?.source_note),
    confidence: asString(raw?.confidence, "medium"),
  };
}

function mapManualRetrievalUnit(raw: any): LibraryManualRetrievalUnitRecord {
  return {
    unitId: asString(raw?.unit_id),
    unitType: asString(raw?.unit_type, "project_intro"),
    moduleId: asString(raw?.module_id),
    questionForms: asStringArray(raw?.question_forms),
    shortAnswer: asString(raw?.short_answer),
    longAnswer: asString(raw?.long_answer),
    keyPoints: asStringArray(raw?.key_points),
    supportingRefs: asStringArray(raw?.supporting_refs),
    hooks: asStringArray(raw?.hooks),
    safeClaims: asStringArray(raw?.safe_claims),
  };
}

function mapRepoSummary(raw: any): LibraryRepoSummaryRecord {
  return {
    repoId: asString(raw?.repo_id),
    label: asString(raw?.label),
    rootPath: asString(raw?.root_path),
    status: asString(raw?.status, "ready"),
    lastScannedAt: asNumber(raw?.last_scanned_at),
    importedDocs: asNumber(raw?.imported_docs),
    importedCodeFiles: asNumber(raw?.imported_code_files),
  };
}

function mapProject(raw: any): LibraryProjectRecord {
  return {
    projectId: asString(raw?.project_id),
    name: asString(raw?.name, "Interview Project"),
    pitch30: asString(raw?.pitch_30),
    pitch90: asString(raw?.pitch_90),
    businessValue: asString(raw?.business_value),
    architecture: asString(raw?.architecture),
    keyMetrics: asStringArray(raw?.key_metrics),
    tradeoffs: asStringArray(raw?.tradeoffs),
    failureCases: asStringArray(raw?.failure_cases),
    limitations: asStringArray(raw?.limitations),
    upgradePlan: asStringArray(raw?.upgrade_plan),
    interviewerHooks: asStringArray(raw?.interviewer_hooks),
    manualEvidence: Array.isArray(raw?.manual_evidence) ? raw.manual_evidence.map(mapManualEvidence) : [],
    manualMetrics: Array.isArray(raw?.manual_metrics) ? raw.manual_metrics.map(mapManualMetric) : [],
    manualRetrievalUnits: Array.isArray(raw?.manual_retrieval_units)
      ? raw.manual_retrieval_units.map(mapManualRetrievalUnit)
      : [],
    repoSummaries: Array.isArray(raw?.repo_summaries) ? raw.repo_summaries.map(mapRepoSummary) : [],
    documents: Array.isArray(raw?.documents) ? raw.documents.map(mapDocument) : [],
    codeFiles: Array.isArray(raw?.code_files) ? raw.code_files.map(mapCodeFile) : [],
  };
}

function mapOverlay(raw: any): LibraryOverlayRecord {
  return {
    overlayId: asString(raw?.overlay_id),
    name: asString(raw?.name, "Interview Overlay"),
    company: asString(raw?.company),
    jobDescription: asString(raw?.job_description),
    businessContext: asString(raw?.business_context),
    focusProjectIds: asStringArray(raw?.focus_project_ids),
    emphasisPoints: asStringArray(raw?.emphasis_points),
    styleProfile: asStringArray(raw?.style_profile),
    depthPolicy: asString(raw?.depth_policy, "standard"),
    createdAt: asNumber(raw?.created_at),
    updatedAt: asNumber(raw?.updated_at),
  };
}

function mapPreset(raw: any): LibraryPresetRecord {
  return {
    presetId: asString(raw?.preset_id),
    name: asString(raw?.name, "Interview Preset"),
    overlayId: asString(raw?.overlay_id),
    projectIds: asStringArray(raw?.project_ids),
    includeRoleDocuments: Boolean(raw?.include_role_documents),
    createdAt: asNumber(raw?.created_at),
    updatedAt: asNumber(raw?.updated_at),
  };
}

function mapBundleSummary(raw: any): LibraryBundleSummaryRecord {
  return {
    bundleId: asString(raw?.bundle_id),
    presetId: asString(raw?.preset_id),
    presetName: asString(raw?.preset_name),
    overlayId: asString(raw?.overlay_id),
    overlayName: asString(raw?.overlay_name),
    projectIds: asStringArray(raw?.project_ids),
    projectNames: asStringArray(raw?.project_names),
    projectCount: asNumber(raw?.project_count),
    retrievalUnitCount: asNumber(raw?.retrieval_unit_count),
    metricEvidenceCount: asNumber(raw?.metric_evidence_count),
    terminologyCount: asNumber(raw?.terminology_count),
    builtAt: asNumber(raw?.built_at),
  };
}

function mapCompiledModuleCard(raw: any): LibraryCompiledModuleCardRecord {
  return {
    moduleId: asString(raw?.module_id),
    projectId: asString(raw?.project_id),
    repoId: asString(raw?.repo_id),
    name: asString(raw?.name),
    responsibility: asString(raw?.responsibility),
    interfaces: asStringArray(raw?.interfaces),
    dependencies: asStringArray(raw?.dependencies),
    designRationale: asString(raw?.design_rationale),
    upstreamModules: asStringArray(raw?.upstream_modules),
    downstreamModules: asStringArray(raw?.downstream_modules),
    keyCallPaths: asStringArray(raw?.key_call_paths),
    failureSurface: asStringArray(raw?.failure_surface),
    riskyInterfaces: asStringArray(raw?.risky_interfaces),
    keyFiles: asStringArray(raw?.key_files),
  };
}

function mapCompiledEvidenceCard(raw: any): LibraryCompiledEvidenceCardRecord {
  return {
    evidenceId: asString(raw?.evidence_id),
    projectId: asString(raw?.project_id),
    moduleId: asString(raw?.module_id),
    evidenceType: asString(raw?.evidence_type),
    title: asString(raw?.title),
    summary: asString(raw?.summary),
    sourceKind: asString(raw?.source_kind),
    sourceRef: asString(raw?.source_ref),
    confidence: asString(raw?.confidence, "medium"),
  };
}

function mapCompiledMetricEvidence(raw: any): LibraryCompiledMetricEvidenceRecord {
  return {
    evidenceId: asString(raw?.evidence_id),
    projectId: asString(raw?.project_id),
    moduleId: asString(raw?.module_id),
    metricName: asString(raw?.metric_name),
    metricValue: asString(raw?.metric_value),
    baseline: asString(raw?.baseline),
    method: asString(raw?.method),
    environment: asString(raw?.environment),
    sourceNote: asString(raw?.source_note),
    confidence: asString(raw?.confidence, "medium"),
  };
}

function mapCompiledRetrievalUnit(raw: any): LibraryCompiledRetrievalUnitRecord {
  return {
    unitId: asString(raw?.unit_id),
    unitType: asString(raw?.unit_type),
    projectId: asString(raw?.project_id),
    moduleId: asString(raw?.module_id),
    questionForms: asStringArray(raw?.question_forms),
    shortAnswer: asString(raw?.short_answer),
    longAnswer: asString(raw?.long_answer),
    keyPoints: asStringArray(raw?.key_points),
    supportingRefs: asStringArray(raw?.supporting_refs),
    hooks: asStringArray(raw?.hooks),
    safeClaims: asStringArray(raw?.safe_claims),
  };
}

function mapProjectCompiledPreview(raw: any): LibraryProjectCompiledPreviewRecord {
  return {
    compiled: Boolean(raw?.compiled),
    projectId: asString(raw?.project_id),
    projectName: asString(raw?.project_name),
    moduleCards: Array.isArray(raw?.module_cards) ? raw.module_cards.map(mapCompiledModuleCard) : [],
    evidenceCards: Array.isArray(raw?.evidence_cards) ? raw.evidence_cards.map(mapCompiledEvidenceCard) : [],
    metricEvidence: Array.isArray(raw?.metric_evidence) ? raw.metric_evidence.map(mapCompiledMetricEvidence) : [],
    retrievalUnits: Array.isArray(raw?.retrieval_units) ? raw.retrieval_units.map(mapCompiledRetrievalUnit) : [],
    terminology: asStringArray(raw?.terminology),
    compiledAt: asNumber(raw?.compiled_at),
  };
}

function mapCompileSummary(raw: any): LibraryCompileSummaryRecord | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  return {
    projects: asStringArray(raw.projects),
    rolePlaybooks: asStringArray(raw.role_playbooks),
    terminologyCount: asNumber(raw.terminology_count),
    modules: asNumber(raw.modules),
    docChunks: asNumber(raw.doc_chunks),
    codeChunks: asNumber(raw.code_chunks),
  };
}

function mapKnowledge(raw: any): LibraryKnowledgeRecord {
  return {
    profile: mapProfile(raw?.profile),
    projects: Array.isArray(raw?.projects) ? raw.projects.map(mapProject) : [],
    roleDocuments: Array.isArray(raw?.role_documents) ? raw.role_documents.map(mapRoleDocument) : [],
  };
}

function mapWorkspace(raw: any): LibraryWorkspaceRecord {
  return {
    workspaceId: asString(raw?.workspace_id),
    name: asString(raw?.name, "Interview Workspace"),
    createdAt: raw?.created_at ?? null,
    updatedAt: raw?.updated_at ?? null,
    knowledge: mapKnowledge(raw?.knowledge),
    overlays: Array.isArray(raw?.overlays) ? raw.overlays.map(mapOverlay) : [],
    presets: Array.isArray(raw?.presets) ? raw.presets.map(mapPreset) : [],
    compiledBundles: Array.isArray(raw?.compiled_bundles) ? raw.compiled_bundles.map(mapBundleSummary) : [],
    compileSummary: mapCompileSummary(raw?.compile_summary),
  };
}

function mapImportSummary(raw: any): LibraryImportSummary | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  return {
    projectName: asString(raw.project_name),
    importedDocs: asNumber(raw.imported_docs),
    importedCodeFiles: asNumber(raw.imported_code_files),
    sourcePath: asString(raw.source_path),
  };
}

function mapSessionPayload(raw: any): LibrarySessionPayload {
  return {
    knowledge: raw?.knowledge ?? {},
    briefing: {
      company: asString(raw?.briefing?.company),
      businessContext: asString(raw?.briefing?.business_context),
      jobDescription: asString(raw?.briefing?.job_description),
      priorityProjects: asStringArray(raw?.briefing?.priority_projects),
      focusTopics: asStringArray(raw?.briefing?.focus_topics),
      styleBias: asStringArray(raw?.briefing?.style_bias),
      likelyQuestions: asStringArray(raw?.briefing?.likely_questions),
    },
    activationSummary: mapBundleSummary(raw?.activation_summary),
  };
}

export async function listLibraryWorkspaces(baseUrl: string): Promise<LibraryWorkspaceRecord[]> {
  const payload = await requestJson<{ workspaces?: unknown[] }>(`${baseUrl}/api/library/workspaces`, {
    errorMessage: "Failed to load library workspaces",
  });
  return Array.isArray(payload.workspaces) ? payload.workspaces.map(mapWorkspace) : [];
}

export async function createLibraryWorkspace(
  baseUrl: string,
  payload: Record<string, unknown>,
): Promise<LibraryWorkspaceRecord> {
  const workspace = await requestJson<any>(`${baseUrl}/api/library/workspaces`, {
    method: "POST",
    payload,
    errorMessage: "Failed to create library workspace",
  });
  return mapWorkspace(workspace);
}

export async function getLibraryWorkspace(baseUrl: string, workspaceId: string): Promise<LibraryWorkspaceRecord> {
  const workspace = await requestJson<any>(`${baseUrl}/api/library/workspaces/${workspaceId}`, {
    errorMessage: "Failed to load library workspace",
  });
  return mapWorkspace(workspace);
}

export async function updateLibraryWorkspace(
  baseUrl: string,
  workspaceId: string,
  payload: Record<string, unknown>,
): Promise<LibraryWorkspaceRecord> {
  const workspace = await requestJson<any>(`${baseUrl}/api/library/workspaces/${workspaceId}`, {
    method: "PUT",
    payload,
    errorMessage: "Failed to update library workspace",
  });
  return mapWorkspace(workspace);
}

export async function createLibraryProject(
  baseUrl: string,
  workspaceId: string,
  payload: Record<string, unknown>,
): Promise<LibraryProjectRecord> {
  const project = await requestJson<any>(`${baseUrl}/api/library/workspaces/${workspaceId}/projects`, {
    method: "POST",
    payload,
    errorMessage: "Failed to create library project",
  });
  return mapProject(project);
}

export async function updateLibraryProject(
  baseUrl: string,
  projectId: string,
  payload: Record<string, unknown>,
): Promise<LibraryProjectRecord> {
  const project = await requestJson<any>(`${baseUrl}/api/library/projects/${projectId}`, {
    method: "PUT",
    payload,
    errorMessage: "Failed to update library project",
  });
  return mapProject(project);
}

export async function deleteLibraryProject(baseUrl: string, projectId: string): Promise<void> {
  await requestJson(`${baseUrl}/api/library/projects/${projectId}`, {
    method: "DELETE",
    errorMessage: "Failed to delete library project",
  });
}

export async function getLibraryProjectCompiledPreview(
  baseUrl: string,
  projectId: string,
): Promise<LibraryProjectCompiledPreviewRecord> {
  const payload = await requestJson<any>(`${baseUrl}/api/library/projects/${projectId}/compiled-preview`, {
    errorMessage: "Failed to load project compiled preview",
  });
  return mapProjectCompiledPreview(payload);
}

export async function listLibraryProjectDocuments(
  baseUrl: string,
  projectId: string,
): Promise<LibraryDocumentRecord[]> {
  const payload = await requestJson<{ documents?: unknown[] }>(`${baseUrl}/api/library/projects/${projectId}/documents`, {
    errorMessage: "Failed to load project documents",
  });
  return Array.isArray(payload.documents) ? payload.documents.map(mapDocument) : [];
}

export async function createLibraryProjectDocument(
  baseUrl: string,
  projectId: string,
  payload: Record<string, unknown>,
): Promise<LibraryDocumentRecord> {
  const document = await requestJson<any>(`${baseUrl}/api/library/projects/${projectId}/documents`, {
    method: "POST",
    payload,
    errorMessage: "Failed to create project document",
  });
  return mapDocument(document);
}

export async function importLibraryProjectPath(
  baseUrl: string,
  projectId: string,
  payload: Record<string, unknown>,
): Promise<{ workspace: LibraryWorkspaceRecord; importSummary: LibraryImportSummary | null }> {
  const response = await requestJson<any>(`${baseUrl}/api/library/projects/${projectId}/repos/import-path`, {
    method: "POST",
    payload,
    errorMessage: "Failed to import project path",
  });
  return {
    workspace: mapWorkspace(response),
    importSummary: mapImportSummary(response?.import_summary),
  };
}

export async function listLibraryProjectRepos(
  baseUrl: string,
  projectId: string,
): Promise<LibraryRepoSummaryRecord[]> {
  const payload = await requestJson<{ repos?: unknown[] }>(`${baseUrl}/api/library/projects/${projectId}/repos`, {
    errorMessage: "Failed to load project repos",
  });
  return Array.isArray(payload.repos) ? payload.repos.map(mapRepoSummary) : [];
}

export async function reindexLibraryRepo(
  baseUrl: string,
  repoId: string,
): Promise<{ workspace: LibraryWorkspaceRecord; importSummary: LibraryImportSummary | null }> {
  const response = await requestJson<any>(`${baseUrl}/api/library/repos/${repoId}/reindex`, {
    method: "POST",
    payload: {},
    errorMessage: "Failed to reindex repo",
  });
  return {
    workspace: mapWorkspace(response),
    importSummary: mapImportSummary(response?.import_summary),
  };
}

export async function listLibraryRoleDocuments(
  baseUrl: string,
  workspaceId: string,
): Promise<LibraryRoleDocumentRecord[]> {
  const payload = await requestJson<{ documents?: unknown[] }>(`${baseUrl}/api/library/workspaces/${workspaceId}/role-documents`, {
    errorMessage: "Failed to load role documents",
  });
  return Array.isArray(payload.documents) ? payload.documents.map(mapRoleDocument) : [];
}

export async function createLibraryRoleDocument(
  baseUrl: string,
  workspaceId: string,
  payload: Record<string, unknown>,
): Promise<LibraryRoleDocumentRecord> {
  const document = await requestJson<any>(`${baseUrl}/api/library/workspaces/${workspaceId}/role-documents`, {
    method: "POST",
    payload,
    errorMessage: "Failed to create role document",
  });
  return mapRoleDocument(document);
}

export async function updateLibraryDocument(
  baseUrl: string,
  documentId: string,
  payload: Record<string, unknown>,
): Promise<LibraryDocumentRecord | LibraryRoleDocumentRecord> {
  const document = await requestJson<any>(`${baseUrl}/api/library/documents/${documentId}`, {
    method: "PUT",
    payload,
    errorMessage: "Failed to update document",
  });
  return asString(document?.scope) === "role" ? mapRoleDocument(document) : mapDocument(document);
}

export async function deleteLibraryDocument(baseUrl: string, documentId: string): Promise<void> {
  await requestJson(`${baseUrl}/api/library/documents/${documentId}`, {
    method: "DELETE",
    errorMessage: "Failed to delete document",
  });
}

export async function createLibraryOverlay(
  baseUrl: string,
  workspaceId: string,
  payload: Record<string, unknown>,
): Promise<LibraryOverlayRecord> {
  const overlay = await requestJson<any>(`${baseUrl}/api/library/workspaces/${workspaceId}/overlays`, {
    method: "POST",
    payload,
    errorMessage: "Failed to create overlay",
  });
  return mapOverlay(overlay);
}

export async function updateLibraryOverlay(
  baseUrl: string,
  overlayId: string,
  payload: Record<string, unknown>,
): Promise<LibraryOverlayRecord> {
  const overlay = await requestJson<any>(`${baseUrl}/api/library/overlays/${overlayId}`, {
    method: "PUT",
    payload,
    errorMessage: "Failed to update overlay",
  });
  return mapOverlay(overlay);
}

export async function createLibraryPreset(
  baseUrl: string,
  workspaceId: string,
  payload: Record<string, unknown>,
): Promise<LibraryPresetRecord> {
  const preset = await requestJson<any>(`${baseUrl}/api/library/workspaces/${workspaceId}/presets`, {
    method: "POST",
    payload,
    errorMessage: "Failed to create preset",
  });
  return mapPreset(preset);
}

export async function updateLibraryPreset(
  baseUrl: string,
  presetId: string,
  payload: Record<string, unknown>,
): Promise<LibraryPresetRecord> {
  const preset = await requestJson<any>(`${baseUrl}/api/library/presets/${presetId}`, {
    method: "PUT",
    payload,
    errorMessage: "Failed to update preset",
  });
  return mapPreset(preset);
}

export async function listLibraryBundles(
  baseUrl: string,
  workspaceId: string,
): Promise<LibraryBundleSummaryRecord[]> {
  const payload = await requestJson<{ bundles?: unknown[] }>(`${baseUrl}/api/library/workspaces/${workspaceId}/bundles`, {
    errorMessage: "Failed to load bundle summaries",
  });
  return Array.isArray(payload.bundles) ? payload.bundles.map(mapBundleSummary) : [];
}

export async function compileLibraryWorkspace(
  baseUrl: string,
  workspaceId: string,
): Promise<LibraryWorkspaceRecord> {
  const workspace = await requestJson<any>(`${baseUrl}/api/workspaces/${workspaceId}/compile`, {
    method: "POST",
    payload: {},
    errorMessage: "Failed to compile library workspace",
  });
  return mapWorkspace(workspace);
}

export async function buildPresetSessionPayload(
  baseUrl: string,
  presetId: string,
): Promise<LibrarySessionPayload> {
  const payload = await requestJson<any>(`${baseUrl}/api/library/presets/${presetId}/build-session-payload`, {
    method: "POST",
    payload: {},
    errorMessage: "Failed to build preset session payload",
  });
  return mapSessionPayload(payload);
}
