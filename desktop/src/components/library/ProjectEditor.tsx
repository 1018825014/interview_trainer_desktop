import { type ChangeEvent, useEffect, useRef, useState } from "react";

import type {
  LibraryCodeFileRecord,
  LibraryProjectAuthoringPackRecord,
  LibraryProjectCompiledPreviewRecord,
  LibraryDocumentRecord,
  LibraryManualEvidenceRecord,
  LibraryManualMetricRecord,
  LibraryManualRetrievalUnitRecord,
  LibraryProjectRecord,
} from "../../types/library";

interface ProjectEditorProps {
  project: LibraryProjectRecord | null;
  authoringPack: LibraryProjectAuthoringPackRecord | null;
  authoringStatus: string;
  compiledPreview: LibraryProjectCompiledPreviewRecord | null;
  onChange: (project: LibraryProjectRecord) => void;
  onBuildAuthoringTemplate: (payload: Record<string, unknown>) => Promise<LibraryProjectAuthoringPackRecord | null>;
  onPreviewAuthoringPack: (payload: Record<string, unknown>) => Promise<void>;
  onApplyAuthoringPack: (payload: Record<string, unknown>) => Promise<void>;
  onCreateDocument: () => void;
  onSaveDocument: (document: LibraryDocumentRecord) => void;
  onDeleteDocument: (document: LibraryDocumentRecord) => void;
  onSave: () => void;
  onDelete: () => void;
}

function joinLines(value: string[]): string {
  return value.join("\n");
}

