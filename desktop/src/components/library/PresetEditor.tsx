import type {
  LibraryBundleSummaryRecord,
  LibraryOverlayRecord,
  LibraryPresetComparisonRecord,
  LibraryPresetRecord,
  LibraryProjectRecord,
} from "../../types/library";

interface PresetEditorProps {
  preset: LibraryPresetRecord | null;
  projects: LibraryProjectRecord[];
  overlays: LibraryOverlayRecord[];
  presets: LibraryPresetRecord[];
  latestBundle: LibraryBundleSummaryRecord | null;
  comparison: LibraryPresetComparisonRecord | null;
  comparePresetId: string;
  onChange: (preset: LibraryPresetRecord) => void;
  onSave: () => void;
  onBuildPayload: () => void;
  onActivate: () => void;
  onClone: () => void;
  onChangeCompareTarget: (presetId: string) => void;
}

function toggleId(list: string[], id: string): string[] {
  return list.includes(id) ? list.filter((item) => item !== id) : [...list, id];
}

export function PresetEditor({
  preset,
  projects,
  overlays,
  presets,
  latestBundle,
  comparison,
  comparePresetId,
  onChange,
  onSave,
  onBuildPayload,
  onActivate,
  onClone,
  onChangeCompareTarget,
}: PresetEditorProps) {
  if (!preset) {
    return (
      <section className="library-editor">
        <div className="panel-head">
          <span>Preset Editor</span>
          <strong>None</strong>
        </div>
        <p className="library-empty">Preset 用来把多个项目、overlay 和 role documents 组合成可直接用于面试会话的知识包。</p>
      </section>
    );
  }

  const otherPresets = presets.filter((item) => item.presetId !== preset.presetId);

  return (
    <section className="library-editor">
      <div className="panel-head">
        <span>Preset Editor</span>
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
        <button className="ghost small" onClick={onClone}>
          Clone Preset
        </button>
      </div>

      <div className="meta-card">
        <div className="panel-head compact">
          <span>Preset Compare</span>
          <strong>{otherPresets.length}</strong>
        </div>
        {otherPresets.length > 0 ? (
          <label>
            对比目标
            <select value={comparePresetId} onChange={(event) => onChangeCompareTarget(event.target.value)}>
              <option value="">不对比</option>
              {otherPresets.map((item) => (
                <option key={item.presetId} value={item.presetId}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <p className="library-empty">至少再创建一个 preset，才能对比不同公司的项目组合。</p>
        )}

        {comparison ? (
          <>
            <div className="session-chip">
              <span>{comparison.leftPreset.name}</span>
              <span>vs</span>
              <span>{comparison.rightPreset.name}</span>
            </div>
            <div className="session-chip">
              <span>Overlay: {comparison.leftOverlayName || "None"}</span>
              <span>{comparison.overlayChanged ? "changed" : "same"}</span>
              <span>Role Docs: {comparison.includeRoleDocumentsChanged ? "changed" : "same"}</span>
            </div>
            {comparison.addedProjects.length > 0 ? (
              <div className="authoring-validation">
                <div className="panel-head compact">
                  <span>Added Projects</span>
                  <strong>{comparison.addedProjects.length}</strong>
                </div>
                {comparison.addedProjects.map((item) => (
                  <p key={item} className="authoring-status">
                    {item}
                  </p>
                ))}
              </div>
            ) : null}
            {comparison.removedProjects.length > 0 ? (
              <div className="authoring-validation">
                <div className="panel-head compact">
                  <span>Removed Projects</span>
                  <strong>{comparison.removedProjects.length}</strong>
                </div>
                {comparison.removedProjects.map((item) => (
                  <p key={item} className="library-error">
                    {item}
                  </p>
                ))}
              </div>
            ) : null}
            {comparison.sharedProjects.length > 0 ? (
              <div className="tokens">
                {comparison.sharedProjects.map((item) => (
                  <span key={item} className="token token-outline">
                    {item}
                  </span>
                ))}
              </div>
            ) : null}
          </>
        ) : comparePresetId ? (
          <p className="library-empty">正在加载 preset 对比结果...</p>
        ) : null}
      </div>
    </section>
  );
}
