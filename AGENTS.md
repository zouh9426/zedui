# AGENTS.md — zedui 项目级规则

本文件约束**本仓库的维护者 agent**（迭代 zedui skill 本身时的纪律）。`zedui/SKILL.md` 约束的是**使用方 agent**（在用户项目里跑 UI 工作流时的行为），两者别混。

## 仓库性质

- 公开开源仓库（GitHub: `zedui`），MIT 协议，Copyright (c) 2026 zouh9426。
- 仓库内容：`zedui/`（skill 本体：SKILL.md + scripts/）、双语文档（README / SETUP）、CHANGELOG、LICENSE、CI。
- 面向所有 AI 编码工具（Kimi Code / Claude Code / Codex 等），**不得偏向任何单一工具**。

## 红线

1. **任何文件不得包含私人绝对路径**（`/Users/...`、个人 home 目录、本机特有配置）。SKILL.md 用「环境探测」机制在运行时解析路径，源码里永不写死。
2. 提交前必须跑：`grep -rnE '/Users/[a-zA-Z0-9_-]+/' . --exclude-dir=.git`，有输出就不许 commit（该模式只匹配真实路径，不会误伤规则自身的描述文字）。CI（`.github/workflows/no-private-paths.yml`）会在 push 时兜底检查，红了必须修。
3. 不留垃圾文件：交接文档、临时试点产物等用完即删，不进仓库。
4. **实测依据一律匿名化**：CHANGELOG / commit message / Release notes / 文档中引用实战项目时，禁止出现用户项目名、内部任务编号、项目内路径等可识别信息——一律写"某生产项目"这类通用表述。公开仓库里，可识别信息与隐私同罪；已发生泄漏时连 git 历史一起改写清除。

## 迭代纪律（每次改动都要做到）

1. **改代码必写 CHANGELOG.md**：条目回答两个问题——改了什么、为什么这么改（决策理由）。
2. **改完同步 GitHub**：commit + push；每个正式版本打 tag 并建 GitHub Release，历史版本快照永不删除。
3. **双语文档同步**：README.md ↔ README.en.md、SETUP.md ↔ SETUP.en.md，改了一边另一边必须在同一次迭代里跟上。中文是主门面（目标用户以中文用户为主），英文版跟随。
4. **SKILL.md 的工作流逻辑改动要克制**：这是经过多轮试点验证的流程，改动需在 CHANGELOG 里写明实测依据，不凭感觉改。

## 真源纪律（仅维护者本机适用，不进任何仓库文件）

skill 本体的唯一真源在本仓库 `zedui/` 目录。线上生效位置 `~/.kimi-code/skills/zedui` 是**指向真源的符号链接**，不是副本。任何修改只改真源（仓库），线上零操作自动生效；发现线上是普通目录时（例如从旧机器恢复、照抄了旧版 rsync 部署），立即迁回并重建链接：

```bash
# 前置：diff -rq 确认真源与线上副本无差异（有差异则以仓库版为准先合并）
diff -rq zedui/ ~/.kimi-code/skills/zedui/
rm -rf ~/.kimi-code/skills/zedui
ln -s <zedui 仓库路径>/zedui ~/.kimi-code/skills/zedui
```

历史注记：本节曾记录"Kimi Code 加载器不跟随符号链接，踩过坑"并采用 rsync 副本模式；2026-08-11 在 v0.34.0 上经对照实验证伪（符号链接 skill 与真实目录 skill 均正常加载），已统一为符号链接模式。
