# 第 001 课：项目骨架与 MVP API

## 1. `src/` 项目结构

当前源码放在：

```text
src/researchos/
```

这样做的目的：

- 避免测试时误导入项目根目录下的临时文件。
- 让 Python 包结构更清楚。
- 后续打包、安装、测试都更接近真实工程。

核心规则：正式代码进 `src/researchos/`，测试进 `tests/`，学习文档进 `docs/`。

## 2. `pyproject.toml`

`pyproject.toml` 是现代 Python 项目的主配置文件。

当前它负责：

- 声明项目名称、版本、Python 版本。
- 声明运行依赖和开发依赖。
- 配置 pytest。
- 配置 Ruff。

最小 MVP 阶段不急着引入 LangGraph、OpenAI、Redis、Postgres 等重依赖。

## 3. FastAPI 最小 API

当前 API 的核心形状：

```text
POST /v1/research-runs
GET  /v1/research-runs/{run_id}
GET  /v1/research-runs/{run_id}/events
GET  /v1/research-runs/{run_id}/artifacts
GET  /v1/research-runs/{run_id}/artifacts/content?path=...
```

这类系统最重要的不是“一次返回答案”，而是支持长任务：

1. 创建任务。
2. 查询任务状态。
3. 流式查看进度。
4. 下载任务产物。

## 4. Pydantic 模型

Pydantic 用来定义接口和内部数据结构。

当前核心模型：

- `ResearchRun`
- `ResearchEvent`
- `Source`
- `Evidence`
- `Claim`
- `CitationVerification`
- `ArtifactMetadata`

为什么重要：

- API 输入输出更稳定。
- 测试更容易写。
- 后续接 LLM 时，能减少松散 `dict` 带来的混乱。

## 5. 文件型 Store

当前没有直接上数据库，而是先做文件型 Store：

- `RunStore`：管理 run 状态。
- `EventStore`：写入事件日志。
- `ArtifactStore`：管理产物。
- `Workspace`：管理目录和路径安全。

这样可以先学习系统边界，再替换成 Postgres / Redis。

## 6. Workspace 隔离

每个 run 的目录：

```text
workspace/tenants/<tenant_id>/users/<user_id>/sessions/<session_id>/runs/<run_id>/
```

关键点：

- 每个任务的输入、输出、证据、trace 分开。
- API 只暴露逻辑路径，不暴露内部绝对路径。
- Artifact 读取必须防止 `../` 路径穿越。

## 7. SSE

SSE 是 Server-Sent Events。

它适合服务端持续推送进度：

```text
event: plan.created
data: {...}
```

相比 WebSocket，它更简单，适合 Research Run Timeline。

## 8. 当前 Git 知识点

查看改动：

```powershell
git status --short
```

含义：

- `??`：新文件，Git 还没跟踪。
- `M`：已跟踪文件被修改。
- `A`：文件已加入暂存区，准备提交。

当前阶段先不要急着 commit。等我们确认第一批代码能运行、测试通过，再做一次小提交。
