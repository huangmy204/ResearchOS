# 第 007 课：长任务取消机制

## 1. 取消不是只改状态

取消 run 时，API 会把状态改成：

```text
cancelled
```

但这还不够。

如果后台 workflow 已经启动，它可能还在继续执行。只改状态、不停止 workflow，会出现这种错误：

```text
用户看到 run 是 cancelled
后台却继续生成 report
最后状态又被改成 completed
```

所以取消长任务需要两层配合：

1. API 层把 run 标记为 `cancelled`。
2. Workflow 层定期检查状态，发现取消后停止执行。

## 2. 当前取消入口

接口：

```text
POST /v1/research-runs/{run_id}/cancel
```

行为：

```text
RunStore.update(status="cancelled", finished=True)
EventStore.append("run.cancelled")
```

如果 run 已经是 `completed`、`failed`、`cancelled`，再次取消不会产生新效果。

## 3. Workflow 如何停止

当前 workflow 在阶段之间调用：

```python
self._raise_if_cancelled(run_id)
```

如果发现 run 当前状态是 `cancelled`，就抛出内部异常：

```python
WorkflowCancelled
```

`run()` 捕获这个异常后直接返回，不再继续写 artifact，也不把状态改成 `completed`。

## 4. 为什么在多个位置检查

长任务不是一个瞬间完成的函数，而是多个阶段组成：

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

用户可能在任意阶段取消。

所以 workflow 需要在阶段之间检查，而不是只在开始检查一次。

## 5. 当前测试覆盖

测试用例：

```text
test_cancelled_research_run_does_not_complete_or_write_report
```

验证内容：

- 创建 run。
- 立即取消。
- 等待一小段时间。
- run 最终仍然是 `cancelled`。
- `outputs/report.md` 没有生成。

## 6. 面试怎么讲

可以这样说：

> 取消长任务不能只在 API 层改状态，因为后台 workflow 可能已经在运行。我在 workflow 阶段之间增加了取消检查，如果 run 已经是 cancelled，就抛出内部异常停止后续流程，避免继续写 report 或把状态覆盖成 completed。测试里也覆盖了取消后不会生成报告产物。
