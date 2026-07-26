[根目录](../CLAUDE.md) > **scripts**

# scripts 模块

## 变更记录 (Changelog)

| 时间 | 类型 | 说明 |
| --- | --- | --- |
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
| `scripts/scan_repo.py` | `main()` | `python3 scripts/scan_repo.py /path/to/repo` |
| `scripts/validate_harness_docs.py` | `main()` | `python3 scripts/validate_harness_docs.py /path/to/repo` |

`scan_repo.py` 支持：

```sh
python3 scripts/scan_repo.py --deep --limit 20000 /path/to/repo
```

## 对外接口

这是 CLI 脚本模块，没有 HTTP/API 服务。

### `scan_repo.py`

- 输入：目标仓库路径、可选 `--deep`、`--limit`、`--output`。
- 输出：默认写入目标仓库 `.agent/repo-facts.json`，并打印输出路径。
- 事实字段包括：顶层结构、manifest、配置、文档、脚本(含嵌套)、CI、测试文件、生成文件候选、风险候选、重要流程候选、缺失能力、`truncated` 截断标记。

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

覆盖文件：`tests/test_harness_scripts.py`。

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
- `tests/test_harness_scripts.py`
- `references/templates.md`
- `SKILL.md`
