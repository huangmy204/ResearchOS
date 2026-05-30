# 第 002 课：依赖管理策略

## 1. 两种依赖文件

当前项目里有：

```text
pyproject.toml
requirements.txt
```

区别：

- `pyproject.toml`：项目级配置，适合现代 Python 工程。
- `requirements.txt`：pip 安装清单，常用于部署、CI 或固定环境。

## 2. 当前 MVP 依赖

`pyproject.toml` 当前运行依赖：

```toml
dependencies = [
    "fastapi>=0.115.0",
    "pydantic>=2.8.0",
    "uvicorn>=0.30.0",
]
```

作用：

- `fastapi`：HTTP API 框架。
- `pydantic`：数据模型和校验。
- `uvicorn`：ASGI 服务启动器。

开发依赖：

```toml
dev = [
    "pytest>=8.2.0",
    "httpx>=0.27.0",
    "ruff>=0.5.0",
]
```

作用：

- `pytest`：测试。
- `httpx`：FastAPI 测试客户端需要。
- `ruff`：代码检查和格式化。

这组依赖适合当前最小后端。

## 3. `requirements.txt` 为什么暂时太重

`requirements.txt` 包含最终系统可能需要的依赖：

- LangGraph / LangChain
- OpenAI
- Qdrant
- Postgres / Redis
- PDF / HTML 解析
- Playwright
- Docker SDK
- 日志、CLI、序列化工具

这些方向合理，但当前阶段不建议全部安装。

原因：

1. 安装慢。
2. 排错成本高。
3. 有些包当前代码还没用到。
4. Playwright、数据库、Docker 都有额外运行环境要求。

## 4. 推荐策略

当前只装 MVP 依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

后续按模块逐步加：

- 接 LangGraph 时再加 `langgraph`。
- 接模型接口时再加 `openai`。
- 接数据库时再加 `sqlalchemy`、`asyncpg`、`redis`。
- 接 PDF 时再加 `pypdf` 或 `pdfplumber`。
- 接浏览器时再加 `playwright`。
- 接 Docker 沙箱时再加 `docker`。

## 5. 版本范围

写法：

```text
fastapi>=0.115,<1.0
```

含义：

- 允许安装 `0.115` 之后的兼容版本。
- 不允许自动升级到 `1.0` 这种可能破坏兼容的大版本。

MVP 阶段可以先用下限版本。项目稳定后再加锁文件或更严格版本范围。
