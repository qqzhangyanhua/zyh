[根目录](../CLAUDE.md) > **references**

# references 模块

## 变更记录 (Changelog)

| 时间 | 类型 | 说明 |
| --- | --- | --- |
| 2026-06-06 13:12:21 | 增量复扫 | 复核 `templates.md`，模板结构与约束未变化。 |
| 2026-06-05 20:33:44 | 初始化 | 生成 references 模块 Claude 工作文档。 |

## 模块职责

`references/` 存放 harness 文档模板。它不是泛用提示词仓库，而是生成目标仓库安全工作入口的模板来源。

## 入口与启动

入口文件：`references/templates.md`。

`SKILL.md` 要求生成或更新目标仓库文档时使用这个模板来源。

## 对外接口

无代码 API。模板定义以下目标文件结构：

- `AGENTS.md`
- `docs/project-map.md`
- `docs/testing.md`
- `docs/dangerous-areas.md`
- `docs/debugging.md`
- `docs/agent-plan-template.md`
- `scripts/check.sh`

## 关键依赖与配置

- 类型：Markdown 模板。
- Not configured：无构建、渲染或模板引擎。

## 数据模型

模板以 `.agent/repo-facts.json` 为事实来源，要求缺失信息明确分类：

- `Not configured`：扫描和文档都显示能力不存在。
- `Needs human confirmation`：存在候选但无权威来源。
- `TODO`：仅用于用户明确要求后续跟进的工作。

## 测试与质量

模板约束由 `scripts/validate_harness_docs.py` 和 `tests/test_harness_scripts.py` 间接保护。尤其要保持：

- `AGENTS.md` 只做入口，不塞成长文档。
- `scripts/check.sh` 只能调用已存在脚本或打印待配置状态。
- 危险区域文档必须覆盖扫描到的风险原因。

## 常见问题 (FAQ)

### 能不能在模板里放 `pytest` 或 `pnpm test`？

不能。除非目标仓库已有并已验证，否则只能列为候选或 `Not configured`。

### 为什么模板反复强调 `Not configured`？

因为噪声 TODO 会误导 Agent。明确不存在的东西不该伪装成待办。

## 相关文件清单

- `references/templates.md`
- `SKILL.md`
- `scripts/validate_harness_docs.py`
