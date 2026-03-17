import type {
  LibraryBundleSummaryRecord,
  LibraryOverlayRecord,
  LibraryPresetRecord,
  LibraryProjectRecord,
} from "../../types/library";

interface PresetEditorProps {
  preset: LibraryPresetRecord | null;
  projects: LibraryProjectRecord[];
  overlays: LibraryOverlayRecord[];
  latestBundle: LibraryBundleSummaryRecord | null;
  onChange: (preset: LibraryPresetRecord) => void;
  onSave: () => void;
  onBuildPayload: () => void;
  onActivate: () => void;
}

function toggleId(list: string[], id: string): string[] {
  return list.includes(id) ? list.filter((item) => item !== id) : [...list, id];
}

export function PresetEditor({
  preset,
  projects,
  overlays,
  latestBundle,
  onChange,
  onSave,
  onBuildPayload,
  onActivate,
}: PresetEditorProps) {
  if (!preset) {
    return (
      <section className="library-editor">
        <div className="panel-head">
          <span>Preset 编辑</span>
          <strong>未选择</strong>
        </div>
        <p className="library-empty">Preset 用来把项目、overlay 和 role 文档组合成面试现场能直接激活的知识包。</p>
      </section>
    );
  }

  return (
    <section className="library-editor">
      <div className="panel-head">
        <span>Preset 编辑</span>
        <strong>{preset.name}</strong>
      </div>

      <label>
        Preset 名称
        <input value={preset.name} onChange={(event) => onChange({ ...preset, name: event.target.value })} />
      </label>

      <label>
        绑定 Overlay
        <select value={preset.overlayId} onChange={(event) => onChange({ ...preset, overlayId: event.target.value })}>
          <option value="">不绑定 Overlay</option>
          {overlays.map((overlay) => (
            <option key={overlay.overlayId} value={overlay.overlayId}>
              {overlay.name}
            </option>
          ))}
        </select>
      </label>

      <div className="library-checkbox-group">
        <span>启用项目</span>
        {projects.map((project) => (
          <label key={project.projectId} className="library-checkbox-item">
            <input
              type="checkbox"
              checked={preset.projectIds.includes(project.projectId)}
              onChange={() => onChange({ ...preset, projectIds: toggleId(preset.projectIds, project.projectId) })}
            />
            <span>{project.name}</span>
          </label>
        ))}
      </div>

      <label className="library-checkbox-inline">
        <input
          type="checkbox"
          checked={preset.includeRoleDocuments}
          onChange={(event) => onChange({ ...preset, includeRoleDocuments: event.target.checked })}
        />
        <span>会话时附带 role documents</span>
      </label>

      {latestBundle ? (
        <div className="route-banner">
          <span>最新 Bundle</span>
          <p>
            {latestBundle.presetName} | {latestBundle.projectCount} 个项目 | {latestBundle.retrievalUnitCount} 个回答单元 |
            {latestBundle.metricEvidenceCount} 个指标证据
          </p>
        </div>
      ) : null}

      <div className="action-row">
        <button className="ghost accent small" onClick={onSave}>
          保存 Preset
        </button>
        <button className="ghost small" onClick={onBuildPayload}>
          构建会话知识包
        </button>
        <button className="ghost small" onClick={onActivate}>
          直接用于当前会话
        </button>
      </div>
    </section>
  );
}
