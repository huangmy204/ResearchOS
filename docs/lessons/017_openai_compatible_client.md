# 第 017 课：OpenAI-compatible LLM Client 与环境变量配置

## 1. 这一阶段新增了什么

新增真实模型调用客户端：

```text
src/researchos/llm/openai_compatible.py
```

新增接口：

```text
POST /v1/models/complete
```

保留接口：

```text
POST /v1/models/dry-run
```

区别是：

| 接口 | 是否真实调用模型 | 用途 |
| --- | --- | --- |
| `/v1/models/dry-run` | 否 | 本地学习、测试调用链 |
| `/v1/models/complete` | 取决于配置 | 真实模型调用或 mock 后备 |

默认情况下系统仍然使用 mock client，不会访问外部 API。

## 2. 为什么选择 OpenAI-compatible

很多模型服务都兼容 OpenAI 的 chat completions 风格接口：

```text
POST {base_url}/chat/completions
```

常见请求结构：

```json
{
  "model": "model-name",
  "messages": [
    {"role": "system", "content": "system prompt"},
    {"role": "user", "content": "user prompt"}
  ],
  "temperature": 0.0,
  "max_tokens": 512
}
```

这样做的好处是：

| 方案 | 优点 | 缺点 |
| --- | --- | --- |
| 直接绑定某一家 SDK | 上手快，官方能力完整 | 换供应商时代码改动大 |
| 只封装 HTTP OpenAI-compatible | 更通用，容易换 base_url | 部分供应商高级功能要单独适配 |
| 自己设计完全独立协议 | 控制力强 | 成本高，和生态脱节 |

当前项目选择第二种，因为它最适合学习和面试展示：边界清晰，可替换性强。

## 3. 需要配置哪些环境变量

真实调用至少需要：

```text
RESEARCHOS_LLM_CLIENT=openai_compatible
RESEARCHOS_LLM_API_KEY=你的 API key
WRITER_MODEL=你的模型名
WRITER_BASE_URL=https://api.openai.com/v1
```

如果你使用的是官方 OpenAI，`WRITER_BASE_URL` 可以是：

```text
https://api.openai.com/v1
```

如果你使用的是其他 OpenAI-compatible 服务，就填对应供应商给你的 base_url。

## 4. 推荐配置：项目根目录 `.env`

学习阶段最推荐在项目根目录创建 `.env`：

```powershell
Copy-Item .env.example .env
```

然后编辑 `.env`：

```text
RESEARCHOS_LLM_CLIENT=openai_compatible
RESEARCHOS_LLM_API_KEY=你的 API key
WRITER_MODEL=你的模型名
WRITER_BASE_URL=https://api.openai.com/v1
```

`.env` 不会被提交，因为它已经在 `.gitignore` 里。

## 5. PowerShell 临时配置

临时配置只在当前 PowerShell 窗口有效，关闭窗口后会失效。适合学习和测试。

```powershell
$env:RESEARCHOS_LLM_CLIENT = "openai_compatible"
$env:RESEARCHOS_LLM_API_KEY = "你的 API key"
$env:WRITER_MODEL = "你的模型名"
$env:WRITER_BASE_URL = "https://api.openai.com/v1"
```

然后启动服务：

```powershell
.\.venv\Scripts\python.exe -m researchos.api.main
```

另开一个 PowerShell 窗口请求：

```powershell
$body = @{
  role = "writer"
  prompt = "Write a short report about citation risk."
  temperature = 0
  max_tokens = 256
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/v1/models/complete" `
  -ContentType "application/json" `
  -Body $body
```

如果是真实调用，返回里应该看到：

```text
response.dry_run = false
response.total_tokens > 0
```

## 6. PowerShell 永久配置

永久配置会写入当前 Windows 用户环境变量。配置后需要重新打开 PowerShell。

```powershell
[Environment]::SetEnvironmentVariable("RESEARCHOS_LLM_CLIENT", "openai_compatible", "User")
[Environment]::SetEnvironmentVariable("RESEARCHOS_LLM_API_KEY", "你的 API key", "User")
[Environment]::SetEnvironmentVariable("WRITER_MODEL", "你的模型名", "User")
[Environment]::SetEnvironmentVariable("WRITER_BASE_URL", "https://api.openai.com/v1", "User")
```

查看是否生效：

```powershell
$env:RESEARCHOS_LLM_CLIENT
$env:WRITER_MODEL
```

不要把 API key 打印给别人看，也不要截图泄露。

## 7. 如何清除临时配置

当前 PowerShell 窗口里可以这样清除：

```powershell
Remove-Item Env:RESEARCHOS_LLM_CLIENT
Remove-Item Env:RESEARCHOS_LLM_API_KEY
Remove-Item Env:WRITER_MODEL
Remove-Item Env:WRITER_BASE_URL
```

清除永久配置：

```powershell
[Environment]::SetEnvironmentVariable("RESEARCHOS_LLM_CLIENT", $null, "User")
[Environment]::SetEnvironmentVariable("RESEARCHOS_LLM_API_KEY", $null, "User")
[Environment]::SetEnvironmentVariable("WRITER_MODEL", $null, "User")
[Environment]::SetEnvironmentVariable("WRITER_BASE_URL", $null, "User")
```

## 8. 为什么不能把 API key 写进代码

API key 是密钥，不是普通配置。

不要这样做：

```python
api_key = "sk-..."
```

原因：

| 风险 | 说明 |
| --- | --- |
| 泄露 | commit 到 GitHub 后别人可能直接看到 |
| 滥用 | 别人可以用你的 key 消耗额度 |
| 难轮换 | key 散落在代码里很难统一替换 |
| 不利部署 | 本地、测试、生产环境通常用不同 key |

正确做法是：代码读取环境变量，密钥由运行环境注入。

## 9. 面试怎么讲

可以这样说：

> 我把模型调用封装成 LLM Client，而不是在业务逻辑里直接写 HTTP 请求。Model Router 负责根据 writer、planner、verifier 等角色选择模型配置，OpenAI-compatible Client 负责把 LLMRequest 转成标准 chat completions 请求，并把供应商响应解析成统一的 LLMResponse。默认使用 Mock Client 保证本地测试稳定，只有显式配置环境变量时才会真实调用模型。

这个回答能体现三个能力：

- 你知道外部 API 要隔离。
- 你知道密钥不能写进代码。
- 你知道测试环境和真实模型调用要分开。
