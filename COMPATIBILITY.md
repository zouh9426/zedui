# COMPATIBILITY — 上游版本契约

> 本文件记录 **zedui v0.4.0** 实测通过的上游版本契约。当前安装副本是否满足 zedui 契约，以 `doctor.py` 的本机体检结果为准（`python3 "$ZEDUI_HOME/scripts/doctor.py"`）；public upstream 是否发生更新需独立核对版本 / commit provenance——doctor 是离线体检，看不到 GitHub 上游。

## zedui-design-schema-v1

DESIGN.md 的文档契约：YAML frontmatter 是全部 token 值的唯一事实源（嵌套 map、无列表、标量加引号的受限 YAML 子集）；正文中 `<!-- zedui:generated:<name>:start/end -->` 标记内的 token 表格是 frontmatter 的派生视图，由 `uupm_to_design.py --from-design` 机械再生。结构与标记不得手改。详见 `SKILL.md`（硬性规则 5 / Phase 3）。

## 上游实测表

| 上游 skill | 版本 | 实测日期 | 关键接口契约 |
|---|---|---|---|
| impeccable | 实测基线 `4.0.4` | 2026-08-14 | `context.mjs` 每 session 只跑一次的协议（`CONTEXT_STALE` / `MANUAL_DETECTOR_REQUIRED` 等指令必须响应；有明确页面/组件时传 `--target <path>`）；critique 的 A/B 隔离子代理协议（Assessment A 先于 detector 结果完成，B 自跑 detector 与浏览器证据）；detector 公开入口 `scripts/detect.mjs`（`scripts/detector/detect-antipatterns.mjs` 为兼容 fallback）；`design-system-font / color / radius / font-size` 四条规则**不含 spacing**（间距字面值由 zedui `token_lint.py` 兜底） |
| design-taste-frontend | 无版本号字段 | 2026-08-14 | Honesty rule（官方设计系统例外条款）、生产环境字体用 `next/font` 等条款；默认 Tailwind v4（间距类 arbitrary 值 `p-[17px]` 由 `token_lint.py` 封） |
| interface-design | 无版本号字段 | 2026-08-14 | `.interface-design/system.md` 读写闭环（zedui 禁止其创建，沉淀落点为 DESIGN.md 的 `## Components` 节） |
| ui-ux-pro-max | 无版本号字段 | 2026-08-14（本机副本契约探测） | `search.py --design-system --json` 契约：外层 `{"design_system": {...}}`。**本机实测副本**输出 12 个色值 + `notes`（含遗留键 `cta`/`text`）；**public upstream main**（a38d04c，2026-08-13）已输出 16 个 semantic roles（`on_secondary`/`on_accent`/`card`/`card_foreground`/`muted_foreground`/`on_destructive` 等）+ 遗留 `cta`/`text`/`on_cta`。桥接脚本对额外 semantic roles 透传、空值槽位丢弃，缺必需角色时 fail-closed 拦截——两个版本形态都兼容 |

## 已知上游动态

- **impeccable 上游已发布 4.1.0 / 4.1.1（2026-08-14），本机实测基线仍为 4.0.4**。4.1.x 变更集中在方向决策/构建流程/critique 呈现/hook 行为（新增 `buildPath` 配置、元素级 `data-impeccable-ignore` 豁免等），detector 规则集（59 条）与 critique A/B 隔离协议未变。本地副本升级到 4.1.x 后用 `doctor.py` 复核，并重点确认 critique 输出契约与 hook 配置字段。

## 说明

- 无版本号字段的上游以实测日期为基线；其协议/行为变更无法用版本号识别，接入或升级后请用 `doctor.py` 复核。
- 本表"实测"均指**本机安装副本**；public upstream 仓库的最新动态（如 impeccable 4.1.1、UUPM semantic palette）单列说明，不与本地基线混为一谈。doctor.py 是离线体检，只对本地安装负责。
- 本仓库不锁定上游版本；本机安装副本是否满足契约以 `doctor.py` 的实时体检结果为准。
