# COMPATIBILITY — 上游版本契约

> 本文件记录 **zedui v0.4.0** 实测通过的上游版本契约。上游漂移时以 `doctor.py` 的本机实时体检结果为准（`python3 "$ZEDUI_HOME/scripts/doctor.py"`）——本表只是已实测的基线，不替代运行时真实状态。

## zedui-design-schema-v1

DESIGN.md 的文档契约：YAML frontmatter 是全部 token 值的唯一事实源（嵌套 map、无列表、标量加引号的受限 YAML 子集）；正文中 `<!-- zedui:generated:<name>:start/end -->` 标记内的 token 表格是 frontmatter 的派生视图，由 `uupm_to_design.py --from-design` 机械再生。结构与标记不得手改。详见 `SKILL.md`（硬性规则 5 / Phase 3）。

## 上游实测表

| 上游 skill | 版本 | 实测日期 | 关键接口契约 |
|---|---|---|---|
| impeccable | `4.0.4` | 2026-08-14 | `context.mjs` 每 session 只跑一次的协议（`CONTEXT_STALE` / `MANUAL_DETECTOR_REQUIRED` 等指令必须响应）；critique 的 A/B 隔离子代理协议（Assessment A 先于 detector 结果完成，B 自跑 detector 与浏览器证据）；`design-system-font / color / radius / font-size` 四条规则**不含 spacing**（间距字面值由 zedui `token_lint.py` 兜底） |
| design-taste-frontend | 无版本号字段 | 2026-08-14 | Honesty rule（官方设计系统例外条款）、生产环境字体用 `next/font` 等条款 |
| interface-design | 无版本号字段 | 2026-08-14 | `.interface-design/system.md` 读写闭环（zedui 禁止其创建，沉淀落点为 DESIGN.md 的 `## Components` 节） |
| ui-ux-pro-max | 无版本号字段 | 2026-08-14 | `search.py --design-system --json` 契约（10 色角色 + `cta` 补足为 11、dials、`spacing_scale` 等） |

## 说明

- 无版本号字段的上游以实测日期为基线；其协议/行为变更无法用版本号识别，接入或升级后请用 `doctor.py` 复核。
- 本仓库不锁定上游版本；任何上游漂移都以 `doctor.py` 的实时体检结果为准。
