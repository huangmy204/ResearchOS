# 第 025 课：最小 LangGraph WorkflowEngine

## 1. 这一阶段新增了什么

新增：

```text
LangGraphWorkflowEngine
```

位置：

```text
src/researchos/runtime/engine.py
```

它把现有节点映射成 LangGraph 的顺序图：

```text
START
  -> planning
  -> retrieval
  -> reading
  -> evidence_extraction
  -> verification
  -> report_writing
  -> evaluation
  -> END
```

## 2. 为什么先做最小版本

LangGraph 可以做复杂图编排，比如：

- 条件分支。
- 循环反思。
- 多 Agent 路由。
- 人工中断。
- checkpoint。

但如果一开始就全部上，会很难判断问题来自哪里。

所以当前只做一件事：

```text
用 LangGraph 跑通和 SequentialWorkflowEngine 一样的节点顺序。
```

先保证行为一致，再逐步加复杂能力。

## 3. 当前为什么不切默认 engine

默认 engine 仍然是：

```text
SequentialWorkflowEngine
```

原因：

- 它已经被完整集成测试覆盖。
- 当前 LangGraph engine 还只是最小兼容层。
- 先保留稳定默认路径，降低引入框架后的风险。

下一步可以做配置开关：

```text
RESEARCHOS_WORKFLOW_ENGINE=sequential|langgraph
```

这样本地可以切 LangGraph，测试和演示也更清楚。

## 4. 面试怎么讲

可以这样说：

> 我没有直接把整个 workflow 改成复杂 LangGraph，而是先抽象 WorkflowEngine，再实现一个最小 LangGraphWorkflowEngine。这个 engine 把已有 WorkflowNode 顺序映射到 LangGraph 的 StateGraph，保证输出 trace 和状态更新逻辑与顺序引擎一致。这样做的好处是迁移风险低，后续再引入条件边、循环和 checkpoint 时，有稳定基线可以对照。

这个回答体现：

- 你知道 LangGraph 的价值。
- 你知道框架迁移要分阶段。
- 你能先保持行为一致，再扩展复杂能力。
- 你理解 graph node 和业务 node 的映射关系。
