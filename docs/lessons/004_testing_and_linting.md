# 第 004 课：测试与静态检查闭环

## 1. Editable Install

命令：

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

含义：

- `-e` 是 editable mode。
- 当前项目会被安装到虚拟环境。
- 修改 `src/` 里的代码后，不需要重新安装，测试可以直接导入最新代码。
- `.[dev]` 表示同时安装 `pyproject.toml` 里的开发依赖。

## 2. Pytest

命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests -v
```

当前测试覆盖：

- 创建 research run。
- 等待 workflow 完成。
- 检查 artifact 是否生成。
- 检查 artifact 内容能读取。
- 检查路径穿越会被拒绝。

这说明当前 MVP 的主要行为链路是通的。

## 3. Ruff

命令：

```powershell
.\.venv\Scripts\python.exe -m ruff check src tests
```

Ruff 负责静态检查：

- import 排序。
- 未使用导入。
- 行长度。
- 常见 Python 代码风险。

这次 Ruff 发现 `Depends(...)` 默认参数写法触发 `B008`。

## 4. `Annotated` + `Depends`

旧写法：

```python
services: AppServices = Depends(get_services)
```

新写法：

```python
services: Annotated[AppServices, Depends(get_services)]
```

好处：

- 类型是 `AppServices`。
- 依赖注入信息放在 `Annotated` 元数据里。
- 避免在默认参数里调用 `Depends(...)`。
- 更适合 FastAPI 与静态检查工具协作。

## 5. 当前验证结果

```text
ruff check: passed
pytest: 4 passed, 1 warning
```

那个 warning 来自 FastAPI / Starlette 测试客户端依赖，不影响当前 MVP 行为。

## 6. Git 知识点

这次改动会让 Git 看到：

- 路由文件被修改：因为改了 `Depends` 写法。
- 少量模型或 Store 文件被格式化：因为修复 import 顺序。
- 新增本讲义文件。

查看方式：

```powershell
git status --short
git diff -- src docs
```
