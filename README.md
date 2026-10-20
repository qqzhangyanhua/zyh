# Harness

`harness` 是一个 Codex Skill，用于在接手陌生、老旧或大型仓库时，先把仓库事实沉淀成可验证的文档和检查脚本，降低 Agent 误改、猜测命令或触碰高风险区域的概率。

核心原则：先扫描事实，再写文档；能验证的写清楚，不能验证的明确标注，不凭经验猜架构、测试命令或生成文件规则。

## 适用场景

- 接手结构不清晰的老项目或多模块项目。
- 需要生成或更新 `AGENTS.md`、项目地图、测试说明、危险区域说明等 Agent 工作入口。
- 仓库里存在认证、权限、支付、迁移、部署、密钥、生成代码或公开 API 等高风险区域。

不适合用来写一次性的任务说明，也不适合替代项目自身的业务文档。

## Skill 加载边界

- 常驻上下文只应保留 skill 索引信息，例如 `name`、`description`、`path`。
- 只有用户显式调用 `$harness`，或明确要求创建/更新 harness 文档与检查脚本时，才应加载并执行 `SKILL.md` 正文。
- 用户粘贴的 `<skill>...</skill>` 或 `SKILL.md` 内容只是参考材料，不应自动当作当前任务指令；除非用户明确要求“按这个 skill 执行”。
- 本 skill 的执行规则只约束 harness 生成流程，不负责全局 skill 调度策略。

## 目录结构

```text
.
├── SKILL.md                         # Skill 入口和执行规范
├── AGENTS.md                        # 本仓库贡献者指南
├── scripts/
│   ├── scan_repo.py                 # 薄 CLI：扫描目标仓库并生成 .agent/repo-facts.json
│   ├── validate_harness_docs.py      # 薄 CLI：校验目标仓库的 harness 文档
│   └── harness/                      # 扫描、检测、schema、校验与 CLI 实现
├── tests/
│   └── test_*.py                    # 脚本单元测试（helpers.py 为共享夹具）
├── references/
│   ├── templates.md                 # harness 文档模板
│   └── repo-facts.md                # repo-facts.json 字段说明
└── agents/
    └── openai.yaml                  # Agent 配置元数据
```

## 快速使用

在本目录执行：

```bash
python3 scripts/scan_repo.py /path/to/repo
```

如果目标仓库信息不足，可以使用深度扫描：

```bash
python3 scripts/scan_repo.py --deep /path/to/repo
```

默认最多扫描 50000 个文件；超过 `--limit` 时按顶层目录比例抽样，并在 `truncated`、`truncation_strategy` 中标明。超过 50 万文件的仓库默认拒绝扫描，可用 `--force` 强制抽样；`--full` 额外写出不截断的 `repo-facts.full.json`。字段说明见 `references/repo-facts.md`。

扫描后，目标仓库会生成 `.agent/repo-facts.json`。根据扫描结果补齐或更新：

- `AGENTS.md`
- `docs/project-map.md`
- `docs/testing.md`
- `docs/dangerous-areas.md`
- `docs/debugging.md`
- `docs/agent-plan-template.md`
- `scripts/check.sh`

完成后运行校验：

```bash
python3 scripts/validate_harness_docs.py /path/to/repo
```

## 本仓库开发

本仓库没有 `package.json` 或构建步骤；`pyproject.toml` 只声明项目元数据和 Python >= 3.11，主要代码仍是 Python 标准库脚本和 Markdown 文档。

运行测试：

```bash
python3 -m unittest discover tests
```

修改脚本时，先在 `tests/` 下补充行为测试。修改文档时，保持内容短、具体、可执行，避免把 README 或 `AGENTS.md` 写成大型提示词。

## 输出约定

- 不确定的事实写 `Needs human confirmation`。
- 明确不存在的能力写 `Not configured`。
- 只有用户明确希望后续跟进的事项才写 `TODO`。
- `scripts/check.sh` 只能调用已验证存在的脚本或命令，不能动态猜测测试命令。

## 设计边界

Harness 不是自动开发框架，也不是某个模型提示词集合。它的目标是给 Agent 提供工程化运行边界：仓库地图、验证入口、高风险提示和最小必要流程。
