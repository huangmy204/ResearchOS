# 第 018 课：用 `.env` 文件管理本地 API Key

## 1. 能不能把 key 和 url 放在项目目录里

可以，但应该放在项目根目录的 `.env` 文件里，而不是写进 Python 代码。

推荐结构：

```text
ResearchOS/
  .env          本地真实配置，不提交
  .env.example  示例配置，可以提交
```

本项目的 `.gitignore` 已经忽略了 `.env`：

```text
.env
```

所以只要你不要强行 `git add .env`，它不会被提交到 GitHub。

## 2. 为什么不用 Python 文件保存 key

不要这样：

```python
API_KEY = "sk-..."
```

原因：

| 做法 | 问题 |
| --- | --- |
| 写进 `.py` 文件 | 很容易被 commit |
| 写进 README | 等于公开泄露 |
| 写进 `.env` | 合适，前提是 `.env` 被 git 忽略 |
| 写进系统环境变量 | 更安全，但换机器时要重新配置 |

学习阶段最推荐 `.env`，因为直观、好改、不会污染代码。

## 3. 怎么创建自己的 `.env`

在项目根目录执行：

```powershell
Copy-Item .env.example .env
```

然后用编辑器打开 `.env`，填入类似配置：

```text
RESEARCHOS_LLM_CLIENT=openai_compatible
RESEARCHOS_LLM_API_KEY=你的阿里云百炼 API Key
RESEARCHOS_LLM_TIMEOUT_SEC=30

BASIC_MODEL=qwen-turbo
BASIC_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

WRITER_MODEL=qwen-plus
WRITER_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

REASONING_MODEL=qwen-plus
REASONING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

VERIFIER_MODEL=qwen-plus
VERIFIER_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

注意：`.env` 里不要加 PowerShell 的 `$env:`，直接写 `KEY=value`。

## 4. `.env` 和 PowerShell 环境变量谁优先

本项目当前规则是：

```text
PowerShell 已经设置的环境变量 > .env 文件 > 代码默认值
```

也就是说，如果你在 PowerShell 里设置了：

```powershell
$env:WRITER_MODEL = "deepseek-chat"
```

即使 `.env` 里写的是：

```text
WRITER_MODEL=qwen-plus
```

程序也会优先使用 PowerShell 里的 `deepseek-chat`。

这个设计很常见，因为部署环境通常通过系统环境变量注入配置，本地开发才用 `.env`。

## 5. 怎么确认 `.env` 没被 Git 跟踪

执行：

```powershell
git status --short
```

如果你只改了 `.env`，正常情况下应该看不到 `.env`。

如果看到了：

```text
?? .env
```

说明 `.gitignore` 没生效，需要先停下来检查，不要提交。

## 6. 面试怎么讲

可以这样说：

> 本地开发我用 `.env` 保存 API key 和模型 base_url，但 `.env` 被 `.gitignore` 忽略，不会提交。代码启动时会读取 `.env`，但不会覆盖系统环境变量。这样既方便本地调试，也符合部署时通过环境变量注入密钥的实践。
