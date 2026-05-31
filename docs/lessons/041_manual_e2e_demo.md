# 041 手动跑通 Corpus 到 Research Run

## 这一步要解决什么

现在代码模块比较多，容易看乱。最好的理解方式是手动跑一次完整链路：

```text
写入资料 -> 查看资料库 -> 创建研究任务 -> 等待完成 -> 查看证据和报告
```

我新增了一个 PowerShell 脚本：

```text
scripts/demo_corpus_run.ps1
```

它会按真实 API 调用系统，不走测试 mock。

## 先启动服务

在项目根目录运行：

```powershell
.\.venv\Scripts\python.exe -m uvicorn researchos.api.main:app --reload --host 127.0.0.1 --port 8000
```

如果你已经有服务在跑，就不用重复启动。

## 再运行演示脚本

另开一个 PowerShell 窗口，运行：

```powershell
.\scripts\demo_corpus_run.ps1
```

如果服务不是 8000 端口：

```powershell
.\scripts\demo_corpus_run.ps1 -BaseUrl "http://localhost:8001"
```

## 脚本做了什么

1. 调用 `GET /readyz`
   确认 API 和 workspace 可用。

2. 调用 `POST /v1/corpus/documents`
   写入一篇 demo 语料。

3. 调用 `GET /v1/corpus`
   查看资料库列表。

4. 调用 `GET /v1/corpus/content?path=...`
   查看单篇语料正文。

5. 调用 `POST /v1/research-runs`
   创建一次研究任务，并设置：

```json
{
  "options": {
    "include_corpus": true
  }
}
```

6. 轮询 `GET /v1/research-runs/{run_id}`
   等待任务完成。

7. 查看 trace、evidence sources、report markdown。

## 当前系统主线

你可以把现在的系统理解成这张图：

```text
Corpus API
  写入和查看资料
    |
    v
Research Run API
  创建一次研究任务
    |
    v
Retrieval Node
  multi-query 检索 + rerank + quality gate
    |
    v
Evidence / Verification / Report
  证据、引用校验、报告、评测
```

## 面试表达

可以这样讲：

“为了让项目不只是测试里的 RAG demo，我做了一条手动可运行的端到端链路。用户可以通过 Corpus API 写入本地语料，再通过 Research Run API 启动研究。系统会把 corpus 加载成 `ResearchDocument`，进入多查询检索、证据提取、引用验证和报告生成。这个 demo 证明了数据接入层和研究 workflow 已经串起来了。”
