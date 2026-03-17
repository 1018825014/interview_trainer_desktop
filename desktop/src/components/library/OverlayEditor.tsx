import type { LibraryOverlayRecord, LibraryProjectRecord } from "../../types/library";

interface OverlayEditorProps {
  overlay: LibraryOverlayRecord | null;
  projects: LibraryProjectRecord[];
  onChange: (overlay: LibraryOverlayRecord) => void;
  onSave: () => void;
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

function toggleId(list: string[], id: string): string[] {
  return list.includes(id) ? list.filter((item) => item !== id) : [...list, id];
}

export function OverlayEditor({ overlay, projects, onChange, onSave }: OverlayEditorProps) {
  if (!overlay) {
    return (
      <section className="library-editor">
        <div className="panel-head">
          <span>Overlay 编辑</span>
          <strong>未选择</strong>
        </div>
        <p className="library-empty">创建一个公司/JD overlay 后，就可以在这里配置表达偏置和聚焦项目。</p>
      </section>
    );
  }

  return (
    <section className="library-editor">
      <div className="panel-head">
        <span>Overlay 编辑</span>
        <strong>{overlay.name}</strong>
      </div>

      <label>
        名称
        <input value={overlay.name} onChange={(event) => onChange({ ...overlay, name: event.target.value })} />
      </label>

      <label>
        公司
        <input value={overlay.company} onChange={(event) => onChange({ ...overlay, company: event.target.value })} />
      </label>

      <label>
        业务背景
        <textarea
          rows={4}
          value={overlay.businessContext}
          onChange={(event) => onChange({ ...overlay, businessContext: event.target.value })}
        />
      </label>

      <label>
        JD
        <textarea
          rows={6}
          value={overlay.jobDescription}
          onChange={(event) => onChange({ ...overlay, jobDescription: event.target.value })}
        />
      </label>

      <div className="library-checkbox-group">
        <span>聚焦项目</span>
        {projects.map((project) => (
          <label key={project.projectId} className="library-checkbox-item">
            <input
              type="checkbox"
              checked={overlay.focusProjectIds.includes(project.projectId)}
              onChange={() => onChange({ ...overlay, focusProjectIds: toggleId(overlay.focusProjectIds, project.projectId) })}
            />
            <span>{project.name}</span>
          </label>
        ))}
      </div>

      <label>
        强调点
        <textarea
          rows={4}
          value={joinLines(overlay.emphasisPoints)}
          onChange={(event) => onChange({ ...overlay, emphasisPoints: splitLines(event.target.value) })}
        />
      </label>

      <label>
        风格约束
        <textarea
          rows={4}
          value={joinLines(overlay.styleProfile)}
          onChange={(event) => onChange({ ...overlay, styleProfile: splitLines(event.target.value) })}
        />
      </label>

      <label>
        深度策略
        <select value={overlay.depthPolicy} onChange={(event) => onChange({ ...overlay, depthPolicy: event.target.value })}>
          <option value="shallow">shallow</option>
          <option value="standard">standard</option>
          <option value="deep">deep</option>
          <option value="defend">defend</option>
        </select>
      </label>

      <div className="action-row">
        <button className="ghost accent small" onClick={onSave}>
          保存 Overlay
        </button>
      </div>
    </section>
  );
}
