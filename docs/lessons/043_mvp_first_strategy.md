# 043 先做最小可运行系统

## 先回答你的问题

可以，而且应该这样做。

一个检索系统不要一开始就追求完整形态，否则很容易同时陷入：

- chunk 怎么切
- embedding 用哪个模型
- 向量库选 Chroma、Qdrant 还是 pgvector
- rerank 怎么做
- query rewrite 怎么做
- agent workflow 怎么循环
- 数据库怎么接
- 前端怎么展示

这些都重要，但它们不是第一优先级。

第一优先级是先跑通一个最小闭环。

## ResearchOS 当前 MVP 闭环

现在已经具备一个最小可运行系统：

```text
1. Corpus API 写入资料
2. Corpus API 查看资料
3. Research Run API 启动研究任务
4. Retrieval 从资料中找证据
5. Workflow 提取证据、验证、写报告
6. Artifact API 查看结果
```

这就是我们当前要守住的主线。

## 怎么启动最小系统

启动 API：

```powershell
.\scripts\start_api.ps1
```

另开一个 PowerShell，跑端到端 demo：

```powershell
.\scripts\demo_corpus_run.ps1
```

如果这两个命令能跑通，就说明最小系统是活的。

## 什么算优化细节

下面这些都属于 MVP 之后的优化：

```text
chunk index manifest
embedding 持久化
向量数据库
LLM query planner
HyDE
高级 reranker
外部专业数据库 connector
前端页面
权限系统
部署
```

它们应该围绕 MVP 逐步增加，而不是打乱 MVP。

## 面试表达

可以这样说：

“我构建这个项目时采用 MVP-first 的方式。第一阶段不是直接接复杂向量库或做完整 agent，而是先跑通 Corpus API 到 Research Run 的最小闭环：资料可以进入系统，系统可以基于资料检索证据，生成报告和评测结果。之后的 chunk index、embedding index、reranker、query planner 和 agentic workflow 都是在这个闭环上逐步增强，而不是重新推倒重来。”

## 下一步怎么走

后续每一步都要回答：

```text
它是在增强 MVP 的哪一段？
```

例如：

- chunk index：增强资料进入检索前的结构化能力。
- embedding index：增强检索召回能力。
- reranker：增强候选证据排序能力。
- query planner：增强问题到检索 query 的转换能力。
- agent workflow：增强失败后的自我修正能力。
