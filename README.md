# zedui

> weft = 纬线。四个独立的 UI skill 是纬线，`DESIGN.md` 是经纱——zedui 把它们织成一匹不漂移的布。

[English](README.en.md) · [安装引导提示词](SETUP.md) · [更新日志](CHANGELOG.md)

zedui 是一个**工作流编排 skill**：它自身不做设计、不做审查，而是把四个成熟的 UI skill 串成一条有规范约束的流水线，解决多 skill 协作时最大的痛点——**每个 skill 各自发明规范文件，产出必然漂移**。

适用于所有支持 SKILL.md 技能的 AI 编码工具（Kimi Code / Claude Code / Codex 等）。

## 工作流

```
Phase 0 开局：编排层提问（≤5 问）→ UUPM 出方案 → 用户确认 → 桥接脚本生成 DESIGN.md
Phase 1 生产：按页面类型路由 → Taste（营销面）/ interface-design（产品面），全部以 DESIGN.md 为规范
Phase 2 审查：Impeccable detector 双层扫描（源码 + 浏览器引擎）→ critique/audit → 修复回流生产者 → 复评
迭代期：任何 UI 变更都走 Phase 1 → Phase 2；规范演进只通过修改 DESIGN.md
```

| 角色 | Skill | 上游 |
|---|---|---|
| 开局定方向 | `ui-ux-pro-max` | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) |
| 营销面生产 | `design-taste-frontend` | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| 产品面生产 | `interface-design` | [Dammyjay93/interface-design](https://github.com/Dammyjay93/interface-design) |
| 审查（只审不修） | `impeccable` | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) |

## 核心设计决策

- **单一 `DESIGN.md` 作唯一事实源（SSOT）**：所有全局视觉决策（色彩/字体/间距/圆角/dial）只许写进项目根的 `DESIGN.md`（YAML frontmatter + 固定章节），禁止任何第二份规范文件。冲突时 `DESIGN.md > skill 内部默认规则`。
- **格式桥接**：UUPM 产出的 JSON 经 `scripts/uupm_to_design.py` 机械转换为 DESIGN.md，保证审查器可解析的格式 100% 稳定，不手写。
- **token 唯一定义层（生成物禁手改）**：代码侧 `tokens.css` 由桥接脚本从 DESIGN.md frontmatter 机械生成——JSON 模式随文档一起产出（`--tokens-css`），规范演进时用 `--from-design` 反解 frontmatter 重新生成；它是生成物，永不允许手改。字面值只许出现在 token 定义层，组件/页面代码只许引用 token 变量。
- **开局人工卡点**：方案摊给用户逐项确认（含次级文字色、中性墨色、暗色 token、CJK 字体栈四个已知短板）后才落盘，无确认的 DESIGN.md 不动工。
- **审查只审不修**：detector 的 `design-system-*` 四条规则机械比对代码与 DESIGN.md，漂移即 finding；修复回流给生产者，改完复评留档。

## 前置条件

1. **四个配套 skill**（见上表，均为第三方开源作品，需自行安装到你的 AI 工具的技能目录）
2. **Python 3**（UUPM 检索脚本与桥接脚本，均纯标准库）
3. **Node.js**（Impeccable detector）
4. 可选：**系统 Chrome/Chromium**（浏览器引擎扫描，能看到计算样式层的间距/对比度/触控问题，强烈建议）

## 安装

**推荐方式（AI 代办）**：打开 [SETUP.md](SETUP.md)，把全文贴给你的 AI agent，它会自动检查依赖、安装五个 skill、配置浏览器引擎并自检。

**手动方式**：把本仓库的 `zedui/` 目录拷进你的 AI 工具的技能目录（如 `~/.agents/skills/`、`~/.claude/skills/`、`~/.kimi-code/skills/`、`~/.codex/skills/`），并按上表安装四个配套 skill。skill 之间按 frontmatter 的 `name:` 互相识别，不挑目录名、不挑工具。

## 使用

装好后，在你的项目里对 AI 说一句类似的话即可触发：

> "用 zedui 给这个项目做 UI" / "按 zedui 流程改版这个落地页"

第一次使用会进入 Phase 0：AI 会问你 3~5 个问题，给出设计方向方案，你确认后生成 `DESIGN.md`，之后每个页面的生产和审查都自动走流水线。

## 仓库结构

```
zedui/
├── SKILL.md                    ← 编排工作流本体（工具无关，运行时探测路径）
└── scripts/uupm_to_design.py   ← 桥接脚本：UUPM JSON → DESIGN.md；DESIGN.md frontmatter → tokens.css（纯标准库；tokens.css 为生成物，禁手改）
README.md / README.en.md        ← 中英双门面
SETUP.md / SETUP.en.md          ← 安装引导提示词（贴给你的 AI 即可）
CHANGELOG.md                    ← 更新与决策日志
```

## 许可证

[MIT](LICENSE) · Copyright (c) 2026 zouh9426

四个配套 skill 的许可证归各自作者所有，安装前请查阅其上游仓库。
