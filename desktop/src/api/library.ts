import { requestJson } from "./client";
import type {
  LibraryAuthoringTemplateRecord,
  LibraryAuthoringSupportingRefRecord,
  LibraryAuthoringValidationRecord,
  LibraryBriefingPayload,
  LibraryBundleComparisonRecord,
  LibraryBundleDetailRecord,
  LibraryBundleSummaryRecord,
  LibraryCompiledEvidenceCardRecord,
  LibraryCompiledMetricEvidenceRecord,
  LibraryCompiledModuleCardRecord,
  LibraryCompiledRetrievalUnitRecord,
  LibraryProjectCompiledPreviewRecord,
  LibraryWorkspaceCompiledPreviewFiltersRecord,
  LibraryWorkspaceCompiledPreviewRecord,
  LibraryWorkspaceCompiledPreviewSummaryRecord,
  LibraryCodeFileRecord,
  LibraryCompileSummaryRecord,
  LibraryDocumentRecord,
  LibraryImportSummary,
  LibraryKnowledgeRecord,
  LibraryManualEvidenceRecord,
  LibraryManualMetricRecord,
  LibraryManualRetrievalUnitRecord,
  LibraryOverlayRecord,
  LibraryPresetComparisonRecord,
  LibraryPresetLatestBundleStatusRecord,
  LibraryPresetRecord,
  LibraryProfileRecord,
  LibraryProjectAuthoringPackRecord,
  LibraryProjectAuthoringSummaryRecord,
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

function mapAuthoringSupportingRef(raw: any): LibraryAuthoringSupportingRefRecord {
  return {
    refId: asString(raw?.ref_id),
    refKind: asString(raw?.ref_kind),
    label: asString(raw?.label),
  };
}

function mapAuthoringSummary(raw: any): LibraryProjectAuthoringSummaryRecord {
  return {
    manualEvidenceCount: asNumber(raw?.manual_evidence_count),
    manualMetricCount: asNumber(raw?.manual_metric_count),
    manualRetrievalUnitCount: asNumber(raw?.manual_retrieval_unit_count),
    availableSupportingRefCount: asNumber(raw?.available_supporting_ref_count),
    usedSupportingRefCount: asNumber(raw?.used_supporting_ref_count),
  };
}

function mapAuthoringValidation(raw: any): LibraryAuthoringValidationRecord {
  return {
    valid: Boolean(raw?.valid),
    errors: asStringArray(raw?.errors),
    warnings: asStringArray(raw?.warnings),
  };
}

function mapProjectAuthoringPack(raw: any): LibraryProjectAuthoringPackRecord {
  return {
    projectId: asString(raw?.project_id),
    projectName: asString(raw?.project_name),
    manualEvidence: Array.isArray(raw?.manual_evidence) ? raw.manual_evidence.map(mapManualEvidence) : [],
    manualMetrics: Array.isArray(raw?.manual_metrics) ? raw.manual_metrics.map(mapManualMetric) : [],
    manualRetrievalUnits: Array.isArray(raw?.manual_retrieval_units)
      ? raw.manual_retrieval_units.map(mapManualRetrievalUnit)
      : [],
    availableSupportingRefs: Array.isArray(raw?.available_supporting_refs)
      ? raw.available_supporting_refs.map(mapAuthoringSupportingRef)
      : [],
    summary: mapAuthoringSummary(raw?.summary),
    validation: mapAuthoringValidation(raw?.validation),
    project: raw?.project ? mapProject(raw.project) : null,
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

function mapPresetComparison(raw: any): LibraryPresetComparisonRecord {
  return {
    leftPreset: mapPreset(raw?.left_preset),
    rightPreset: mapPreset(raw?.right_preset),
    addedProjects: asStringArray(raw?.added_projects),
    removedProjects: asStringArray(raw?.removed_projects),
    sharedProjects: asStringArray(raw?.shared_projects),
    leftOverlayName: asString(raw?.left_overlay_name),
    rightOverlayName: asString(raw?.right_overlay_name),
    overlayChanged: Boolean(raw?.overlay_changed),
    leftIncludeRoleDocuments: Boolean(raw?.left_include_role_documents),
    rightIncludeRoleDocuments: Boolean(raw?.right_include_role_documents),
    includeRoleDocumentsChanged: Boolean(raw?.include_role_documents_changed),
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
    includeRoleDocuments: Boolean(raw?.include_role_documents),
    projectCount: asNumber(raw?.project_count),
    retrievalUnitCount: asNumber(raw?.retrieval_unit_count),
    metricEvidenceCount: asNumber(raw?.metric_evidence_count),
    terminologyCount: asNumber(raw?.terminology_count),
    builtAt: asNumber(raw?.built_at),
  };
}

function mapPresetLatestBundleStatus(raw: any): LibraryPresetLatestBundleStatusRecord {
  return {
    preset: mapPreset(raw?.preset),
    latestBundle: raw?.latest_bundle ? mapBundleSummary(raw.latest_bundle) : null,
    status: asString(raw?.status, "missing") as "missing" | "current" | "stale",
    reasons: asStringArray(raw?.reasons),
    staleProjectNames: asStringArray(raw?.stale_project_names),
  };
}

function mapAuthoringTemplate(raw: any): LibraryAuthoringTemplateRecord {
  return {
    templateId: asString(raw?.template_id),
    name: asString(raw?.name, "Authoring Template"),
    description: asString(raw?.description),
    sourceProjectId: asString(raw?.source_project_id),
    sourceProjectName: asString(raw?.source_project_name),
    manualEvidence: Array.isArray(raw?.manual_evidence) ? raw.manual_evidence.map(mapManualEvidence) : [],
    manualMetrics: Array.isArray(raw?.manual_metrics) ? raw.manual_metrics.map(mapManualMetric) : [],
    manualRetrievalUnits: Array.isArray(raw?.manual_retrieval_units)
      ? raw.manual_retrieval_units.map(mapManualRetrievalUnit)
      : [],
    createdAt: asNumber(raw?.created_at),
    updatedAt: asNumber(raw?.updated_at),
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

function mapWorkspaceCompiledPreviewSummary(raw: any): LibraryWorkspaceCompiledPreviewSummaryRecord {
  return {
    projectId: asString(raw?.project_id),
    projectName: asString(raw?.project_name),
    moduleCount: asNumber(raw?.module_count),
    evidenceCount: asNumber(raw?.evidence_count),
    metricCount: asNumber(raw?.metric_count),
    retrievalUnitCount: asNumber(raw?.retrieval_unit_count),
  };
}

function mapWorkspaceCompiledPreviewFilters(raw: any): LibraryWorkspaceCompiledPreviewFiltersRecord {
  return {
    projectId: asString(raw?.project_id),
    artifactKind: asString(raw?.artifact_kind),
    search: asString(raw?.search),
  };
}

function mapWorkspaceCompiledPreview(raw: any): LibraryWorkspaceCompiledPreviewRecord {
  return {
    compiled: Boolean(raw?.compiled),
    moduleCards: Array.isArray(raw?.module_cards) ? raw.module_cards.map(mapCompiledModuleCard) : [],
    evidenceCards: Array.isArray(raw?.evidence_cards) ? raw.evidence_cards.map(mapCompiledEvidenceCard) : [],
    metricEvidence: Array.isArray(raw?.metric_evidence) ? raw.metric_evidence.map(mapCompiledMetricEvidence) : [],
    retrievalUnits: Array.isArray(raw?.retrieval_units) ? raw.retrieval_units.map(mapCompiledRetrievalUnit) : [],
    terminology: asStringArray(raw?.terminology),
    compiledAt: asNumber(raw?.compiled_at),
    filters: mapWorkspaceCompiledPreviewFilters(raw?.filters),
    projectSummaries: Array.isArray(raw?.project_summaries)
      ? raw.project_summaries.map(mapWorkspaceCompiledPreviewSummary)
      : [],
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
    authoringTemplates: Array.isArray(raw?.authoring_templates) ? raw.authoring_templates.map(mapAuthoringTemplate) : [],
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

function mapBriefing(raw: any): LibraryBriefingPayload {
  return {
    company: asString(raw?.company),
    businessContext: asString(raw?.business_context ?? raw?.businessContext),
    jobDescription: asString(raw?.job_description ?? raw?.jobDescription),
    priorityProjects: asStringArray(raw?.priority_projects ?? raw?.priorityProjects),
    focusTopics: asStringArray(raw?.focus_topics ?? raw?.focusTopics),
    styleBias: asStringArray(raw?.style_bias ?? raw?.styleBias),
    likelyQuestions: asStringArray(raw?.likely_questions ?? raw?.likelyQuestions),
  };
}

function mapBundleDetail(raw: any): LibraryBundleDetailRecord {
  return {
    ...mapBundleSummary(raw),
    knowledge: raw?.knowledge ?? {},
    briefing: mapBriefing(raw?.briefing),
  };
}

function mapBundleComparison(raw: any): LibraryBundleComparisonRecord {
  return {
    leftBundle: mapBundleSummary(raw?.left_bundle),
    rightBundle: mapBundleSummary(raw?.right_bundle),
    addedProjects: asStringArray(raw?.added_projects),
    removedProjects: asStringArray(raw?.removed_projects),
    projectCountDelta: asNumber(raw?.project_count_delta),
    retrievalUnitDelta: asNumber(raw?.retrieval_unit_delta),
    metricEvidenceDelta: asNumber(raw?.metric_evidence_delta),
    terminologyDelta: asNumber(raw?.terminology_delta),
    addedFocusTopics: asStringArray(raw?.added_focus_topics),
    removedFocusTopics: asStringArray(raw?.removed_focus_topics),
    addedRetrievalUnits: asStringArray(raw?.added_retrieval_units),
    removedRetrievalUnits: asStringArray(raw?.removed_retrieval_units),
    addedEvidenceTitles: asStringArray(raw?.added_evidence_titles),
    removedEvidenceTitles: asStringArray(raw?.removed_evidence_titles),
    addedHookTexts: asStringArray(raw?.added_hook_texts),
    removedHookTexts: asStringArray(raw?.removed_hook_texts),
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

export async function getLibraryProjectAuthoringPack(
  baseUrl: string,
  projectId: string,
): Promise<LibraryProjectAuthoringPackRecord> {
  const payload = await requestJson<any>(`${baseUrl}/api/library/projects/${projectId}/authoring-pack`, {
    errorMessage: "Failed to load project authoring pack",
  });
  return mapProjectAuthoringPack(payload);
}

export async function previewLibraryProjectAuthoringPack(
  baseUrl: string,
  projectId: string,
  payload: Record<string, unknown>,
): Promise<LibraryProjectAuthoringPackRecord> {
  const response = await requestJson<any>(`${baseUrl}/api/library/projects/${projectId}/authoring-pack/preview`, {
    method: "POST",
    payload,
    errorMessage: "Failed to preview project authoring pack",
  });
  return mapProjectAuthoringPack(response);
}

export async function buildLibraryProjectAuthoringPackTemplate(
  baseUrl: string,
  projectId: string,
  payload: Record<string, unknown>,
): Promise<LibraryProjectAuthoringPackRecord> {
  const response = await requestJson<any>(`${baseUrl}/api/library/projects/${projectId}/authoring-pack/template`, {
    method: "POST",
    payload,
    errorMessage: "Failed to build project authoring pack template",
  });
  return mapProjectAuthoringPack(response);
}

export async function updateLibraryProjectAuthoringPack(
  baseUrl: string,
  projectId: string,
  payload: Record<string, unknown>,
): Promise<LibraryProjectAuthoringPackRecord> {
  const response = await requestJson<any>(`${baseUrl}/api/library/projects/${projectId}/authoring-pack`, {
    method: "PUT",
    payload,
    errorMessage: "Failed to update project authoring pack",
  });
  return mapProjectAuthoringPack(response);
}

export async function getLibraryWorkspacePresetStatuses(
  baseUrl: string,
  workspaceId: string,
): Promise<LibraryPresetLatestBundleStatusRecord[]> {
  const payload = await requestJson<any>(`${baseUrl}/api/library/workspaces/${workspaceId}/preset-statuses`, {
    errorMessage: "Failed to load workspace preset statuses",
  });
  return Array.isArray(payload?.preset_statuses) ? payload.preset_statuses.map(mapPresetLatestBundleStatus) : [];
}

export async function createLibraryAuthoringTemplate(
  baseUrl: string,
  workspaceId: string,
  payload: Record<string, unknown>,
): Promise<LibraryAuthoringTemplateRecord> {
  const template = await requestJson<any>(`${baseUrl}/api/library/workspaces/${workspaceId}/authoring-templates`, {
    method: "POST",
    payload,
    errorMessage: "Failed to create authoring template",
  });
  return mapAuthoringTemplate(template);
}

export async function updateLibraryAuthoringTemplate(
  baseUrl: string,
  templateId: string,
  payload: Record<string, unknown>,
): Promise<LibraryAuthoringTemplateRecord> {
  const template = await requestJson<any>(`${baseUrl}/api/library/authoring-templates/${templateId}`, {
    method: "PUT",
    payload,
    errorMessage: "Failed to update authoring template",
  });
  return mapAuthoringTemplate(template);
}

export async function deleteLibraryAuthoringTemplate(baseUrl: string, templateId: string): Promise<void> {
  await requestJson(`${baseUrl}/api/library/authoring-templates/${templateId}`, {
    method: "DELETE",
    errorMessage: "Failed to delete authoring template",
  });
}

export async function applyLibraryAuthoringTemplateToProject(
  baseUrl: string,
  projectId: string,
  payload: Record<string, unknown>,
): Promise<LibraryProjectAuthoringPackRecord> {
  const response = await requestJson<any>(`${baseUrl}/api/library/projects/${projectId}/authoring-pack/apply-template`, {
    method: "POST",
    payload,
    errorMessage: "Failed to apply authoring template",
  });
  return mapProjectAuthoringPack(response);
}

export async function getLibraryWorkspaceCompiledPreview(
  baseUrl: string,
  workspaceId: string,
  filters?: Partial<LibraryWorkspaceCompiledPreviewFiltersRecord>,
): Promise<LibraryWorkspaceCompiledPreviewRecord> {
  const searchParams = new URLSearchParams();
  if (filters?.projectId) {
    searchParams.set("project_id", filters.projectId);
  }
  if (filters?.artifactKind) {
    searchParams.set("artifact_kind", filters.artifactKind);
  }
  if (filters?.search) {
    searchParams.set("search", filters.search);
  }
  const query = searchParams.toString();
  const payload = await requestJson<any>(
    `${baseUrl}/api/library/workspaces/${workspaceId}/compiled-preview${query ? `?${query}` : ""}`,
    {
      errorMessage: "Failed to load workspace compiled preview",
    },
  );
  return mapWorkspaceCompiledPreview(payload);
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

export async function cloneLibraryPreset(
  baseUrl: string,
  presetId: string,
  payload: Record<string, unknown>,
): Promise<LibraryPresetRecord> {
  const preset = await requestJson<any>(`${baseUrl}/api/library/presets/${presetId}/clone`, {
    method: "POST",
    payload,
    errorMessage: "Failed to clone preset",
  });
  return mapPreset(preset);
}

export async function compareLibraryPresets(
  baseUrl: string,
  leftPresetId: string,
  rightPresetId: string,
): Promise<LibraryPresetComparisonRecord> {
  const payload = await requestJson<any>(`${baseUrl}/api/library/presets/${leftPresetId}/compare/${rightPresetId}`, {
    errorMessage: "Failed to compare presets",
  });
  return mapPresetComparison(payload);
}

export async function getLibraryPresetLatestBundleStatus(
  baseUrl: string,
  presetId: string,
): Promise<LibraryPresetLatestBundleStatusRecord> {
  const payload = await requestJson<any>(`${baseUrl}/api/library/presets/${presetId}/latest-bundle-status`, {
    errorMessage: "Failed to load preset bundle status",
  });
  return mapPresetLatestBundleStatus(payload);
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

export async function getLibraryBundleDetail(baseUrl: string, bundleId: string): Promise<LibraryBundleDetailRecord> {
  const payload = await requestJson<any>(`${baseUrl}/api/library/bundles/${bundleId}`, {
    errorMessage: "Failed to load bundle detail",
  });
  return mapBundleDetail(payload);
}

export async function compareLibraryBundles(
  baseUrl: string,
  leftBundleId: string,
  rightBundleId: string,
): Promise<LibraryBundleComparisonRecord> {
  const payload = await requestJson<any>(`${baseUrl}/api/library/bundles/${leftBundleId}/compare/${rightBundleId}`, {
    errorMessage: "Failed to compare bundles",
  });
  return mapBundleComparison(payload);
}

export async function reuseLibraryBundleSessionPayload(
  baseUrl: string,
  bundleId: string,
): Promise<LibrarySessionPayload> {
  const payload = await requestJson<any>(`${baseUrl}/api/library/bundles/${bundleId}/reuse-session-payload`, {
    method: "POST",
    payload: {},
    errorMessage: "Failed to reuse bundle payload",
  });
  return mapSessionPayload(payload);
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
