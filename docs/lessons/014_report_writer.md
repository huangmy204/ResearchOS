# 第 014 课：ReportWriter 抽象

## 1. 为什么要拆 ReportWriter

workflow 不应该负责写报告细节。

workflow 的职责是：

```text
规划阶段
检索阶段
证据阶段
验证阶段
写作阶段
完成阶段
```

ReportWriter 的职责是：

```text
把 source/evidence/claim/citation 组织成报告
```

拆开后，workflow 更像调度器，writer 更像可替换能力模块。

## 2. 当前报告产物

当前 writer 生成三类 artifact：

```text
outputs/report.md
outputs/report.json
outputs/executive_summary.md
```

区别：

- `report.md`：给人看，适合面试展示。
- `report.json`：给程序读，适合前端、评测、自动化。
- `executive_summary.md`：摘要产物。

## 3. 为什么需要 markdown 和 JSON 两份

Markdown 适合阅读：

```text
Summary
Evidence
Claim Verification
Limitations
```

JSON 适合结构化处理：

```text
sources
evidence
claims
citations
limitations
```

Agent 项目通常需要两者：

- 人类看报告。
- 系统继续处理结构化结果。

## 4. Citation 在报告里的作用

当前 markdown 会写：

```text
Citation: `source_id:evidence_id`
```

这不是最终引用格式，但它表达了关键关系：

```text
Claim
  -> Evidence
  -> Source
```

面试里要强调：

> 报告不是直接生成自然语言，而是从 evidence graph 中取 source、evidence、claim、verification 组装出来。

## 5. 后续怎么扩展

当前实现：

```text
EvidenceReportWriter
```

后续可以新增：

```text
LLMReportWriter
CitationRichReportWriter
LongFormReportWriter
```

只要它们实现同一个 `ReportWriter` 接口，workflow 就不用大改。

## 6. 面试怎么讲

可以这样说：

> 我把报告生成从 workflow 里拆成了 ReportWriter。workflow 只负责推进状态和准备 verified evidence，writer 负责把 source、evidence、claim 和 citation verification 组织成 markdown 和 JSON 两类报告产物。这样后续替换成 LLM writer 或更复杂的 citation writer 时，不需要重写主流程。
