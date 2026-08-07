# UIweft Setup Guide Prompt

> **Usage**: copy the **entire content** of this file (starting from the divider below) and paste it to your AI agent (Kimi Code / Claude Code / Codex, etc.). It will automatically complete the full installation and self-check.
> 中文版：[SETUP.md](SETUP.md)

---

You are an installation assistant. Please help me install **UIweft** (the UI-spec orchestration skill) and its four companion skills. Follow the steps below; after each step, tell me the result. If any step fails, stop and report — do not skip anything.

## Step 1: Identify the environment

1. Confirm which tool you are (Kimi Code / Claude Code / Codex / other) and determine your skills directory. Common candidates:
   - `~/.agents/skills/` (common convention)
   - `~/.kimi-code/skills/` (Kimi Code)
   - `~/.claude/skills/` (Claude Code)
   - `~/.codex/skills/` (Codex)
   If your tool has its own designated skills directory, use that convention.
2. Check dependencies: `python3 --version`, `node --version`. If either is missing, tell me how to install it and stop.
3. (Optional but recommended) Check whether the system has Chrome/Chromium and note the executable path (on macOS it's usually `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`) — the browser engine will need it later.

## Step 2: Check existing installations

Walk the skills directory looking for `SKILL.md` files, read the `name:` field in the frontmatter, and check whether the following five skills are installed (**match by `name`, not by directory name** — the directory name may differ from the skill name):

| Skill name | Purpose |
|---|---|
| `uiweft` | The orchestration layer itself |
| `ui-ux-pro-max` | Kickoff & direction |
| `design-taste-frontend` | Marketing-facing production |
| `interface-design` | Product-facing production |
| `impeccable` | Review |

Report a list of what's present / missing.

## Step 3: Install the missing skills

- **uiweft**: `git clone https://github.com/zouh9426/uiweft` into a temp directory, then copy its `uiweft/` subdirectory into the skills directory.
- **The four companion skills**: install each into the same skills directory following its upstream repo's README:
  - `ui-ux-pro-max` → https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
  - `design-taste-frontend` → https://github.com/Leonxlnx/taste-skill
  - `interface-design` → https://github.com/Dammyjay93/interface-design
  - `impeccable` → https://github.com/pbakaus/impeccable
- Prefer the upstream-provided official install method (npm CLI / `npx skills add`, etc.); if none exists, copy the skill directory from the repo into the skills directory. After installing, verify by `name:` that all five skills are in place.

## Step 4: Configure the Impeccable browser engine (optional, strongly recommended)

If Chrome/Chromium was found in Step 1:

```bash
cd <技能目录下 impeccable 的实际位置> && PUPPETEER_SKIP_DOWNLOAD=1 npm i puppeteer
export PUPPETEER_EXECUTABLE_PATH="<你的 Chrome 可执行文件路径>"
```

Then tell me: every future session that runs browser-engine scans needs this environment variable (it's recommended to add it to your shell config).

## Step 5: Self-check

Run the following in order (using the actual paths resolved in Steps 2/3):

1. `python3 <ui-ux-pro-max>/scripts/search.py "dashboard" --domain style` — should return style suggestions rather than an error
2. `node <impeccable>/scripts/detector/detect-antipatterns.mjs --help` (if that path doesn't exist, search inside the impeccable directory for the actual location of `detect-antipatterns.mjs`) — should print usage info
3. `python3 <uiweft>/scripts/uupm_to_design.py --help` — should print usage info

When all three pass, report back to me: the install paths of the five skills, the Chrome path (if configured), and a confirmation sentence — "UIweft installation complete. Say 'use uiweft for UI' in your project to get started."
