# CLAUDE.md

> Claude Code 在此项目中的协作指南。请先阅读本文件，再开始任何代码改动。

## 1. 项目概述

**clash-subcribe** 是一个多合一的 Clash 订阅处理脚本，核心能力：

- **多源合并**：从 N 个订阅源（HTTP(S) URL / 本地文件 / 节点链接列表）抓取配置并合并为单个 Clash 配置。
- **额外处理**（pipeline 形式，可插拔）：
  - 节点去重（按 `server:port`、协议类型、完整指纹）
  - 节点过滤（按关键词、地区、协议类型、延迟、流量）
  - 节点重命名（统一前缀、地区标签、序号）
  - 排序策略（按名称 / 类型 / 自定义权重）
  - 配置增强（rule-providers、rules、proxy-groups、TUN/REDIR 等模板注入）
  - 节点健康检查（可选：HTTP/TCP ping）
- **协议字段不校验**：订阅里出现的 `type`、必填字段、未知字段一律透传，**不**做按协议类型的强校验（`ss` 必须带 `cipher` 之类）；协议不断迭代，把这一层校验交给下游 Clash/mihomo 客户端。只有 `name` / `type` / `server` / `port` 四个**通用元信息**是必填的。
- **多种输出**：
  - 写入本地 YAML 文件
  - 输出到 `stdout`
  - 启动一个本地 HTTP 服务，对外提供订阅链接（便于路由器/客户端拉取）

## 2. 技术栈

