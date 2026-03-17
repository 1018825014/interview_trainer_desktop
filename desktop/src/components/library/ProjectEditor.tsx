import type { LibraryProjectRecord } from "../../types/library";

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
        <textarea
          rows={4}
          value={project.businessValue}
          onChange={(event) => onChange({ ...project, businessValue: event.target.value })}
        />
      </label>

      <label>
        架构概述
        <textarea
          rows={4}
          value={project.architecture}
          onChange={(event) => onChange({ ...project, architecture: event.target.value })}
        />
      </label>

      <label>
        关键指标
        <textarea
          rows={4}
          value={joinLines(project.keyMetrics)}
          onChange={(event) => onChange({ ...project, keyMetrics: splitLines(event.target.value) })}
        />
      </label>

      <label>
        Tradeoff
        <textarea
          rows={4}
          value={joinLines(project.tradeoffs)}
          onChange={(event) => onChange({ ...project, tradeoffs: splitLines(event.target.value) })}
        />
      </label>

      <label>
        Failure Cases
        <textarea
          rows={4}
          value={joinLines(project.failureCases)}
          onChange={(event) => onChange({ ...project, failureCases: splitLines(event.target.value) })}
        />
      </label>

      <label>
        Limitations
        <textarea
          rows={4}
          value={joinLines(project.limitations)}
          onChange={(event) => onChange({ ...project, limitations: splitLines(event.target.value) })}
        />
      </label>

      <label>
        Upgrade Plan
        <textarea
          rows={4}
          value={joinLines(project.upgradePlan)}
          onChange={(event) => onChange({ ...project, upgradePlan: splitLines(event.target.value) })}
        />
      </label>

      <label>
        Interviewer Hooks
        <textarea
          rows={4}
          value={joinLines(project.interviewerHooks)}
          onChange={(event) => onChange({ ...project, interviewerHooks: splitLines(event.target.value) })}
        />
      </label>

      <label>
        第一份项目文档
        <textarea
          rows={6}
          value={project.documents[0]?.content ?? ""}
          onChange={(event) =>
            onChange({
              ...project,
              documents: event.target.value
                ? [{ path: project.documents[0]?.path ?? "notes.md", content: event.target.value }]
                : [],
            })
          }
        />
      </label>

      <label>
        第一段代码路径
        <input
          value={project.codeFiles[0]?.path ?? ""}
          onChange={(event) =>
            onChange({
              ...project,
              codeFiles: project.codeFiles.length > 0
                ? [{ ...project.codeFiles[0], path: event.target.value }]
                : [{ path: event.target.value, content: "" }],
            })
          }
        />
      </label>

      <label>
        第一段代码内容
        <textarea
          rows={8}
          value={project.codeFiles[0]?.content ?? ""}
          onChange={(event) =>
            onChange({
              ...project,
              codeFiles: event.target.value
                ? [
                    {
                      path: project.codeFiles[0]?.path ?? "src/main.py",
                      content: event.target.value,
                    },
                  ]
                : [],
            })
          }
        />
      </label>

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
