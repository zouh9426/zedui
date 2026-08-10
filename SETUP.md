# zedui 安装引导提示词

> **用法**：把本文件**全部内容**（从下面分隔线开始）复制贴给你的 AI agent（Kimi Code / Claude Code / Codex 等均可），它会自动完成全套安装与自检。
> English version: [SETUP.en.md](SETUP.en.md)

---

你是安装助手。请帮我安装 **zedui**（UI 规范编排 skill）及其四个配套 skill。按以下步骤执行，每步完成后告诉我结果；任何一步失败，停下来报告，不要跳过。

## 第 1 步：识别环境

1. 确认你是什么工具（Kimi Code / Claude Code / Codex / 其他），确定你的技能目录。常见候选：
   - `~/.agents/skills/`（通用约定）
   - `~/.kimi-code/skills/`（Kimi Code）
   - `~/.claude/skills/`（Claude Code）
   - `~/.codex/skills/`（Codex）
   如果你的工具另有约定的技能目录，以你的约定为准。
2. 检查依赖工具：`python3 --version`、`node --version`。缺哪个先告诉我安装方法并停下。
3. （可选但建议）检查系统是否有 Chrome/Chromium，记录可执行文件路径（macOS 通常是 `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`），后面浏览器引擎要用。

## 第 2 步：检查已有安装

在技能目录下逐层找 `SKILL.md`，读 frontmatter 的 `name:` 字段，检查以下五个 skill 是否已安装（**按 name 匹配，不按目录名**——目录名可能与 skill 名不同）：

| skill 名 | 作用 |
|---|---|
| `zedui` | 编排层本体 |
| `ui-ux-pro-max` | 开局定方向 |
| `design-taste-frontend` | 营销面生产 |
| `interface-design` | 产品面生产 |
| `impeccable` | 审查 |

列出"已有 / 缺失"清单给我。

## 第 3 步：安装缺失的 skill

- **zedui**：`git clone https://github.com/zouh9426/zedui` 到临时目录，把其中的 `zedui/` 子目录拷进技能目录。
- **四个配套 skill**：按各自上游仓库的 README 指引安装到同一技能目录：
  - `ui-ux-pro-max` → https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
  - `design-taste-frontend` → https://github.com/Leonxlnx/taste-skill
  - `interface-design` → https://github.com/Dammyjay93/interface-design
  - `impeccable` → https://github.com/pbakaus/impeccable
- 优先使用上游提供的官方安装方式（npm CLI / `npx skills add` 等）；没有就把仓库里的 skill 目录拷进技能目录。安装后再次按 `name:` 核实五个 skill 全部就位。

## 第 4 步：配置 Impeccable 浏览器引擎（可选，强烈建议）

如果第 1 步找到了 Chrome/Chromium：

```bash
cd <技能目录下 impeccable 的实际位置> && PUPPETEER_SKIP_DOWNLOAD=1 npm i puppeteer
export PUPPETEER_EXECUTABLE_PATH="<你的 Chrome 可执行文件路径>"
```

并告诉我：以后跑浏览器引擎扫描的会话里都需要这个环境变量（建议写进 shell 配置）。

## 第 5 步：自检

依次运行（路径用第 2/3 步解析出的实际位置）：

1. `python3 <ui-ux-pro-max>/scripts/search.py "dashboard" --domain style` —— 应返回风格建议而非报错
2. `node <impeccable>/scripts/detector/detect-antipatterns.mjs --help`（若该路径不存在，在 impeccable 目录内搜索 `detect-antipatterns.mjs` 的实际位置）—— 应输出用法说明
3. `python3 <zedui>/scripts/uupm_to_design.py --help` —— 应输出用法说明

三项全过后，向我汇报：五个 skill 的安装路径、Chrome 路径（如配置）、以及一句确认——"zedui 安装完成，对你的项目说『用 zedui 做 UI』即可开始"。
