# 第 015 课：Model Router 骨架

## 1. 为什么需要 Model Router

Agent 系统通常不会只用一个模型。

不同阶段适合不同模型：

- planner 需要推理能力。
- searcher 需要快。
- writer 需要长上下文和写作能力。
- verifier 需要更严谨。
- reviewer 需要检查和反思能力。

如果每个节点自己读环境变量，模型配置会散落在各处。

Model Router 的作用是：

```text
按角色选择模型配置
```

## 2. 当前支持的角色

```text
basic
planner
searcher
reader
writer
verifier
reviewer
```

当前默认映射：

```text
planner/reviewer -> reasoning model
writer           -> writer model
verifier         -> verifier model
searcher/reader  -> basic model
```

## 3. 当前只是骨架

现在 Model Router 不会调用 LLM。

它只回答：

```text
这个角色应该使用哪个模型？
base_url 是什么？
是否已经配置？
provider 是什么？
```

这一步的意义是为真实 LLM client 铺路。

## 4. 新增调试接口

```text
GET /v1/models
```

返回所有角色的模型配置。

这对调试很有用：

- 启动服务后可以确认环境变量有没有生效。
- 面试展示时可以说明系统支持多模型路由。
- 后续接 LLM 时可以直接复用这个配置层。

## 5. 为什么不现在直接调用 LLM

因为调用 LLM 会引入更多变量：

- API key。
- 网络。
- 模型兼容性。
- 成本。
- prompt 设计。
- 响应解析。

当前更合理的顺序是：

```text
Model Router
  -> LLM Client
  -> Planner/Writer/Verifier 节点替换
```

## 6. 面试怎么讲

可以这样说：

> 我先做了 Model Router，而不是直接在 workflow 里写死某个模型。Router 按 planner、writer、verifier 等角色返回模型配置。这样后续可以给不同 Agent 节点分配不同模型，例如 planner 用 reasoning model，writer 用长上下文模型，verifier 用更准确的模型。当前它还不调用 LLM，只是完成配置和路由边界。
