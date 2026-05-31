# 第 008 课：如何自己运行和测试 ResearchOS

## 1. 安装开发依赖

在项目根目录运行：

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

如果遇到 SSL 问题，可以用：

```powershell
.\.venv\Scripts\python.exe -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -e ".[dev]"
```

## 2. 跑自动化测试

```powershell
.\.venv\Scripts\python.exe -m pytest tests -v
```

当前期望结果：

```text
7 passed
```

## 3. 跑静态检查

```powershell
.\.venv\Scripts\python.exe -m ruff check src tests
```

当前期望结果：

```text
All checks passed!
```

## 4. 启动本地 API 服务

```powershell
.\.venv\Scripts\python.exe -m researchos.api.main
```

默认地址：

```text
http://localhost:8000
```

常用页面：

```text
http://localhost:8000/docs
http://localhost:8000/healthz
http://localhost:8000/readyz
http://localhost:8000/metricsz
```

停止服务：

```text
Ctrl + C
```

## 5. 手动创建一个 run

另开一个 PowerShell 窗口：

```powershell
$body = @{
  tenant_id = "tenant"
  user_id = "user"
  session_id = "manual"
  request_id = "manual-001"
  query = "Analyze AI agents for legal research."
} | ConvertTo-Json

$result = Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/v1/research-runs" `
  -ContentType "application/json" `
  -Body $body

$result
```

重点看返回里的：

```text
run_id
events_url
artifacts_url
```

## 6. 查询 run 状态

```powershell
$runId = $result.run_id
Invoke-RestMethod "http://localhost:8000/v1/research-runs/$runId"
```

如果 workflow 已完成，状态应该是：

```text
completed
```

## 7. 列出所有 runs

```powershell
Invoke-RestMethod "http://localhost:8000/v1/research-runs"
```

这个接口适合手动测试，因为你不需要记住所有 `run_id`。

## 8. 查看事件历史

```powershell
Invoke-RestMethod "http://localhost:8000/v1/research-runs/$runId/events/history"
```

你应该能看到类似事件：

```text
run.created
plan.created
source.retrieved
evidence.extracted
claim.verified
report.completed
```

这个接口返回的是普通 JSON，比 SSE 更适合初学阶段调试。

## 9. 查看 artifacts

列出 artifacts：

```powershell
Invoke-RestMethod "http://localhost:8000/v1/research-runs/$runId/artifacts"
```

读取报告：

```powershell
Invoke-RestMethod "http://localhost:8000/v1/research-runs/$runId/artifacts/content?path=outputs/report.md"
```

读取证据图：

```powershell
Invoke-RestMethod "http://localhost:8000/v1/research-runs/$runId/artifacts/content?path=evidence/evidence_graph.json"
```

## 10. 测试幂等创建

再次发送同一个 `request_id`：

```powershell
$second = Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/v1/research-runs" `
  -ContentType "application/json" `
  -Body $body

$second.run_id
$result.run_id
```

两个 `run_id` 应该一样。

## 11. 测试取消 run

创建一个新 run，马上取消：

```powershell
$cancelBody = @{
  session_id = "manual-cancel"
  query = "cancel this run"
} | ConvertTo-Json

$cancelRun = Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/v1/research-runs" `
  -ContentType "application/json" `
  -Body $cancelBody

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/v1/research-runs/$($cancelRun.run_id)/cancel"
```

再查状态：

```powershell
Invoke-RestMethod "http://localhost:8000/v1/research-runs/$($cancelRun.run_id)"
```

状态应该是：

```text
cancelled
```

## 12. 当前新增的调试接口

```text
GET /v1/research-runs
GET /v1/research-runs/{run_id}/events/history
```

这两个接口主要用于学习和调试：

- 第一个看当前系统有哪些任务。
- 第二个看某个任务到底发生过哪些事件。

## 13. 手动测试本地 RAG

创建一个带 `documents` 的 run：

```powershell
$ragBody = @{
  session_id = "manual-rag"
  query = "legal research citation risk"
  documents = @(
    @{
      title = "Legal AI memo"
      text = "AI agents can reduce legal research time by searching cases. A key risk is hallucinated citations that are not supported by evidence."
    },
    @{
      title = "Cooking note"
      text = "Sourdough bread needs flour, water, salt, and patient fermentation."
    }
  )
} | ConvertTo-Json -Depth 5

$ragRun = Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/v1/research-runs" `
  -ContentType "application/json" `
  -Body $ragBody

$ragRun
```

