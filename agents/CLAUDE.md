[根目录](../CLAUDE.md) > **agents**

# agents 模块

## 变更记录 (Changelog)

| 时间 | 类型 | 说明 |
| --- | --- | --- |
| 2026-06-06 13:12:21 | 增量复扫 | 复核 `openai.yaml`，元数据未变化。 |
| 2026-06-05 20:33:44 | 初始化 | 生成 agents 模块 Claude 工作文档。 |

## 模块职责

`agents/` 保存 Agent 平台元数据，用来描述 skill 的展示名称、简短说明和默认提示。

## 入口与启动

入口文件：`agents/openai.yaml`。

## 对外接口

无运行时 API。当前 YAML 暴露：

- `interface.display_name`
- `interface.short_description`
- `interface.default_prompt`

## 关键依赖与配置

- 类型：YAML 元数据。
- Not configured：无 schema 校验器、无生成流程。

## 数据模型

`interface` 是唯一顶层对象，描述该 skill 在 Agent 环境中的呈现方式。

## 测试与质量

当前没有专门测试覆盖 `agents/openai.yaml`。如果未来这个文件参与发布或平台加载，应该增加最小 schema 校验。

## 常见问题 (FAQ)

### 这里能不能放执行规则？

不要。执行规则属于 `SKILL.md`，用户说明属于 `README.md` 或 `AGENTS.md`。这里应该只放平台元数据。

## 相关文件清单

- `agents/openai.yaml`
- `SKILL.md`
