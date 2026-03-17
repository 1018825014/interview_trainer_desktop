# Persistent Knowledge Module Thread Prompt

这份文档既是“开发任务书”，也是你可以直接粘贴到新 Codex 线程里的启动 prompt。

结论先说：

- 是的，这本质上就是一个 `prompt + 任务边界说明 + 验收标准`
- 最好单开一个新 Codex 线程来做
- 这个线程只负责“本地持久化的多项目资料库”模块，不要顺手去改音频、ASR、live bridge 之类无关主线

## 1. 直接可复制的启动 Prompt

把下面整段复制到一个新的 Codex 线程里：

```text
请在这个项目里专门开发“本地持久化的多项目资料库”模块。

在开始前，请先阅读以下文件：

1. E:/qqbroDownload/interview_trainer_desktop/CODEX_SESSION_HANDOFF.md
2. E:/qqbroDownload/interview_trainer_desktop/FUTURE_DEVELOPMENT_SPEC.md
3. E:/qqbroDownload/interview_trainer_desktop/MULTI_THREAD_WORKFLOW.md
4. E:/qqbroDownload/interview_trainer_desktop/THREAD_OWNERSHIP.md

项目根目录：
E:/qqbroDownload/interview_trainer_desktop

本线程的目标：
- 把当前的临时 workspace 升级为“本地持久化的多项目资料库”
- 支持长期维护用户背景、多项目、代码仓库、项目文档、岗位资料
- 支持把“长期资料库”和“本次面试 overlay”分开管理
- 支持后续像 Codex/Cursor/Claude Code 那样，对用户项目进行长期导入和按需检索

本线程优先做这些事：
1. 设计资料库的数据模型
2. 设计本地持久化方案
3. 支持多个项目和多个 repo
4. 支持导入本地目录并生成项目索引
5. 支持代码/文档的基础索引与元数据管理
6. 提供清晰的后端 API
7. 给桌面端补最小可用的资料库管理 UI

本线程不要优先做这些：
- 不要继续深挖音频采集
- 不要继续优化实时 ASR
- 不要继续优化 live bridge
- 不要大改当前的实时问答主链路，除非为了接入资料库必须改接口

重要约束：
- 优先复用已有代码，不要推翻重写
- 优先做可渐进演进的结构，不要一次性设计过重
- 如果需要修改共享文件（如 api.py / service.py / types.py / README.md），请先遵守 MULTI_THREAD_WORKFLOW.md 和 THREAD_OWNERSHIP.md

建议实现方向：
- 资料层：profile / projects / repos / role-docs / overlays
- 索引层：repo map / module cards / code chunks / doc chunks / terminology / lightweight retrieval metadata
- 存储层：本地持久化（文件或嵌入式数据库均可，但要说明取舍）
- 接口层：workspace list/create/update/compile/import-path 之外，继续扩成真正的 library 管理

验收标准：
- 用户资料不再是内存态，重启后仍保留
- 能管理多个项目，而不是只有一个 project
- 能为每个项目保存多个文档和多个代码目录
- 能为“本次面试”叠加临时资料，而不污染长期资料库
- 能为后续问答链路提供可复用的结构化知识包

交付要求：
- 实现代码
- 更新 README.md
- 更新 CODEX_SESSION_HANDOFF.md
- 必要时更新 FUTURE_DEVELOPMENT_SPEC.md
- 如果做了结构性决策，要写清楚为什么这样做

工作方式：
- 先检查当前代码再动手
- 先做最小可用版本，再继续扩展
- 全程用中文
```

## 2. 本线程真正要解决的问题

当前项目里的 `workspace` 只是“临时编辑 + 内存编译”的调试入口，不是最终产品形态。

最终应当变成两层：

### 第一层：长期个人资料库

长期维护，跨面试复用：

- 个人背景
- 目标岗位
- 自我介绍素材
- 所有项目
- 各项目代码仓库
- 各项目文档
- 学习资料
- 项目级 summary / module / code map / follow-up tree

### 第二层：本次面试 overlay

临时叠加，不污染长期资料：

- 公司
- JD
- 业务背景
- 这场面试特有资料
- 这次想优先强调的项目

## 3. 推荐子任务拆分

建议让新线程优先按这个顺序推进：

1. 定义持久化数据模型
2. 实现本地存储
3. 支持多个项目
4. 支持本地目录导入
5. 支持项目级索引元数据
6. 给前端一个最小管理页
7. 再考虑检索增强

## 4. 建议优先接触的文件

建议先读这些文件：

- `backend/src/interview_trainer/workspace.py`
- `backend/src/interview_trainer/knowledge.py`
- `backend/src/interview_trainer/api.py`
- `backend/src/interview_trainer/service.py`
- `desktop/src/App.tsx`
- `desktop/src/api/client.ts`
- `desktop/src/types.ts`

## 5. 本线程的边界

这个线程应该尽量把改动集中在：

- `backend/src/interview_trainer/workspace.py`
- 新增的 storage / repository / indexing 相关模块
- `backend/src/interview_trainer/api.py`
- 少量必要的 `service.py` 接口改动
- `desktop/src/App.tsx` 里的 workspace 面板
- 新增的前端 workspace 组件

这个线程尽量不要碰：

- `audio.py`
- `transcription.py`
- `realtime_transcription.py`
- `turns.py`

除非确实需要改公共接口，并且已经遵守多线程协作规范。

## 6. 完成后的回写要求

新线程完成后，至少要回写：

- `CODEX_SESSION_HANDOFF.md`
- `FUTURE_DEVELOPMENT_SPEC.md`
- 如果新增了协作规则，也更新 `THREAD_OWNERSHIP.md`

这样主线程和其他线程才能继续接力。
