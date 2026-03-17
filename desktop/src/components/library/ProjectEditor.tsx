import type { LibraryCodeFileRecord, LibraryDocumentRecord, LibraryProjectRecord } from "../../types/library";

interface ProjectEditorProps {
  project: LibraryProjectRecord | null;
  onChange: (project: LibraryProjectRecord) => void;
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

function addBlankDocument(project: LibraryProjectRecord): LibraryProjectRecord {
  const nextDocument: LibraryDocumentRecord = {
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
  return { ...project, documents: [...project.documents, nextDocument] };
}

function updateDocument(project: LibraryProjectRecord, documentId: string, patch: Partial<LibraryDocumentRecord>): LibraryProjectRecord {
  return {
    ...project,
    documents: project.documents.map((document) =>
      document.documentId === documentId ? { ...document, ...patch } : document,
    ),
  };
}

function deleteDocument(project: LibraryProjectRecord, documentId: string): LibraryProjectRecord {
  return {
    ...project,
    documents: project.documents.filter((document) => document.documentId !== documentId),
  };
}

function updateCodeFile(project: LibraryProjectRecord, index: number, patch: Partial<LibraryCodeFileRecord>): LibraryProjectRecord {
  return {
    ...project,
    codeFiles: project.codeFiles.map((file, fileIndex) => (fileIndex === index ? { ...file, ...patch } : file)),
  };
}

export function ProjectEditor({ project, onChange, onSave, onDelete }: ProjectEditorProps) {
  if (!project) {
    return (
      <section className="library-editor">
        <div className="panel-head">
          <span>项目编辑</span>
          <strong>未选择</strong>
        </div>
        <p className="library-empty">从左侧选一个项目，或者先新建项目。</p>
      </section>
    );
  }

  return (
    <section className="library-editor">
      <div className="panel-head">
        <span>项目编辑</span>
        <strong>{project.name}</strong>
      </div>

      <label>
        项目名称
        <input value={project.name} onChange={(event) => onChange({ ...project, name: event.target.value })} />
      </label>

      <label>
        30 秒版本
        <textarea rows={3} value={project.pitch30} onChange={(event) => onChange({ ...project, pitch30: event.target.value })} />
      </label>

      <label>
        90 秒版本
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
          <span>文档资产</span>
          <strong>{project.documents.length}</strong>
        </div>
        <div className="action-row">
          <button className="ghost small" onClick={() => onChange(addBlankDocument(project))}>
            新增文档
          </button>
        </div>
        {project.documents.length === 0 ? <p className="library-empty">还没有项目文档，可以手工录入或从 repo 导入。</p> : null}
        {project.documents.map((document) => (
          <div key={document.documentId} className="meta-card">
            <div className="panel-head compact">
              <span>{document.sourceKind === "repo_import" ? "导入文档" : "手工文档"}</span>
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
              <button className="ghost small" onClick={() => onChange(deleteDocument(project, document.documentId))}>
                删除文档
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="meta-card">
        <div className="panel-head compact">
          <span>代码快照</span>
          <strong>{project.codeFiles.length}</strong>
        </div>
        {project.codeFiles.length === 0 ? <p className="library-empty">当前项目还没有代码快照。</p> : null}
        {project.codeFiles.map((codeFile, index) => (
          <div key={`${codeFile.path}-${index}`} className="meta-card">
            <div className="panel-head compact">
              <span>{codeFile.sourceKind === "repo_import" ? "导入代码" : "手工代码"}</span>
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
