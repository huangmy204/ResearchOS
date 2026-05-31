# 第 026 课：通过配置切换 Workflow Engine

## 1. 本课解决什么问题

上一课只是实现了 `LangGraphWorkflowEngine`，但主系统默认还不会使用它。

本课把 engine 选择权放到配置里：

```env
RESEARCHOS_WORKFLOW_ENGINE=sequential
RESEARCHOS_WORKFLOW_ENGINE=langgraph
```

这意味着同一套 API、Store、Artifact 和测试链路，可以切换不同的 workflow 执行策略。

## 2. 为什么要放在配置层

如果把 engine 写死在代码里，每次切换都要改源码。

配置化以后：

- 本地开发可以默认走 `sequential`，稳定、容易调试。
- 演示 LangGraph 时可以切到 `langgraph`。
- 测试可以分别覆盖两种执行器。
- 未来部署时可以按环境启用不同执行策略。

这是一种常见工程做法：业务代码不关心具体实现，启动时由配置决定依赖对象。

## 3. 代码结构

配置入口：

```text
src/researchos/config.py
```

新增字段：

```text
Settings.workflow_engine
```

服务组装入口：

```text
src/researchos/api/services.py
```

新增函数：

```text
build_workflow_engine(...)
```

它根据 `settings.workflow_engine` 返回：

```text
sequential -> SequentialWorkflowEngine
langgraph  -> LangGraphWorkflowEngine
```

然后传给：

```text
ResearchWorkflow(..., engine=workflow_engine)
```

## 4. 这和依赖注入有什么关系

`ResearchWorkflow` 不自己决定用哪种 engine，而是接收外部传入的 engine。

这就是依赖注入的核心思想：

```text
对象需要什么能力，由外部组装后传进去。
```

好处是：

- 更容易测试。
- 更容易替换实现。
- 主业务逻辑不被框架选择污染。

## 5. 为什么还保留 sequential 默认值

`SequentialWorkflowEngine` 是当前最稳定的执行路径。

`LangGraphWorkflowEngine` 现在已经能跑完整链路，但它目前还是顺序图：

```text
START -> planning -> retrieval -> reading -> evidence_extraction -> verification -> report_writing -> evaluation -> END
```

所以当前策略是：

```text
默认稳定，配置启用 LangGraph。
```

等后续加入条件边、循环、checkpoint 后，再考虑是否把 LangGraph 设为默认。

## 6. 面试怎么说

可以这样回答：

> 我把 workflow engine 做成可配置项，而不是把 LangGraph 直接写死到业务流程里。启动时 `build_services` 会读取 `RESEARCHOS_WORKFLOW_ENGINE`，再注入 `SequentialWorkflowEngine` 或 `LangGraphWorkflowEngine`。这样主 workflow 只依赖 `WorkflowEngine` 抽象，不关心底层是普通顺序执行还是 LangGraph 图执行。这个设计降低了迁移风险，也方便测试和灰度切换。

这个回答体现三点：

- 你理解依赖注入。
- 你知道框架迁移要保留稳定回退路径。
- 你能把 LangGraph 接入讲成工程设计，而不是简单“用了一个库”。
