---
name: git-commit
description: 执行 git 提交操作。触发时机：用户提及"提交"、"commit"、"git commit"、"提交代码"、"帮我提交"等。默认全自动：自动检测并忽略脏文件、自动按 diff 推断 Conventional Commits 信息、自动选择 staging 范围；只在最终执行 git commit 前请求一次确认。
---

# git-commit Skill

专门处理本项目的 git 提交工作流。设计哲学：**少问多做，一次确认**。

## 触发关键词

- 「提交」「commit」「git commit」「提交一下」「帮我提交」
- `git commit -m "..."`

只要用户表达"想要把变更提交到仓库"的意思，就走本 skill。

## 用户 hint 识别（优先于自动推断）

在执行自动推断前，**先扫描用户原话**提取 hint，命中即覆盖自动推断：

| 用户原话模式 | 覆盖行为 |
|---|---|
| `message 是 <X>` / `提交信息是 <X>` / `m="<X>"` | 直接采用 `<X>` 作为 commit 信息，跳过推断 |
| `用 <type> 提交` / `type 是 <type>` | 强制使用指定 type（`feat`/`fix`/`docs`/...） |
| `scope 是 <X>` | 强制使用指定 scope |
| `body 是 <X>` | 使用指定 body，跳过自动生成 |
| `只提交 <path>` / `不要带 <path>` | 调整 staging 范围 |
| `不要 .gitignore` / `跳过 ignore 检查` | 跳过脏文件处理 |

hint 解析失败时（信息不全 / 与 Conventional Commits 不符），**降级为自动推断**，并在最终报告中说明降级原因。

---

## 流程

### Step 1: 收集（自动, 无交互）

```bash
git status --porcelain
git diff --stat                  # 推断 type 用
git log -5 --pretty='%h %s'      # 参考项目历史风格
git diff --cached --name-only    # 已暂存
```

把路径、文件统计、近期 commit 风格都收齐。**禁止**向用户输出中间状态。

### Step 2: 脏文件处理（自动, 无交互）

按下面两个名单分类处理，**不询问**：

#### 名单 A: 清晰应忽略（自动加 `.gitignore` + 自动 `git rm --cached` 如果已跟踪）

命中即追加对应规则到 `.gitignore`（按现有风格、空行分组、保留末尾换行），最后在报告中以「自动忽略」列出。

| 类别 | 模式 |
|---|---|
| Python 缓存 | `__pycache__/`、`*.pyc`、`*.pyo`、`*.pyd` |
| 虚拟环境 | `.venv/`、`venv/`、`.env/`、`env/`、`ENV/` |
| 构建产物 | `build/`、`dist/`、`*.egg-info/`、`*.egg`、`wheels/` |
| 测试/工具缓存 | `.pytest_cache/`、`.ruff_cache/`、`.mypy_cache/`、`.coverage`、`htmlcov/` |
| IDE | `.idea/`、`.vscode/`、`*.swp`、`*.swo`、`*.iml` |
| 操作系统 | `.DS_Store`、`Thumbs.db`、`desktop.ini` |
| 项目输出 | `output/`、`*.output.yaml`、`*.clash.yaml` |
| 用户私有配置 | `config/config.local.yaml`、`config/config.yaml`（保留 `*.example.yaml`） |
| 敏感凭据 | `.env`、`.env.*`、`*.secret`、`*.token`、`*.cookie`、`*.pem`、`*.key` |
| 日志 | `*.log`、`logs/` |
| uv | `uv.lock.local` |

#### 名单 B: 可疑应忽略（自动加 `.gitignore` + 报告中标注 ⚠️）

| 模式 | 触发条件 |
|---|---|
| `*.local`、`*.local.json`、`*.local.yaml` | 文件名匹配（Claude Code 等工具的 local-only 约定） |
| `*.mcp.json` | 文件名匹配（MCP 配置通常含本地 IP） |
| 文件内容包含 `127.0.0.1`、`localhost`、`192.168.`、`10.0.`、`172.16-31.` 后跟端口 | 内容扫描命中 |
| 文件名包含 `secret`/`token`/`password`/`credential`（名单 A 已覆盖的除外） | 文件名匹配 |

#### 名单 A 优先于名单 B

- 一个文件命中名单 A → 不再做内容扫描
- 命中名单 B 后，从报告中读出"⚠️ 忽略了可疑文件 X"清单

#### 重复规则抑制

写入 `.gitignore` 前用 `grep -F` 检查规则是否已存在；存在则跳过，**不**重复添加。

#### 全部命中后

`git status --porcelain` 复检；剩余的"待入库"文件进入 Step 3。

### Step 3: 自动推断 commit 信息（无交互）

**前提**：若 Step 0（hint 识别）已给出完整 commit 信息，本步直接跳过。

#### 3.1 type 推断

| 特征 | 推断 type |
|---|---|
| 全部变更在 `docs/`、`*.md`（且非 README 之外的代码说明） | `docs` |
| 全部变更在 `tests/` | `test` |
| 全部是格式化（仅空白/缩进变更） | `style` |
| 修改 `src/` 且包含新文件 / 新模块 | `feat` |
| 包含 `fix`/`bug`/`修复`/`patch` 关键词的文件名或路径 | `fix` |
| 仅修改 `pyproject.toml` / `uv.lock` / 工具配置 | `build` |
| 仅修改 `.github/` / `ci` 相关 | `ci` |
| 其它 | `chore` |

> 多个特征冲突时按优先级：`fix` > `feat` > `refactor` > 其它

#### 3.2 scope 推断

