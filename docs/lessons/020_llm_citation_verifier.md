# 第 020 课：把引用校验接入 LLM Verifier

## 1. 这一阶段新增了什么

新增模块：

```text
src/researchos/verification/
```

核心类：

```text
RuleBasedCitationVerifier
LLMCitationVerifier
```

workflow 现在不再直接在内部构造 `CitationVerification`，而是调用：

```text
citation_verifier.verify(...)
```

这让 citation verification 变成一个可替换节点。

## 2. Verifier 和 Writer 的区别

| 节点 | 主要目标 | 输出 |
| --- | --- | --- |
| Writer | 把证据和结论写成报告 | Markdown / report JSON |
| Verifier | 判断 claim 是否被 evidence 支持 | 结构化 verification |

Writer 可以生成自然语言。

Verifier 更适合输出结构化 JSON，因为系统后面要依赖它的字段做判断。

## 3. 为什么 verifier 要返回 JSON

LLM 如果返回一段自然语言，比如：

```text
这个证据大体支持该说法，但还需要更多上下文。
```

人能看懂，但程序不好稳定解析。

所以当前 prompt 要求模型返回：

```json
{
  "support_status": "supported",
  "rationale": "short reason",
  "confidence": 0.91
}
```

这样代码可以把它转换成：

```text
CitationVerification
```

## 4. 支持状态有哪些

当前允许：

```text
supported
partially_supported
unsupported
contradicted
not_enough_information
```

这些状态比简单的 true/false 更适合 RAG。

原因是证据和 claim 的关系经常不是二元的：

| 状态 | 含义 |
| --- | --- |
| supported | 证据直接支持 claim |
| partially_supported | 证据支持一部分，但不完整 |
| unsupported | 证据没有支持 claim |
| contradicted | 证据和 claim 冲突 |
| not_enough_information | 证据不足，无法判断 |

## 5. 当前 fallback 设计

LLM verifier 可能失败：

- API key 错误。
- 模型服务超时。
- 返回内容不是 JSON。
- 返回了非法状态。

所以当前设计是：

```text
LLMCitationVerifier
  -> 尝试调用 LLM
  -> 尝试解析 JSON
  -> 成功：生成 LLM verification
  -> 失败：回退到 RuleBasedCitationVerifier
```

如果是 LLM 成功生成，`verification_id` 会类似：

```text
ver_local_001_llm
```

如果 fallback，则仍然类似：

```text
ver_local_001
```

并且 rationale 里会带上 fallback 原因。

## 6. 当前代码链路

```text
ResearchWorkflow.run()
  -> retrieve top chunk
  -> build source
  -> build evidence
  -> build claim
  -> citation_verifier.verify(...)
  -> write evidence/citation_verification.json
  -> report_writer.write(...)
```

注意：报告 writer 使用的是 verifier 的结果。

也就是说 verifier 的判断会影响报告里的 `Claim Verification`。

## 7. 面试怎么讲

可以这样说：

> 我把 citation verification 从 workflow 里拆成了 CitationVerifier 接口。默认规则版 verifier 保证本地测试稳定；配置真实 LLM 后，会使用 LLMCitationVerifier，让模型判断 claim 是否被 evidence 支持。为了让结果可被程序消费，我要求 LLM 返回固定 JSON，包括 support_status、rationale 和 confidence。如果模型失败或返回格式错误，系统会 fallback 到规则版 verifier，保证 run 不会因为外部模型失败而中断。

这段话可以体现：

- 你知道 LLM 输出不能无约束。
- 你知道 Agent 节点要有结构化契约。
- 你考虑了外部依赖失败。
- 你把 workflow 和具体模型调用解耦了。