查看检索结果：

```powershell
Invoke-RestMethod "http://localhost:8000/v1/research-runs/$($ragRun.run_id)/artifacts/content?path=sources/parsed/retrieval_results.json"
```

查看 evidence：

```powershell
Invoke-RestMethod "http://localhost:8000/v1/research-runs/$($ragRun.run_id)/artifacts/content?path=evidence/evidence.json"
```

你应该看到系统选择了 `Legal AI memo`，而不是 `Cooking note`。

查看结构化报告 JSON：

```powershell
Invoke-RestMethod "http://localhost:8000/v1/research-runs/$($ragRun.run_id)/artifacts/content?path=outputs/report.json"
```

重点看：

```text
sources
evidence
claims
citations
limitations
```

### 切换 BM25 检索

默认策略是：

```text
RESEARCHOS_RETRIEVAL_STRATEGY=keyword
```

如果想测试 BM25：

```powershell
$env:RESEARCHOS_RETRIEVAL_STRATEGY = "bm25"
.\.venv\Scripts\python.exe -m researchos.api.main
```

再按上面的 RAG 请求创建 run。

测试完可以清掉当前 PowerShell 会话里的环境变量：

```powershell
Remove-Item Env:RESEARCHOS_RETRIEVAL_STRATEGY
```

## 14. 查看正式 Evidence API

查看完整证据包：

```powershell
Invoke-RestMethod "http://localhost:8000/v1/research-runs/$($ragRun.run_id)/evidence"
```

这个接口一次返回：

```text
sources
evidence
claims
citation_verification
evidence_graph
```

只查看证据图：

```powershell
Invoke-RestMethod "http://localhost:8000/v1/research-runs/$($ragRun.run_id)/evidence/graph"
```

如果你想看 RAG 有没有真正命中资料，优先看：

```text
sources[0].title
evidence[0].text
claims[0].evidence_ids
citation_verification[0].support_status
```

## 15. 运行 Eval Harness

运行内置 smoke dataset：

```powershell
.\.venv\Scripts\python.exe -m researchos.evals.harness --dataset evals/datasets/smoke_cases.jsonl
```

运行后会生成：

```text
evals/reports/smoke_cases_latest.json
```

这个报告会包含：

```text
case_count
pass_count
avg_metrics
results
```

当前最小 eval 会检查：

- retrieval_recall
- citation_precision
- claim_support_rate
- report_completeness
- tool_success_rate

`latency_sec` 和 `estimated_cost` 会记录，但不会直接决定 pass/fail。

## 16. 查看 Model Router 配置

接口：

```powershell
Invoke-RestMethod "http://localhost:8000/v1/models"
```

默认情况下，如果没有配置模型，会看到：

```text
configured = false
provider = unconfigured
```

你可以临时设置环境变量再启动服务：

```powershell
$env:BASIC_MODEL = "fast-model"
$env:REASONING_MODEL = "reasoning-model"
$env:WRITER_MODEL = "writer-model"
$env:VERIFIER_MODEL = "verifier-model"
.\.venv\Scripts\python.exe -m researchos.api.main
```

角色含义：

```text
basic     通用快速模型
planner   规划模型
searcher  检索相关模型，当前走 basic
reader    阅读相关模型，当前走 basic
writer    报告写作模型
verifier  引用校验模型
reviewer  评审模型，当前走 reasoning
```

## 17. 手动测试 Mock LLM Client

这个接口用于验证“模型路由 -> LLM Client -> 响应结构”的链路，但不会真的调用外部大模型。

```powershell
$llmBody = @{
  role = "writer"
  prompt = "Write a short report about citation risk."
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/v1/models/dry-run" `
  -ContentType "application/json" `
  -Body $llmBody
```

重点看这些字段：

```text
profile.role
profile.model
response.content
response.dry_run
response.total_tokens
```

当前 `response.dry_run = true`，表示这是模拟调用。后续接入真实 LLM 后，这个接口可以继续用来调试 prompt、模型选择和 token 统计。

## 18. 手动测试真实 OpenAI-compatible LLM

先在当前 PowerShell 窗口临时配置：

```powershell
$env:RESEARCHOS_LLM_CLIENT = "openai_compatible"
$env:RESEARCHOS_LLM_API_KEY = "你的 API key"
$env:WRITER_MODEL = "你的模型名"
$env:WRITER_BASE_URL = "https://api.openai.com/v1"
```

