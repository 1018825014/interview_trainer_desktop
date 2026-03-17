import type {
  LibraryEntitySelection,
  LibraryPresetLatestBundleStatusRecord,
  LibraryWorkspaceRecord,
} from "../../types/library";

interface WorkspaceNavProps {
  workspaces: LibraryWorkspaceRecord[];
  workspace: LibraryWorkspaceRecord | null;
  presetStatuses: LibraryPresetLatestBundleStatusRecord[];
  selection: LibraryEntitySelection | null;
  onSelectWorkspace: (workspaceId: string) => void;
  onSelect: (selection: LibraryEntitySelection) => void;
  onCreateWorkspace: () => void;
  onCreateProject: () => void;
  onCreateOverlay: () => void;
  onCreatePreset: () => void;
}

function isActive(selection: LibraryEntitySelection | null, type: LibraryEntitySelection["type"], id: string): boolean {
  return Boolean(selection && selection.type === type && selection.id === id);
}

export function WorkspaceNav({
  workspaces,
  workspace,
  presetStatuses,
  selection,
  onSelectWorkspace,
  onSelect,
  onCreateWorkspace,
  onCreateProject,
  onCreateOverlay,
  onCreatePreset,
}: WorkspaceNavProps) {
  const presetStatusById = new Map(presetStatuses.map((item) => [item.preset.presetId, item]));

  return (
    <aside className="library-nav">
      <div className="panel-head">
        <span>Library</span>
        <strong>{workspaces.length}</strong>
      </div>

      <div className="action-row library-nav-actions">
        <button className="ghost accent small" onClick={onCreateWorkspace}>
          New Workspace
        </button>
        <button className="ghost small" onClick={onCreateProject} disabled={!workspace}>
          Project +
        </button>
        <button className="ghost small" onClick={onCreateOverlay} disabled={!workspace}>
          Overlay +
        </button>
        <button className="ghost small" onClick={onCreatePreset} disabled={!workspace}>
          Preset +
        </button>
      </div>

      <div className="library-section">
        <div className="library-section-head">
          <span>Workspaces</span>
        </div>
        <div className="library-list">
          {workspaces.length === 0 ? (
            <p className="library-empty">No persisted workspace yet. Create one to get started.</p>
          ) : (
            workspaces.map((item) => (
              <button
                key={item.workspaceId}
                className={`library-list-item ${workspace?.workspaceId === item.workspaceId ? "active" : ""}`}
                onClick={() => onSelectWorkspace(item.workspaceId)}
              >
                <strong>{item.name}</strong>
                <small>{item.knowledge.projects.length} projects</small>
              </button>
            ))
          )}
        </div>
      </div>

      {workspace ? (
        <>
          <div className="library-section">
            <div className="library-section-head">
              <span>Projects</span>
              <small>{workspace.knowledge.projects.length}</small>
            </div>
            <div className="library-list">
              <button
                className={`library-list-item ${isActive(selection, "workspace", workspace.workspaceId) ? "active" : ""}`}
                onClick={() => onSelect({ type: "workspace", id: workspace.workspaceId })}
              >
                <strong>{workspace.name}</strong>
                <small>Profile and long-term materials</small>
              </button>
              {workspace.knowledge.projects.map((project) => (
                <button
                  key={project.projectId}
                  className={`library-list-item ${isActive(selection, "project", project.projectId) ? "active" : ""}`}
                  onClick={() => onSelect({ type: "project", id: project.projectId })}
                >
                  <strong>{project.name}</strong>
                  <small>{project.repoSummaries.length} repo / {project.documents.length} docs</small>
                </button>
              ))}
            </div>
          </div>

          <div className="library-section">
            <div className="library-section-head">
              <span>Overlays</span>
              <small>{workspace.overlays.length}</small>
            </div>
            <div className="library-list">
              {workspace.overlays.map((overlay) => (
                <button
                  key={overlay.overlayId}
                  className={`library-list-item ${isActive(selection, "overlay", overlay.overlayId) ? "active" : ""}`}
                  onClick={() => onSelect({ type: "overlay", id: overlay.overlayId })}
                >
                  <strong>{overlay.name}</strong>
                  <small>{overlay.company || "No company"} / {overlay.depthPolicy}</small>
                </button>
              ))}
            </div>
          </div>

          <div className="library-section">
            <div className="library-section-head">
              <span>Presets</span>
              <small>{workspace.presets.length}</small>
            </div>
            <div className="library-list">
              {workspace.presets.map((preset) => {
                const status = presetStatusById.get(preset.presetId);
                const statusLabel = status ? status.status.toUpperCase() : "UNKNOWN";
                const statusDetail =
                  status?.status === "stale"
                    ? `${status.reasons.length} stale reason${status.reasons.length === 1 ? "" : "s"}`
                    : status?.status === "missing"
                      ? "No bundle yet"
                      : "Bundle ready";
                return (
                  <button
                    key={preset.presetId}
                    className={`library-list-item ${isActive(selection, "preset", preset.presetId) ? "active" : ""}`}
                    onClick={() => onSelect({ type: "preset", id: preset.presetId })}
                  >
                    <strong>{preset.name}</strong>
                    <small>
                      {statusLabel} / {preset.projectIds.length} projects / {statusDetail}
                    </small>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="library-section">
            <div className="library-section-head">
              <span>Bundles</span>
              <small>{workspace.compiledBundles.length}</small>
            </div>
            <div className="library-list">
              {workspace.compiledBundles
                .slice()
                .reverse()
                .map((bundle) => (
                  <button
                    key={bundle.bundleId}
                    className={`library-list-item ${isActive(selection, "bundle", bundle.bundleId) ? "active" : ""}`}
                    onClick={() => onSelect({ type: "bundle", id: bundle.bundleId })}
                  >
                    <strong>{bundle.presetName || "Bundle"}</strong>
                    <small>{bundle.projectCount} projects / {bundle.retrievalUnitCount} RU</small>
                  </button>
                ))}
            </div>
          </div>
        </>
      ) : null}
    </aside>
  );
}
