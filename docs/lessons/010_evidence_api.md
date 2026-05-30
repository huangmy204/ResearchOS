# 第 010 课：Evidence API

## 1. 为什么需要 Evidence API

Artifact 是底层产物文件。

Evidence API 是面向前端、调试和面试演示的读取接口。

区别：

```text
artifact: 文件路径和文件内容
evidence api: 结构化证据链
```

如果只通过 artifact 读取，调用方必须知道很多内部路径。

Evidence API 把常用证据结构聚合成一个响应。

## 2. 当前新增接口

完整证据包：

```text
GET /v1/research-runs/{run_id}/evidence
```

只看证据图：

```text
GET /v1/research-runs/{run_id}/evidence/graph
```

## 3. Evidence Bundle 包含什么

```text
sources
evidence
claims
citation_verification
evidence_graph
```

它表达的是：

```text
Source
  -> Evidence
  -> Claim
  -> CitationVerification
  -> EvidenceGraph
```

## 4. 为什么仍然保留 artifact

Evidence API 不替代 artifact。

两者关系：

```text
workflow 写 artifact
api 从 artifact 读取并校验结构
client 获取结构化响应
```

这样做的好处：

- artifact 可以长期保存。
- API 可以提供更友好的读取方式。
- 后续前端不用关心内部文件路径。

## 5. 面试怎么讲

可以这样说：

> RAG 检索出来的 evidence 不应该只藏在文件里，所以我加了 Evidence API。底层仍然把 sources、evidence、claims、citation verification 和 evidence graph 作为 artifacts 保存；API 层读取这些 artifact，校验成 Pydantic 模型，再返回结构化证据包。这样前端、调试和面试演示都能直接看到证据链。
