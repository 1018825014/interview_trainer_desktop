import { useEffect, useMemo, useState } from "react";
import {
  buildPresetSessionPayload,
  compareLibraryBundles,
  compileLibraryWorkspace,
  createLibraryProjectDocument,
  createLibraryOverlay,
  createLibraryPreset,
  createLibraryProject,
  createLibraryRoleDocument,
  createLibraryWorkspace,
  deleteLibraryDocument,
  deleteLibraryProject,
  getLibraryBundleDetail,
  getLibraryProjectAuthoringPack,
  getLibraryProjectCompiledPreview,
  getLibraryWorkspaceCompiledPreview,
  getLibraryWorkspace,
  importLibraryProjectPath,
  listLibraryWorkspaces,
  previewLibraryProjectAuthoringPack,
  reindexLibraryRepo,
  reuseLibraryBundleSessionPayload,
  updateLibraryDocument,
  updateLibraryOverlay,
  updateLibraryProjectAuthoringPack,
  updateLibraryPreset,
  updateLibraryProject,
  updateLibraryWorkspace,
} from "../../api/library";
import { sampleLibraryWorkspace } from "../../mock/sample";
import type {
  LibraryBundleSummaryRecord,
  LibraryBundleComparisonRecord,
  LibraryBundleDetailRecord,
  LibraryEntitySelection,
  LibraryOverlayRecord,
  LibraryPresetRecord,
  LibraryDocumentRecord,
  LibraryProjectAuthoringPackRecord,
  LibraryProjectCompiledPreviewRecord,
  LibraryProfileRecord,
  LibraryProjectRecord,
  LibraryRoleDocumentRecord,
  LibrarySessionPayload,
  LibraryWorkspaceCompiledPreviewRecord,
  LibraryWorkspaceRecord,
} from "../../types/library";
import { OverlayEditor } from "./OverlayEditor";
import { PresetEditor } from "./PresetEditor";
import { ProjectEditor } from "./ProjectEditor";
import { StatusRail } from "./StatusRail";
import { WorkspaceNav } from "./WorkspaceNav";

interface LibraryPanelProps {
  backendBaseUrl: string;
  backendOnline: boolean;
  onActivateSession: (payload: LibrarySessionPayload) => Promise<void>;
}

function defaultProfile(): LibraryProfileRecord {
  return {
    headline: "LLM application engineer",
    summary: "",
    strengths: [],
    targetRoles: [],
    introMaterial: [],
  };
}

function defaultRoleDocument(): LibraryRoleDocumentRecord {
  return {
    documentId: "role-draft",
    scope: "role",
    title: "Role Notes",
    path: "role/notes.md",
    content: "",
    sourceKind: "manual",
    sourcePath: "",
    repoId: "",
    updatedAt: Date.now() / 1000,
  };
}

function defaultProjectDocument(project: LibraryProjectRecord): LibraryDocumentRecord {
  return {
    documentId: `draft-${Date.now()}`,
    scope: "project",
    title: "New Document",
    path: `notes/${project.documents.length + 1}.md`,
    content: "",
    sourceKind: "manual",
    sourcePath: "",
    repoId: "",
    updatedAt: Date.now() / 1000,
  };
}

