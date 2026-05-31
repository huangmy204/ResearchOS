# 第 023 课：Workflow Trace API

## 1. 这一阶段新增了什么

新增接口：

```text
GET /v1/research-runs/{run_id}/trace
```

它读取底层 artifact：

```text
traces/workflow_trace.json
```

并返回结构化响应：

```text
run_id
nodes
summary
```

## 2. 为什么不只用 artifact API

artifact API 很通用：

```text
GET /v1/research-runs/{run_id}/artifacts/content?path=traces/workflow_trace.json
```

但它的问题是：

- 调用方必须知道具体文件路径。
- 返回的是原始文件内容。
- 不方便前端直接渲染节点状态。
- 不方便对 trace 做 summary。

Trace API 是更稳定的业务入口：

```text
GET /v1/research-runs/{run_id}/trace
```

前端和面试演示都可以直接使用。

## 3. 返回内容怎么看

`nodes` 是每个节点的执行记录：

```text
node
status
step_name
duration_ms
event_type
artifacts
```

`summary` 是接口层聚合出来的概览：

```text
node_count
total_duration_ms
completed
node_names
```

## 4. 面试怎么讲

可以这样说：

> workflow trace 底层仍然作为 artifact 保存，保证每个 run 的执行过程可以追溯。但我又封装了一个 Trace API，前端或调试工具不用知道内部文件路径，就能直接拿到节点列表、耗时和完成状态。这个设计把底层存储和外部查询接口分开，既保留 artifact 的可审计性，也提供了更好的产品接口。

这体现的是：

- 你知道 artifact 是内部持久化。
- 你知道 API 是对外契约。
- 你能为前端和调试场景设计更方便的接口。
- 你能把 workflow 从黑盒变成可观察流程。
