# 第 013 课：BM25Retriever

## 1. 为什么引入 BM25

简单关键词重合只看：

```text
query 里有多少词也出现在 chunk 里
```

这很直观，但太粗糙。

BM25 仍然是关键词检索，但它考虑更多信息：

- 词在 chunk 里出现几次。
- 词在整个语料里是否稀有。
- chunk 长度是否过长。

所以 BM25 通常比简单关键词重合更适合文本检索。

## 2. 三种检索方式对比

| 方式 | 优点 | 缺点 | 当前定位 |
|---|---|---|---|
| 简单关键词重合 | 最简单、可解释、无依赖 | 不考虑词频和稀有度 | MVP baseline |
| BM25 | 经典、稳定、仍可解释 | 不理解语义同义词 | 当前升级版 |
| Embedding + Vector DB | 能做语义相似检索 | 成本更高、依赖更多、调试更复杂 | 后续阶段 |

## 3. BM25 的直觉

BM25 会奖励：

```text
重要词出现
重要词多次出现
稀有词出现
```

同时会抑制：

```text
特别长的 chunk 靠堆词获得高分
```

这就是为什么它比简单关键词重合更稳。

## 4. 当前实现

相关文件：

```text
src/researchos/retrieval/bm25.py
```

当前实现不引入外部依赖，而是用纯 Python 写了最小 BM25。

核心参数：

```text
k1 = 1.5
b = 0.75
```

含义：

- `k1` 控制词频增长的饱和速度。
- `b` 控制文档长度归一化强度。

这两个默认值是 BM25 常见经验值。

## 5. 为什么不直接用 `rank-bm25`

可以用，但当前阶段先不用。

原因：

- 纯 Python 实现更适合学习。
- 不增加依赖。
- 方便看懂算法输入输出。
- 当前数据量很小，性能不是瓶颈。

后续如果数据量变大，可以替换成成熟库或搜索引擎。

## 6. 如何切换策略

环境变量：

```text
RESEARCHOS_RETRIEVAL_STRATEGY=keyword
RESEARCHOS_RETRIEVAL_STRATEGY=bm25
```

代码入口：

```text
build_retriever(strategy)
```

workflow 只依赖：

```python
self.retriever.retrieve(...)
```

所以替换策略不会改 workflow 主链路。

## 7. 面试怎么讲

可以这样说：

> 我先抽象了 Retriever 接口，然后实现了 keyword 和 BM25 两种本地检索策略。keyword 版本适合做 baseline，BM25 会考虑词频、逆文档频率和 chunk 长度归一化，因此比简单关键词重合更稳。通过 `RESEARCHOS_RETRIEVAL_STRATEGY` 可以切换策略，workflow 不需要知道底层检索算法。