function splitLines(value: string): string[] {
  return value
    .replace(/\r/g, "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function emptyAuthoringDraft(): string {
  return JSON.stringify(
    {
      manual_evidence: [],
      manual_metrics: [],
      manual_retrieval_units: [],
    },
    null,
    2,
  );
}

function buildAuthoringDraftPayload(args: {
  manualEvidence: LibraryManualEvidenceRecord[];
  manualMetrics: LibraryManualMetricRecord[];
  manualRetrievalUnits: LibraryManualRetrievalUnitRecord[];
}): string {
  return JSON.stringify(
    {
      manual_evidence: args.manualEvidence.map((item) => ({
        evidence_id: item.evidenceId,
        module_id: item.moduleId,
        evidence_type: item.evidenceType,
        title: item.title,
        summary: item.summary,
        source_kind: item.sourceKind,
        source_ref: item.sourceRef,
        confidence: item.confidence,
      })),
      manual_metrics: args.manualMetrics.map((item) => ({
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
      manual_retrieval_units: args.manualRetrievalUnits.map((item) => ({
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
    },
    null,
    2,
  );
}

function buildAuthoringDraft(project: LibraryProjectRecord | null): string {
  if (!project) {
    return emptyAuthoringDraft();
  }
  return buildAuthoringDraftPayload({
    manualEvidence: project.manualEvidence,
    manualMetrics: project.manualMetrics,
    manualRetrievalUnits: project.manualRetrievalUnits,
  });
}

function buildAuthoringDraftFromPack(pack: LibraryProjectAuthoringPackRecord | null): string {
  if (!pack) {
    return emptyAuthoringDraft();
  }
  return buildAuthoringDraftPayload({
    manualEvidence: pack.manualEvidence,
    manualMetrics: pack.manualMetrics,
    manualRetrievalUnits: pack.manualRetrievalUnits,
  });
}

function parseAuthoringDraft(draft: string): { payload: Record<string, unknown> | null; error: string } {
  try {
    const parsed = JSON.parse(draft);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return {
        payload: null,
        error: "Authoring pack must be a JSON object with manual_evidence / manual_metrics / manual_retrieval_units.",
      };
    }
    return { payload: parsed as Record<string, unknown>, error: "" };
  } catch (error) {
    return {
      payload: null,
      error: error instanceof Error ? error.message : "Invalid JSON draft.",
    };
  }
}

function updateDocument(project: LibraryProjectRecord, documentId: string, patch: Partial<LibraryDocumentRecord>): LibraryProjectRecord {
  return {
    ...project,
    documents: project.documents.map((document) =>
      document.documentId === documentId ? { ...document, ...patch } : document,
    ),
  };
}

function updateCodeFile(project: LibraryProjectRecord, index: number, patch: Partial<LibraryCodeFileRecord>): LibraryProjectRecord {
  return {
    ...project,
    codeFiles: project.codeFiles.map((file, fileIndex) => (fileIndex === index ? { ...file, ...patch } : file)),
  };
}

function addManualEvidence(project: LibraryProjectRecord): LibraryProjectRecord {
  const nextItem: LibraryManualEvidenceRecord = {
    evidenceId: `manual-evidence-${Date.now()}`,
    moduleId: "",
    evidenceType: "manual_note",
    title: "New Evidence",
    summary: "",
    sourceKind: "manual_note",
    sourceRef: "",
    confidence: "medium",
  };
  return { ...project, manualEvidence: [...project.manualEvidence, nextItem] };
}

function updateManualEvidence(
  project: LibraryProjectRecord,
  evidenceId: string,
  patch: Partial<LibraryManualEvidenceRecord>,
): LibraryProjectRecord {
  return {
    ...project,
    manualEvidence: project.manualEvidence.map((item) => (item.evidenceId === evidenceId ? { ...item, ...patch } : item)),
  };
}

function deleteManualEvidence(project: LibraryProjectRecord, evidenceId: string): LibraryProjectRecord {
  return {
    ...project,
    manualEvidence: project.manualEvidence.filter((item) => item.evidenceId !== evidenceId),
  };
}

function addManualMetric(project: LibraryProjectRecord): LibraryProjectRecord {
  const nextItem: LibraryManualMetricRecord = {
    evidenceId: `manual-metric-${Date.now()}`,
    moduleId: "",
    metricName: "metric_name",
    metricValue: "",
    baseline: "",
    method: "manual note",
    environment: "workspace",
    sourceNote: "",
    confidence: "medium",
  };
  return { ...project, manualMetrics: [...project.manualMetrics, nextItem] };
}

function updateManualMetric(
  project: LibraryProjectRecord,
  evidenceId: string,
  patch: Partial<LibraryManualMetricRecord>,
): LibraryProjectRecord {
  return {
    ...project,
    manualMetrics: project.manualMetrics.map((item) => (item.evidenceId === evidenceId ? { ...item, ...patch } : item)),
  };
}

function deleteManualMetric(project: LibraryProjectRecord, evidenceId: string): LibraryProjectRecord {
  return {
    ...project,
    manualMetrics: project.manualMetrics.filter((item) => item.evidenceId !== evidenceId),
  };
}

function addManualRetrievalUnit(project: LibraryProjectRecord): LibraryProjectRecord {
  const nextItem: LibraryManualRetrievalUnitRecord = {
    unitId: `manual-ru-${Date.now()}`,
    unitType: "project_intro",
    moduleId: "",
    questionForms: [],
    shortAnswer: "",
    longAnswer: "",
    keyPoints: [],
    supportingRefs: [],
    hooks: [],
    safeClaims: [],
  };
  return {
    ...project,
    manualRetrievalUnits: [...project.manualRetrievalUnits, nextItem],
  };
}

function updateManualRetrievalUnit(
  project: LibraryProjectRecord,
  unitId: string,
  patch: Partial<LibraryManualRetrievalUnitRecord>,
): LibraryProjectRecord {
  return {
    ...project,
    manualRetrievalUnits: project.manualRetrievalUnits.map((item) => (item.unitId === unitId ? { ...item, ...patch } : item)),
  };
}

function deleteManualRetrievalUnit(project: LibraryProjectRecord, unitId: string): LibraryProjectRecord {
  return {
    ...project,
    manualRetrievalUnits: project.manualRetrievalUnits.filter((item) => item.unitId !== unitId),
  };
}

export function ProjectEditor({
  project,
  authoringPack,
  authoringStatus,
  compiledPreview,
  onChange,
  onBuildAuthoringTemplate,
  onPreviewAuthoringPack,
  onApplyAuthoringPack,
  onCreateDocument,
  onSaveDocument,
  onDeleteDocument,
  onSave,
  onDelete,
}: ProjectEditorProps) {
  const [authoringDraft, setAuthoringDraft] = useState(() => buildAuthoringDraft(project));
  const [authoringDraftError, setAuthoringDraftError] = useState("");
  const importInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    setAuthoringDraft(buildAuthoringDraft(project));
    setAuthoringDraftError("");
  }, [project?.projectId]);

  function handlePreviewDraft() {
    const parsed = parseAuthoringDraft(authoringDraft);
    if (!parsed.payload) {
      setAuthoringDraftError(parsed.error);
      return;
    }
    setAuthoringDraftError("");
    void onPreviewAuthoringPack(parsed.payload);
  }

  function handleApplyDraft() {
    const parsed = parseAuthoringDraft(authoringDraft);
    if (!parsed.payload) {
      setAuthoringDraftError(parsed.error);
      return;
    }
    setAuthoringDraftError("");
    void onApplyAuthoringPack(parsed.payload);
  }

  async function handleBuildTemplate(mode: "replace" | "append", payload: Record<string, unknown> = {}) {
    const pack = await onBuildAuthoringTemplate({
      source: "compiled_preview",
      mode,
      ...payload,
    });
    if (pack) {
      setAuthoringDraft(buildAuthoringDraftFromPack(pack));
      setAuthoringDraftError("");
    }
  }

  function handleExportDraft() {
    const blob = new Blob([authoringDraft], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${project.projectId || "project"}-authoring-pack.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function handleImportDraftClick() {
    importInputRef.current?.click();
  }

  async function handleImportDraftFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    try {
      const content = await file.text();
      setAuthoringDraft(content);
      setAuthoringDraftError("");
    } catch (error) {
      setAuthoringDraftError(error instanceof Error ? error.message : "Failed to import JSON file.");
    } finally {
      event.target.value = "";
    }
  }

  if (!project) {
    return (
      <section className="library-editor">
        <div className="panel-head">
          <span>Project Editor</span>
          <strong>None</strong>
        </div>
        <p className="library-empty">从左侧选择一个项目，或者先创建一个项目。</p>
      </section>
    );
  }

  return (
    <section className="library-editor">
      <div className="panel-head">
        <span>Project Editor</span>
        <strong>{project.name}</strong>
      </div>

      <label>
        项目名称
        <input value={project.name} onChange={(event) => onChange({ ...project, name: event.target.value })} />
      </label>

      <label>
        30 秒讲法
        <textarea rows={3} value={project.pitch30} onChange={(event) => onChange({ ...project, pitch30: event.target.value })} />
      </label>

      <label>
        90 秒讲法
        <textarea rows={4} value={project.pitch90} onChange={(event) => onChange({ ...project, pitch90: event.target.value })} />
      </label>

      <label>
        业务价值
        <textarea rows={4} value={project.businessValue} onChange={(event) => onChange({ ...project, businessValue: event.target.value })} />
      </label>

      <label>
        架构概述
        <textarea rows={4} value={project.architecture} onChange={(event) => onChange({ ...project, architecture: event.target.value })} />
      </label>

      <label>
        关键指标
        <textarea rows={4} value={joinLines(project.keyMetrics)} onChange={(event) => onChange({ ...project, keyMetrics: splitLines(event.target.value) })} />
      </label>

      <label>
        Tradeoff
        <textarea rows={4} value={joinLines(project.tradeoffs)} onChange={(event) => onChange({ ...project, tradeoffs: splitLines(event.target.value) })} />
      </label>

      <label>
        Failure Cases
        <textarea rows={4} value={joinLines(project.failureCases)} onChange={(event) => onChange({ ...project, failureCases: splitLines(event.target.value) })} />
      </label>

      <label>
        Limitations
        <textarea rows={4} value={joinLines(project.limitations)} onChange={(event) => onChange({ ...project, limitations: splitLines(event.target.value) })} />
      </label>

      <label>
        Upgrade Plan
        <textarea rows={4} value={joinLines(project.upgradePlan)} onChange={(event) => onChange({ ...project, upgradePlan: splitLines(event.target.value) })} />
      </label>

      <label>
        Interviewer Hooks
        <textarea rows={4} value={joinLines(project.interviewerHooks)} onChange={(event) => onChange({ ...project, interviewerHooks: splitLines(event.target.value) })} />
      </label>

      <div className="meta-card">
        <div className="panel-head compact">
          <span>Manual Evidence</span>
          <strong>{project.manualEvidence.length}</strong>
        </div>
        <div className="action-row">
          <button className="ghost small" onClick={() => onChange(addManualEvidence(project))}>
            新增证据
          </button>
        </div>
        {project.manualEvidence.length === 0 ? <p className="library-empty">先把能证明你说法的 benchmark、日志、设计结论写进来。</p> : null}
        {project.manualEvidence.map((item) => (
          <div key={item.evidenceId} className="meta-card">
            <div className="panel-head compact">
              <span>{item.evidenceType}</span>
              <strong>{item.title || item.evidenceId}</strong>
            </div>
            <label>
              标题
              <input value={item.title} onChange={(event) => onChange(updateManualEvidence(project, item.evidenceId, { title: event.target.value }))} />
            </label>
            <label>
              类型
              <input
                value={item.evidenceType}
                onChange={(event) => onChange(updateManualEvidence(project, item.evidenceId, { evidenceType: event.target.value }))}
              />
            </label>
            <label>
              摘要
              <textarea
                rows={4}
                value={item.summary}
                onChange={(event) => onChange(updateManualEvidence(project, item.evidenceId, { summary: event.target.value }))}
              />
            </label>
            <label>
              Source Ref
              <input
                value={item.sourceRef}
                onChange={(event) => onChange(updateManualEvidence(project, item.evidenceId, { sourceRef: event.target.value }))}
              />
            </label>
            <div className="session-chip">
              <span>{item.sourceKind}</span>
              <span>{item.confidence}</span>
            </div>
            <div className="action-row">
              <button className="ghost small" onClick={() => onChange(deleteManualEvidence(project, item.evidenceId))}>
                删除证据
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="meta-card">
        <div className="panel-head compact">
          <span>Manual Metrics</span>
          <strong>{project.manualMetrics.length}</strong>
        </div>
        <div className="action-row">
          <button className="ghost small" onClick={() => onChange(addManualMetric(project))}>
            新增指标
          </button>
        </div>
        {project.manualMetrics.length === 0 ? <p className="library-empty">把最想在面试里拿出来的量化结果和测量口径写进来。</p> : null}
        {project.manualMetrics.map((item) => (
          <div key={item.evidenceId} className="meta-card">
            <div className="panel-head compact">
              <span>{item.metricName}</span>
              <strong>{item.metricValue || "No value"}</strong>
            </div>
            <label>
              Metric Name
              <input
                value={item.metricName}
                onChange={(event) => onChange(updateManualMetric(project, item.evidenceId, { metricName: event.target.value }))}
              />
            </label>
            <label>
              Metric Value
              <input
                value={item.metricValue}
                onChange={(event) => onChange(updateManualMetric(project, item.evidenceId, { metricValue: event.target.value }))}
              />
            </label>
            <label>
              Baseline
              <input
                value={item.baseline}
                onChange={(event) => onChange(updateManualMetric(project, item.evidenceId, { baseline: event.target.value }))}
              />
            </label>
            <label>
              Method
              <input value={item.method} onChange={(event) => onChange(updateManualMetric(project, item.evidenceId, { method: event.target.value }))} />
            </label>
            <label>
              Environment
              <input
                value={item.environment}
                onChange={(event) => onChange(updateManualMetric(project, item.evidenceId, { environment: event.target.value }))}
              />
            </label>
            <label>
              Source Note
              <input
                value={item.sourceNote}
                onChange={(event) => onChange(updateManualMetric(project, item.evidenceId, { sourceNote: event.target.value }))}
              />
            </label>
            <div className="session-chip">
              <span>{item.confidence}</span>
            </div>
            <div className="action-row">
              <button className="ghost small" onClick={() => onChange(deleteManualMetric(project, item.evidenceId))}>
                删除指标
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="meta-card">
        <div className="panel-head compact">
          <span>Manual Retrieval Units</span>
          <strong>{project.manualRetrievalUnits.length}</strong>
        </div>
        <div className="action-row">
          <button className="ghost small" onClick={() => onChange(addManualRetrievalUnit(project))}>
            新增回答单元
          </button>
        </div>
        {project.manualRetrievalUnits.length === 0 ? (
          <p className="library-empty">把你最希望系统优先命中的项目讲法、tradeoff 讲法和深挖讲法提前写好。</p>
        ) : null}
        {project.manualRetrievalUnits.map((item) => (
          <div key={item.unitId} className="meta-card">
            <div className="panel-head compact">
              <span>{item.unitType}</span>
              <strong>{item.shortAnswer || item.unitId}</strong>
            </div>
            <label>
              Unit Type
              <input
                value={item.unitType}
                onChange={(event) => onChange(updateManualRetrievalUnit(project, item.unitId, { unitType: event.target.value }))}
              />
            </label>
            <label>
              Question Forms
              <textarea
                rows={3}
                value={joinLines(item.questionForms)}
                onChange={(event) =>
                  onChange(updateManualRetrievalUnit(project, item.unitId, { questionForms: splitLines(event.target.value) }))
                }
              />
            </label>
            <label>
              Short Answer
              <textarea
                rows={3}
                value={item.shortAnswer}
                onChange={(event) => onChange(updateManualRetrievalUnit(project, item.unitId, { shortAnswer: event.target.value }))}
              />
            </label>
            <label>
              Long Answer
              <textarea
                rows={5}
                value={item.longAnswer}
                onChange={(event) => onChange(updateManualRetrievalUnit(project, item.unitId, { longAnswer: event.target.value }))}
              />
            </label>
            <label>
              Key Points
              <textarea
                rows={3}
                value={joinLines(item.keyPoints)}
                onChange={(event) =>
                  onChange(updateManualRetrievalUnit(project, item.unitId, { keyPoints: splitLines(event.target.value) }))
                }
              />
            </label>
            <label>
              Supporting Refs
              <textarea
                rows={2}
                value={joinLines(item.supportingRefs)}
                onChange={(event) =>
                  onChange(updateManualRetrievalUnit(project, item.unitId, { supportingRefs: splitLines(event.target.value) }))
                }
              />
            </label>
            <label>
              Hooks
              <textarea
                rows={2}
                value={joinLines(item.hooks)}
                onChange={(event) => onChange(updateManualRetrievalUnit(project, item.unitId, { hooks: splitLines(event.target.value) }))}
              />
            </label>
            <label>
              Safe Claims
              <textarea
                rows={2}
                value={joinLines(item.safeClaims)}
                onChange={(event) =>
                  onChange(updateManualRetrievalUnit(project, item.unitId, { safeClaims: splitLines(event.target.value) }))
                }
              />
            </label>
            <div className="action-row">
              <button className="ghost small" onClick={() => onChange(deleteManualRetrievalUnit(project, item.unitId))}>
                删除回答单元
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="meta-card">
        <div className="panel-head compact">
          <span>Batch Authoring Pack</span>
          <strong>{authoringPack?.validation.valid ? "Validated" : "Draft"}</strong>
        </div>
        <p className="library-empty">
          Replace manual evidence, metrics, and retrieval units in one JSON payload. Use preview before apply so duplicate ids
          and missing supporting refs are caught early.
        </p>
        <div className="action-row">
          <button
            className="ghost small"
            onClick={() => {
              setAuthoringDraft(buildAuthoringDraft(project));
              setAuthoringDraftError("");
            }}
          >
            Load Current Draft
          </button>
          <button className="ghost small" onClick={() => void handleBuildTemplate("replace")}>
            Draft From Compiled
          </button>
          <button className="ghost small" onClick={() => void handleBuildTemplate("append")}>
            Append From Compiled
          </button>
          <button className="ghost small" onClick={handleExportDraft}>
            Export JSON
          </button>
          <button className="ghost small" onClick={handleImportDraftClick}>
            Import JSON
          </button>
          <button className="ghost small" onClick={handlePreviewDraft}>
            Preview Draft
          </button>
          <button className="ghost accent small" onClick={handleApplyDraft}>
            Apply Pack
          </button>
        </div>
        <input ref={importInputRef} type="file" accept="application/json,.json" hidden onChange={handleImportDraftFile} />
        <label>
          Authoring JSON
          <textarea
            className="authoring-pack-textarea"
            rows={18}
            value={authoringDraft}
            onChange={(event) => setAuthoringDraft(event.target.value)}
          />
        </label>
        {authoringDraftError ? <p className="library-error">{authoringDraftError}</p> : null}
        {authoringStatus ? <p className="authoring-status">{authoringStatus}</p> : null}
        {authoringPack ? (
          <>
            <div className="session-chip">
              <span>{authoringPack.summary.manualEvidenceCount} evidence</span>
              <span>{authoringPack.summary.manualMetricCount} metrics</span>
              <span>{authoringPack.summary.manualRetrievalUnitCount} RU</span>
              <span>{authoringPack.summary.usedSupportingRefCount}/{authoringPack.summary.availableSupportingRefCount} refs used</span>
            </div>
            {authoringPack.availableSupportingRefs.length > 0 ? (
              <div className="tokens">
                {authoringPack.availableSupportingRefs.map((item) => (
                  <span key={item.refId} className="token token-outline">
                    {item.refId} ({item.refKind})
                  </span>
                ))}
              </div>
            ) : null}
            {authoringPack.validation.errors.length > 0 ? (
              <div className="authoring-validation">
                <div className="panel-head compact">
                  <span>Errors</span>
                  <strong>{authoringPack.validation.errors.length}</strong>
                </div>
                {authoringPack.validation.errors.map((item) => (
                  <p key={item} className="library-error">
                    {item}
                  </p>
                ))}
              </div>
            ) : null}
            {authoringPack.validation.warnings.length > 0 ? (
              <div className="authoring-validation">
                <div className="panel-head compact">
                  <span>Warnings</span>
                  <strong>{authoringPack.validation.warnings.length}</strong>
                </div>
                {authoringPack.validation.warnings.map((item) => (
                  <p key={item} className="authoring-status">
                    {item}
                  </p>
                ))}
              </div>
            ) : null}
          </>
        ) : null}
      </div>

      <div className="meta-card">
        <div className="panel-head compact">
          <span>Compiled Preview</span>
          <strong>{compiledPreview?.compiled ? "Ready" : "Not Compiled"}</strong>
        </div>
        {compiledPreview?.compiled ? (
          <>
            <div className="session-chip">
              <span>{compiledPreview.moduleCards.length} modules</span>
              <span>{compiledPreview.evidenceCards.length} evidence</span>
              <span>{compiledPreview.metricEvidence.length} metrics</span>
              <span>{compiledPreview.retrievalUnits.length} RU</span>
            </div>
            <div className="action-row">
              <button className="ghost small" onClick={() => void handleBuildTemplate("replace")}>
                Replace Draft From Preview
              </button>
              <button className="ghost small" onClick={() => void handleBuildTemplate("append")}>
                Append Preview To Draft
              </button>
            </div>
            <p>Last compile: {new Date(compiledPreview.compiledAt * 1000).toLocaleString()}</p>
            <div className="tokens">
              {compiledPreview.terminology.slice(0, 12).map((term) => (
                <span key={term} className="token token-outline">
                  {term}
                </span>
              ))}
            </div>
            {compiledPreview.moduleCards.map((item) => (
              <div key={item.moduleId} className="meta-card">
                <div className="panel-head compact">
                  <span>Module</span>
                  <strong>{item.name}</strong>
                </div>
                <p>{item.responsibility}</p>
                <p>{item.designRationale}</p>
                <div className="session-chip">
                  {item.keyFiles.slice(0, 3).map((path) => (
                    <span key={path}>{path}</span>
                  ))}
                </div>
              </div>
            ))}
            {compiledPreview.evidenceCards.map((item) => (
              <div key={item.evidenceId} className="meta-card">
                <div className="panel-head compact">
                  <span>{item.evidenceType}</span>
                  <strong>{item.title}</strong>
                </div>
                <p>{item.summary}</p>
                <div className="session-chip">
                  <span>{item.sourceKind}</span>
                  <span>{item.confidence}</span>
                </div>
                <div className="action-row">
                  <button
                    className="ghost small"
                    onClick={() =>
                      void handleBuildTemplate("append", {
                        evidence_ids: [item.evidenceId],
                        metric_ids: [],
                        retrieval_unit_ids: [],
                      })
                    }
                  >
                    Add Evidence To Draft
                  </button>
                </div>
              </div>
            ))}
            {compiledPreview.metricEvidence.map((item) => (
              <div key={item.evidenceId} className="meta-card">
                <div className="panel-head compact">
                  <span>{item.metricName}</span>
                  <strong>{item.metricValue || "No value"}</strong>
                </div>
                <p>
                  Baseline: {item.baseline || "--"} / Method: {item.method || "--"}
                </p>
                <div className="action-row">
                  <button
                    className="ghost small"
                    onClick={() =>
                      void handleBuildTemplate("append", {
                        evidence_ids: [],
                        metric_ids: [item.evidenceId],
                        retrieval_unit_ids: [],
                      })
                    }
                  >
                    Add Metric To Draft
                  </button>
                </div>
              </div>
            ))}
            {compiledPreview.retrievalUnits.map((item) => (
              <div key={item.unitId} className="meta-card">
                <div className="panel-head compact">
                  <span>{item.unitType}</span>
                  <strong>{item.shortAnswer || item.unitId}</strong>
                </div>
                <p>{item.longAnswer}</p>
                <div className="session-chip">
                  {item.supportingRefs.slice(0, 4).map((ref) => (
                    <span key={ref}>{ref}</span>
                  ))}
                </div>
                <div className="action-row">
                  <button
                    className="ghost small"
                    onClick={() =>
                      void handleBuildTemplate("append", {
                        evidence_ids: [],
                        metric_ids: [],
                        retrieval_unit_ids: [item.unitId],
                      })
                    }
                  >
                    Add RU To Draft
                  </button>
                </div>
              </div>
            ))}
          </>
        ) : (
          <p className="library-empty">先 compile workspace，项目下方就会出现自动生成的 module / evidence / retrieval unit 预览。</p>
        )}
      </div>

      <div className="meta-card">
        <div className="panel-head compact">
          <span>Documents</span>
          <strong>{project.documents.length}</strong>
        </div>
        <div className="action-row">
          <button className="ghost small" onClick={onCreateDocument}>
            新增文档
          </button>
        </div>
        {project.documents.length === 0 ? <p className="library-empty">还没有项目文档，可以手工录入或从 repo 导入。</p> : null}
        {project.documents.map((document) => (
          <div key={document.documentId} className="meta-card">
            <div className="panel-head compact">
              <span>{document.sourceKind === "repo_import" ? "Imported" : "Manual"}</span>
              <strong>{document.title || document.path || "Untitled"}</strong>
            </div>
            <label>
              标题
              <input
                value={document.title}
                onChange={(event) => onChange(updateDocument(project, document.documentId, { title: event.target.value }))}
              />
            </label>
            <label>
              路径
              <input
                value={document.path}
                onChange={(event) => onChange(updateDocument(project, document.documentId, { path: event.target.value }))}
              />
            </label>
            <label>
              内容
              <textarea
                rows={6}
                value={document.content}
                onChange={(event) => onChange(updateDocument(project, document.documentId, { content: event.target.value }))}
              />
            </label>
            <div className="session-chip">
              <span>{document.sourceKind}</span>
              {document.repoId ? <span>repo {document.repoId.slice(0, 8)}</span> : null}
            </div>
            <div className="action-row">
              <button className="ghost accent small" onClick={() => onSaveDocument(document)}>
                Save Doc
              </button>
              <button className="ghost small" onClick={() => onDeleteDocument(document)}>
                删除文档
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="meta-card">
        <div className="panel-head compact">
          <span>Code Snapshots</span>
          <strong>{project.codeFiles.length}</strong>
        </div>
        {project.codeFiles.length === 0 ? <p className="library-empty">当前项目还没有代码快照。</p> : null}
        {project.codeFiles.map((codeFile, index) => (
          <div key={`${codeFile.path}-${index}`} className="meta-card">
            <div className="panel-head compact">
              <span>{codeFile.sourceKind === "repo_import" ? "Imported" : "Manual"}</span>
              <strong>{codeFile.path}</strong>
            </div>
            <label>
              路径
              <input value={codeFile.path} onChange={(event) => onChange(updateCodeFile(project, index, { path: event.target.value }))} />
            </label>
            <label>
              内容
              <textarea
                rows={8}
                value={codeFile.content}
                onChange={(event) => onChange(updateCodeFile(project, index, { content: event.target.value }))}
              />
            </label>
            <div className="session-chip">
              <span>{codeFile.sourceKind}</span>
              {codeFile.repoId ? <span>repo {codeFile.repoId.slice(0, 8)}</span> : null}
            </div>
          </div>
        ))}
      </div>

      <div className="action-row">
        <button className="ghost accent small" onClick={onSave}>
          保存项目
        </button>
        <button className="ghost small" onClick={onDelete}>
          删除项目
        </button>
      </div>
    </section>
  );
}
