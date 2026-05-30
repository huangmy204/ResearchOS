# 第 005 课：ResearchRun 字段级理解

## 1. 为什么先看 `ResearchRun`

`ResearchRun` 是当前项目最核心的对象。

一句话理解：

> 一个 `ResearchRun` 就是一次研究任务的“任务单”。

它记录：

- 谁发起了任务。
- 任务问的是什么。
- 当前跑到哪一步。
- 是否完成或失败。
- 结果应该去哪里查。

相关代码：

```text
src/researchos/models/run.py
src/researchos/stores/run_store.py
src/researchos/api/routes_runs.py
```

## 2. 三个模型分别做什么

当前有三个 run 相关模型：

```python
ResearchRunCreate
ResearchRun
ResearchRunCreateResponse
```

它们对应三个阶段：

```text
用户创建任务时传入的数据
  -> ResearchRunCreate

系统内部保存的完整任务状态
  -> ResearchRun

API 创建成功后返回给用户的数据
  -> ResearchRunCreateResponse
```

不要把这三个模型混在一起。

## 3. `ResearchRunCreate`

这是用户创建任务时的请求体。

接口：

```text
POST /v1/research-runs
```

字段：

| 字段 | 类型 | 用途 |
|---|---|---|
| `tenant_id` | `str` | 租户 ID，用来支持多组织或多团队隔离。MVP 默认是 `default`。 |
| `user_id` | `str` | 用户 ID，用来区分同一租户下的不同用户。MVP 默认是 `default`。 |
| `session_id` | `str` | 会话 ID，用来把同一次对话或工作会话里的 run 归到一起。 |
| `request_id` | `str | None` | 请求 ID，未来可用于幂等性，避免重复创建相同任务。 |
| `query` | `str` | 用户真正要研究的问题。不能为空。 |
| `options` | `dict` | 运行选项，比如深度、是否启用评测、是否启用 web search。MVP 先保留结构。 |
| `models` | `dict[str, str]` | 模型配置，比如 planner 用哪个模型、writer 用哪个模型。MVP 先保留结构。 |

### 为什么 `query` 用 `Field(min_length=1)`

```python
query: str = Field(min_length=1)
```

意思是：用户不能提交空问题。

如果没有这个限制，系统可能创建一个没有研究目标的 run，后面的 planner、searcher、writer 都不知道该做什么。

## 4. `ResearchRun`

这是系统内部真正保存的任务状态。

它不是用户直接提交的，而是 `RunStore.create()` 根据 `ResearchRunCreate` 生成的。

字段：

| 字段 | 类型 | 用途 |
|---|---|---|
| `run_id` | `str` | 系统生成的唯一任务 ID，例如 `run_xxx`。后续查状态、查事件、查 artifact 都靠它。 |
| `tenant_id` | `str` | 从请求继承，用于 workspace 路径隔离。 |
| `user_id` | `str` | 从请求继承，用于 workspace 路径隔离。 |
| `session_id` | `str` | 从请求继承，用于 workspace 路径隔离。 |
| `request_id` | `str | None` | 从请求继承，未来做幂等性。 |
| `status` | `RunStatus` | 当前任务状态，例如 `planning`、`writing`、`completed`。 |
| `query` | `str` | 原始研究问题。 |
| `created_at` | `datetime` | run 创建时间。 |
| `updated_at` | `datetime` | run 最近一次更新时间。 |
| `finished_at` | `datetime | None` | run 完成、失败或取消的时间。未结束时是 `None`。 |
| `error` | `str | None` | 失败原因。正常运行时是 `None`。 |
| `current_step` | `str | None` | 当前正在做的人类可读步骤，例如 `writing report artifacts`。 |
| `progress` | `dict[str, int]` | 当前进度，例如 `completed_steps: 3`、`total_steps: 7`。 |

## 5. `RunStatus`

`RunStatus` 限制 run 只能处于固定状态之一：

```python
created
planning
searching
reading
extracting_evidence
verifying
writing
reviewing
completed
failed
cancelled
```

为什么不用普通字符串？

因为普通字符串很容易写错，例如：

```text
complete
completed
done
finish
```

如果状态随便写，前端、测试和 workflow 都很难稳定协作。

用 `Literal[...]` 的好处是把状态集合固定下来。

## 6. `progress`

当前默认值：

```python
{"completed_steps": 0, "total_steps": 7}
```

它不是最终评测指标，只是给前端或 API 使用的任务进度。

例如：

```json
{
  "completed_steps": 3,
  "total_steps": 7
}
```

可以理解成：

> 这个 run 总共有 7 个阶段，现在完成了 3 个。

## 7. `ResearchRunCreateResponse`

这是创建 run 成功后返回给用户的简化信息。

字段：

| 字段 | 类型 | 用途 |
|---|---|---|
| `run_id` | `str` | 后续所有查询都要用这个 ID。 |
| `status` | `RunStatus` | 创建后的初始状态，通常是 `created`。 |
| `events_url` | `str` | SSE 事件流地址。 |
| `artifacts_url` | `str` | artifact 列表地址。 |

为什么不直接返回完整 report？

因为 report 是后台 workflow 生成的，创建任务时还没有完成。

所以创建接口只返回：

```text
任务 ID
事件流地址
产物地址
```

## 8. 字段在代码里的流动

创建任务时：

```text
用户请求 JSON
  -> ResearchRunCreate
  -> RunStore.create()
  -> ResearchRun
  -> inputs/task.json
  -> ResearchRunCreateResponse
```

workflow 运行时：

```text
ResearchWorkflow.run(run_id)
  -> RunStore.get(run_id)
  -> RunStore.update(status/current_step/progress)
  -> EventStore.append(...)
```

查询状态时：

```text
GET /v1/research-runs/{run_id}
  -> RunStore.get(run_id)
  -> ResearchRun
```

## 9. 面试怎么讲

30 秒版：

> `ResearchRun` 是这个系统的任务状态模型。用户提交的是 `ResearchRunCreate`，系统会生成完整的 `ResearchRun`，里面包含 run_id、用户隔离信息、任务状态、时间戳、进度和错误信息。创建接口不会等待报告完成，而是返回 run_id、events_url 和 artifacts_url，让前端通过状态查询、SSE 和 artifact API 跟踪长任务。

深入版：

> 我把输入模型、内部状态模型和响应模型分开，是为了让接口边界更清楚。用户创建任务时不应该传 status、created_at 这些系统字段；系统内部需要完整状态；创建成功后也没必要把所有字段都返回给客户端，只要返回后续追踪任务所需的 run_id、events_url 和 artifacts_url。

## 10. 当前可以记住的设计原则

1. 用户传入的是意图，不是系统状态。
2. 系统生成 `run_id`、时间戳和初始状态。
3. 长任务不要同步等待完成。
4. 状态字段要固定，不能随便写字符串。
5. 响应模型应该只返回客户端下一步需要的信息。
