# 第 006 课：`request_id` 幂等创建

## 1. 什么是幂等

幂等的意思是：

> 同一个操作执行一次和执行多次，结果应该一样。

在当前项目里，场景是创建 research run。

如果用户因为网络抖动、浏览器重复提交、前端重试，连续发送两次相同创建请求，系统不应该创建两个重复 run。

## 2. `request_id` 的作用

`request_id` 是客户端传来的请求唯一标识。

例子：

```json
{
  "tenant_id": "tenant",
  "user_id": "user",
  "session_id": "session",
  "request_id": "req-001",
  "query": "Analyze AI agents for legal research."
}
```

如果同一个范围内再次提交 `request_id=req-001`，系统返回第一次创建的 run。

## 3. 为什么范围包含 tenant/user/session

幂等判断不是只看 `request_id`。

当前判断范围是：

```text
tenant_id + user_id + session_id + request_id
```

原因：

- 不同租户可能都使用 `req-001`。
- 不同用户可能都使用 `req-001`。
- 同一用户不同 session 也可能有重复编号。

所以 `request_id` 只在自己的上下文里唯一。

## 4. 当前代码链路

创建请求进入：

```text
POST /v1/research-runs
```

路由先查已有 run：

```text
RunStore.find_by_request_id(request)
```

如果存在：

```text
直接返回已有 run_id
不写新的 run.created 事件
不启动新的 workflow
```

如果不存在：

```text
RunStore.create(request)
EventStore.append("run.created")
asyncio.create_task(workflow.run(run_id))
```

## 5. 为什么不启动第二个 workflow

如果重复请求又启动一次 workflow，会有两个问题：

1. 同一个 run 可能被两个后台任务同时更新。
2. 事件和 artifact 可能重复写入。

所以幂等命中时，只返回已有 run，不再触发副作用。

## 6. 测试覆盖

测试用例：

```text
test_research_run_create_is_idempotent_with_request_id
```

验证内容：

- 第一次创建返回一个 `run_id`。
- 第二次使用相同 `request_id` 创建。
- 第二次返回的 `run_id` 和第一次相同。

## 7. 面试怎么讲

可以这样说：

> 我给创建 run 的接口加了 `request_id` 幂等能力。因为长任务创建接口很容易遇到前端重复点击或网络重试，如果没有幂等，会重复创建研究任务。现在系统会在 tenant、user、session 范围内查找相同 request_id，如果已经存在就返回原 run，不再写事件，也不再启动 workflow。
