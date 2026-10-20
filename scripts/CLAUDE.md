[根目录](../CLAUDE.md) > **scripts**

# scripts 模块

## 变更记录 (Changelog)

| 时间 | 类型 | 说明 |
| --- | --- | --- |
| 2026-10-20 | 修复 | 扫描抽样、候选总数、风险 token 匹配、CI 命令提取、校验规则修复（详见根 `CLAUDE.md`）；本文档入口/接口/测试章节已按包结构更新。 |
| 2026-07-27 | 功能 | 完成 issue #7 Slice 5：新增 `scripts/harness/content_detectors.py` 内容层探测（CI 命令、Dockerfile 指令、pyproject `[tool.*]` 键名、`.env.example` key、pre-commit hook id、CODEOWNERS、SECURITY.md 摘要），所有读取共享 `ContentBudget`（`--content-budget-bytes`，默认 8 MiB）；见根 `CLAUDE.md` 变更记录详情。注：本文档自 Slice 1-4（`scripts/harness/` 包化、两阶段扫描、语言规则表、任务系统解析器）以来落后于代码现状，`入口/对外接口/数据模型` 章节仍按早期单文件版本描述，需要单独一次全量复扫更新。 |
| 2026-06-06 14:43:29 | 修复 | `detect_package_scripts` 改用相对路径判断 SKIP_DIRS;`detect_existing_scripts` 递归检测嵌套脚本;`scan()` 新增 `truncated` 字段;校验正则放开 `/` 支持嵌套脚本引用。 |
| 2026-06-06 13:12:21 | 增量复扫 | 复核 `scan_repo.py` 与 `validate_harness_docs.py`，行为与文档一致，无变化。 |
| 2026-06-05 20:33:44 | 初始化 | 生成 scripts 模块 Claude 工作文档。 |

## 模块职责

`scripts/` 是 harness 的可执行核心，负责两件事：

1. 扫描目标仓库并输出保守事实。
2. 校验目标仓库是否具备最小 agent harness 文档和检查入口。

## 入口与启动

| 文件 | 入口 | 用法 |
| --- | --- | --- |
| `scripts/scan_repo.py` | `harness.cli.scan_main()` | `python3 scripts/scan_repo.py /path/to/repo` |
| `scripts/validate_harness_docs.py` | `harness.cli.validate_main()` | `python3 scripts/validate_harness_docs.py /path/to/repo` |

包内模块：`walker`（git/os 遍历、比例配额与等距抽样）、`detectors`（路径级探测）、`task_parsers`（任务系统）、`content_detectors`（受预算限制的内容层）、`sampling`、`schema`、`rules`、`validator`、`scanner`（编排）。

`scan_repo.py` 支持：

```sh
python3 scripts/scan_repo.py --deep /path/to/repo
```

## 对外接口

这是 CLI 脚本模块，没有 HTTP/API 服务。

### `scan_repo.py`

- 输入：目标仓库路径、可选 `--deep`、`--limit`（默认 50000）、`--output`、`--full`、`--force`、`--content-budget-bytes`。
- 输出：默认写入目标仓库 `.agent/repo-facts.json`，并打印输出路径。
- 事实字段（schema v2）见 `references/repo-facts.md`。

### `validate_harness_docs.py`

- 输入：目标仓库路径。
- 输出：校验通过打印 `harness docs validated`；失败打印 `ERROR: ...` 并返回非零状态。
- 校验范围：必需文档、`.agent/repo-facts.json`、`AGENTS.md` 引用、危险区域覆盖、`scripts/check.sh` 是否可执行、是否包含猜测式命令。

## 关键依赖与配置

- 只使用 Python 标准库：`argparse`、`json`、`os`、`re`、`datetime`、`pathlib`。
- `pyproject.toml` 仅声明项目名、版本和 Python >= 3.11。
- GitHub Actions CI 仅运行 `python3 -m unittest discover tests`；Not configured：无 `requirements.txt`、`ruff.toml`、`mypy.ini`、`pytest.ini`。

## 数据模型

核心数据结构是 JSON 字典：

- `top_level`：顶层目录与文件。
- `manifests` / `configs` / `docs`：项目事实索引。
- `test_files` / `existing_scripts` / `ci_configs`：验证入口候选。
- `generated_candidates` / `risk_candidates` / `important_flow_candidates`：需要人工关注的风险与流程候选。
- `missing_capabilities`：缺失能力，不伪装成 TODO。

## 测试与质量

覆盖文件：`tests/test_*.py`，运行 `python3 -m unittest discover tests`。

重点测试行为：

- 标准扫描写出保守事实。
- 深度扫描提取文档提示与缺失能力。
- 校验器接受最小有效 harness。
- 校验器拒绝未验证命令、运行时猜测、缺失脚本、缺失必需文件、过长 `AGENTS.md`、含 `Unknown` 的文档。
- 扫描器跳过 `.agent`，识别 CI、Makefile、pre-commit、Python 配置、monorepo manifest。

## 常见问题 (FAQ)

### 为什么不自动猜 `pytest`、`pnpm test` 或 `make test`？

因为猜命令会让 Agent 写出假文档。这个模块的核心规则是：候选就是候选，验证过才是命令。

### 为什么 `.agent/` 被跳过？

`.agent/repo-facts.json` 是可再生成扫描产物。把生成物重新当作源事实会污染扫描结果。

### 能不能把缺失能力都写 TODO？

不能。明确不存在的能力写 `Not configured`。只有用户明确要求后续跟进，才写 TODO。

## 相关文件清单

- `scripts/scan_repo.py`
- `scripts/validate_harness_docs.py`
- `tests/`
- `references/templates.md`
- `references/repo-facts.md`
- `SKILL.md`