function splitLines(value: string): string[] {
  return value
    .replace(/\r/g, "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function joinLines(value: string[]): string {
  return value.join("\n");
}

function defaultSelection(workspace: LibraryWorkspaceRecord): LibraryEntitySelection {
  const firstProject = workspace.knowledge.projects[0];
  if (firstProject) {
    return { type: "project", id: firstProject.projectId };
  }
  return { type: "workspace", id: workspace.workspaceId };
}

function ensureSelection(
  selection: LibraryEntitySelection | null,
  workspace: LibraryWorkspaceRecord,
): LibraryEntitySelection {
  if (!selection) {
    return defaultSelection(workspace);
  }
  if (selection.type === "workspace" && selection.id === workspace.workspaceId) {
    return selection;
  }
  if (selection.type === "project" && workspace.knowledge.projects.some((item) => item.projectId === selection.id)) {
    return selection;
  }
  if (selection.type === "overlay" && workspace.overlays.some((item) => item.overlayId === selection.id)) {
    return selection;
  }
  if (selection.type === "preset" && workspace.presets.some((item) => item.presetId === selection.id)) {
    return selection;
  }
  if (selection.type === "bundle" && workspace.compiledBundles.some((item) => item.bundleId === selection.id)) {
    return selection;
  }
  return defaultSelection(workspace);
}

function serializeWorkspacePayload(workspace: LibraryWorkspaceRecord): Record<string, unknown> {
  return {
    name: workspace.name,
    knowledge: {
      profile: {
        headline: workspace.knowledge.profile.headline,
        summary: workspace.knowledge.profile.summary,
        strengths: workspace.knowledge.profile.strengths,
        target_roles: workspace.knowledge.profile.targetRoles,
        intro_material: workspace.knowledge.profile.introMaterial,
      },
      projects: workspace.knowledge.projects.map((project) => serializeProjectPayload(project)),
      role_documents: workspace.knowledge.roleDocuments.map((document) => ({
        document_id: document.documentId,
        title: document.title,
        path: document.path,
        content: document.content,
        source_kind: document.sourceKind,
        source_path: document.sourcePath,
        repo_id: document.repoId,
        updated_at: document.updatedAt,
      })),
    },
  };
}

function serializeProjectPayload(project: LibraryProjectRecord): Record<string, unknown> {
  return {
    project_id: project.projectId,
    name: project.name,
    pitch_30: project.pitch30,
    pitch_90: project.pitch90,
    business_value: project.businessValue,
    architecture: project.architecture,
    key_metrics: project.keyMetrics,
    tradeoffs: project.tradeoffs,
    failure_cases: project.failureCases,
    limitations: project.limitations,
    upgrade_plan: project.upgradePlan,
    interviewer_hooks: project.interviewerHooks,
    manual_evidence: project.manualEvidence.map((item) => ({
      evidence_id: item.evidenceId,
      module_id: item.moduleId,
      evidence_type: item.evidenceType,
      title: item.title,
      summary: item.summary,
      source_kind: item.sourceKind,
      source_ref: item.sourceRef,
      confidence: item.confidence,
    })),
    manual_metrics: project.manualMetrics.map((item) => ({
      evidence_id: item.evidenceId,
      module_id: item.moduleId,
      metric_name: item.metricName,
      metric_value: item.metricValue,
      baseline: item.baseline,
      method: item.method,
      environment: item.environment,
      source_note: item.sourceNote,
      confidence: item.confidence,
    })),
    manual_retrieval_units: project.manualRetrievalUnits.map((item) => ({
      unit_id: item.unitId,
      unit_type: item.unitType,
      module_id: item.moduleId,
      question_forms: item.questionForms,
      short_answer: item.shortAnswer,
      long_answer: item.longAnswer,
      key_points: item.keyPoints,
      supporting_refs: item.supportingRefs,
      hooks: item.hooks,
      safe_claims: item.safeClaims,
    })),
    repo_summaries: project.repoSummaries.map((repo) => ({
      repo_id: repo.repoId,
      label: repo.label,
      root_path: repo.rootPath,
      status: repo.status,
      last_scanned_at: repo.lastScannedAt,
      imported_docs: repo.importedDocs,
      imported_code_files: repo.importedCodeFiles,
    })),
    documents: project.documents.map((document) => ({
      document_id: document.documentId,
      title: document.title,
      path: document.path,
      content: document.content,
      source_kind: document.sourceKind,
      source_path: document.sourcePath,
      repo_id: document.repoId,
      updated_at: document.updatedAt,
    })),
    code_files: project.codeFiles.map((file) => ({
      path: file.path,
      content: file.content,
      source_kind: file.sourceKind,
      source_path: file.sourcePath,
      repo_id: file.repoId,
    })),
  };
}

function serializeOverlayPayload(overlay: LibraryOverlayRecord): Record<string, unknown> {
  return {
    overlay_id: overlay.overlayId,
    name: overlay.name,
    company: overlay.company,
    job_description: overlay.jobDescription,
    business_context: overlay.businessContext,
    focus_project_ids: overlay.focusProjectIds,
    emphasis_points: overlay.emphasisPoints,
    style_profile: overlay.styleProfile,
    depth_policy: overlay.depthPolicy,
  };
}

function serializePresetPayload(preset: LibraryPresetRecord): Record<string, unknown> {
  return {
    preset_id: preset.presetId,
    name: preset.name,
    overlay_id: preset.overlayId,
    project_ids: preset.projectIds,
    include_role_documents: preset.includeRoleDocuments,
  };
}

function latestBundleForPreset(
  preset: LibraryPresetRecord | null,
  bundles: LibraryBundleSummaryRecord[],
): LibraryBundleSummaryRecord | null {
  if (!preset) {
    return bundles.length > 0 ? bundles[bundles.length - 1] : null;
  }
  const matches = bundles.filter((item) => item.presetId === preset.presetId);
  return matches.length > 0 ? matches[matches.length - 1] : null;
}

export function LibraryPanel({ backendBaseUrl, backendOnline, onActivateSession }: LibraryPanelProps) {
  const [workspaceList, setWorkspaceList] = useState<LibraryWorkspaceRecord[]>([]);
  const [workspace, setWorkspace] = useState<LibraryWorkspaceRecord | null>(null);
  const [selection, setSelection] = useState<LibraryEntitySelection | null>(null);
  const [importPath, setImportPath] = useState("");
  const [statusMessage, setStatusMessage] = useState("准备加载本地资料库");
  const [latestPayload, setLatestPayload] = useState<LibrarySessionPayload | null>(null);
  const [projectCompiledPreview, setProjectCompiledPreview] = useState<LibraryProjectCompiledPreviewRecord | null>(null);
  const [projectAuthoringPack, setProjectAuthoringPack] = useState<LibraryProjectAuthoringPackRecord | null>(null);
  const [projectAuthoringStatus, setProjectAuthoringStatus] = useState("");
  const [workspaceCompiledPreview, setWorkspaceCompiledPreview] = useState<LibraryWorkspaceCompiledPreviewRecord | null>(null);
  const [workspacePreviewFilters, setWorkspacePreviewFilters] = useState({
    projectId: "",
    artifactKind: "",
    search: "",
  });
  const [bundleDetail, setBundleDetail] = useState<LibraryBundleDetailRecord | null>(null);
  const [bundleComparison, setBundleComparison] = useState<LibraryBundleComparisonRecord | null>(null);
  const [compareBundleId, setCompareBundleId] = useState("");

  function syncWorkspace(next: LibraryWorkspaceRecord) {
    setWorkspace(next);
    setSelection((current) => ensureSelection(current, next));
    setWorkspaceList((current) => {
      const others = current.filter((item) => item.workspaceId !== next.workspaceId);
      return [next, ...others].sort((left, right) => (right.updatedAt ?? 0) - (left.updatedAt ?? 0));
    });
  }

  async function refreshWorkspace(workspaceId: string) {
    const refreshed = await getLibraryWorkspace(backendBaseUrl, workspaceId);
    syncWorkspace(refreshed);
    return refreshed;
  }

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!backendOnline) {
        if (!workspace) {
          setWorkspaceList([sampleLibraryWorkspace]);
          setWorkspace(sampleLibraryWorkspace);
          setSelection(defaultSelection(sampleLibraryWorkspace));
          setStatusMessage("后端离线，先展示示例资料库。");
        }
        return;
      }

      try {
        const items = await listLibraryWorkspaces(backendBaseUrl);
        if (cancelled) {
          return;
        }
        setWorkspaceList(items);
        if (items.length === 0) {
          setWorkspace(null);
          setSelection(null);
          setStatusMessage("还没有持久化资料库，点击左侧“新建资料库”开始。");
          return;
        }
        const targetId =
          workspace && items.some((item) => item.workspaceId === workspace.workspaceId)
            ? workspace.workspaceId
            : items[0].workspaceId;
        const refreshed = await getLibraryWorkspace(backendBaseUrl, targetId);
        if (cancelled) {
          return;
        }
        setWorkspace(refreshed);
        setSelection((current) => ensureSelection(current, refreshed));
        setStatusMessage(`已加载 ${items.length} 个资料库。`);
      } catch (error) {
        if (!cancelled) {
          setStatusMessage(error instanceof Error ? error.message : "加载资料库失败，展示示例数据。");
          if (!workspace) {
            setWorkspaceList([sampleLibraryWorkspace]);
            setWorkspace(sampleLibraryWorkspace);
            setSelection(defaultSelection(sampleLibraryWorkspace));
          }
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [backendBaseUrl, backendOnline]);

  const selectedProject = useMemo(() => {
    if (!workspace || selection?.type !== "project") {
      return null;
    }
    return workspace.knowledge.projects.find((item) => item.projectId === selection.id) ?? null;
  }, [workspace, selection]);

  const selectedOverlay = useMemo(() => {
    if (!workspace || selection?.type !== "overlay") {
      return null;
    }
    return workspace.overlays.find((item) => item.overlayId === selection.id) ?? null;
  }, [workspace, selection]);

  const selectedPreset = useMemo(() => {
    if (!workspace || selection?.type !== "preset") {
      return null;
    }
    return workspace.presets.find((item) => item.presetId === selection.id) ?? null;
  }, [workspace, selection]);

  const selectedBundle = useMemo(() => {
    if (!workspace || selection?.type !== "bundle") {
      return null;
    }
    return workspace.compiledBundles.find((item) => item.bundleId === selection.id) ?? null;
  }, [workspace, selection]);

  const presetLatestBundle = useMemo(
    () => latestBundleForPreset(selectedPreset, workspace?.compiledBundles ?? []),
    [selectedPreset, workspace],
  );

  useEffect(() => {
    let cancelled = false;

    async function loadProjectCompiledPreview() {
      if (!selectedProject || !backendOnline) {
        setProjectCompiledPreview(null);
        return;
      }
      try {
        const preview = await getLibraryProjectCompiledPreview(backendBaseUrl, selectedProject.projectId);
        if (!cancelled) {
          setProjectCompiledPreview(preview);
        }
      } catch {
        if (!cancelled) {
          setProjectCompiledPreview(null);
        }
      }
    }

    void loadProjectCompiledPreview();
    return () => {
      cancelled = true;
    };
  }, [backendBaseUrl, backendOnline, selectedProject?.projectId, workspace?.updatedAt, workspace?.compileSummary?.modules]);

  useEffect(() => {
    let cancelled = false;

    async function loadProjectAuthoringPack() {
      if (!selectedProject) {
        setProjectAuthoringPack(null);
        setProjectAuthoringStatus("");
        return;
      }
      if (!backendOnline) {
        setProjectAuthoringPack(null);
        setProjectAuthoringStatus("后端离线，批量预检与原子保存暂不可用。");
        return;
      }
      try {
        const pack = await getLibraryProjectAuthoringPack(backendBaseUrl, selectedProject.projectId);
        if (!cancelled) {
          setProjectAuthoringPack(pack);
          setProjectAuthoringStatus("");
        }
      } catch (error) {
        if (!cancelled) {
          setProjectAuthoringPack(null);
          setProjectAuthoringStatus(error instanceof Error ? error.message : "加载 authoring pack 失败。");
        }
      }
    }

    void loadProjectAuthoringPack();
    return () => {
      cancelled = true;
    };
  }, [backendBaseUrl, backendOnline, selectedProject?.projectId]);

  useEffect(() => {
    let cancelled = false;

    async function loadWorkspaceCompiledPreview() {
      if (!workspace || !backendOnline) {
        setWorkspaceCompiledPreview(null);
        return;
      }
      try {
        const preview = await getLibraryWorkspaceCompiledPreview(backendBaseUrl, workspace.workspaceId, workspacePreviewFilters);
        if (!cancelled) {
          setWorkspaceCompiledPreview(preview);
        }
      } catch {
        if (!cancelled) {
          setWorkspaceCompiledPreview(null);
        }
      }
    }

    void loadWorkspaceCompiledPreview();
    return () => {
      cancelled = true;
    };
  }, [
    backendBaseUrl,
    backendOnline,
    workspace?.workspaceId,
    workspace?.updatedAt,
    workspace?.compileSummary?.modules,
    workspacePreviewFilters.projectId,
    workspacePreviewFilters.artifactKind,
    workspacePreviewFilters.search,
  ]);

  useEffect(() => {
    setWorkspacePreviewFilters({
      projectId: "",
      artifactKind: "",
      search: "",
    });
  }, [workspace?.workspaceId]);

  useEffect(() => {
    let cancelled = false;

    async function loadBundleArtifacts() {
      if (!selectedBundle || !backendOnline) {
        setBundleDetail(null);
        setBundleComparison(null);
        setCompareBundleId("");
        return;
      }
      try {
        const detail = await getLibraryBundleDetail(backendBaseUrl, selectedBundle.bundleId);
        if (!cancelled) {
          setBundleDetail(detail);
          setBundleComparison(null);
          setCompareBundleId((current) => {
            if (current && current !== selectedBundle.bundleId) {
              return current;
            }
            const fallback = (workspace?.compiledBundles ?? []).find((item) => item.bundleId !== selectedBundle.bundleId);
            return fallback?.bundleId ?? "";
          });
        }
      } catch {
        if (!cancelled) {
          setBundleDetail(null);
          setBundleComparison(null);
          setCompareBundleId("");
        }
      }
    }

    void loadBundleArtifacts();
    return () => {
      cancelled = true;
    };
  }, [backendBaseUrl, backendOnline, selectedBundle?.bundleId, workspace?.compiledBundles]);

  useEffect(() => {
    let cancelled = false;

    async function loadBundleComparison() {
      if (!selectedBundle || !compareBundleId || !backendOnline) {
        setBundleComparison(null);
        return;
      }
      try {
        const comparison = await compareLibraryBundles(backendBaseUrl, selectedBundle.bundleId, compareBundleId);
        if (!cancelled) {
          setBundleComparison(comparison);
        }
      } catch {
        if (!cancelled) {
          setBundleComparison(null);
        }
      }
    }

    void loadBundleComparison();
    return () => {
      cancelled = true;
    };
  }, [backendBaseUrl, backendOnline, selectedBundle?.bundleId, compareBundleId]);

  function updateProfile(profile: LibraryProfileRecord) {
    setWorkspace((current) =>
      current
        ? {
            ...current,
            knowledge: {
              ...current.knowledge,
              profile,
            },
          }
        : current,
    );
  }

  function updateRoleDocument(document: LibraryRoleDocumentRecord) {
    setWorkspace((current) => {
      if (!current) {
        return current;
      }
      const nextRoleDocuments = current.knowledge.roleDocuments.some((item) => item.documentId === document.documentId)
        ? current.knowledge.roleDocuments.map((item) => (item.documentId === document.documentId ? document : item))
        : [...current.knowledge.roleDocuments, document];
      return {
        ...current,
        knowledge: {
          ...current.knowledge,
          roleDocuments: nextRoleDocuments,
        },
      };
    });
  }

  function deleteRoleDocument(documentId: string) {
    setWorkspace((current) =>
      current
        ? {
            ...current,
            knowledge: {
              ...current.knowledge,
              roleDocuments: current.knowledge.roleDocuments.filter((item) => item.documentId !== documentId),
            },
          }
        : current,
    );
  }

  function updateProject(project: LibraryProjectRecord) {
    setWorkspace((current) =>
      current
        ? {
            ...current,
            knowledge: {
              ...current.knowledge,
              projects: current.knowledge.projects.map((item) => (item.projectId === project.projectId ? project : item)),
            },
          }
        : current,
    );
  }

  function applyProjectAuthoringPack(projectId: string, pack: LibraryProjectAuthoringPackRecord) {
    setWorkspace((current) =>
      current
        ? {
            ...current,
            updatedAt: Date.now() / 1000,
            compileSummary: null,
            knowledge: {
              ...current.knowledge,
              projects: current.knowledge.projects.map((item) =>
                item.projectId === projectId
                  ? {
                      ...item,
                      manualEvidence: pack.manualEvidence,
                      manualMetrics: pack.manualMetrics,
                      manualRetrievalUnits: pack.manualRetrievalUnits,
                    }
                  : item,
              ),
            },
          }
        : current,
    );
    setProjectCompiledPreview(null);
    setWorkspaceCompiledPreview(null);
  }

  function replaceProjectDocument(projectId: string, document: LibraryDocumentRecord) {
    setWorkspace((current) =>
      current
        ? {
            ...current,
            knowledge: {
              ...current.knowledge,
              projects: current.knowledge.projects.map((item) =>
                item.projectId === projectId
                  ? {
                      ...item,
                      documents: item.documents.some((entry) => entry.documentId === document.documentId)
                        ? item.documents.map((entry) => (entry.documentId === document.documentId ? document : entry))
                        : [...item.documents, document],
                    }
                  : item,
              ),
            },
          }
        : current,
    );
  }

  function removeProjectDocument(projectId: string, documentId: string) {
    setWorkspace((current) =>
      current
        ? {
            ...current,
            knowledge: {
              ...current.knowledge,
              projects: current.knowledge.projects.map((item) =>
                item.projectId === projectId
                  ? {
                      ...item,
                      documents: item.documents.filter((entry) => entry.documentId !== documentId),
                    }
                  : item,
              ),
            },
          }
        : current,
    );
  }

  function updateOverlay(overlay: LibraryOverlayRecord) {
    setWorkspace((current) =>
      current
        ? {
            ...current,
            overlays: current.overlays.map((item) => (item.overlayId === overlay.overlayId ? overlay : item)),
          }
        : current,
    );
  }

  function updatePreset(preset: LibraryPresetRecord) {
    setWorkspace((current) =>
      current
        ? {
            ...current,
            presets: current.presets.map((item) => (item.presetId === preset.presetId ? preset : item)),
          }
        : current,
    );
  }

  async function handleSelectWorkspace(workspaceId: string) {
    if (!backendOnline) {
      const local = workspaceList.find((item) => item.workspaceId === workspaceId);
      if (local) {
        setWorkspace(local);
        setSelection(defaultSelection(local));
        setStatusMessage("后端离线，当前显示的是本地示例资料库。");
      }
      return;
    }
    try {
      const next = await refreshWorkspace(workspaceId);
      setSelection(defaultSelection(next));
      setStatusMessage(`已切换到 ${next.name}。`);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "切换资料库失败。");
    }
  }

  async function handleCreateWorkspace() {
    if (!backendOnline) {
      setStatusMessage("后端离线时不能创建持久化资料库。");
      return;
    }
    try {
      const created = await createLibraryWorkspace(backendBaseUrl, {
        name: `Persistent Library ${workspaceList.length + 1}`,
        knowledge: {
          profile: {
            headline: defaultProfile().headline,
            summary: "",
            strengths: [],
            target_roles: [],
            intro_material: [],
          },
          projects: [],
          role_documents: [],
        },
      });
      syncWorkspace(created);
      setSelection({ type: "workspace", id: created.workspaceId });
      setStatusMessage("已创建新的持久化资料库。");
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "创建资料库失败。");
    }
  }

  async function handleSaveWorkspace() {
    if (!backendOnline || !workspace) {
      setStatusMessage("当前没有可保存的持久化资料库。");
      return;
    }
    try {
      const saved = await updateLibraryWorkspace(backendBaseUrl, workspace.workspaceId, serializeWorkspacePayload(workspace));
      syncWorkspace(saved);
      setStatusMessage("资料库背景与长期资料已保存。");
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "保存资料库失败。");
    }
  }

  async function handleCreateRoleDocument() {
    if (!workspace) {
      setStatusMessage("请先创建资料库。");
      return;
    }
    if (!backendOnline) {
      updateRoleDocument({
        ...defaultRoleDocument(),
        documentId: `role-draft-${Date.now()}`,
        path: `role/${Date.now()}.md`,
        updatedAt: Date.now() / 1000,
      });
      setStatusMessage("后端离线，先在本地示例里新增 Role 文档。");
      return;
    }
    try {
      const created = await createLibraryRoleDocument(backendBaseUrl, workspace.workspaceId, {
        title: "New Role Note",
        path: `role/${Date.now()}.md`,
        content: "",
      });
      updateRoleDocument(created);
      setStatusMessage("已新建 Role 文档。");
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "新建 Role 文档失败。");
    }
  }

  async function handleSaveRoleDocument(document: LibraryRoleDocumentRecord) {
    if (!workspace) {
      setStatusMessage("请先创建资料库。");
      return;
    }
    if (!backendOnline) {
      setStatusMessage("后端离线，无法直接保存 Role 文档。");
      return;
    }
    try {
      const payload = {
        title: document.title,
        path: document.path,
        content: document.content,
        source_kind: document.sourceKind,
        source_path: document.sourcePath,
        repo_id: document.repoId,
      };
      const saved = document.documentId.startsWith("role-draft-")
        ? await createLibraryRoleDocument(backendBaseUrl, workspace.workspaceId, payload)
        : await updateLibraryDocument(backendBaseUrl, document.documentId, payload);
      updateRoleDocument(saved as LibraryRoleDocumentRecord);
      if (document.documentId.startsWith("role-draft-")) {
        deleteRoleDocument(document.documentId);
      }
      setStatusMessage(`Role 文档 ${document.title || document.path} 已保存。`);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "保存 Role 文档失败。");
    }
  }

  async function handleDeleteRoleDocument(document: LibraryRoleDocumentRecord) {
    if (!workspace) {
      return;
    }
    if (!backendOnline || document.documentId.startsWith("role-draft-")) {
      deleteRoleDocument(document.documentId);
      setStatusMessage("已删除 Role 文档。");
      return;
    }
    try {
      await deleteLibraryDocument(backendBaseUrl, document.documentId);
      deleteRoleDocument(document.documentId);
      setStatusMessage(`Role 文档 ${document.title || document.path} 已删除。`);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "删除 Role 文档失败。");
    }
  }

  async function handleCreateProjectDocument() {
    if (!selectedProject) {
      setStatusMessage("请先选择一个项目。");
      return;
    }
    if (!backendOnline) {
      updateProject({
        ...selectedProject,
        documents: [...selectedProject.documents, defaultProjectDocument(selectedProject)],
      });
      setStatusMessage("后端离线，先在本地示例里新增文档。");
      return;
    }
    try {
      const created = await createLibraryProjectDocument(backendBaseUrl, selectedProject.projectId, {
        title: "New Document",
        path: `notes/${selectedProject.documents.length + 1}.md`,
        content: "",
      });
      replaceProjectDocument(selectedProject.projectId, created);
      setStatusMessage("已新建项目文档。");
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "新建项目文档失败。");
    }
  }

  async function handleSaveProjectDocument(document: LibraryDocumentRecord) {
    if (!selectedProject) {
      setStatusMessage("请先选择一个项目。");
      return;
    }
    if (!backendOnline) {
      setStatusMessage("后端离线，无法直接保存文档。");
      return;
    }
    try {
      const payload = {
        title: document.title,
        path: document.path,
        content: document.content,
        source_kind: document.sourceKind,
        source_path: document.sourcePath,
        repo_id: document.repoId,
      };
      const saved = document.documentId.startsWith("draft-")
        ? await createLibraryProjectDocument(backendBaseUrl, selectedProject.projectId, payload)
        : await updateLibraryDocument(backendBaseUrl, document.documentId, payload);
      replaceProjectDocument(selectedProject.projectId, saved as LibraryDocumentRecord);
      if (document.documentId.startsWith("draft-")) {
        removeProjectDocument(selectedProject.projectId, document.documentId);
      }
      setStatusMessage(`文档 ${document.title || document.path} 已保存。`);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "保存文档失败。");
    }
  }

  async function handleDeleteProjectDocument(document: LibraryDocumentRecord) {
    if (!selectedProject) {
      return;
    }
    if (!backendOnline || document.documentId.startsWith("draft-")) {
      removeProjectDocument(selectedProject.projectId, document.documentId);
      setStatusMessage("已删除项目文档。");
      return;
    }
    try {
      await deleteLibraryDocument(backendBaseUrl, document.documentId);
      removeProjectDocument(selectedProject.projectId, document.documentId);
      setStatusMessage(`文档 ${document.title || document.path} 已删除。`);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "删除文档失败。");
    }
  }

  async function handleCreateProject() {
    if (!backendOnline || !workspace) {
      setStatusMessage("请先连接后端并创建资料库。");
      return;
    }
    try {
      const created = await createLibraryProject(backendBaseUrl, workspace.workspaceId, {
        name: `Project ${workspace.knowledge.projects.length + 1}`,
      });
      const next = {
        ...workspace,
        knowledge: {
          ...workspace.knowledge,
          projects: [...workspace.knowledge.projects, created],
        },
      };
      syncWorkspace(next);
      setSelection({ type: "project", id: created.projectId });
      setStatusMessage(`已创建项目 ${created.name}。`);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "创建项目失败。");
    }
  }

  async function handleSaveProject() {
    if (!backendOnline || !selectedProject) {
      setStatusMessage("请先选择一个项目。");
      return;
    }
    try {
      const saved = await updateLibraryProject(
        backendBaseUrl,
        selectedProject.projectId,
        serializeProjectPayload(selectedProject),
      );
      updateProject(saved);
      setStatusMessage(`项目 ${saved.name} 已保存。`);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "保存项目失败。");
    }
  }

  async function handlePreviewProjectAuthoringPack(payload: Record<string, unknown>) {
    if (!backendOnline || !selectedProject) {
      setProjectAuthoringStatus("请先连接后端并选择项目。");
      return;
    }
    try {
      const preview = await previewLibraryProjectAuthoringPack(
        backendBaseUrl,
        selectedProject.projectId,
        payload,
      );
      setProjectAuthoringPack(preview);
      setProjectAuthoringStatus(
        preview.validation.valid
          ? "批量草稿预检通过，可以直接应用。"
          : `预检发现 ${preview.validation.errors.length} 个错误，请先修正。`,
      );
    } catch (error) {
      setProjectAuthoringStatus(error instanceof Error ? error.message : "预检 authoring pack 失败。");
    }
  }

  async function handleApplyProjectAuthoringPack(payload: Record<string, unknown>) {
    if (!backendOnline || !selectedProject) {
      setProjectAuthoringStatus("请先连接后端并选择项目。");
      return;
    }
    try {
      const result = await updateLibraryProjectAuthoringPack(
        backendBaseUrl,
        selectedProject.projectId,
        payload,
      );
      setProjectAuthoringPack(result);
      applyProjectAuthoringPack(selectedProject.projectId, result);
      setProjectAuthoringStatus("批量素材已保存，当前项目的编译预览已标记为需要重新 compile。");
      setStatusMessage(`项目 ${selectedProject.name} 的批量 authoring pack 已应用。`);
    } catch (error) {
      setProjectAuthoringStatus(error instanceof Error ? error.message : "应用 authoring pack 失败。");
    }
  }

  async function handleDeleteProject() {
    if (!backendOnline || !workspace || !selectedProject) {
      setStatusMessage("请先选择一个项目。");
      return;
    }
    try {
      await deleteLibraryProject(backendBaseUrl, selectedProject.projectId);
      const remainingProjects = workspace.knowledge.projects.filter((item) => item.projectId !== selectedProject.projectId);
      const nextWorkspace = {
        ...workspace,
        knowledge: {
          ...workspace.knowledge,
          projects: remainingProjects,
        },
      };
      syncWorkspace(nextWorkspace);
      setSelection(
        remainingProjects[0]
          ? { type: "project", id: remainingProjects[0].projectId }
          : { type: "workspace", id: workspace.workspaceId },
      );
      setStatusMessage(`已删除项目 ${selectedProject.name}。`);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "删除项目失败。");
    }
  }

  async function handleImportRepo() {
    if (!backendOnline || !selectedProject) {
      setStatusMessage("请先选择项目并连接后端。");
      return;
    }
    if (!importPath.trim()) {
      setStatusMessage("请先填写要导入的本地 repo 路径。");
      return;
    }
    try {
      const imported = await importLibraryProjectPath(backendBaseUrl, selectedProject.projectId, {
        path: importPath.trim(),
        project_name: selectedProject.name,
      });
      syncWorkspace(imported.workspace);
      setStatusMessage(
        imported.importSummary
          ? `已导入 ${imported.importSummary.importedDocs} 份文档和 ${imported.importSummary.importedCodeFiles} 段代码。`
          : "已导入本地路径。",
      );
      setImportPath("");
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "导入 repo 失败。");
    }
  }

  async function handleReindexRepo(repoId: string) {
    if (!backendOnline) {
      setStatusMessage("后端离线时不能重新扫描 repo。");
      return;
    }
    try {
      const reindexed = await reindexLibraryRepo(backendBaseUrl, repoId);
      syncWorkspace(reindexed.workspace);
      setStatusMessage(
        reindexed.importSummary
          ? `已重新扫描 repo，刷新了 ${reindexed.importSummary.importedDocs} 份文档和 ${reindexed.importSummary.importedCodeFiles} 段代码。`
          : "已重新扫描当前 repo。",
      );
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "重新扫描 repo 失败。");
    }
  }

  async function handleCreateOverlay() {
    if (!backendOnline || !workspace) {
      setStatusMessage("请先连接后端并创建资料库。");
      return;
    }
    try {
      const created = await createLibraryOverlay(backendBaseUrl, workspace.workspaceId, {
        name: `Overlay ${workspace.overlays.length + 1}`,
        focus_project_ids: selectedProject ? [selectedProject.projectId] : [],
      });
      const next = {
        ...workspace,
        overlays: [...workspace.overlays, created],
      };
      syncWorkspace(next);
      setSelection({ type: "overlay", id: created.overlayId });
      setStatusMessage(`已创建 overlay ${created.name}。`);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "创建 overlay 失败。");
    }
  }

  async function handleSaveOverlay() {
    if (!backendOnline || !selectedOverlay) {
      setStatusMessage("请先选择一个 overlay。");
      return;
    }
    try {
      const saved = await updateLibraryOverlay(
        backendBaseUrl,
        selectedOverlay.overlayId,
        serializeOverlayPayload(selectedOverlay),
      );
      updateOverlay(saved);
      setStatusMessage(`Overlay ${saved.name} 已保存。`);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "保存 overlay 失败。");
    }
  }

  async function handleCreatePreset() {
    if (!backendOnline || !workspace) {
      setStatusMessage("请先连接后端并创建资料库。");
      return;
    }
    try {
      const created = await createLibraryPreset(backendBaseUrl, workspace.workspaceId, {
        name: `Preset ${workspace.presets.length + 1}`,
        project_ids: selectedProject ? [selectedProject.projectId] : workspace.knowledge.projects.slice(0, 1).map((item) => item.projectId),
        overlay_id: workspace.overlays[0]?.overlayId ?? "",
        include_role_documents: true,
      });
      const next = {
        ...workspace,
        presets: [...workspace.presets, created],
      };
      syncWorkspace(next);
      setSelection({ type: "preset", id: created.presetId });
      setStatusMessage(`已创建 preset ${created.name}。`);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "创建 preset 失败。");
    }
  }

  async function handleSavePreset() {
    if (!backendOnline || !selectedPreset) {
      setStatusMessage("请先选择一个 preset。");
      return;
    }
    try {
      const saved = await updateLibraryPreset(
        backendBaseUrl,
        selectedPreset.presetId,
        serializePresetPayload(selectedPreset),
      );
      updatePreset(saved);
      setStatusMessage(`Preset ${saved.name} 已保存。`);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "保存 preset 失败。");
    }
  }

  async function handleRefreshWorkspace() {
    if (!backendOnline || !workspace) {
      setStatusMessage("当前没有可刷新的资料库。");
      return;
    }
    try {
      const refreshed = await refreshWorkspace(workspace.workspaceId);
      setStatusMessage(`已刷新 ${refreshed.name}。`);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "刷新资料库失败。");
    }
  }

  async function handleCompileWorkspace() {
    if (!backendOnline || !workspace) {
      setStatusMessage("请先创建并保存资料库。");
      return;
    }
    try {
      const compiled = await compileLibraryWorkspace(backendBaseUrl, workspace.workspaceId);
      syncWorkspace(compiled);
      setStatusMessage("资料库已完成 compile，可以继续构建面试知识包。");
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "编译资料库失败。");
    }
  }

  async function buildPayloadForSelectedPreset(): Promise<LibrarySessionPayload | null> {
    if (!backendOnline || !selectedPreset || !workspace) {
      setStatusMessage("请先选择一个 preset。");
      return null;
    }
    try {
      const payload = await buildPresetSessionPayload(backendBaseUrl, selectedPreset.presetId);
      setLatestPayload(payload);
      try {
        await refreshWorkspace(workspace.workspaceId);
      } catch {
        setWorkspace((current) =>
          current
            ? {
                ...current,
                compiledBundles: [...current.compiledBundles, payload.activationSummary],
              }
            : current,
        );
      }
      setStatusMessage(
        `已构建 ${payload.activationSummary.projectCount} 个项目的会话知识包，包含 ${payload.activationSummary.retrievalUnitCount} 个回答单元。`,
      );
      return payload;
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "构建会话知识包失败。");
      return null;
    }
  }

  async function handleBuildPayload() {
    await buildPayloadForSelectedPreset();
  }

  async function handleActivate() {
    const payload = await buildPayloadForSelectedPreset();
    if (!payload) {
      return;
    }
    try {
      await onActivateSession(payload);
      setStatusMessage(`Preset ${payload.activationSummary.presetName} 已用于当前会话。`);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "将 preset 用于当前会话失败。");
    }
  }

  /*
  async function handleReuseBundle() {
    if (!backendOnline || !selectedBundle) {
      setStatusMessage("璇峰厛閫夋嫨涓€涓彲澶嶇敤鐨?bundle銆?);
      return;
    }
    try {
      const payload = await reuseLibraryBundleSessionPayload(backendBaseUrl, selectedBundle.bundleId);
      setLatestPayload(payload);
      await onActivateSession(payload);
      setStatusMessage(`Bundle ${selectedBundle.bundleId.slice(0, 8)} 宸茬敤浜庡綋鍓嶄細璇濄€俙);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "浣跨敤鍘嗗彶 bundle 澶辫触銆?);
    }
  }

  */

  async function handleReuseBundle() {
    if (!backendOnline || !selectedBundle) {
      setStatusMessage("请先选择一个可复用的 bundle。");
      return;
    }
    try {
      const payload = await reuseLibraryBundleSessionPayload(backendBaseUrl, selectedBundle.bundleId);
      setLatestPayload(payload);
      await onActivateSession(payload);
      setStatusMessage(`Bundle ${selectedBundle.bundleId.slice(0, 8)} 已用于当前会话。`);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "使用历史 bundle 失败。");
    }
  }

  const profile = workspace?.knowledge.profile ?? defaultProfile();

  return (
    <section className="panel panel-library-shell">
      <div className="library-panel">
        <WorkspaceNav
          workspaces={workspaceList}
          workspace={workspace}
          selection={selection}
          onSelectWorkspace={handleSelectWorkspace}
          onSelect={setSelection}
          onCreateWorkspace={handleCreateWorkspace}
          onCreateProject={handleCreateProject}
          onCreateOverlay={handleCreateOverlay}
          onCreatePreset={handleCreatePreset}
        />

        <div className="library-main">
          {workspace && selection?.type === "workspace" ? (
            <section className="library-editor">
              <div className="panel-head">
                <span>Workspace 编辑</span>
                <strong>{workspace.name}</strong>
              </div>

              <label>
                资料库名称
                <input value={workspace.name} onChange={(event) => setWorkspace({ ...workspace, name: event.target.value })} />
              </label>

              <label>
                背景标题
                <input value={profile.headline} onChange={(event) => updateProfile({ ...profile, headline: event.target.value })} />
              </label>

              <label>
                背景摘要
                <textarea
                  rows={4}
                  value={profile.summary}
                  onChange={(event) => updateProfile({ ...profile, summary: event.target.value })}
                />
              </label>

              <label>
                个人强项
                <textarea
                  rows={4}
                  value={joinLines(profile.strengths)}
                  onChange={(event) => updateProfile({ ...profile, strengths: splitLines(event.target.value) })}
                />
              </label>

              <label>
                目标岗位
                <textarea
                  rows={3}
                  value={joinLines(profile.targetRoles)}
                  onChange={(event) => updateProfile({ ...profile, targetRoles: splitLines(event.target.value) })}
                />
              </label>

              <label>
                自我介绍素材
                <textarea
                  rows={4}
                  value={joinLines(profile.introMaterial)}
                  onChange={(event) => updateProfile({ ...profile, introMaterial: splitLines(event.target.value) })}
                />
              </label>

              <div className="meta-card">
                <div className="panel-head compact">
                  <span>Role Documents</span>
                  <strong>{workspace.knowledge.roleDocuments.length}</strong>
                </div>
                <div className="action-row">
                  <button className="ghost small" onClick={handleCreateRoleDocument}>
                    新增 Role 文档
                  </button>
                </div>
                {workspace.knowledge.roleDocuments.length === 0 ? (
                  <p className="library-empty">还没有 role 文档，可以按公司或岗位拆多份维护。</p>
                ) : null}
                {workspace.knowledge.roleDocuments.map((document) => (
                  <div key={document.documentId} className="meta-card">
                    <div className="panel-head compact">
                      <span>{document.sourceKind}</span>
                      <strong>{document.title}</strong>
                    </div>
                    <label>
                      标题
                      <input
                        value={document.title}
                        onChange={(event) => updateRoleDocument({ ...document, title: event.target.value })}
                      />
                    </label>
                    <label>
                      路径
                      <input
                        value={document.path}
                        onChange={(event) => updateRoleDocument({ ...document, path: event.target.value })}
                      />
                    </label>
                    <label>
                      内容
                      <textarea
                        rows={6}
                        value={document.content}
                        onChange={(event) => updateRoleDocument({ ...document, content: event.target.value })}
                      />
                    </label>
                    <div className="action-row">
                      <button className="ghost accent small" onClick={() => handleSaveRoleDocument(document)}>
                        Save Role Doc
                      </button>
                      <button className="ghost small" onClick={() => handleDeleteRoleDocument(document)}>
                        删除 Role 文档
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              <div className="meta-card">
                <div className="panel-head compact">
                  <span>Workspace Preview</span>
                  <strong>{workspaceCompiledPreview?.compiled ? "Ready" : "Not Compiled"}</strong>
                </div>
                {workspaceCompiledPreview?.compiled ? (
                  <>
                    <div className="action-row">
                      <label>
                        Project
                        <select
                          value={workspacePreviewFilters.projectId}
                          onChange={(event) =>
                            setWorkspacePreviewFilters((current) => ({ ...current, projectId: event.target.value }))
                          }
                        >
                          <option value="">All</option>
                          {workspace.knowledge.projects.map((project) => (
                            <option key={project.projectId} value={project.projectId}>
                              {project.name}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Artifact
                        <select
                          value={workspacePreviewFilters.artifactKind}
                          onChange={(event) =>
                            setWorkspacePreviewFilters((current) => ({ ...current, artifactKind: event.target.value }))
                          }
                        >
                          <option value="">All</option>
                          <option value="module">Module</option>
                          <option value="evidence">Evidence</option>
                          <option value="metric">Metric</option>
                          <option value="retrieval">Retrieval</option>
                        </select>
                      </label>
                    </div>
                    <label>
                      Search
                      <input
                        value={workspacePreviewFilters.search}
                        onChange={(event) =>
                          setWorkspacePreviewFilters((current) => ({ ...current, search: event.target.value }))
                        }
                        placeholder="latency / retrieval / router"
                      />
                    </label>
                    <div className="session-chip">
                      <span>{workspaceCompiledPreview.moduleCards.length} modules</span>
                      <span>{workspaceCompiledPreview.evidenceCards.length} evidence</span>
                      <span>{workspaceCompiledPreview.metricEvidence.length} metrics</span>
                      <span>{workspaceCompiledPreview.retrievalUnits.length} RU</span>
                    </div>
                    {workspaceCompiledPreview.projectSummaries.length > 0 ? (
                      <div className="tokens">
                        {workspaceCompiledPreview.projectSummaries.map((summary) => (
                          <span key={summary.projectId} className="token token-outline">
                            {summary.projectName}: {summary.moduleCount}/{summary.evidenceCount}/{summary.metricCount}/
                            {summary.retrievalUnitCount}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="library-empty">Current filters removed all project summaries.</p>
                    )}
                    {workspaceCompiledPreview.moduleCards.slice(0, 6).map((item) => (
                      <div key={item.moduleId} className="meta-card">
                        <div className="panel-head compact">
                          <span>Module</span>
                          <strong>{item.name}</strong>
                        </div>
                        <p>{item.responsibility}</p>
                      </div>
                    ))}
                    {workspaceCompiledPreview.evidenceCards.slice(0, 6).map((item) => (
                      <div key={item.evidenceId} className="meta-card">
                        <div className="panel-head compact">
                          <span>{item.evidenceType}</span>
                          <strong>{item.title}</strong>
                        </div>
                        <p>{item.summary}</p>
                      </div>
                    ))}
                    {workspaceCompiledPreview.metricEvidence.slice(0, 6).map((item) => (
                      <div key={item.evidenceId} className="meta-card">
                        <div className="panel-head compact">
                          <span>{item.metricName}</span>
                          <strong>{item.metricValue || "--"}</strong>
                        </div>
                        <p>{item.baseline || "--"} / {item.method || "--"}</p>
                      </div>
                    ))}
                    {workspaceCompiledPreview.retrievalUnits.slice(0, 8).map((item) => (
                      <div key={item.unitId} className="meta-card">
                        <div className="panel-head compact">
                          <span>{item.unitType}</span>
                          <strong>{item.shortAnswer || item.unitId}</strong>
                        </div>
                        <p>{item.longAnswer}</p>
                      </div>
                    ))}
                  </>
                ) : (
                  <p className="library-empty">Run compile first, then use filters here to inspect workspace artifacts.</p>
                )}
              </div>

              <div className="action-row">
                <button className="ghost accent small" onClick={handleSaveWorkspace}>
                  保存资料库
                </button>
              </div>
            </section>
          ) : null}

          {selection?.type === "project" ? (
            <ProjectEditor
              project={selectedProject}
              authoringPack={projectAuthoringPack}
              authoringStatus={projectAuthoringStatus}
              compiledPreview={projectCompiledPreview}
              onChange={updateProject}
              onPreviewAuthoringPack={handlePreviewProjectAuthoringPack}
              onApplyAuthoringPack={handleApplyProjectAuthoringPack}
              onCreateDocument={handleCreateProjectDocument}
              onSaveDocument={handleSaveProjectDocument}
              onDeleteDocument={handleDeleteProjectDocument}
              onSave={handleSaveProject}
              onDelete={handleDeleteProject}
            />
          ) : null}

          {selection?.type === "overlay" ? (
            <OverlayEditor
              overlay={selectedOverlay}
              projects={workspace?.knowledge.projects ?? []}
              onChange={updateOverlay}
              onSave={handleSaveOverlay}
            />
          ) : null}

          {selection?.type === "preset" ? (
            <PresetEditor
              preset={selectedPreset}
              projects={workspace?.knowledge.projects ?? []}
              overlays={workspace?.overlays ?? []}
              latestBundle={presetLatestBundle}
              onChange={updatePreset}
              onSave={handleSavePreset}
              onBuildPayload={handleBuildPayload}
              onActivate={handleActivate}
            />
          ) : null}

          {selection?.type === "bundle" ? (
            <section className="library-editor">
              <div className="panel-head">
                <span>Bundle Summary</span>
                <strong>{selectedBundle?.presetName || "Bundle"}</strong>
              </div>
              {selectedBundle ? (
                <>
                  <div className="route-banner">
                    <span>Project Coverage</span>
                    <p>{selectedBundle.projectNames.join(" / ") || "未选择项目"}</p>
                  </div>
                  <div className="session-chip">
                    <span>{selectedBundle.projectCount} 项目</span>
                    <span>{selectedBundle.retrievalUnitCount} RU</span>
                    <span>{selectedBundle.metricEvidenceCount} metric</span>
                    <span>{selectedBundle.terminologyCount} terms</span>
                  </div>
                  <div className="action-row">
                    <button className="ghost accent small" onClick={handleReuseBundle}>
                      用这个 Bundle 激活会话
                    </button>
                  </div>
                  {bundleDetail ? (
                    <div className="meta-card">
                      <div className="panel-head compact">
                        <span>Saved Briefing</span>
                        <strong>{bundleDetail.briefing.company || "No company"}</strong>
                      </div>
                      <p>{bundleDetail.briefing.businessContext || "No business context"}</p>
                      <div className="tokens">
                        {bundleDetail.briefing.focusTopics.map((topic) => (
                          <span key={topic} className="token token-outline">
                            {topic}
                          </span>
                        ))}
                      </div>
                      <div className="session-chip">
                        {bundleDetail.briefing.priorityProjects.map((projectName) => (
                          <span key={projectName}>{projectName}</span>
                        ))}
                      </div>
                    </div>
                  ) : null}
                  {workspace && workspace.compiledBundles.length > 1 ? (
                    <div className="meta-card">
                      <div className="panel-head compact">
                        <span>Compare Bundle</span>
                        <strong>{bundleComparison ? "Ready" : "Idle"}</strong>
                      </div>
                      <label>
                        对比对象
                        <select value={compareBundleId} onChange={(event) => setCompareBundleId(event.target.value)}>
                          <option value="">不对比</option>
                          {workspace.compiledBundles
                            .filter((item) => item.bundleId !== selectedBundle.bundleId)
                            .map((item) => (
                              <option key={item.bundleId} value={item.bundleId}>
                                {(item.presetName || item.bundleId.slice(0, 8)) + " / " + new Date(item.builtAt * 1000).toLocaleString()}
                              </option>
                            ))}
                        </select>
                      </label>
                      {bundleComparison ? (
                        <>
                          <div className="session-chip">
                            <span>project delta {bundleComparison.projectCountDelta}</span>
                            <span>RU delta {bundleComparison.retrievalUnitDelta}</span>
                            <span>metric delta {bundleComparison.metricEvidenceDelta}</span>
                            <span>term delta {bundleComparison.terminologyDelta}</span>
                          </div>
                          <p>Added projects: {bundleComparison.addedProjects.join(" / ") || "--"}</p>
                          <p>Removed projects: {bundleComparison.removedProjects.join(" / ") || "--"}</p>
                          <p>Added focus topics: {bundleComparison.addedFocusTopics.join(" / ") || "--"}</p>
                          <p>Removed focus topics: {bundleComparison.removedFocusTopics.join(" / ") || "--"}</p>
                          <p>Added retrieval units: {bundleComparison.addedRetrievalUnits.join(" / ") || "--"}</p>
                          <p>Removed retrieval units: {bundleComparison.removedRetrievalUnits.join(" / ") || "--"}</p>
                          <p>Added evidence: {bundleComparison.addedEvidenceTitles.join(" / ") || "--"}</p>
                          <p>Removed evidence: {bundleComparison.removedEvidenceTitles.join(" / ") || "--"}</p>
                          <p>Added hooks: {bundleComparison.addedHookTexts.join(" / ") || "--"}</p>
                          <p>Removed hooks: {bundleComparison.removedHookTexts.join(" / ") || "--"}</p>
                        </>
                      ) : (
                        <p className="library-empty">选择另一个 bundle 后，这里会显示项目覆盖和回答素材规模的差异。</p>
                      )}
                    </div>
                  ) : null}
                </>
              ) : (
                <p className="library-empty">这个 bundle 不存在或还没有生成。</p>
              )}
            </section>
          ) : null}

          {!workspace ? (
            <section className="library-editor">
              <div className="panel-head">
                <span>Persistent Library</span>
                <strong>Empty</strong>
              </div>
              <p className="library-empty">创建一个资料库后，就可以开始维护项目、overlay、preset 和 bundle。</p>
            </section>
          ) : null}
        </div>

        <StatusRail
          workspace={workspace}
          project={selectedProject}
          selectedBundle={selectedBundle}
          latestPayload={latestPayload}
          importPath={importPath}
          statusMessage={statusMessage}
          onImportPathChange={setImportPath}
          onRefreshWorkspace={handleRefreshWorkspace}
          onCompileWorkspace={handleCompileWorkspace}
          onImportRepo={handleImportRepo}
          onReindexRepo={handleReindexRepo}
        />
      </div>
    </section>
  );
}
