# clash-subcribe

> 多合一的 Clash 订阅处理脚本 —— 把多个订阅源合并成一个，并支持去重 / 过滤 / 重命名 / 排序等额外处理。

## 状态

**项目处于初始化 / 规划阶段。** 当前仓库仅包含：

- 项目元信息（`pyproject.toml`）
- Python 版本声明（`.python-version`）
- AI 协作规范（`CLAUDE.md`）

第一个可运行版本将按 [`CLAUDE.md`](./CLAUDE.md) 中描述的分层流水线架构落地： `fetcher → parser → processor → renderer → emitter`。

## 计划能力

- **多源合并**：HTTP(S) 订阅、本地文件、单节点 URL 列表
- **额外处理**：
  - 节点去重（按 `server:port`、协议类型、完整指纹）
  - 节点过滤（关键词、地区、协议类型）
  - 节点重命名（统一前缀、地区标签、序号）
  - 排序策略
  - Clash 配置模板注入（rule-providers / proxy-groups / TUN 等）
  - 可选节点健康检查
- **多种输出**：本地 YAML、`stdout`、本地 HTTP 订阅服务

## 技术栈

- Python ≥ 3.12
- 依赖管理：[`uv`](https://docs.astral.sh/uv/)（强制，详见 `CLAUDE.md` §11）
- 运行时：`pyyaml`、`httpx`、`pydantic`、`rich`、`tenacity`、`click`

## 开发

> 所有命令必须通过 `uv` 执行，详见 [`CLAUDE.md`](./CLAUDE.md) §4 / §11。

```bash
# 同步依赖
uv sync --all-extras

# 运行（待 src 落地后）
uv run python -m clash_subcribe -c config/config.example.yaml

# 测试 / lint
uv run pytest
uv run ruff check src tests
uv run ruff format --check src tests
```

## 添加依赖

```bash
uv add <package>            # 运行时依赖
uv add --dev <package>      # 开发依赖
```

请勿直接编辑 `pyproject.toml` 的依赖区块 —— 依赖与 `uv.lock` 由 `uv` 统一维护。

## 目录预览

```
src/clash_subcribe/
├── cli.py
├── pipeline.py
├── fetcher/
├── parser/
├── processors/
├── renderer/
└── emitter/
```

## 许可证

待定。
