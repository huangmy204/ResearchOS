# 042 Corpus Index Manifest

## 为什么先做 manifest

很多 RAG 教程会直接跳到向量库，但真实工程里通常要先回答几个问题：

- corpus 里有哪些文件？
- 哪些文件已经被索引？
- 文件内容有没有变？
- 之后要不要重建 embedding？

所以这一步先做文件级索引清单，也就是 index manifest。

它不是向量库，而是向量库之前的账本。

## 新增接口

```text
GET /v1/corpus/index
```

读取当前索引清单。

```text
POST /v1/corpus/index
```

扫描 corpus 文件并重建索引清单。

## Manifest 里有什么

每个文件会记录：

```text
path
title
size_bytes
suffix
modified_at
content_sha256
status
```

其中最重要的是 `content_sha256`。

它是文件内容的 hash，可以用来判断文件是否变化：

```text
旧 hash == 新 hash -> 内容没变，不需要重建 embedding
旧 hash != 新 hash -> 内容变了，需要重建 embedding
```

## 当前它和向量库的关系

当前系统还没有真正持久化 embedding index。

但 manifest 已经把后续向量库需要的基础信息准备好了：

```text
corpus file
-> index manifest
-> chunk
-> embedding
-> vector index
```

后续接 Chroma、Qdrant、FAISS 或 pgvector 时，manifest 可以用来做增量索引。

## 面试表达

可以这样讲：

“我没有一开始就直接接向量库，而是先做了 corpus index manifest。它记录每个语料文件的 path、mtime、size 和 sha256。这样系统可以知道哪些文档已经被索引，哪些文档内容发生变化。后续做 embedding index 时，就可以基于 hash 做增量更新，而不是每次全量重建。”
