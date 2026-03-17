# Multi-Thread Workflow

本文件用于约束“多个 Codex 线程同时开发同一个项目”时的协作方式。

结论先说：

- 最稳的方法不是“大家都在同一个工作目录里直接改”
- 最稳的方法是：`一个线程一个工作目录隔离 + 一个线程一组明确职责 + 少量共享文件串行修改`

如果你真的要并行开发，推荐优先使用下面这套方法。

## 1. 最推荐的方法

### 1.1 一线程一 worktree / 一目录

最推荐的结构是：

- 主目录：当前线程继续调试和联调
- 资料库线程：单独目录
- 其他功能线程：再单独目录

如果用 Git，推荐：

- 一个线程一个 `git worktree`
- 一个线程一个代码分支

这不是“Chat 对话分支”，而是“代码隔离分支”，目的只是避免文件互相覆盖。

建议命名：

- `codex/runtime-debug`
- `codex/knowledge-library`
- `codex/eval-system`

## 2. 如果暂时不想开 worktree

如果多个线程必须共用同一个工作目录，那至少要遵守：

1. 每个线程只负责自己认领的模块
2. 修改共享文件前，先看 `THREAD_OWNERSHIP.md`
3. 共享文件尽量串行修改，不要同时改
4. 每个线程结束前，更新 handoff 文档

这不是最稳，但比完全无规则地同时改强很多。

## 3. 强制协作规则

### 3.1 文件所有权优先

一个线程已经认领的文件，其他线程不要随便改。

### 3.2 共享文件最危险

这些文件冲突概率最高：

- `backend/src/interview_trainer/api.py`
- `backend/src/interview_trainer/service.py`
- `backend/src/interview_trainer/types.py`
- `desktop/src/App.tsx`
- `README.md`
- `CODEX_SESSION_HANDOFF.md`
- `FUTURE_DEVELOPMENT_SPEC.md`

如果必须改这些文件：

- 尽量缩小 diff
- 先看别的线程有没有正在占用
- 必要时让一个线程先落接口，另一个线程后接 UI

### 3.3 不要同时改同一个大文件

尤其是：

- `App.tsx`
- `service.py`
- `api.py`

这类文件最容易出现“后写覆盖前写”的问题。

## 4. 推荐的模块划分方式

### 4.1 线程 A：运行时与调试

负责：

- 启动
- backend / frontend 联调
- 音频链路
- ASR
- live bridge
- runtime bug 修复

### 4.2 线程 B：资料库模块

负责：

- 本地持久化
- 多项目资料库
- 代码导入与索引
- workspace / library UI
- overlay 模型

### 4.3 线程 C：评测与回放

负责：

- eval
- replay
- quality metrics
- prompt comparison

这样比“每个线程都改一点全部模块”冲突少很多。

## 5. 最稳的开发流程

推荐流程：

1. 先明确线程职责
2. 在 `THREAD_OWNERSHIP.md` 里登记
3. 每个线程只在自己的模块范围内开发
4. 共享接口通过少量文件对接
5. 阶段结束后再合并回主线

## 6. 端口与运行环境隔离

并行开发时，最好也隔离运行端口：

- 线程 A backend: `8000`
- 线程 A frontend: `5173`
- 线程 B backend: `8001`
- 线程 B frontend: `5174`
- 线程 C backend: `8002`
- 线程 C frontend: `5175`

否则多个线程一启动就会互相抢端口，看起来像“项目坏了”，其实只是实例冲突。

## 7. 日志隔离

不同线程最好各自写自己的日志目录：

- `run_logs/runtime-debug/`
- `run_logs/knowledge-library/`
- `run_logs/eval-system/`

这样调试时不会把日志混在一起。

## 8. 文档同步规则

每个线程完成一轮工作后，至少同步这些信息：

- 改了什么
- 验证了什么
- 还剩什么
- 哪些共享文件被动过

最少更新：

- `CODEX_SESSION_HANDOFF.md`

如果是长期规划变化，再更新：

- `FUTURE_DEVELOPMENT_SPEC.md`

## 9. 什么时候必须停下来同步

如果发生这些情况，不要硬改：

- 发现另一个线程也在改同一个核心文件
- 需要改共享接口，但接口尚未稳定
- 需要改动范围超出原本线程职责
- 发现已有实现与你的方案明显冲突

这时应该先同步，再继续。

## 10. 最终建议

如果你准备单独开一个 Codex 线程做“持久化多项目资料库”，我的明确建议是：

- 最好给它单独一个代码工作目录
- 如果用 Git，就给它单独一个 worktree 和分支
- 至少不要和当前“启动/debug/runtime”线程共改同一批共享文件

一句话总结：

- `功能并行可以`
- `同文件乱改不行`
- `隔离目录 + 明确职责 + 共享文件串行修改` 是最稳的方案
