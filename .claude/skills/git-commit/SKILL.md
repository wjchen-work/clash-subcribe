---
name: git-commit
description: 执行 git 提交操作。触发时机：用户提及"提交"、"commit"、"git commit"、"提交代码"、"帮我提交"等。当本次变更中存在不应被版本管理的文件时，会先提示加入 .gitignore；同时强制要求 commit 信息遵循 Conventional Commits 规范。
---

# git-commit Skill

专门处理本项目的 git 提交工作流。两道关卡：**先过滤脏文件，再规范提交信息**。

## 触发关键词

- 「提交」「commit」「git commit」「提交一下」「帮我提交」
- 「git commit -m ...」

只要用户表达"想要把变更提交到仓库"的意思，就走本 skill。

---

## 流程

### 1. 收集待提交文件

依次执行：

```bash
git status --porcelain          # 工作区变更
git diff --cached --name-only   # 已暂存
git log -1 --pretty=%B          # 最近一次 commit 信息（用于参考风格）
```

把**所有**变更路径（`A/M/D/R/C/U/?/?!`）收集到一个 `staged_paths: list[str]` 列表里。

### 2. 脏文件检测 → 决定是否更新 .gitignore

对照下面的「应忽略清单」检查 `staged_paths`。**只要命中任何一条**，就必须先处理 `.gitignore` 才能继续。

#### 应忽略清单（本项目常见）

| 类别 | 模式示例 |
|---|---|
| Python 字节码/缓存 | `__pycache__/`、`*.pyc`、`*.pyo`、`*.pyd` |
| 虚拟环境 | `.venv/`、`venv/`、`.env/` |
| 构建产物 | `build/`、`dist/`、`*.egg-info/`、`wheels/` |
| 测试/工具缓存 | `.pytest_cache/`、`.ruff_cache/`、`.mypy_cache/`、`.coverage`、`htmlcov/` |
| IDE | `.idea/`、`.vscode/`、`*.swp`、`*.swo`、`*.iml` |
| 操作系统 | `.DS_Store`、`Thumbs.db`、`desktop.ini` |
| 项目输出 | `output/`、`*.output.yaml`、`*.clash.yaml` |
| 用户私有配置 | `config/config.local.yaml`、`config/config.yaml`（保留 `*.example.yaml`） |
| 敏感凭据 | `.env`、`.env.*`、`*.secret`、`*.token`、`*.cookie` |
| 日志 | `*.log`、`logs/` |
| uv | `uv.lock.local` |

#### 处理方式

1. 用 `grep -F` 逐条模式匹配 `staged_paths`，命中即归入 `dirty_files`。
2. **如果 `dirty_files` 非空**：
   - 对每个命中模式，检查项目根 `.gitignore` 是否已经存在对应规则（用 `grep -F` 读 `.gitignore`）。**已存在则跳过**。
   - 把缺失的规则**追加**到 `.gitignore`（按类别分组、空行分隔，参考现有风格），并在文件末尾保留一个换行。
   - 对 `dirty_files` 中实际存在的文件执行 `git rm --cached <path>`（如果已跟踪）或保持未跟踪（如果是 untracked）。
   - 把更新后的 `.gitignore` 一并加入本次提交。
   - 用 `git status` 复检，向用户**明确列出**被忽略的文件清单，**等待用户确认**后再继续。
3. **如果 `dirty_files` 为空**：直接进入步骤 3。

> **关键原则**：永远不要自动 `git add` 任何用户没要求添加的文件；不要自动 `git commit`；每一步要可被用户中断。

### 3. Conventional Commits 校验

读取用户给出的 commit 信息（从 prompt 里直接拿，或 `git commit -m` 的参数，或通过交互询问）。**逐项校验**：

#### 3.1 基本格式

```
<type>(<scope>): <subject>

[body]

[footer(s)]
```

