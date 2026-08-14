# zedui

> weft = 纬线。四个独立的 UI skill 是纬线，`DESIGN.md` 是经纱——zedui 把它们织成一匹不漂移的布。
> (weft: the crosswise threads in weaving. The four independent UI skills are the wefts, and `DESIGN.md` is the warp — zedui weaves them into a cloth that doesn't drift.)

[中文](README.md) · [Setup guide prompt](SETUP.en.md) · [Changelog](CHANGELOG.md)

zedui is a **workflow orchestration skill**: it doesn't do design or review itself. Instead, it chains four mature UI skills into a spec-constrained pipeline, solving the biggest pain point of multi-skill collaboration — **each skill invents its own spec file, so outputs inevitably drift**.

Works with any AI coding tool that supports SKILL.md skills (Kimi Code / Claude Code / Codex, etc.).

## Workflow

```
Phase 0 Kickoff: orchestration-layer questions (≤5) → UUPM proposes a direction → user confirms → bridge script generates DESIGN.md
Phase 1 Production: routed by page type → Taste (marketing-facing) / interface-design (product-facing), all governed by DESIGN.md
Phase 2 Review: context.mjs guidance (once per session) → critique (A/B isolated) → audit → zedui hard gate (mechanical detector diff + browser-engine scan) → fixes routed back to producers → re-review
Iteration: every UI change goes through Phase 1 → Phase 2; spec evolution happens only by editing DESIGN.md
```

| Role | Skill | Upstream |
|---|---|---|
| Kickoff & direction | `ui-ux-pro-max` | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) |
| Marketing-facing production | `design-taste-frontend` | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| Product-facing production | `interface-design` | [Dammyjay93/interface-design](https://github.com/Dammyjay93/interface-design) |
| Review (review only, never fix) | `impeccable` | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) |

## Core design decisions

- **A single `DESIGN.md` as the single source of truth (SSOT)**: all global visual decisions (color / typography / spacing / radius / dial) may only live in the project-root `DESIGN.md` (YAML frontmatter + fixed sections); no second spec file is allowed. On conflict, `DESIGN.md > skill-internal default rules`.
- **Format bridging**: the JSON produced by UUPM is mechanically converted into DESIGN.md by `scripts/uupm_to_design.py`; mechanical conversion plus script-side checks keep the format stable and parser-friendly — never hand-written. The write is fail-closed: missing color roles / fonts / dials, or a type scale with fewer than 6 steps, aborts with an error; only an explicit `--allow-incomplete` writes TBD placeholders for a partial draft.
- **The token layer is generated, never hand-edited**: the frontmatter is the single source of truth; both the token table inside the `<!-- zedui:generated:* -->` markers in the DESIGN.md body and the code-side `tokens.css` are derived artifacts, mechanically produced by the bridge script — in JSON mode via `--tokens-css`, and on spec evolution via `--from-design`, which rewrites the body table and tokens.css together from the frontmatter. Hand-editing them is forbidden. Literal values may live only in the token definition layer; component and page code may only reference token variables.
- **Human checkpoint at kickoff**: the proposal is laid out to the user for item-by-item confirmation (covering four known weak spots: secondary text color, neutral ink, dark tokens, and the CJK font stack) before it is written to disk; without confirmation, no DESIGN.md is produced.
- **Review only, never fix**: the detector's four `design-system-*` rules mechanically diff the code against DESIGN.md; any drift is a finding. Fixes are routed back to the producer, then re-reviewed and archived.

## Prerequisites

1. **The four companion skills** (see the table above — all third-party open source; install them into your AI tool's skills directory yourself)
2. **Python 3** (for the UUPM search script and the bridge script — both pure standard library)
3. **Node.js** (for the Impeccable detector)
4. Optional but strongly recommended: **system Chrome/Chromium** (for browser-engine scanning, which catches spacing/contrast/touch issues at the computed-style layer)

## Installation

**Recommended (let your AI do it)**: open [SETUP.en.md](SETUP.en.md) and paste the entire file into your AI agent — it will check dependencies, install the five skills, configure the browser engine, and run self-checks automatically.

**Manual**: copy this repo's `zedui/` directory into your AI tool's skills directory (e.g. `~/.agents/skills/`, `~/.claude/skills/`, `~/.kimi-code/skills/`, `~/.codex/skills/`) and install the four companion skills per the table above. Skills recognize each other by the `name:` field in their frontmatter — directory names and tools don't matter.

## Usage

Once installed, trigger it in your project by telling your AI something like:

> "Use zedui to build the UI for this project" / "Redesign this landing page following the zedui flow"

The first use enters Phase 0: the AI asks you 3–5 questions, proposes a design direction, and generates `DESIGN.md` once you confirm. After that, production and review for every page run through the pipeline automatically.

## Repository structure

```
zedui/
├── SKILL.md                    ← the orchestration workflow itself (tool-agnostic; probes paths at runtime)
├── scripts/uupm_to_design.py   ← bridge: UUPM JSON → DESIGN.md; DESIGN.md frontmatter → body generated table + tokens.css (stdlib only; artifacts never hand-edited)
├── scripts/token_lint.py       ← spacing literal lint (closes the gap where the upstream detector doesn't cover spacing)
└── scripts/doctor.py           ← environment health check (full-pipeline self-check)
README.md / README.en.md        ← bilingual front doors (CN / EN)
SETUP.md / SETUP.en.md          ← setup guide prompt (paste it to your AI)
CHANGELOG.md                    ← changelog and decision log
```

## License

[MIT](LICENSE) · Copyright (c) 2026 zouh9426

The four companion skills are licensed by their respective authors; check their upstream repos before installing.