- **语言**：Python ≥ 3.12（见 `.python-version`）
- **包管理 / 构建**：**强制使用 [`uv`](https://docs.astral.sh/uv/)** 管理依赖与运行脚本，`pyproject.toml` 仅作为被 `uv` 自动维护的清单文件。详见 §11 依赖管理规范。
- **依赖运行时**：
  - `pyyaml` — Clash YAML 解析与序列化
  - `httpx` — 异步 HTTP 客户端（抓取订阅）
  - `pydantic` — 数据模型与配置校验
  - `rich` — 美化的控制台输出与日志
  - `tenacity` — 抓取重试
  - `click`（或 `typer`）— CLI 框架
- **依赖开发**：`pytest`、`pytest-asyncio`、`ruff`、`mypy`

> 当且仅当确实需要某个依赖时才通过 `uv add` 添加，避免空依赖膨胀。

## 3. 项目结构

采用**分层 + 流水线**架构。每个处理阶段（fetch → parse → merge → process → render → emit）是独立的、可测试的模块。

```
clash-subcribe/
├── src/
│   └── clash_subcribe/
│       ├── __init__.py
│       ├── __main__.py            # python -m clash_subcribe 入口
│       ├── cli.py                 # click/typer 命令定义
│       ├── config.py              # 用户配置加载与校验
│       ├── logging_setup.py       # 全局 logging 配置（rich handler）
│       ├── pipeline.py            # 编排各 stage，处理上下文
│       ├── exceptions.py          # 自定义异常层级
│       ├── models/
│       │   ├── __init__.py
│       │   ├── proxy.py           # Proxy 节点数据模型
│       │   └── config.py          # ClashConfig 数据模型
│       ├── fetcher/
│       │   ├── __init__.py
│       │   ├── base.py            # Fetcher 抽象基类
│       │   ├── http_fetcher.py    # HTTP(S) 订阅抓取
│       │   └── file_fetcher.py    # 本地文件
│       ├── parser/
│       │   ├── __init__.py
│       │   ├── base.py            # Parser 抽象基类
│       │   ├── clash_parser.py    # Clash YAML → Proxy list
│       │   └── url_parser.py      # ss/ssr/vmess/trojan/hy2 URL → Proxy
│       ├── processors/
│       │   ├── __init__.py
│       │   ├── base.py            # Processor 抽象基类
│       │   ├── dedup.py
│       │   ├── filter.py
│       │   ├── rename.py
│       │   ├── sort.py
│       │   └── healthcheck.py     # 可选
│       ├── renderer/
│       │   ├── __init__.py
│       │   └── clash_renderer.py  # Proxy list + template → Clash YAML
│       └── emitter/
│           ├── __init__.py
│           ├── file_emitter.py
│           ├── stdout_emitter.py
│           └── http_emitter.py
├── config/
│   ├── config.example.yaml        # 用户配置示例
│   └── clash.template.yaml        # Clash 输出模板
├── tests/
│   ├── unit/
│   └── integration/
├── pyproject.toml
├── README.md
└── CLAUDE.md
```

### 3.1 模块职责矩阵

| 模块 | 输入 | 输出 | 是否可独立测试 |
|---|---|---|---|
| `fetcher` | URL / 文件路径 | 原始订阅文本 | ✅ |
| `parser` | 原始文本 | `list[Proxy]` | ✅ |
| `processor` | `list[Proxy]` | `list[Proxy]` | ✅ |
| `renderer` | `list[Proxy]` + 模板 | Clash YAML 文本 | ✅ |
| `emitter` | YAML 文本 | 副作用（写文件 / 启动 HTTP） | 部分 |

## 4. 开发工作流

### 4.1 环境搭建

> **所有环境操作必须经由 `uv` 完成**（详见 §11）。不要直接 `pip install`，不要手工创建 `.venv`。

```bash
# 克隆后首次进入项目
uv sync --all-extras       # 创建 .venv 并安装全部依赖（含 dev extras）

# 添加新依赖
uv add <package>            # 运行时依赖
uv add --dev <package>      # 开发依赖

# 移除依赖
uv remove <package>

# 升级某个依赖
uv add <package> --upgrade
```

### 4.2 常用命令

> **所有脚本运行都必须通过 `uv run`**，让 `uv` 自动激活虚拟环境并锁定依赖版本。**禁止**直接 `python ...` / `pytest ...` / `ruff ...`。

| 任务 | 命令 |
|---|---|
| 运行脚本（开发期） | `uv run python -m clash_subcribe -c config/config.example.yaml` |
| 运行单元测试 | `uv run pytest tests/unit -q` |
| 运行集成测试 | `uv run pytest tests/integration -q` |
| Lint | `uv run ruff check src tests` |
| 格式化 | `uv run ruff format src tests` |
| 类型检查 | `uv run mypy src` |
| 进入 venv shell | `uv shell` |

### 4.3 新增功能的开发顺序

1. **先看 `config/config.example.yaml`** 是否已经预留配置点。
2. **新功能尽量封装为 Processor**，实现 `processors/base.py` 中的接口。
3. **写测试**：`tests/unit/processors/test_<name>.py`。
4. **更新配置示例**：把新参数加进 `config.example.yaml` 并加注释。
5. **更新 README**：补充使用样例。

## 5. 日志规范（重点）

### 5.1 总体原则

- 使用标准 `logging`，**禁止**在业务代码中用 `print`。
- 每个模块 `logger = logging.getLogger(__name__)`。
- 通过 `logging_setup.py` 统一初始化：
  - 控制台：`rich.logging.RichHandler`，按级别着色，显示时间、级别、模块、消息。
  - 文件：可选 `--log-file` 启动参数，开启后追加写入，格式为结构化 `%(asctime)s %(levelname)-8s %(name)s :: %(message)s`。
- 默认级别 `INFO`，`--verbose / -v` 提升为 `DEBUG`，`--quiet / -q` 降为 `WARNING`。
- **绝不打印**订阅 token、Authorization 头、完整 cookie、密码字段；命中时仅打印 `***`。

### 5.2 必须打印日志的关键节点

| 阶段 | 日志级别 | 必含字段 |
|---|---|---|
| 启动 | `INFO` | 配置路径、源数量、输出目标、启用的 processors |
| 抓取每个源 | `INFO` | 源名称、URL（域名脱敏）、HTTP 状态、耗时、字节数 |
| 抓取失败 | `WARNING` 重试 / `ERROR` 放弃 | 错误类型、重试次数 |
| 解析 | `INFO` | 解析后节点数、跳过的不可解析条目数 |
| 合并 | `INFO` | 合并前/后节点数 |
| 每个 processor | `INFO`（开始+结束）/ `DEBUG`（细节） | 名称、前后节点数、耗时 |
| 输出 | `INFO` | 输出路径/URL、字节数、节点数 |
| 结束 | `INFO` | 总耗时、统计摘要 |
| 异常 | `ERROR` + `exc_info=True` | 完整堆栈、上下文（哪个源/哪个 stage） |

### 5.3 日志格式示例

```
2026-06-15 10:23:01  INFO     clash_subcribe.pipeline :: 启动订阅处理 pipeline（3 个源，输出 -> output.yaml）
2026-06-15 10:23:01  DEBUG    clash_subcribe.config    :: 加载配置: config/config.example.yaml
2026-06-15 10:23:02  INFO     clash_subcribe.fetcher   :: [源1/3] 抓取 sub.example.com/xxx -> 200 OK, 12.3 KB, 1.42s
2026-06-15 10:23:03  WARNING  clash_subcribe.fetcher   :: [源2/3] sub2.example.com -> 第 1/3 次重试: ConnectTimeout
2026-06-15 10:23:05  INFO     clash_subcribe.parser    :: [源1/3] 解析完成：45 节点（跳过 0 条不可解析条目）
2026-06-15 10:23:05  INFO     clash_subcribe.processor :: [dedup] 去重: 120 -> 98, 0.03s
2026-06-15 10:23:05  INFO     clash_subcribe.processor :: [rename] 已重命名 98 节点, 0.01s
2026-06-15 10:23:05  INFO     clash_subcribe.emitter   :: 写入 output.yaml (12.4 KB, 98 节点)
2026-06-15 10:23:05  INFO     clash_subcribe.pipeline :: 完成，总耗时 4.21s
```

### 5.4 日志使用约束（AI 协作时请遵守）

- 不要写 `print("...")` 来"快速调试"，请用 `logger.debug(...)` 并提交前移除/保留。
- 不要在循环里逐条 `INFO` 节点；逐条用 `DEBUG`，整体阶段用 `INFO`。
- 不要吞异常：除明确可恢复的分支外，一律 `logger.exception(...)` 或重新抛出。
- 不要记录敏感信息（见 5.1）。

## 6. 配置约定

- 用户配置使用 YAML，`config/config.example.yaml` 是唯一权威示例。
- 所有 processor 通过配置启用/禁用，按声明顺序执行：

```yaml
sources:
  - name: provider-a
    url: https://sub.example.com/xxx
  - name: provider-b
    url: https://sub2.example.com/yyy
  - name: local
    path: ./local.yaml

processors:
  - dedup
  - filter:
      keywords: [免费, 测速, 过期]
      regions: [HK, JP, US]
  - rename:
      prefix: "[A]"
      add_region_tag: true
  - sort:
      by: name

output:
  type: file           # file | stdout | http
  path: ./output.yaml  # file 时使用
  template: ./config/clash.template.yaml
```

## 7. 错误处理

- 在 `exceptions.py` 中定义层级：
  - `ClashSubError` (基类)
    - `SourceFetchError`
    - `ParseError`
    - `RenderError`
    - `ConfigError`
- CLI 顶层捕获后退出码：`0` 成功；`1` 部分失败；`2` 完全失败。
- 单个源抓取失败不应中断整个 pipeline（除非 `sources[].required: true`）。

## 8. 编码风格

- **类型注解**：所有公开函数必须带完整类型注解；内部函数也尽量带。
- **不可变优先**：`dataclass(frozen=True)` 或 `pydantic.BaseModel`。
- **纯函数**：processors 应当是无副作用的 `Iterable[Proxy] -> Iterable[Proxy]`。
- **命名**：模块小写下划线；类 `PascalCase`；常量 `UPPER_SNAKE`。
- **行宽**：100 字符（`ruff` 配置）。
- **导入顺序**：遵循 `ruff` 默认（stdlib → third-party → local）。
- **文档字符串**：公开 API 使用 Google 风格 docstring，简短说明 + 参数 + 返回 + 异常。
- **注释克制**：代码中**不要有过多的注释**，保持代码整洁。
  - 默认不写行内注释（`#`）；仅在以下情况保留：解释"为什么"（why）而非"是什么"（what）、标注 TODO/FIXME/XXX、解释非显然的算法或外部约束。
  - 类/函数的 docstring 保持一句话概述即可；仅在参数/返回/异常不显然时展开。
  - 删注释时不要破坏类型注解、可执行的字符串字面量或 `# noqa` / `# type: ignore` 等工具指令。

## 9. 测试约定

- 单元测试覆盖每个 fetcher / parser / processor / renderer 的正常路径与边界。
- 集成测试用 `pytest` fixture 注入小型 YAML fixture 文件。
- 重要回归点（去重、过滤、合并顺序）必须有断言节点数与名称的测试。
- 不依赖真实外网：fetcher 用 `respx`（httpx mock 库）或本地文件 fetcher。

## 10. Claude 协作备忘

- 在做改动前，**先读** `config/config.example.yaml`、`pyproject.toml`、`uv.lock`、相关模块的现有代码。
- 新增依赖前先确认是否会显著增加安装体积（httpx、pyyaml 是必要；其他可考虑可选 extra）。
- **依赖操作**：使用 `uv add / uv remove / uv add --dev`，**绝不**直接编辑 `pyproject.toml` 的 `[project.dependencies]` / `[project.optional-dependencies]` 区块（详见 §11）。
- **运行命令**：使用 `uv run ...`，**绝不**直接调用 `python` / `pytest` / `ruff` / `mypy`。
- 涉及输出 YAML 时，保持 key 顺序与原 Clash 配置一致，避免破坏现有 diff。
- 任何破坏性变更（如 CLI 选项重命名、配置结构变化）必须在 README 顶部写明迁移说明。
- 完成改动后，请确认 `uv run pytest`、`uv run ruff check`、`uv run ruff format --check` 全部通过。

## 11. 依赖管理规范（强制）

> 本节是**硬性规范**，违反任何一条都属于不允许的改动。

### 11.1 工具

- **唯一依赖管理工具**：[`uv`](https://docs.astral.sh/uv/)。
- **唯一运行入口**：`uv run ...`（在已 `uv sync` 的项目里，`uv run` 会自动激活虚拟环境并锁定 `uv.lock` 中的版本）。
- **不使用**：`pip` / `pip-tools` / `poetry` / `pdm` / `conda` / 手工编辑 `requirements*.txt`。

### 11.2 禁止直接编辑 `pyproject.toml` 的依赖区块

`pyproject.toml` 中以下区块**只能由 `uv` 自动维护**，禁止 AI / 人工直接修改：

- `[project] dependencies`
- `[project.optional-dependencies]`
- `[dependency-groups]`（PEP 735）

允许直接编辑的区块（不在禁用范围内）：

- `[project]` 下的元信息（`name` / `version` / `description` / `readme` / `requires-python`）
- `[build-system]`（构建后端选择）
- `[tool.*]`（`ruff`、`mypy`、`pytest` 等工具配置）

### 11.3 依赖操作命令速查

| 需求 | 命令 | 是否允许直接编辑 `pyproject.toml` |
|---|---|---|
| 新增运行时依赖 | `uv add httpx` | ❌ |
| 新增开发依赖 | `uv add --dev pytest` | ❌ |
| 新增可选 extra | `uv add --optional http respx` | ❌ |
| 固定版本 | `uv add "httpx==0.27.2"` | ❌ |
| 升级 | `uv add httpx --upgrade` | ❌ |
| 移除 | `uv remove httpx` | ❌ |
| 安装/同步全部 | `uv sync --all-extras` | — |
| 锁定文件 | 自动生成 `uv.lock`，**不要**手改 | ❌ |
| 升级 lock | `uv lock --upgrade` | ❌ |

### 11.4 提交前检查

变更依赖后，PR / 提交必须包含：

- `pyproject.toml`（由 `uv` 修改的合法区块）
- `uv.lock`（必须随 `pyproject.toml` 一起更新，CI 会校验两者一致）

### 11.5 紧急 / 例外情况

仅当 `uv` 本身出现 bug 或不可用时，才允许临时手工编辑 `pyproject.toml`，但必须在 PR 描述中注明原因，并在恢复后第一时间用 `uv lock` 重新规范化。

## 12. 待办（路线图）

- [x] 选定依赖管理工具：**uv**
- [ ] 落地基础 logger 与 CLI 框架
- [ ] 实现 fetcher + clash_parser
- [ ] 实现 dedup / filter / rename / sort processor
- [ ] 输出 file / stdout emitter
- [ ] 配置文件与示例
- [ ] 测试套件与 CI
- [ ] （可选）HTTP emitter、本地订阅服务
- [ ] （可选）节点健康检查
