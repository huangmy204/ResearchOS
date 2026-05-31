# 040 Corpus 写入 API

## 这一步解决什么问题

上一阶段我们只能让系统从 `workspace/corpus` 目录读取文件。这样虽然工程上可行，但使用时不直观：你需要手动进文件夹创建 `.md` 或 `.txt`。

这一步新增 Corpus 写入 API，让资料可以通过 HTTP 进入系统。

## 新增接口

```text
POST /v1/corpus/documents
```

创建一篇本地语料。

请求示例：

```json
{
  "path": "legal/citation-risk.md",
  "title": "Legal Citation Risk",
  "text": "Unsupported citations create legal research risk.",
  "overwrite": false
}
```

如果不传 `path`，系统会根据 title 生成文件名，例如：

```text
Legal Citation Risk -> legal-citation-risk.md
```

```text
GET /v1/corpus/content?path=legal/citation-risk.md
```

查看某篇语料正文。

```text
GET /v1/corpus
```

列出当前语料库文件。

## 当前完整使用顺序

```text
1. POST /v1/corpus/documents
   把资料写进本地 corpus

2. GET /v1/corpus
   确认系统能看到资料

3. GET /v1/corpus/content?path=...
   查看单篇资料内容

4. POST /v1/research-runs
   options.include_corpus=true
   启动一次基于 corpus 的研究
```

## 为什么这不是“上传文件功能”

当前接口是最小语料写入，不是完整文件上传系统。

它只处理结构化文本：

- title
- text
- path

真正的文件上传还会涉及：

- multipart form
- PDF/Word 解析
- 文件大小限制
- 病毒扫描
- OCR
- 异步解析任务

所以当前设计更适合 MVP：先把“语料进入检索系统”的链路跑通。

## 路径安全

所有 path 都必须是 corpus 根目录下的相对路径。

允许：

```text
legal/citation-risk.md
```

拒绝：

```text
../secret.txt
/absolute/path.txt
```

这是检索系统里非常重要的安全边界：API 不能让用户读写 corpus 目录之外的文件。

## 面试表达

可以这样说：

“我把 corpus 管理和 research run 分开了。Corpus API 负责写入、列出和读取本地语料；Research Run API 只负责启动一次研究。当 run 设置 `include_corpus=true` 时，系统把 corpus 文件加载成 `ResearchDocument`，再进入 RAG workflow。这样数据接入层和检索生成层是解耦的，后续接文件上传、PDF 解析或外部专业数据库时，不需要改主 workflow。”
