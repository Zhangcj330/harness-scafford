# harness-scaffold

面向长时间运行 coding agent 工作流的 Python 优先脚手架。

这个仓库围绕几条不能破坏的约束来设计：

- run 必须可持久化、可恢复
- 每次 run 都要在 `.runs/` 下产生可审计的工件
- 实际工作在 `.worktrees/` 里的隔离工作区完成
- `docs/` 是给人和 agent 共用的事实来源
- 可观测性从一开始就内建，而不是后补

## 快速开始

```bash
uv sync --extra dev
uv run harness run examples/tasks/offline-smoke.yaml
uv run harness dashboard
```

启动本地可观测性栈：

```bash
uv run harness obs up
uv run harness obs down
```

如果本机没有安装 Docker，harness 仍然可以运行，并继续输出本地 JSON 工件，只是不会启动 Grafana 相关服务。

## 主要命令

- `uv run harness run <task-file>`
- `uv run harness resume <run-id>`
- `uv run harness review <run-id>`
- `uv run harness dashboard`
- `uv run harness obs up`
- `uv run harness obs down`

## 文档入口

- [AGENTS.md](AGENTS.md)
- [docs/index.md](docs/index.md)
- [docs/architecture.md](docs/architecture.md)
- [docs/operations.md](docs/operations.md)
- [docs/observability.md](docs/observability.md)

## 说明

这个脚手架是 local-first 的。设置了 `OPENAI_API_KEY` 后可以调用真实 OpenAI 模型；但默认开发体验仍然是确定性的、可离线验证的，这样仓库可以在不依赖线上模型的情况下完成 CI 测试。
