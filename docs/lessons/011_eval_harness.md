# 第 011 课：Evaluation Harness

## 1. 为什么 Agent 项目需要评测

Agent 项目不能只靠人工看报告。

原因：

- prompt 改动可能让结果变差。
- 检索策略改动可能找错证据。
- 模型升级可能带来行为变化。
- 没有评测就很难发现回归。

Evaluation Harness 的作用是把“这个系统表现好不好”变成可重复运行的检查。

## 2. 当前最小评测流程

命令：

```powershell
.\.venv\Scripts\python.exe -m researchos.evals.harness --dataset evals/datasets/smoke_cases.jsonl
```

流程：

```text
读取 JSONL dataset
  -> 每条 case 创建 research run
  -> 执行 workflow
  -> 读取 sources / claims / citations / report
  -> 计算 metrics
  -> 写 eval report
```

## 3. Dataset 格式

一行一个 case：

```json
{
  "case_id": "smoke_local_rag_001",
  "query": "legal research citation risk",
  "documents": [],
  "expected_source_keywords": ["Legal AI memo"],
  "expected_report_sections": ["Summary", "Evidence"]
}
```

## 4. 当前指标

质量指标：

- `retrieval_recall`
- `citation_precision`
- `claim_support_rate`
- `report_completeness`
- `tool_success_rate`

观测指标：

- `latency_sec`
- `estimated_cost`

pass/fail 只看质量指标。

原因：`latency_sec=0`、`estimated_cost=0` 不代表质量差，它们和质量指标不是同一个方向。

## 5. 面试怎么讲

可以这样说：

> 我给项目加了一个最小 Evaluation Harness。它读取 JSONL 数据集，每个 case 自动创建 research run，跑完整 workflow，然后读取 artifacts 来计算 retrieval recall、citation precision、claim support rate 和 report completeness。这样后续改 retrieval、prompt、模型或 workflow 时，可以用同一批 case 做回归检查。
