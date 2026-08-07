# CHANGELOG

本项目所有值得记录的变更都写在这里。格式约定：每条目回答两个问题——**改了什么**、**为什么这么改（决策理由）**。

## [0.2.0] - 2026-08-07

开源发布 + 工具无关化改造。

- **SKILL.md 移除全部硬编码安装路径**（原 `~/.agents/skills/...`、`~/.kimi-code/skills/...`），新增「环境探测」一节：agent 会话开始时在候选技能目录（`~/.agents/skills/`、`~/.kimi-code/skills/`、`~/.claude/skills/`、`~/.codex/skills/`、项目级 `.agents/skills/`）中**按 SKILL.md frontmatter 的 `name:` 字段**解析五个 HOME 变量，全文命令改用 `$XXX_HOME` 占位。理由：开源后面向 Kimi Code / Claude Code / Codex 等所有工具，路径硬编码等于私有；且目录名与 skill 名可能不一致（如 `taste-skill/` 目录装的是 `design-taste-frontend`），必须按名解析。
- **新增 README.md（中文主门面）/ README.en.md**：项目介绍、前置依赖、安装指引、快速上手。理由：开源门面；中文为主是因为目标用户群是中文用户。
- **新增 SETUP.md / SETUP.en.md 安装引导提示词**：用户贴给自己的 AI agent 即可完成全套依赖检查与安装。理由：四个配套 skill 均为第三方依赖，手动安装门槛高，让 AI 代办最省事。
- **新增 LICENSE（MIT，Copyright (c) 2026 zouh9426）**。理由：MIT 的「保留版权声明」条款即署名保留，满足作者诉求；skill 类项目无专利考量，不需要 Apache-2.0 的重量。
- **新增 AGENTS.md**：迭代纪律（同步 GitHub、写日志、双语同步、无私有路径红线）。
- **新增 GitHub Actions 私有路径检查 CI**。理由：防止后续迭代把本地路径误提交到公开仓库（设计已消除必要性，CI 做兜底）。

## [0.1.0] - 2026-08-07

基线快照。从旧工作区（UIweave_Skill）迁入的原始版本，路径为硬编码、仅供历史留档，不建议新用户使用。

继承自旧工作区的核心架构决策（详见 README）：

- UIweft 定位为四个 UI skill 的**工作流编排层**，自身无设计/审查能力：UUPM 定方向 → Taste/interface-design 按页面类型生产 → Impeccable 只审不修。
- **单一 DESIGN.md 作 SSOT**（Impeccable 的 google-labs 规范格式，YAML frontmatter），禁止一切平行规范文件；冲突优先级 `DESIGN.md > skill 内部默认规则`。
- UUPM JSON → DESIGN.md 走 `uupm_to_design.py` 机械桥接，保证 detector 可解析格式 100% 稳定。
- 开局人工卡点：UUPM 不提问，提问由编排层做（≤5 问，含内容语言、图片生成能力检测）；方案确认后才落盘 DESIGN.md。
- 修复回流生产者；豁免前决策必须先备案进 DESIGN.md。
- 经三轮模拟试点（三个模拟项目）验证，累计修进 SKILL.md 9+ 处优化。
