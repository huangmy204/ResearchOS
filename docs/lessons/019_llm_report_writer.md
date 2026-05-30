# 第 019 课：把报告生成接入 LLM Writer

## 1. 这一阶段新增了什么

之前的 research run 报告由规则版 `EvidenceReportWriter` 生成。

现在新增：

```text
LLMReportWriter
```

位置：

```text
src/researchos/reporting/writer.py
```

当配置为：

```text
RESEARCHOS_LLM_CLIENT=openai_compatible
```

workflow 会优先使用真实 LLM 生成报告。

默认 mock 模式下仍然使用规则版 writer，所以没有 API key 的环境也能稳定运行测试。

## 2. 为什么不是直接替换掉规则版 writer

真实 LLM 是外部依赖，可能出现：

| 问题 | 例子 |
| --- | --- |
| 配置错误 | API key 填错、模型名不存在 |
| 网络失败 | 超时、连接失败 |
| 供应商失败 | 429 限流、5xx 错误 |
| 输出不稳定 | 格式不完全符合预期 |

如果把规则版 writer 完全删掉，那么模型一失败，整个 research run 就会失败。

所以当前设计是：

```text
LLMReportWriter
  -> 尝试调用 LLM
  -> 成功：输出 LLM 报告
  -> 失败：回退到 EvidenceReportWriter
```

这叫 graceful fallback，面试里非常好讲。

## 3. 当前调用链

```text
ResearchWorkflow.run()
  -> 检索 evidence
  -> 构造 source / evidence / claim / verification
  -> report_writer.write(...)
       -> LLMReportWriter
          -> LLMClient.complete(...)
          -> ReportDraft
  -> 写入 outputs/report.md
  -> 写入 outputs/report.json
  -> 写入 outputs/executive_summary.md
```

注意：workflow 不需要知道底层是规则版 writer 还是真实 LLM writer。

这就是接口抽象的价值。

## 4. 怎么判断是否真的用了 LLM

查看：

```text
outputs/report.json
```

重点字段：

```text
generation.mode
generation.model
generation.provider
generation.dry_run
generation.total_tokens
```

如果真实调用成功，应该类似：

```text
generation.mode = llm
generation.dry_run = false
generation.model = qwen-plus
```

如果模型调用失败并回退，应该看到：

```text
generation.mode = fallback
generation.reason = 错误原因
```

如果是默认规则版 writer，可能没有 `generation` 字段。

## 5. 为什么 prompt 里要强调证据边界

当前 prompt 会告诉模型：

- 只基于给定 evidence 写报告。
- 不要编造 source。
- 保留指定 citation label。
- 明确写 limitation。

这是 RAG 项目的关键习惯：模型负责表达，证据负责约束。

不应该让 LLM 自己“凭感觉”补充事实。

## 6. 面试怎么讲

可以这样说：

> 报告生成节点我做成了可插拔 writer。默认使用规则版 EvidenceReportWriter，保证本地测试稳定；当配置真实 LLM 后，服务装配层会切换到 LLMReportWriter。LLMReportWriter 会把 evidence、claim、verification 组装成 prompt 调用模型，并把 token、模型名、dry_run 等信息写入 report.json。如果外部模型失败，会自动 fallback 到规则版报告，避免整个 run 失败。

这段回答能体现：

- 你理解外部 LLM 的不稳定性。
- 你会做接口抽象。
- 你知道 RAG 报告必须受证据约束。
- 你考虑了可测试性和降级策略。