- **第一行 ≤ 72 字符**；subject 不以大写开头、不以句号结尾、采用祈使语气。
- **type** 必须是下表之一（小写）：
  | type | 用途 |
  |---|---|
  | `feat` | 新功能 |
  | `fix` | 修复 bug |
  | `docs` | 仅文档变更 |
  | `style` | 不影响代码含义的格式（空白、格式化、缺失分号等） |
  | `refactor` | 既非新功能也非 bug 修复的代码重构 |
  | `perf` | 性能优化 |
  | `test` | 新增/修改测试 |
  | `build` | 构建系统或外部依赖变更 |
  | `ci` | CI 配置文件与脚本变更 |
  | `chore` | 其他不修改 `src/` 或 `tests/` 的杂项 |
  | `revert` | 回滚先前的 commit |
- **scope**（可选但推荐）：本次变更的影响范围，用小写名词，如 `pipeline`、`fetcher`、`dedup`、`config`、`cli`。
- **breaking change**：若包含不兼容变更，必须在 type/scope 后加 `!`，并在 footer 出现 `BREAKING CHANGE: <说明>`。

#### 3.2 校验脚本（用 bash 在 commit 前跑一遍）

```bash
MSG='<待提交信息第一行>'
# 1) 匹配 <type>(<scope>)?(!)?: <subject>
echo "$MSG" | grep -Eq '^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9_-]+\))?(!)?: .+'
# 2) subject 长度
[ "${#MSG}" -le 72 ] || echo "WARN: subject > 72 chars"
# 3) subject 不以 . 结尾
echo "$MSG" | grep -qE '\.$' && echo "WARN: subject ends with '.'"
```

#### 3.3 不通过怎么办

- 直接告诉用户**哪一条规则没满足**，并给出**改写建议**（保持用户原意）。
- **不要自作主张改写后直接 commit**；让用户确认。

### 4. 确认 staging 范围

- 默认只暂存「步骤 2 复检后」认为应该入库的文件。**绝不**用 `git add .` / `git add -A`。
- 给出形如下面的预览，请用户**逐项确认**：

  ```
  即将提交：
    + src/clash_subcribe/fetcher/http_fetcher.py   (新增)
    ~ src/clash_subcribe/pipeline.py               (修改)
    + .gitignore                                   (新增忽略规则: .venv/, *.log)
    - __pycache__/foo.pyc                          (从暂存移除, 已加入 .gitignore)

  commit 信息:
    feat(fetcher): add async http fetcher with retry
  ```

  用户确认后再 `git add <明确路径>`、`git commit -m "..."`。

### 5. 执行与回显

- 用 `git commit -m "..."` 提交；如有 body/footer，**优先用 `git commit -F` 从临时文件读**，避免 shell 转义陷阱。
- 提交后立刻 `git log -1 --stat` 回显结果，并把步骤 2 处理的脏文件数量也一并汇报。
- 若用户在多分支、存在 pre-commit hook 等复杂场景下，**报错就停下**，让用户决定是否 `--no-verify` / 切分支等。

---

## 反模式（必须避免）

- ❌ 用 `print` 输出关键信息（违反 CLAUDE.md §5，统一用 logger；本 skill 在 CLI 中也尽量把信息打到 stderr 或对话上下文，不污染 commit 输出）。
- ❌ 自动 `git add .` / `git commit --amend` / `git push`，三件套全部需要用户二次确认。
- ❌ 静默忽略 .gitignore 检查结果——必须显式报告「检测到 N 个脏文件，已采取 X 处理」。
- ❌ 把用户没要求的额外文件顺手带上（比如顺手 `ruff format` 改动了一行无关代码）。
- ❌ 提交信息里出现 `update`、`misc`、`wip`、`test` 这种无意义 type 或描述。

## 输出契约

执行完一次完整的 git-commit 工作流后，向用户汇报：

```
✅ 提交完成: <commit hash> - <commit subject>
   - 新增/修改/删除文件: N
   - .gitignore 新增规则: <条目或"无">
   - 过滤掉的脏文件: <条目或"无">
```

如有任何步骤被用户中止或校验失败，**明确说明中断位置与原因**，不要隐瞒。
