# 第 016 课：LLM Client 抽象与 Mock 调用

## 1. 这一阶段新增了什么

本阶段没有直接接入真实大模型，而是新增了一个 LLM Client 抽象和一个 mock 实现。

新增代码：

```text
src/researchos/llm/client.py
src/researchos/llm/mock.py
src/researchos/llm/__init__.py
```

新增接口：

```text
POST /v1/models/dry-run
```

这个接口会模拟一次模型调用，但不会访问外部网络，也不会消耗 API 费用。

## 2. 为什么先做 Mock LLM Client

真实 LLM 接入会同时引入很多变量：

| 问题 | 影响 |
| --- | --- |
| API key | 本地、CI、部署环境都要配置 |
| 网络请求 | 可能超时、限流、失败 |
| 模型差异 | 不同供应商响应格式不同 |
| 成本 | 每次调试都会花 token |
| Prompt 设计 | 输出不稳定，测试不好写 |

所以更合理的顺序是：

```text
Model Router
  -> LLM Client 抽象
  -> Mock LLM Client
  -> 真实 OpenAI-compatible Client
  -> 替换 workflow 里的 deterministic 节点
```

这不是拖慢进度，而是在给后续真实 Agent 铺一层稳定边界。

## 3. Model Router 和 LLM Client 的分工

Model Router 只回答一个问题：

```text
某个角色应该使用哪个模型配置？
```

例如：

```text
writer -> writer_model
planner -> reasoning_model
verifier -> verifier_model
```

LLM Client 负责另一个问题：

```text
拿到模型配置和 messages 后，如何完成一次模型调用？
```

所以边界是：

```text
role
  -> Model Router
  -> ModelProfile
  -> LLM Client
  -> LLMResponse
```

面试里可以这样讲：

> 我没有让 workflow 直接依赖某个具体大模型 SDK，而是先抽象出 LLM Client。Model Router 负责按 Agent 角色选择模型，LLM Client 负责执行调用。当前实现是 Mock Client，用来验证调用链、响应结构和测试稳定性。后续接 OpenAI-compatible API 时，只需要新增一个真实 client，不需要大改路由和 workflow。

## 4. 三个核心数据结构

### LLMMessage

表示一次对话消息：

```text
role: system | user | assistant
content: 消息内容
```

它和 OpenAI Chat Completions / Responses API 的消息结构类似，方便后续接真实模型。

### LLMRequest

表示一次模型调用请求：

```text
profile: ModelProfile
messages: list[LLMMessage]
temperature: float
max_tokens: int | None
```

这里不要只传一个 prompt 字符串，因为真实 Agent 通常需要 system prompt、用户问题、检索证据、历史上下文等多段消息。

### LLMResponse

表示一次模型调用结果：

```text
content: 模型输出文本
model: 实际使用的模型名
provider: 模型供应商
prompt_tokens: 输入 token 估算
completion_tokens: 输出 token 估算
total_tokens: 总 token
dry_run: 是否为模拟调用
```

`dry_run` 很重要，因为它能明确告诉调用方：这次没有真的访问 LLM。

## 5. 为什么要记录 token 字段

Agent 项目里 token 不只是账单问题，也影响系统设计：

| 维度 | 为什么重要 |
| --- | --- |
| 成本 | 每个 run 的调用成本需要可估算 |
| 上下文长度 | RAG 拼接太多证据会超过窗口 |
| 延迟 | 输入越长，模型响应越慢 |
| 策略选择 | 简单任务可以用便宜模型，复杂任务用推理模型 |

当前 mock client 只做粗略估算，真实 client 接入后会使用供应商返回的 usage 字段。

## 6. Mock、Fake、Stub 的区别

面试中如果被问到测试替身，可以这样区分：

| 类型 | 特点 | 本项目当前接近哪种 |
| --- | --- | --- |
| Stub | 返回固定结果 | 部分符合 |
| Fake | 有可运行逻辑，但不是生产实现 | 更接近 |
| Mock | 关注是否被按预期调用 | 也有一点 |

我们这里命名为 `MockLLMClient`，主要是为了表达“模拟外部 LLM 调用”。严格说，它更像一个轻量 fake：会根据 role 生成响应，并估算 token。

## 7. 手动测试命令

先启动服务：

```powershell
.\.venv\Scripts\python.exe -m researchos.api.main
```

再请求 dry-run：

```powershell
$body = @{
  role = "writer"
  prompt = "Write a short report about citation risk."
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/v1/models/dry-run" `
  -ContentType "application/json" `
  -Body $body
```

你应该看到：

```text
profile.role = writer
response.dry_run = true
response.content 以 [mock:writer] 开头
response.total_tokens > 0
```

## 8. 当前仍然没有做什么

当前还没有：

- 调用真实 LLM API。
- 设计 planner / writer / verifier 的真实 prompt。
- 把 workflow 的 deterministic report writer 替换成 LLM writer。
- 做流式模型输出。

下一步更合理的是接入 OpenAI-compatible client，但先保留 mock client 作为测试和本地开发后备方案。
