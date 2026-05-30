# 第 003 课：Research Run 运行链路

## 1. FastAPI 应用入口

入口文件：

```text
src/researchos/api/main.py
```

核心职责：

- 创建 FastAPI app。
- 初始化 services。
- 注册 CORS 中间件。
- 挂载 health、runs、artifacts 路由。
- 用 uvicorn 启动服务。

关键结构：

```text
create_app(...)
  -> build_services(...)
  -> include_router(...)
```

技术点：应用入口只负责装配，不写业务逻辑。

## 2. 依赖注入

相关文件：

```text
src/researchos/api/services.py
src/researchos/api/deps.py
```

`build_services` 创建共享对象：

- `Workspace`
- `RunStore`
- `EventStore`
- `ArtifactStore`
- `ResearchWorkflow`

这些对象被放到：

```text
app.state.services
```

路由函数通过 FastAPI 的 `Depends(get_services)` 获取它们。

好处：

- 路由函数不用自己创建依赖。
- 测试时可以创建独立 app 和临时 workspace。
- 后续替换 Store 实现更容易。

## 3. 创建 Research Run

相关文件：

```text
src/researchos/api/routes_runs.py
```

接口：

```text
POST /v1/research-runs
```

处理顺序：

```text
接收 ResearchRunCreate
  -> RunStore.create
  -> EventStore.append("run.created")
  -> asyncio.create_task(workflow.run(run_id))
  -> 返回 run_id / events_url / artifacts_url
```

技术点：

- API 只负责启动任务，不等待任务完成。
- 后台任务用 `asyncio.create_task` 启动。
- 返回值里给出后续查询和订阅地址。

## 4. 后台任务

当前后台任务：

```text
ResearchWorkflow.run(run_id)
```

相关文件：

```text
src/researchos/runtime/workflow.py
```

当前 workflow 是确定性的 MVP，不调用真实 LLM。

阶段顺序：

```text
planning
searching
reading
extracting_evidence
verifying
writing
reviewing
completed
```

每个阶段都会：

```text
RunStore.update(...)
EventStore.append(...)
```

这保证状态查询和事件流来自同一套状态变化。

## 5. SSE 事件流

接口：

```text
GET /v1/research-runs/{run_id}/events
```

返回类型：

```text
text/event-stream
```

核心逻辑：

```text
while run 未结束:
  读取 last_sequence 之后的新事件
  yield SSE 文本
  sleep 0.25 秒
```

SSE 事件格式：

```text
id: 1
event: plan.created
data: {...}
```

适用场景：

- 任务进度流。
- Timeline。
- 轻量实时通知。

常见坑：

- 不能一次性返回完整列表，否则就不是流式。
- 要处理客户端断开连接。
- 事件要有 sequence，方便后续做断线续传。

## 6. 文件型 Store

当前 MVP 使用本地文件，不使用数据库。

### `RunStore`

职责：

- 创建 run。
- 更新 status、progress、current_step。
- 保存 `inputs/task.json`。

### `EventStore`

职责：

- 追加事件。
- 保存 `traces/events.jsonl`。
- 按 sequence 读取事件。

### `ArtifactStore`

职责：

- 写 JSON / 文本产物。
- 列出 run 下所有 artifact。
- 按逻辑路径读取 artifact。

### `Workspace`

职责：

- 创建 run 目录结构。
- 拼接 run 目录路径。
- 防止 artifact 路径逃逸。

## 7. Artifact API

相关文件：

```text
src/researchos/api/routes_artifacts.py
```

接口：

```text
GET /v1/research-runs/{run_id}/artifacts
GET /v1/research-runs/{run_id}/artifacts/content?path=...
```

关键设计：

- 对前端暴露逻辑路径，例如 `outputs/report.md`。
- 内部绝对路径不暴露。
- 读取前必须经过 `Workspace.resolve_artifact_path`。

这能避免路径穿越，例如：

```text
../README
```

## 8. 当前链路总图

```text
Client
  -> FastAPI routes
  -> AppServices
  -> RunStore / EventStore / ArtifactStore
  -> ResearchWorkflow
  -> Workspace files
  -> SSE / Artifact API
```

一句话总结：

> API 负责接入，Workflow 负责推进，Store 负责持久化，Workspace 负责隔离，SSE 和 Artifact API 负责把运行过程与结果暴露给外部。

## 9. Git 知识点：文档改动怎么看

查看当前改动：

```powershell
git status --short
```

这次应该主要看到：

```text
?? docs/interview/
?? docs/lessons/003_run_lifecycle.md
M  docs/learning_notes.md
```

含义：

- `??`：新文档，Git 还没有跟踪。
- `M`：已有文档被修改。

如果只想看文档差异：

```powershell
git diff -- docs
```
