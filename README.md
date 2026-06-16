# clash-subcribe

> 多合一的 Clash 订阅处理工具 —— 把多个订阅源合并、去重、过滤、重命名、排序，并按自定义模板渲染为最终的 Clash 配置。

## 项目背景

在日常使用 Clash / Clash Meta / mihomo 等代理客户端时，经常会遇到这样的场景：

- 同时订阅了多个机场或自建节点，单一订阅源不够用；
- 不同来源的节点质量参差不齐，需要按地区、关键词、协议类型筛选；
- 多个来源里常有重复节点（同一服务器被不同机场转售）；
- 默认的 Clash 配置缺少 `rule-providers`、`proxy-groups`、TUN/REDIR 等能力，需要注入统一模板。

`clash-subcribe` 就是为解决上述问题而生的。它把「抓取 → 解析 → 处理 → 渲染 → 输出」抽象成一条可插拔的流水线，让你用一份 YAML 配置就能生成最终可直接被路由器或客户端拉取的 Clash 订阅。

## 功能特性

- **多源合并**
  - HTTP(S) 订阅链接
  - 本地 YAML 配置文件
  - 单节点 URL 列表（`ss://`、`ssr://`、`vmess://`、`trojan://`、`hy2://` 等）
- **节点处理（按声明顺序执行）**
  - 去重：按 `server:port` + 协议类型 + 完整指纹判定
  - 过滤：关键词、地区、协议类型、延迟、流量
  - 重命名：统一前缀、地区标签、自动序号
  - 排序：按名称、协议类型或自定义权重
  - 健康检查（可选）：HTTP / TCP ping
- **配置增强**
  - 内置 `rule-providers`、`rules`、`proxy-groups` 模板注入
  - 支持 TUN / REDIR 等高级模式
- **多种输出**
  - 写入本地 YAML 文件
  - 输出到 `stdout`
  - 启动本地 HTTP 服务，提供订阅链接给路由器或客户端拉取

## 技术栈

- **语言**：Python ≥ 3.12
- **依赖管理 / 运行**：[`uv`](https://docs.astral.sh/uv/)
- **运行时依赖**：`pyyaml`、`httpx`、`pydantic`、`rich`、`tenacity`、`click`
- **开发依赖**：`pytest`、`pytest-asyncio`、`ruff`、`mypy`

## 项目结构

采用**分层 + 流水线**架构，每个阶段都是独立、可测试的模块。

```
clash-subcribe/
├── src/
│   └── clash_subcribe/
│       ├── __init__.py
│       ├── __main__.py            # python -m clash_subcribe 入口
│       ├── cli.py                 # 命令行参数定义
│       ├── config.py              # 用户配置加载与校验
│       ├── logging_setup.py       # 全局日志配置
│       ├── pipeline.py            # 流水线编排
│       ├── exceptions.py          # 自定义异常层级
│       ├── models/                # Proxy / ClashConfig 数据模型
│       ├── fetcher/               # 抓取：HTTP / 本地文件
│       ├── parser/                # 解析：Clash YAML / 单节点 URL
│       ├── processors/            # 处理：dedup / filter / rename / sort / healthcheck
│       ├── renderer/              # 渲染：节点列表 + 模板 → Clash YAML
│       └── emitter/               # 输出：file / stdout / http
├── config/
│   ├── config.example.yaml        # 用户配置示例
│   └── clash.template.yaml        # Clash 输出模板
├── tests/
│   ├── unit/
│   └── integration/
├── pyproject.toml
└── README.md
```

### 模块职责

| 模块 | 输入 | 输出 | 作用 |
|---|---|---|---|
| `fetcher` | URL / 文件路径 | 原始订阅文本 | 抓取订阅源 |
| `parser` | 原始文本 | `list[Proxy]` | 解析为标准节点模型 |
| `processor` | `list[Proxy]` | `list[Proxy]` | 去重 / 过滤 / 重命名 / 排序 |
| `renderer` | `list[Proxy]` + 模板 | Clash YAML 文本 | 渲染最终配置 |
| `emitter` | YAML 文本 | 副作用 | 写文件 / 输出 / 启动 HTTP |

## 安装

> 本项目使用 [`uv`](https://docs.astral.sh/uv/) 进行依赖管理，请先安装 `uv`。

```bash
# 克隆仓库
git clone https://github.com/<your-org>/clash-subcribe.git
cd clash-subcribe

# 同步依赖（含开发依赖）
uv sync --all-extras
```

## 使用方式

### 1. 准备配置文件

复制示例配置并按需修改：

```bash
cp config/config.example.yaml config/config.yaml
```

一个最小可用的配置示例：

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
  type: file                 # file | stdout | http
  path: ./output.yaml        # file 时使用
  template: ./config/clash.template.yaml
```

### 2. 运行

```bash
# 通过配置文件生成最终订阅
uv run python -m clash_subcribe -c config/config.yaml

# 直接输出到 stdout（适合管道）
uv run python -m clash_subcribe -c config/config.yaml --output stdout

# 输出到本地 HTTP 订阅服务（便于路由器拉取）
uv run python -m clash_subcribe -c config/config.yaml --output http --port 8080
```

### 3. 命令行参数

| 参数 | 说明 |
|---|---|
| `-c / --config` | 配置文件路径（必填） |
| `-o / --output` | 输出目标，覆盖配置中的 `output.type` |
| `-v / --verbose` | 输出 DEBUG 日志 |
| `-q / --quiet` | 仅输出 WARNING 及以上 |
| `--log-file` | 同时写入日志文件 |
| `--port` | HTTP emitter 端口（默认 `8080`） |

## 流水线示例

抓取 → 解析 → 合并 → 去重 → 过滤 → 重命名 → 排序 → 渲染 → 输出，过程类似：

```
┌────────┐    ┌────────┐    ┌────────┐    ┌────────────┐    ┌─────────┐    ┌────────┐
│ fetch  │ -> │ parse  │ -> │ merge  │ -> │ processors │ -> │ render  │ -> │ emit   │
└────────┘    └────────┘    └────────┘    └────────────┘    └─────────┘    └────────┘
  原始文本      Proxy 列表     合并节点      dedup / filter /     Clash YAML    文件 / stdout
                                            rename / sort                     / HTTP
```

## 常见操作

### 添加新依赖

```bash
uv add <package>            # 运行时依赖
uv add --dev <package>      # 开发依赖
```

`pyproject.toml` 的依赖区块与 `uv.lock` 由 `uv` 统一维护，请勿手工编辑。

### 运行测试与检查

```bash
# 单元测试
uv run pytest tests/unit -q

# 集成测试
uv run pytest tests/integration -q

# Lint
uv run ruff check src tests

# 格式化
uv run ruff format src tests

# 类型检查
uv run mypy src
```

## 路线图

- [x] 选定依赖管理工具：`uv`
- [ ] 基础 logger 与 CLI 框架
- [ ] `fetcher` + `clash_parser`
- [ ] `dedup` / `filter` / `rename` / `sort` processor
- [ ] `file` / `stdout` emitter
- [ ] 配置文件与示例
- [ ] 测试套件与 CI
- [ ] （可选）HTTP emitter、本地订阅服务
- [ ] （可选）节点健康检查

## 许可证

待定。
