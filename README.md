# Harness

`harness` 是一个 Codex Skill，用于在接手陌生、老旧或大型仓库时，先把仓库事实沉淀成可验证的文档和检查脚本，降低 Agent 误改、猜测命令或触碰高风险区域的概率。

核心原则：先扫描事实，再写文档；能验证的写清楚，不能验证的明确标注，不凭经验猜架构、测试命令或生成文件规则。

## 适用场景

- 接手结构不清晰的老项目或多模块项目。
- 需要生成或更新 `AGENTS.md`、项目地图、测试说明、危险区域说明等 Agent 工作入口。
- 仓库里存在认证、权限、支付、迁移、部署、密钥、生成代码或公开 API 等高风险区域。

不适合用来写一次性的任务说明，也不适合替代项目自身的业务文档。

## 目录结构

```text
.
├── SKILL.md                         # Skill 入口和执行规范
├── AGENTS.md                        # 本仓库贡献者指南
├── scripts/
│   ├── scan_repo.py                 # 扫描目标仓库并生成 .agent/repo-facts.json
│   └── validate_harness_docs.py     # 校验目标仓库的 harness 文档
├── tests/
│   └── test_harness_scripts.py      # 脚本单元测试
├── references/
│   └── templates.md                 # harness 文档模板
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
python3 scripts/scan_repo.py --deep --limit 20000 /path/to/repo
```

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

本仓库没有 `package.json` 或构建步骤，主要由 Python 标准库脚本和 Markdown 文档组成。

运行测试：

```bash
python3 -m unittest tests/test_harness_scripts.py
```

修改脚本时，优先补充 `tests/test_harness_scripts.py` 中的行为测试。修改文档时，保持内容短、具体、可执行，避免把 README 或 `AGENTS.md` 写成大型提示词。

## 输出约定

- 不确定的事实写 `Needs human confirmation`。
- 明确不存在的能力写 `Not configured`。
- 只有用户明确希望后续跟进的事项才写 `TODO`。
- `scripts/check.sh` 只能调用已验证存在的脚本或命令，不能动态猜测测试命令。

## 设计边界

Harness 不是自动开发框架，也不是某个模型提示词集合。它的目标是给 Agent 提供工程化运行边界：仓库地图、验证入口、高风险提示和最小必要流程。
