# Thread Ownership

本文件是一个简单的人肉协作表。

用途：

- 让多个 Codex 线程知道“谁在负责什么”
- 降低同时修改同一批文件的概率

规则：

- 开新线程前，先看这个文件
- 新线程开始一个明确模块前，先补一行
- 工作结束后，把状态改成 `done` 或 `idle`

## 当前建议分工

| Thread Name | Purpose | Status | Owned Areas | Shared Files Allowed | Notes |
| --- | --- | --- | --- | --- | --- |
| runtime-debug | 启动、联调、音频/ASR/runtime 调试 | active | `audio.py`, `transcription.py`, `realtime_transcription.py`, runtime logs, startup flow | `api.py`, `service.py`, `App.tsx`, docs | 当前线程 |
| knowledge-library | 本地持久化多项目资料库 | planned | `workspace.py`, future storage/index modules, workspace UI, import/index flow | `api.py`, `service.py`, `types.py`, `App.tsx`, docs | 建议新开线程 |
| eval-system | 评测与回放 | planned | future eval/replay modules | `service.py`, docs, UI summary areas | 暂未开始 |

## 共享文件注意事项

以下文件可以被多个线程触碰，但一定要谨慎：

- `backend/src/interview_trainer/api.py`
- `backend/src/interview_trainer/service.py`
- `backend/src/interview_trainer/types.py`
- `desktop/src/App.tsx`
- `README.md`
- `CODEX_SESSION_HANDOFF.md`
- `FUTURE_DEVELOPMENT_SPEC.md`

建议：

- 同一时间尽量只允许一个线程改这些文件
- 如果必须并行改，尽量把一个线程限制在接口层，另一个线程限制在渲染层

## 新线程登记模板

复制下面一行补充：

| your-thread-name | 你的目标 | active | 你负责的目录/文件 | 允许触碰的共享文件 | 备注 |