启动服务：

```powershell
.\.venv\Scripts\python.exe -m researchos.api.main
```

另开一个 PowerShell 窗口请求：

```powershell
$completeBody = @{
  role = "writer"
  prompt = "Write a short report about citation risk."
  temperature = 0
  max_tokens = 256
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/v1/models/complete" `
  -ContentType "application/json" `
  -Body $completeBody
```

如果配置正确，应该看到：

```text
response.dry_run = false
response.content = 真实模型返回的文本
```

如果你没有配置 `RESEARCHOS_LLM_CLIENT=openai_compatible`，这个接口会继续走 mock client，`response.dry_run` 会是 `true`。

## 19. 手动测试 LLM Report Writer

在 `.env` 已经配置好阿里云百炼后，启动服务：

```powershell
.\.venv\Scripts\python.exe -m researchos.api.main
```

创建一个带本地文档的 research run：

```powershell
$llmRunBody = @{
  session_id = "manual-llm-writer"
  query = "legal research citation risk"
  documents = @(
    @{
      title = "Legal AI memo"
      text = "Unsupported citations create legal research risk. Legal research assistants need citation verification."
    }
  )
} | ConvertTo-Json -Depth 5

$llmRun = Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/v1/research-runs" `
  -ContentType "application/json" `
  -Body $llmRunBody
```

等待几秒后查看报告：

```powershell
Invoke-RestMethod "http://localhost:8000/v1/research-runs/$($llmRun.run_id)/artifacts/content?path=outputs/report.md"
```

查看结构化报告：

```powershell
Invoke-RestMethod "http://localhost:8000/v1/research-runs/$($llmRun.run_id)/artifacts/content?path=outputs/report.json"
```

重点看：

```text
generation.mode
generation.model
generation.dry_run
generation.total_tokens
```

如果真实 LLM 成功参与报告生成，应看到：

```text
generation.mode = llm
generation.dry_run = false
```

## 20. 手动检查 LLM Citation Verifier

当 `.env` 中配置了：

```text
RESEARCHOS_LLM_CLIENT=openai_compatible
VERIFIER_MODEL=qwen-plus
VERIFIER_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

完整 research run 会在 claim verification 阶段调用 LLM verifier。

查看校验结果：

```powershell
Invoke-RestMethod "http://localhost:8000/v1/research-runs/$($llmRun.run_id)/artifacts/content?path=evidence/citation_verification.json"
```

如果 LLM verifier 成功，通常会看到：

```text
verification_id = ver_local_001_llm
support_status = supported / partially_supported / unsupported / contradicted / not_enough_information
rationale = LLM 返回的判断理由
```

如果 LLM verifier 失败，系统会回退到规则版 verifier，`verification_id` 通常不带 `_llm`，并且 `rationale` 里会记录 fallback 原因。

## 21. 手动检查 LLM Research Planner

当 `.env` 中配置了：

```text
RESEARCHOS_LLM_CLIENT=openai_compatible
REASONING_MODEL=qwen-plus
REASONING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

完整 research run 会在 planning 阶段调用 LLM planner。

查看计划 artifact：

```powershell
Invoke-RestMethod "http://localhost:8000/v1/research-runs/$($llmRun.run_id)/artifacts/content?path=plans/research_plan.json"
```

如果 LLM planner 成功，你会看到模型生成的步骤：

```text
step_id
goal
agent
expected_output
```

如果失败，系统会回退到静态计划，并在第一步中写入：

```text
planner_fallback_reason
```

## 22. 查看节点化 Workflow Trace

完整 run 完成后，可以查看节点执行轨迹：

```powershell
Invoke-RestMethod "http://localhost:8000/v1/research-runs/$($llmRun.run_id)/artifacts/content?path=traces/workflow_trace.json"
```

重点看：

```text
nodes[].node
nodes[].duration_ms
nodes[].event_type
nodes[].artifacts
```

当前节点顺序是：

```text
planning
retrieval
reading
evidence_extraction
verification
report_writing
evaluation
completion
```

这份 trace 可以帮助你在面试里解释：一个 research run 不是一段黑盒文本生成，而是多个可追踪节点串起来的流程。

也可以使用正式 Trace API：

```powershell
Invoke-RestMethod "http://localhost:8000/v1/research-runs/$($llmRun.run_id)/trace"
```

这个接口会额外返回 `summary`，更适合前端和演示。
