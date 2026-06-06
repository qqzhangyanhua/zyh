[根目录](../CLAUDE.md) > **tests**

# tests 模块

## 变更记录 (Changelog)

| 时间 | 类型 | 说明 |
| --- | --- | --- |
| 2026-06-06 13:12:21 | 增量复扫 | 复核 `test_harness_scripts.py`，测试集与文档一致，无变化。 |
| 2026-06-05 20:33:44 | 初始化 | 生成 tests 模块 Claude 工作文档。 |

## 模块职责

`tests/` 负责保护 `scripts/` 的外部行为，尤其是“不要猜命令、不要夸大事实、不要漏掉高风险候选”这些核心约束。

## 入口与启动

测试入口：

```sh
python3 -m unittest tests/test_harness_scripts.py
```

## 对外接口

该模块没有生产 API。它通过 `subprocess.run` 执行仓库内脚本，验证 CLI 返回码、标准输出和生成的 JSON 内容。

## 关键依赖与配置

- Python 标准库：`unittest`、`tempfile`、`subprocess`、`json`、`pathlib`。
- Not configured：无独立测试配置文件。

## 数据模型

测试主要构造临时目标仓库：

- 临时目录作为目标 repo。
- 写入最小脚本、文档、manifest、CI、风险路径或配置文件。
- 执行 `scan_repo.py` 或 `validate_harness_docs.py`。
- 读取 `.agent/repo-facts.json` 或检查输出错误。

## 测试与质量

当前测试覆盖：

- 扫描基础事实、脚本、manifest、测试、生成文件和风险候选。
- 深度扫描文档提示与缺失能力。
- CI、Makefile、pre-commit、bin 脚本、Python 配置、monorepo manifest 检测。
- 校验器接受有效 harness。
- 校验器拒绝未验证命令、运行时猜测、缺失脚本引用、非可执行 `check.sh`、缺失必需文件、文档中的 `Unknown`、过长 `AGENTS.md`。

## 常见问题 (FAQ)

### 修改扫描逻辑时最容易破坏什么？

最容易破坏的是候选事实与已验证事实的边界。新增检测时必须判断它是事实、候选还是缺失能力。

### 为什么测试用临时目录？

这样不会污染真实仓库，也能精确控制输入。测试数据结构比 mock 更清楚。

## 相关文件清单

- `tests/test_harness_scripts.py`
- `scripts/scan_repo.py`
- `scripts/validate_harness_docs.py`