- 统计各顶层目录下的文件数
- 排除 `tests/`、`docs/`、`__pycache__/` 自身
- 取**非 src 目录**下文件数最多的目录名作为 scope（保持小写）

> 例：本次主要改 `src/clash_subcribe/fetcher/*` + `tests/unit/test_fetcher.py` → scope 推断为 `fetcher`
>
> 例：本次跨 fetcher/parser/processor/renderer 多模块均匀分布 → **省略 scope**

#### 3.3 subject 生成

- 从主要变更的**目录名/模块名**派生关键词
- 祈使语气、不大写开头、不以 `.` 结尾
- 目标长度 **≤ 50 字符**（不是 72，给 body 留空间）

启发式模板：
- 新增完整模块 → `<模块名> <动词> <对象>`，如 `add pipeline skeleton`
- 修复 → `fix <对象>`，如 `fix fetcher timeout`
- 文档 → `update <文档名>`，如 `update readme usage`
- 杂项 → `update <主要文件>`，如 `update pyproject deps`

#### 3.4 subject 自动缩短（不询问）

若生成的 subject > 50 字符，按顺序尝试：

1. 删除虚词：`a`/`an`/`the`/`in`/`on`/`for`/`to`/`with`/`and`/`of`
2. 用常用缩写：`config`→`cfg`、`error`→`err`、`function`→`fn`、`implement`→`impl`、`dependency`→`dep`、`documentation`→`docs`
3. 截断到 50 字符（保留整词，最后一个单词末尾去 `e`/`s` 等以更接近原意）

缩短后必须在最终报告中以「subject 自动缩短：X → Y」明示。

#### 3.5 body 自动生成

**仅当**满足以下任一条件：
- 文件数 > 5
- 跨 ≥ 3 个目录
- 修改了 `.gitignore`（追加规则值得说明）

生成规则：
- 用 `- <要点>` 项目符号
- 按目录分组：`src/` → 测试 → 配置 → 其它
- 每组不超过 2 行
- 总行数不超过 8 行
- 不复述 subject 已说过的内容

示例：

```
- 五段式 pipeline 骨架 (fetcher/parser/processor/renderer/emitter)
- 单元 + 集成测试, fixture 与 conftest
- 配置示例与 clash 输出模板
- .gitignore: 追加 .mcp.json / .claude/settings.local.json
```

### Step 4: 唯一一次确认（必须）

把以下信息**合并展示**，给用户一次 `AskUserQuestion` 机会：

```
即将提交 50 个文件 (2 个本地配置已自动忽略):

staging:
  ~ .gitignore  ~ README.md  ~ pyproject.toml
  + .claude/  + config/  + src/  + tests/  + uv.lock

自动忽略: .mcp.json, .claude/settings.local.json  (已写入 .gitignore)

commit:
  feat(scaffold): bootstrap full pipeline skeleton

  - 五段式 pipeline 骨架 (fetcher/parser/processor/renderer/emitter)
  - 单元 + 集成测试, fixture 与 conftest
  - 配置示例与 clash 输出模板
  - .gitignore: 追加 .mcp.json / .claude/settings.local.json
```

提供 4 个选项：

| 选项 | 含义 |
|---|---|
| **确认提交**（推荐） | 立即执行 |
| 调整信息 | 用户提供新的 subject/body/tyype，重新走 3.5 |
| 调整 staging | 用户指定要排除的路径，仅 commit 其余文件 |
| 查看 diff 详情 | 用 `git diff --stat` 展开，不提交 |

> 用户若在 prompt 中已表达「直接提交」/「帮我 commit」/「Y」/「确认」，则**跳过本步**直接进入 Step 5。

### Step 5: 执行与回显

- staging：用 `git add <明确路径>` 逐项加入（**禁用** `git add .` / `-A`）
- commit：用 `git commit -F <tmpfile>`（避免 shell 转义），tmpfile 写完即用，提交后删除
- 提交后回显：
  ```bash
  git log -1 --stat
  git status --short
  ```
- 按输出契约汇报

---

## 反模式

- ❌ **多轮问询**（本 skill 设计的上限是 Step 4 一次；任何其它场景下用户答一次就该走完流程）
- ❌ 自动 `git push` / `git commit --amend` / `git reset --hard`（三件套必须用户显式确认）
- ❌ `git add .` / `git add -A`（必须用明确路径，避免误带 Step 2 漏判的脏文件）
- ❌ 静默处理（任何自动行为必须在最终报告中明示）
- ❌ 提交信息包含 `update`/`misc`/`wip`/`test` 这类无意义 type 或描述
- ❌ 主体超过 50 字符仍提交（即使 type 合法）

## 输出契约

执行完一次 git-commit 工作流后，**必须**给出 4 行报告：

```
✅ 提交完成: <hash> - <subject>
   - 新增/修改/删除: <N> (新增 A / 修改 M / 删除 D)
   - .gitignore 新增规则: <条目 或 "无">
   - 自动忽略的脏文件: <条目 或 "无">
   - subject 自动缩短: <"原" → "新" 或 "无">
   - 推断来源: <自动推断 / 用户 hint>
```

如有任何步骤被用户中止 / 校验失败 / 报错停下，**明确说明中断位置与原因**，不隐瞒。

## 调试 / 旁路

- `git push` 不在本 skill 范围内，用户需显式说「push」才走
- pre-commit hook 失败：停下并报告，不自动 `--no-verify`
- 仓库处于 detached HEAD / rebase 中：停下并报告，不继续
- 远程分支与本地分歧：停下并报告
