# 第 021 课：把研究计划接入 LLM Planner

## 1. 这一阶段新增了什么

新增模块：

```text
src/researchos/planning/
```

核心类：

```text
StaticResearchPlanner
LLMResearchPlanner
```

workflow 现在不再写死 plan，而是调用：

```text
research_planner.plan(run)
```

生成的计划会保存为 artifact：

```text
plans/research_plan.json
```

## 2. Planner 在 Agent 项目里做什么

Planner 的职责是把用户问题拆成可执行步骤。

例如：

```text
用户问题：
legal research citation risk

Planner 输出：
1. 明确问题范围
2. 检索或读取相关资料
3. 抽取证据
4. 校验证据是否支持结论
5. 写报告
```

它不应该直接写最终答案，也不应该替代 evidence verifier。

## 3. 为什么 Planner 也要结构化输出

如果 Planner 只输出自然语言：

```text
先查资料，再分析，然后写报告。
```

程序很难知道：

- 哪一步由哪个 agent 执行。
- 每一步的目标是什么。
- 每一步应该产出什么。

所以当前要求 LLM 返回 JSON：

```json
{
  "steps": [
    {
      "step_id": "step_001",
      "goal": "Clarify the research question",
      "agent": "planner",
      "expected_output": "research plan"
    }
  ]
}
```

## 4. 当前和 LangGraph 的关系

现在的 planner 已经生成结构化步骤，但 workflow 还没有真正按 plan 动态调度节点。

也就是说，当前状态是：

```text
LLM Planner 生成计划
固定 workflow 执行 MVP 链路
```

下一步接 LangGraph 后，plan 可以进一步影响节点编排。

先做 planner 的价值是：让系统先拥有“计划产物”，后面再把计划接入图执行。

## 5. Fallback 设计

LLM planner 可能失败：

- 模型超时。
- 返回了坏 JSON。
- 缺少 steps。
- step 字段不完整。

所以当前设计：

```text
LLMResearchPlanner
  -> 尝试调用 LLM
  -> 尝试解析 PlanDraft
  -> 成功：使用 LLM plan
  -> 失败：回退到 StaticResearchPlanner
```

如果 fallback，第一步里会带：

```text
planner_fallback_reason
```

方便调试。

## 6. 当前完整 demo 链路

现在 research run 已经包含三个 LLM 增强节点：

```text
LLM Planner
  -> local retrieval
  -> evidence / claim
  -> LLM Verifier
  -> LLM Writer
  -> artifacts
```

虽然还没上 LangGraph，但已经是一个实际可跑的 Agent MVP。

## 7. 面试怎么讲

可以这样说：

> 我把 planner 从 workflow 中拆成 ResearchPlanner 接口。默认 StaticResearchPlanner 保证本地稳定；配置真实模型后，LLMResearchPlanner 会根据 query 和本地文档标题生成结构化 plan，并保存为 plans/research_plan.json。当前 workflow 还没有完全动态执行 plan，但这个设计先把计划产物和执行链路解耦，为后续接 LangGraph 做准备。

这段回答能体现：

- 你知道 Agent 需要计划层。
- 你知道 LLM 输出要结构化。
- 你没有让 workflow 和模型调用强耦合。
- 你理解现在 MVP 和后续 LangGraph 之间的演进关系。
