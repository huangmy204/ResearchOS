# 第 024 课：WorkflowEngine 抽象

## 1. 这一阶段新增了什么

新增文件：

```text
src/researchos/runtime/engine.py
```

核心对象：

```text
WorkflowEngine
SequentialWorkflowEngine
```

上一阶段我们已经把 workflow 拆成了节点：

```text
PlanningNode
RetrievalNode
VerificationNode
ReportWritingNode
...
```

这一阶段进一步把“如何执行这些节点”抽出来。

## 2. WorkflowNode 和 WorkflowEngine 的区别

| 概念 | 职责 |
| --- | --- |
| WorkflowNode | 单个节点做什么 |
| WorkflowEngine | 节点按什么规则执行 |

例如：

```text
VerificationNode
  负责判断 claim 是否被 evidence 支持

SequentialWorkflowEngine
  负责按顺序执行所有节点
  负责更新 run 状态
  负责写事件
  负责写 workflow trace
  负责处理取消检查
```

## 3. 为什么要抽 WorkflowEngine

如果不抽 engine，`ResearchWorkflow` 会同时负责：

- 组装节点。
- 执行节点。
- 更新状态。
- 写事件。
- 写 trace。
- 处理取消。
- 处理失败。

这会让它重新变成一个大类。

抽出 engine 后：

```text
ResearchWorkflow
  -> 负责组织业务依赖和完成/失败收尾

WorkflowEngine
  -> 负责执行节点
```

职责更清楚。

## 4. 和 LangGraph 的关系

当前 engine 是：

```text
SequentialWorkflowEngine
```

也就是顺序执行。

未来可以新增：

```text
LangGraphWorkflowEngine
```

理论上 `ResearchWorkflow` 不需要重写整体逻辑，只要替换 engine：

```text
SequentialWorkflowEngine
  -> LangGraphWorkflowEngine
```

这就是这一步的核心价值：先定义替换点，再接复杂框架。

## 5. 面试怎么讲

可以这样说：

> 我没有急着把 workflow 全部迁到 LangGraph，而是先抽出 WorkflowEngine。节点本身只描述单步业务逻辑，engine 负责节点执行策略、状态更新、事件写入、trace 写入和取消检查。当前实现是 SequentialWorkflowEngine，后续可以替换成 LangGraphWorkflowEngine。这样能先稳定业务边界，再引入图编排框架。

这段回答能体现：

- 你知道框架接入前要先抽象边界。
- 你理解节点逻辑和执行策略应该分离。
- 你不是为了用 LangGraph 而用 LangGraph。
- 你在为后续扩展做工程铺垫。
