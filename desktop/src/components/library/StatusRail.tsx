import type {
  LibraryBundleSummaryRecord,
  LibraryProjectRecord,
  LibrarySessionPayload,
  LibraryWorkspaceRecord,
} from "../../types/library";

interface StatusRailProps {
  workspace: LibraryWorkspaceRecord | null;
  project: LibraryProjectRecord | null;
  selectedBundle: LibraryBundleSummaryRecord | null;
  latestPayload: LibrarySessionPayload | null;
  importPath: string;
  statusMessage: string;
  onImportPathChange: (value: string) => void;
  onRefreshWorkspace: () => void;
  onCompileWorkspace: () => void;
  onImportRepo: () => void;
  onReindexRepo: (repoId: string) => void;
}

function formatTime(value: number | null | undefined): string {
  if (!value) {
    return "--";
  }
  return new Date(value * 1000).toLocaleString();
}

export function StatusRail({
  workspace,
  project,
  selectedBundle,
  latestPayload,
  importPath,
  statusMessage,
  onImportPathChange,
  onRefreshWorkspace,
  onCompileWorkspace,
  onImportRepo,
  onReindexRepo,
}: StatusRailProps) {
  const latestBundle =
    selectedBundle ??
    latestPayload?.activationSummary ??
    (workspace && workspace.compiledBundles.length > 0 ? workspace.compiledBundles[workspace.compiledBundles.length - 1] : null);

  return (
    <aside className="status-rail">
      <div className="panel-head">
        <span>状态与资产</span>
        <strong>{workspace ? "Ready" : "Idle"}</strong>
      </div>

      <div className="meta-card">
        <div className="panel-head compact">
          <span>工作区状态</span>
          <strong>{workspace?.name ?? "未加载"}</strong>
        </div>
        <p>{statusMessage}</p>
        <p>更新时间：{formatTime(workspace?.updatedAt)}</p>
        <div className="action-row">
          <button className="ghost small" onClick={onRefreshWorkspace} disabled={!workspace}>
            刷新
          </button>
          <button className="ghost accent small" onClick={onCompileWorkspace} disabled={!workspace}>
            编译资料库
          </button>
        </div>
      </div>

      {workspace?.compileSummary ? (
        <div className="meta-card">
          <div className="panel-head compact">
            <span>Compile Summary</span>
            <strong>{workspace.compileSummary.projects.length}</strong>
          </div>
          <div className="session-chip">
            <span>{workspace.compileSummary.modules} modules</span>
            <span>{workspace.compileSummary.docChunks} docs</span>
            <span>{workspace.compileSummary.codeChunks} code</span>
            <span>{workspace.compileSummary.terminologyCount} terms</span>
          </div>
        </div>
      ) : null}

      {project ? (
        <div className="meta-card">
          <div className="panel-head compact">
            <span>项目资产</span>
            <strong>{project.name}</strong>
          </div>
          <p>{project.repoSummaries.length} 个 repo / {project.documents.length} 份文档 / {project.codeFiles.length} 段代码</p>
          {project.repoSummaries.length > 0 ? (
            <ul className="note-list">
              {project.repoSummaries.map((repo) => (
                <li key={repo.repoId}>
                  <div>
                    {repo.label}: {repo.importedDocs} docs + {repo.importedCodeFiles} code
                  </div>
                  <div className="session-chip">
                    <span>{repo.status}</span>
                    <span>{formatTime(repo.lastScannedAt)}</span>
                  </div>
                  <div className="action-row">
                    <button className="ghost small" onClick={() => onReindexRepo(repo.repoId)}>
                      Reindex Repo
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p>还没有 repo，可从本地路径导入。</p>
          )}
          <label>
            导入本地 repo 路径
            <input value={importPath} onChange={(event) => onImportPathChange(event.target.value)} placeholder="E:\\path\\to\\project" />
          </label>
          <button className="ghost small" onClick={onImportRepo} disabled={!importPath.trim()}>
            导入到当前项目
          </button>
        </div>
      ) : null}

      {latestBundle ? (
        <div className="meta-card">
          <div className="panel-head compact">
            <span>最近 Bundle</span>
            <strong>{latestBundle.presetName || latestBundle.bundleId.slice(0, 8)}</strong>
          </div>
          <p>{latestBundle.projectNames.join(" / ") || "未绑定项目"}</p>
          <div className="session-chip">
            <span>{latestBundle.projectCount} 项目</span>
            <span>{latestBundle.retrievalUnitCount} RU</span>
            <span>{latestBundle.metricEvidenceCount} metric</span>
            <span>{latestBundle.terminologyCount} terms</span>
          </div>
        </div>
      ) : null}

      {latestPayload ? (
        <div className="meta-card">
          <div className="panel-head compact">
            <span>最近激活 Payload</span>
            <strong>{latestPayload.briefing.company || "No company"}</strong>
          </div>
          <p>{latestPayload.briefing.businessContext || "未提供业务背景"}</p>
          <div className="tokens">
            {latestPayload.briefing.focusTopics.map((topic) => (
              <span key={topic} className="token token-outline">
                {topic}
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </aside>
  );
}
