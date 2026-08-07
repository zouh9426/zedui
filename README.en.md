# UIweft

> weft = 纬线。四个独立的 UI skill 是纬线，`DESIGN.md` 是经纱——UIweft 把它们织成一匹不漂移的布。
> (weft: the crosswise threads in weaving. The four independent UI skills are the wefts, and `DESIGN.md` is the warp — UIweft weaves them into a cloth that doesn't drift.)

[中文](README.md) · [Setup guide prompt](SETUP.md) · [Changelog](CHANGELOG.md)

UIweft is a **workflow orchestration skill**: it doesn't do design or review itself. Instead, it chains four mature UI skills into a spec-constrained pipeline, solving the biggest pain point of multi-skill collaboration — **each skill invents its own spec file, so outputs inevitably drift**.

Works with any AI coding tool that supports SKILL.md skills (Kimi Code / Claude Code / Codex, etc.).

## Workflow

```
Phase 0 开局：编排层提问（≤5 问）→ UUPM 出方案 → 用户确认 → 桥接脚本生成 DESIGN.md
Phase 1 生产：按页面类型路由 → Taste（营销面）/ interface-design（产品面），全部以 DESIGN.md 为规范
Phase 2 审查：Impeccable detector 双层扫描（源码 + 浏览器引擎）→ critique/audit → 修复回流生产者 → 复评
迭代期：任何 UI 变更都走 Phase 1 → Phase 2；规范演进只通过修改 DESIGN.md
```

| Role | Skill | Upstream |
|---|---|---|
| Kickoff & direction | `ui-ux-pro-max` | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) |
| Marketing-facing production | `design-taste-frontend` | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| Product-facing production | `interface-design` | [Dammyjay93/interface-design](https://github.com/Dammyjay93/interface-design) |
| Review (review only, never fix) | `impeccable` | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) |

## Core design decisions

- **A single `DESIGN.md` as the single source of truth (SSOT)**: all global visual decisions (color / typography / spacing / radius / dial) may only live in the project-root `DESIGN.md` (YAML frontmatter + fixed sections); no second spec file is allowed. On conflict, `DESIGN.md > skill-internal default rules`.
- **Format bridging**: the JSON produced by UUPM is mechanically converted into DESIGN.md by `scripts/uupm_to_design.py`, guaranteeing a 100% stable, parser-friendly format — never hand-written.
- **Human checkpoint at kickoff**: the proposal is laid out to the user for item-by-item confirmation (covering four known weak spots: secondary text color, neutral ink, dark tokens, and the CJK font stack) before it is written to disk; without confirmation, no DESIGN.md is produced.
- **Review only, never fix**: the detector's four `design-system-*` rules mechanically diff the code against DESIGN.md; any drift is a finding. Fixes are routed back to the producer, then re-reviewed and archived.

## Prerequisites

1. **The four companion skills** (see the table above — all third-party open source; install them into your AI tool's skills directory yourself)
2. **Python 3** (for the UUPM search script and the bridge script — both pure standard library)
3. **Node.js** (for the Impeccable detector)
4. Optional but strongly recommended: **system Chrome/Chromium** (for browser-engine scanning, which catches spacing/contrast/touch issues at the computed-style layer)

## Installation

**Recommended (let your AI do it)**: open [SETUP.md](SETUP.md) and paste the entire file into your AI agent — it will check dependencies, install the five skills, configure the browser engine, and run self-checks automatically.

**Manual**: copy this repo's `uiweft/` directory into your AI tool's skills directory (e.g. `~/.agents/skills/`, `~/.claude/skills/`, `~/.kimi-code/skills/`, `~/.codex/skills/`) and install the four companion skills per the table above. Skills recognize each other by the `name:` field in their frontmatter — directory names and tools don't matter.

## Usage

Once installed, trigger it in your project by telling your AI something like:

> "Use uiweft to build the UI for this project" / "Redesign this landing page following the uiweft flow"

The first use enters Phase 0: the AI asks you 3–5 questions, proposes a design direction, and generates `DESIGN.md` once you confirm. After that, production and review for every page run through the pipeline automatically.

## Repository structure

```
uiweft/
├── SKILL.md                    ← 编排工作流本体（工具无关，运行时探测路径）
└── scripts/uupm_to_design.py   ← UUPM JSON → DESIGN.md 桥接脚本（纯标准库）
README.md / README.en.md        ← 中英双门面
SETUP.md / SETUP.en.md          ← 安装引导提示词（贴给你的 AI 即可）
CHANGELOG.md                    ← 更新与决策日志
```

## License

[MIT](LICENSE) · Copyright (c) 2026 zouh9426

The four companion skills are licensed by their respective authors; check their upstream repos before installing.
