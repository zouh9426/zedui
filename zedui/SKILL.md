---
name: zedui
description: 项目级 UI 规范编排工作流。项目开局时用 UI-UX-Pro-Max 定方向并生成唯一规范文件 DESIGN.md；随后按页面类型路由到 design-taste-frontend（营销/落地页）或 interface-design（产品页/后台/仪表盘）；每个页面完成后用 Impeccable 做审查（critique 设计评审 + audit 技术审计），再由 zedui 硬门禁做机械把关，修复回流给生产者。Use when starting a new project's UI design, establishing or evolving DESIGN.md, building any UI page, or auditing UI consistency.
---

# zedui — UI 规范编排工作流

你不是在"做 UI"，你是在**编排四个 UI skill 的工作流**。四个 skill 各自的完整能力读它们自己的 SKILL.md，本文件只定义串联逻辑。

## 分工总览

| 角色 | Skill 名 | 职责 |
|---|---|---|
| 开局定方向 | `ui-ux-pro-max`（UUPM） | 从用户需求生成设计方向（风格/色板/字体/dial），数据驱动，不提问 |
| 营销面生产 | `design-taste-frontend`（Taste） | 落地页、定价页、关于页、博客、作品集、改版 |
| 产品面生产 | `interface-design` | Dashboard、后台、设置页、表单、数据界面、onboarding |
| 审查（只审不修） | `impeccable` | critique 设计评审 + audit 技术审计 + detector 证据 |

**唯一规范文件：项目根的 `DESIGN.md`。** 它是所有 skill 的唯一事实源（SSOT）。任何全局视觉决策只许写进 DESIGN.md，不许存在第二份规范文件（特别禁止创建 `.interface-design/system.md`）。

**token 的唯一定义点是 DESIGN.md frontmatter。** 它有两个派生层，都是生成物、永不允许手改：正文里 `<!-- zedui:generated:* -->` 标记内的 token 表格（由桥接脚本 `--from-design` 从 frontmatter 机械再生，改了会被下次同步覆盖），以及代码侧的 `tokens.css`（同一命令生成）。改值只能改 frontmatter 再重新同步——**同步命令成功返回后三层一致**；写盘是每个文件各自原子替换（不是两文件事务），万一中途失败产生不一致，由 `doctor.py` 的项目侧检查检出并按提示重跑同步恢复。

```
Phase 0 开局：提问 → UUPM 出方案 → 用户确认 → 桥接脚本生成 DESIGN.md
Phase 1 生产：按页面类型路由 → Taste / interface-design / UUPM 兜底，全部以 DESIGN.md 为规范
Phase 2 审查：context 引导 → critique（A/B 隔离评审）→ audit → ZedUI 硬门禁 → 修复回流 → 复评
迭代期：任何 UI 变更都走 Phase 1 → Phase 2；token 类规范演进通过修改 DESIGN.md frontmatter；marketing/product dials 按 Phase 3 更新 DESIGN.md Overview 的 dial 表
```

---

## 环境探测（每次会话先做，工具无关）

本 skill 不写死任何安装路径——不同 AI 工具（Kimi Code / Claude Code / Codex 等）的技能目录不同。**会话开始时先解析出五个 HOME 变量，之后本文所有命令里的 `$XXX_HOME` 都指解析结果。**

**解析规则（按 skill 名匹配，不是按目录名）**：在候选技能目录下逐层找 `SKILL.md`，读 frontmatter 的 `name:` 字段与目标 skill 名比对（**不区分大小写**，兼容改名前安装的副本）——目录名和 skill 名可能不一致（例如目录 `taste-skill/` 里装的 skill 名是 `design-taste-frontend`），按目录名找会漏。**用 `find` 实现时加 `-L` 跟随符号链接**——skill 常以符号链接方式安装进技能目录，裸 `find` 不跟随符号链接会把它们整棵漏掉。

候选技能目录（**项目级优先、先命中先用**：同一 skill 装在多处时按此顺序找到第一个匹配即停，避免误用全局旧副本）：

- 当前项目内的 `.agents/skills/`、`.kimi-code/skills/`、`.claude/skills/`（项目级安装，最优先）
- `~/.agents/skills/`（通用约定）
- `~/.kimi-code/skills/`（Kimi Code）
- `~/.claude/skills/`（Claude Code）
- `~/.codex/skills/`（Codex）
- 当前工具文档/配置声明的其他技能目录

需要解析的五个 HOME：

| 变量 | 对应 skill | 用途 |
|---|---|---|
| `$UUPM_HOME` | `ui-ux-pro-max` | `scripts/search.py` 检索脚本、`data/` 知识库 |
| `$TASTE_HOME` | `design-taste-frontend` | 营销面生产 |
| `$ID_HOME` | `interface-design` | 产品面生产 |
| `$IMP_HOME` | `impeccable` | context 引导 / detector / hook-admin / critique / audit |
| `$ZEDUI_HOME` | `zedui`（本 skill 自身） | `scripts/uupm_to_design.py` 桥接脚本、`token_lint.py`、`doctor.py` |

解析结果**显式告诉用户一行**（哪个 skill 在哪个路径）。任何一个解析不到：**告知用户缺哪个、请参照项目 README/SETUP 安装**——缺的 skill 在当前任务链上（如要做产品页却缺 interface-design）就停下来等安装；当前任务用不到的（如纯营销项目缺 interface-design）记录后可继续，但路由到它之前必须装好。不要静默跳过或瞎猜路径。

装好后做全链路体检。**你已解析出的五个 HOME 是宿主实际选定的路径——显式传给 doctor，不要让它再猜一遍**：

```bash
python3 "$ZEDUI_HOME/scripts/doctor.py" \
  --skill-home zedui="$ZEDUI_HOME" --skill-home ui-ux-pro-max="$UUPM_HOME" \
  --skill-home design-taste-frontend="$TASTE_HOME" \
  --skill-home interface-design="$ID_HOME" --skill-home impeccable="$IMP_HOME"
```

doctor 无参数运行时也能自动发现（覆盖上面的候选目录），但**自动发现只是 fallback**：它不复制各宿主真实的 loader 优先级，多副本时它选的第一命中不一定是宿主实际加载的那份（输出里会以 `[explicit]` / `[auto-discovered]` 标注来源，多副本会警告）。显式路径无效时 doctor fail-closed，不会偷偷退回自动发现。

**会话快照注意**：宿主注入的 skill 内容是会话开始时的快照——zedui 或上游 skill 更新后，**新开/重启会话**再依赖新行为，否则编排指令与磁盘真源可能不一致（2026-08 实测：同一会话内磁盘已 v0.4.x，注入的仍是旧版 Phase 2 顺序）。

---

## Phase 0：开局定方向（新项目 / 无 DESIGN.md 时）

触发：项目里没有 DESIGN.md，且用户要做任何 UI。已有 DESIGN.md 但不符合契约（指针文件、无 frontmatter、detector 解析失败）时，走 0.0 迁移，不要重新定方向。

### 0.0 既有规范迁移（有旧规范但不符合契约时）

触发：项目已有 DESIGN.md 但不是本工作流的契约格式（无 frontmatter / frontmatter 解析失败 / 只是指向其他文档的指针文件），或无 DESIGN.md 但存在既有设计规范文档（如 `docs/design/` 下的设计系统文档）。**此时不走 0.1~0.4 重定方向**——旧文档里的设计决策是已确认事实，重新检索等于推翻既有产品。

迁移步骤：

1. **定位规范源**：读指针目标或搜索项目内设计规范文档，确认它是用户认可的现行规范（不确定就问，别猜）。
2. **翻译而非重定**：把旧文档的全局决策（色板、字体、圆角、字号、间距、明暗支持）逐项翻译成 UUPM JSON 结构（结构见 `$ZEDUI_HOME/scripts/uupm_to_design.py` 头部注释），**禁止发明新 token、禁止改动任何已有值**。旧文档没覆盖的字段（dial 三档、spacing 等）按默认/建议值给出并标注"新增建议，待确认"。
3. **四确认项照旧**：0.3 的次级文字色 / 中性墨色 / 暗色 token / CJK 字体栈逐项检查，缺则补——旧规范最常缺的正是这四项。**补建议 token 前先对照页面实现值**：detector 的 `design-system-color` 有颜色通道容差（±6）——建议值若与页面既有实现色接近，会把真实的未登记色"无意洗白"判为色板内、不再报漂移。拿不准的页面色保持漂移状态更安全。
4. **用户确认（硬性卡点，同 0.3）**：翻译结果 + 建议项摊开确认；旧规范文档的处置（归档 / 保留为细则文档并在 DESIGN.md 建立引用）一并裁决——**禁止静默双规范并存**。
5. **落盘**：用桥接脚本从翻译后的 JSON 生成 DESIGN.md + tokens.css（`--tokens-css`），格式由脚本保证可解析；覆盖既有 DESIGN.md 用 `--force`（指针内容已完成历史使命）。tokens.css 接入样式入口，旧 `:root` 手写 token 块替换为别名映射。**落盘前先对照旧值**：桥接脚本的圆角/字号用默认阶梯（rounded 默认 "0px,4px,8px,12px,16px,24px"、type-scale 默认 "12px,14px,16px,20px,24px,32px,40px,48px,64px"），**不含旧文档的圆角/字号值时旧值会被静默丢弃**——detector 随后把页面里的旧值报成漂移，迁移保真直接失败（2026-08-12 某模拟项目实测：旧值 6px 圆角不显式传参即被丢弃）。落盘前必须把旧文档的全部圆角/字号值对照默认阶梯，缺的用 `--rounded` / `--type-scale` 显式传入。**无样式入口形态**：旧项目可能纯内联样式、无全局 CSS、无 `:root` 块——"tokens.css 接入样式入口"无物可接。此时 tokens.css 落盘项目根或样式目录，并在 PROJECT_INDEX 登记"未接入，留待页面改版时启用"即可，不算漏步。
6. **验证**：跑 2.3 的 detector 门禁确认 frontmatter 可解析、`design-system-*` 四条规则能正常比对；对既有代码的漂移 finding 只报告，修复走 Phase 1/2 正常回流。

### 0.1 提问（编排层做，UUPM 不会提问）

读用户的提示词，**推导出还缺什么**，只问缺失的，3~5 个问题封顶，不许啰嗦。候选维度：

- 产品类型与核心场景（SaaS 工具？电商？内容站？）
- 目标受众（开发者？消费者？企业？）
- **内容语言（中文 / 英文 / 双语）**——决定字体决策是否有效，见 0.3 确认项 4
- 风格倾向或"vibe 词"（极简？极客？奢华？）
- 参考：竞品、参考站、参考图
- 既有品牌资产（logo、品牌色、指定字体）
- 明暗模式倾向
- 技术栈（先看 `package.json` 等项目文件，探测不到才问）

**参考图处理**：UUPM 读不了图。用户给了参考图时，由主 agent 直接看图，把风格特征（色彩倾向、密度、圆角风格、字体气质）翻译成关键词，并入 UUPM 查询词。

### 0.1.1 图片资产能力检测（提问前先做）

检查当前环境有没有图片生成工具（`generate_image`、MCP 生图、IDE 集成生图等），结论记入 0.3 的确认清单——Taste 的素材优先级链第一位就是图生成，**没有这个能力时 hero 等关键视觉只能退到 picsum 随机占位（内容不可控，实测会毁掉 hero）或用户供图**。必须在开局让用户知情选择：自己供图 / 接受随机占位 / 后续补生成。

### 0.2 UUPM 生成方案

```bash
python3 "$UUPM_HOME/scripts/search.py" "<产品类型> <行业> <风格关键词>" \
  --design-system -p "<项目名>" --json \
  --variance <V> --motion <M> --density <D>
```

- 查询词 = 用户提示词 + 0.1 的回答 + 参考图关键词的组合，要具体（"fintech dashboard dark mode" 好于 "dashboard"）。
- dials 初值按主场景给（产品型项目 3/4/7 上下、营销型项目 7/6/4 上下），**最终值在 0.3 与用户敲定**。
- 输出是 JSON（结构见桥接脚本头部注释），包含 pattern/style/colors/typography/dials/spacing_scale/motion_snippet/anti_patterns。**zedui 要求 11 个必需色角色**；不同版本的 UUPM 副本输出的色键集合不同（较旧副本可能缺 `cta`，较新副本会多输出 semantic roles 如 `on_secondary`/`card_foreground`/`muted_foreground` 等）——缺的必需角色在 0.3 当场补齐，额外的 semantic roles 由桥接脚本自动透传（空值槽位自动丢弃），都不用特殊处理。
- UUPM 检索 0 命中时它会明说用的是默认值——把这种不确定性如实转告用户，不要掩饰。

### 0.3 用户确认（硬性卡点，每次必停）

把方案摊开来给用户看，必须包含：

- 风格名 + 关键词 + 明暗支持
- 完整色板（11 个必需角色 + extras，带 hex；副本缺 `cta` 等必需角色时当场补齐）
- 标题/正文字体
- 建议的 marketing / product 两组 dial 档位——**按风格倾向给建议，不要无脑用固定值**：极简/Linear 风建议 marketing 6/4/3、product 3/3/7；张扬/编辑风可用 marketing 8/6/4 起步
- 建议的圆角阶梯与字号阶梯（桥接脚本默认值，用户可改；字号阶梯至少 6 档，否则标题/正文字号无从派生）
- 反模式清单（这个项目要避免什么）

**四个确认项（UUPM 数据的已知短板，逐项和用户确认）：**

1. **次级文字色**：UUPM 色板没有 body 次级文本灰，落地页/产品页都会需要。不够就当场补一个 `secondary_text` token。
2. **中性墨色**：UUPM 色板为营销页优化，foreground 常是品牌色（蓝色文字）。产品页正文用品牌色会很难看——确认正文是否改用中性色，标题才用 foreground。
3. **暗色 token**：UUPM JSON 只产出一套色值，明暗支持只是标注。项目要双模的话，当场补 `dark_*` 系列 token，否则 Taste 的双模强制会无 token 可用。
4. **CJK 字体栈（中文/双语项目必须确认）**：UUPM 的字体库全是 Latin 字体，**不含 CJK 字形**——中文内容会静默回退到系统默认宋体/黑体，字体决策等于半失效，且 detector 完全测不出这种回退（它只看 font-family 声明）。中文项目必须把 fontFamily 写成栈：`"EB Garamond, Noto Serif SC"`（Latin 字体在前管西文与数字，CJK 字体在后管中文），Google Fonts URL 同步加上 CJK family。**字体相关 JSON 字段要四个一起改**：`heading` / `body` 的 fontFamily、`google_fonts_url`、`css_import`——只改前三个会让 URL / 导入与实际字体栈对不上。**且 `google_fonts_url` 要逐 family 核对**：UUPM 输出的 URL 可能含 heading/body 之外的字体（实测出现过 Cinzel 不属于任一），detector 的 `design-system-font` 比对 URL 时必报 finding——多余字体从 JSON 里清掉，别留进 URL。
5. **等宽字体栈（代码密集型 UI 必须确认）**：页面里有代码块 / endpoint / API key / 日志等 mono 内容时，当场在 JSON 的 `typography` 里补 `mono` 字段（如 `"ui-monospace, SF Mono, SFMono-Regular, Menlo, Consolas, monospace"`）——桥接脚本会把它带进 frontmatter、正文和 tokens.css 的 `--font-mono`。不登记的话，detector 的 `design-system-font` 会把组件里的 mono 声明报成漂移，而 design-system-* 不许豁免，只能事后走 Phase 3 补规范（2026-08 A/B 试点实测发生）。

**用户明确说可以了才进入 0.4。有任何修改就调整后重新确认。**

### 0.3.1 调整机制

用户要改方案的某个局部（换 accent、改字体、调 dial）时：**直接编辑 UUPM 输出的 JSON 对应字段 → 把改动后的关键项重新给用户确认 → 再跑桥接脚本**。不要为局部微调重新检索（重新检索会换掉整套方案）。

### 0.4 落盘 DESIGN.md

用桥接脚本做机械转换（保证格式永远能被 Impeccable detector 解析），同时生成代码侧 token 定义层：

```bash
python3 "$ZEDUI_HOME/scripts/uupm_to_design.py" uupm_output.json \
  -o <项目根>/DESIGN.md \
  --tokens-css <项目样式目录>/tokens.css \
  [--rounded "0px,4px,8px,12px,16px,24px"] \
  [--type-scale "12px,14px,16px,20px,24px,32px,40px,48px,64px"] \
  --marketing-dials V,M,D [--product-dials V,M,D]
```

**落盘校验是 fail-closed 的**：11 个颜色角色、标题/正文字体、≥6 档且含 `base`+`2xl` 的字号阶梯、marketing + product 两组 dial，缺一即报错退出、不落盘——0.3 没确认完的方案到不了 DESIGN.md（UUPM 副本缺 `cta` 等必需角色时，必须在 0.3 补进 JSON）。确需先落地残缺草案时显式加 `--allow-incomplete`（会写 TBD 占位），但 Phase 0 正式落盘不该用它。

**`--tokens-css` 目标目录**：没有既定样式目录的项目——Next.js 落 `app/`、普通前端落 `css/` 或 `styles/`，完全无样式目录就先落项目根，样式体系成型后再迁。`tokens.css` 落盘后接入项目样式入口（如全局 CSS 里 `@import`/拷贝引入），项目若已有手写 `:root` token 块，用它替换并把旧变量名映射为别名指向新变量（防引用断裂）。DESIGN.md + tokens.css 生成后，Phase 0 完成。之后任何页面才可以动工。

---

## Phase 1：页面生产路由

每要做一个页面，先查路由表，再带着约束指令调用对应 skill。

### 路由表

| 页面类型 | 交给谁 |
|---|---|
| 落地页 / 定价页 / 关于页 / 营销页 / 博客 / 作品集 / 官网改版 | **design-taste-frontend** |
| Dashboard / 管理后台 / 设置页 / 表单 / 数据表格 / 多步向导 / 登录注册 / onboarding / 空状态 | **interface-design** |
| 邮件模板 / 原生移动页面 / 幻灯片 / 品牌物料 / 两者都不沾的边缘页 | **编排层直接做**：查 UUPM 知识库（`search.py "<主题>" --domain ux|style|color|typography`）取建议，按 DESIGN.md 规范自行构建 |
| 拿不准归属的 | 按"这个页面是让人**看**的还是让人**用**的"裁决：看 → Taste，用 → interface-design |

Taste 会主动拒绝产品型页面、interface-design 会主动拒绝营销页面（都写在它们的 frontmatter 里）——路由冲突时尊重 skill 自己的边界声明，转给另一方。

### 调用 Taste 时的约束指令（必须包含）

1. **DESIGN.md 已定，规范不重定**：色彩、字体、间距、圆角全部从 DESIGN.md 读；你的 Brief Inference 只做执行层选择（布局家族、动效曲线、素材），不许推翻 DESIGN.md 的任何 token。**dial 推断表也不许覆盖 DESIGN.md 的 marketing 组**（实测 Taste 会按自己的 1.A 表给极简风项目推 5-6/3-4，以 DESIGN.md 为准）。
2. dial 三档用 DESIGN.md 里记录的 **marketing 组**。
3. 有图片生成能力时按你自己的优先级链生成真实素材。
4. **响应式是交付硬指标**：每个多列布局都必须带 `<768px` 的显式单列坍缩（你自己 §3.E/§7 的规则），交付清单里的 Mobile collapse 项不许放水。
5. 颜色/字号/圆角/间距一律引用 tokens.css 变量，不写字面值（硬性规则 6）。
6. 遵守你自己的 Pre-Flight 清单交付。
7. **官方设计系统例外**：项目若走 Material / Fluent / Carbon 等官方体系，按你自己的 Honesty rule 装官方包、用官方 token——不要手工重建其 CSS，也不要把 DESIGN.md token 强刷到官方组件上。这种项目在 Phase 0 就应把"采用官方体系"写进 DESIGN.md，token 层只承载品牌色等增量。
8. **字体加载按你的生产规则**：Next.js 用 `next/font`，其他生产环境 self-host + `font-display: swap`；DESIGN.md 里的 `css_import`（Google Fonts @import）只是开发期便利，不许带进生产。

### 调用 interface-design 时的约束指令（必须包含）

1. **把项目根的 DESIGN.md 当作你的 system 文件**读取并遵守；**禁止创建 `.interface-design/system.md`**——任务结束时你那"是否保存 system 供后续会话复用"的环节，落点改为 DESIGN.md 的 `## Components` 节（见第 3 条），不开新文件。
2. 全局 token（色/字/间距/圆角）以 DESIGN.md 为唯一来源；你内部的设计规则只补 DESIGN.md 没规定的执行细节。
3. 构建中沉淀的新组件规范（测量值、用法），**追加到 DESIGN.md 的 `## Components` 章节**（格式：组件名 / 关键测量值 / 何时用），复用 ≥2 次才收录。全局 token 的变更不许写这里——全局变更走"规范演进"流程（见 Phase 3）。
4. dial 三档用 DESIGN.md 里记录的 **product 组**。
5. **响应式与触达**：所有交互元素触达面积 ≥44×44px（你自己的 Polish 规则）；窄视口下 sidebar/多栏布局要有显式降级方案。
6. 颜色/字号/圆角/间距一律引用 tokens.css 变量，不写字面值（硬性规则 6）。
7. 构建后过你自己的 4 项自检（Swap/Squint/Signature/Token test）。

### 冲突裁决

```
DESIGN.md ＞ skill 内部默认规则
```

skill 的内部规则全部是"DESIGN.md 没规定时的默认值"，不是与 DESIGN.md 平级的第二套规范。唯一例外是官方设计系统（Material / Fluent / Carbon 等）：项目明确采用官方体系时，官方 token 与组件优先，DESIGN.md 只承载品牌增量——这个例外本身也必须记录在 DESIGN.md 里。

---

## Phase 2：审查（Impeccable 评审 + zedui 硬门禁，只审不修）

触发：每个页面完成后；每次迭代完成后；用户要求"体检"时。

### 2.0 Impeccable 上下文引导（每 session 一次，最先做）

```bash
node "$IMP_HOME/scripts/context.mjs" --target <当前页面/组件路径>
```

有明确审查目标（页面/组件文件或路由）时**必须传 `--target`**（上游要求，monorepo 下还靠它选定活动项目）；开局全项目体检时可省略。

每个会话**只跑一次，不许重跑**（上游硬协议）。它加载项目的 PRODUCT.md / DESIGN.md 与 surface 上下文，并可能下发必须响应的指令：`CONTEXT_STALE`（上下文过期，按指引刷新）、`MANUAL_DETECTOR_REQUIRED`（无自动 hook 时改完 UI 要手动跑 detector）、`NO_PRODUCT_MD`、`MONOREPO_TARGET_REQUIRED` 等。**收到指令就遵循，不要当普通输出略过。**之后所有 Impeccable 命令（critique / audit）都建立在这个上下文之上。

### 2.1 critique 设计评审（先评，不许先喂 detector 结果）

按 Impeccable 自己的 critique 协议执行，两条铁律：

- **Assessment A（主观设计判断）必须先于任何 detector 结果完成**——detector 输出是确定性的，但它会锚定设计判断（上游明文规定）。因此编排层**不得在 critique 之前把 detector 扫描结果灌进上下文**；顺序永远是 critique 在前、硬门禁复核在后。
- **A 与 B 必须是两个互不可见的隔离子代理**（环境支持 sub-agent 时这是 mandatory，不是建议）；detector 与浏览器证据由 **Assessment B 自己运行**，父上下文不重跑。降级为单上下文必须按上游要求挂 `⚠️ DEGRADED` 横幅自曝。

产物：Nielsen 10 项启发式按 Impeccable 当前 critique 协议与实际适用性计分——全部 10 项适用时满分 /40；某项对当前页面确实不适用时可按上游协议标 n/a，分母按 applicable maximum 重算（如 8 项适用为 /32）。评分细节始终以 Impeccable 自己的 critique 协议为准，zedui 只做编排、不写死分母。同时产出 P0-P3 问题清单，快照存 `.impeccable/critique/`（critique 自带 trend，复评时对比）。

### 2.2 audit 技术审计

无障碍/性能/主题/响应式/实现完整性 5 维 /20 分。第 5 维（Implementation Integrity）上游会自行调用 detector 并逐条在上下文中复核，编排层不代跑。

按 Impeccable 自己 SKILL.md 的命令协议调用；**只用它的审查类命令，不用 build/fix 类命令**（polish/shape/animate 等一律不用）。

### 2.3 ZedUI 硬门禁（机械把关，全部通过才算审查通过）

critique/audit 是判断层；以下机械检查由编排层直接把关。

**a) design-system 漂移清零**：复用 critique Assessment B 已跑出的 detector 结果（没有则按下文命令自跑）——`design-system-font / design-system-color / design-system-radius / design-system-font-size` 四条规则机械比对代码与 DESIGN.md frontmatter 声明的字体/色板/圆角/字号阶梯。**这四类 finding 必须清零，不接受豁免**（那是真漂移，豁免处置见 2.4）。

detector CLI 实操要点：

```bash
node "$IMP_HOME/scripts/detect.mjs" --json <目标文件或目录>
```

- 同时会报约 60 条 slop/quality 规则（AI 味、排版等）；exit code 2 = 有发现。
- `scripts/detect.mjs` 是上游当前公开入口（facade），`--json`/`--viewport` 等参数全兼容；它不存在时（旧版本）回退内部入口 `scripts/detector/detect-antipatterns.mjs`，再在 `$IMP_HOME` 内搜索实际位置（`hook-admin.mjs` 同理）。

**检测边界（实测确认）**：`design-system-color` 只检查**属性声明处的字面值**（`color: #00C853` 会被抓）；CSS 自定义属性的定义行（`--accent: #xxx`）和 `var()` 引用**不检查**。而且实测**只抓部分属性位置的字面值**——`box-shadow` 值内、部分上下文会漏。另外它有颜色通道容差（±6）——与色板近似的未登记色会被判为色板内静默通过，临界色值需人工复核。**detector 清零后应人工补网**：`grep -nE "#[0-9a-fA-F]{3,8}|rgba?\("` 扫一遍源码，确认没有漏网的色值字面量再交付。注意 exit code 2 = 有 finding，不是运行出错——脚本化处理时别当失败。

**b) 间距字面值 lint（zedui 自补的兜底）**：上游 detector 的 design-system 比对**不覆盖 spacing**——`padding: 17px` 这类字面值不会成为 finding，"间距字面值必然被抓"是不成立的。用 zedui 自带的 token lint 兜底：

```bash
python3 "$ZEDUI_HOME/scripts/token_lint.py" <目标文件或目录>
```

规则：组件层样式里的 padding/margin/gap 字面值必须引用 `var(--space-*)`；定位属性（top/right/bottom/left/inset 系列）只抓绝对长度字面值——百分比定位（`top: 50%` 居中、装饰光晕的 `top: -20%`）是组件内部摆放，不是间距节奏，不报。已 disposition 的合法 finding 用行内注释豁免：在该行加 `/* token-lint-ignore: 理由 */` 即跳过该行（可 grep 审计）；token 定义层（tokens.css 等生成物）豁免。**目标是 exit 0 可信仰**：全绿 = 无未处置 finding，不靠口头记忆。

**c) 浏览器引擎扫描 + 多端视口（有浏览器时必须跑）**：源码级 CLI 只看文本，**看不见计算样式**——间距挤压、实际对比度、触摸目标、CJK 字体回退全部漏检（试点项目漏过一个 padding 被层叠覆盖的 bug，用户肉眼抓到）。同一 CLI 传 URL 即自动启用浏览器引擎（注意 `engines/browser/detect-url.mjs` 是库不是入口，直接跑它什么都不扫）。**浏览器引擎扫全量 DOM，含 hidden 视图**（2026-08 实测：JS 切换的隐藏 tab/视图内的 kicker 也会上报）——覆盖更全是好事，但可见性相关规则在隐藏 DOM 上的 finding 需人工甄别，别误判成默认视图有问题。用法：

```bash
# 首次准备：cd "$IMP_HOME" && PUPPETEER_SKIP_DOWNLOAD=1 npm i puppeteer
# 用系统 Chrome，免去下载 Chromium
export PUPPETEER_EXECUTABLE_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"  # macOS 示例；其他平台换成对应 Chrome/Chromium 可执行文件路径
node "$IMP_HOME/scripts/detect.mjs" "file://<页面绝对路径>.html"
```

**多端视口检查（手机 / 平板 / 桌面）**：detector 没有专门的响应式规则（实测：`--viewport` 参数有效，但固定宽度+无媒体查询的页面在手机视口下也能过扫描——它查不出布局坍缩问题）。所以多端适配检查 = **三档视口各跑一次浏览器引擎 + 每档截图人工审查**：

```bash
for vp in 390x844 768x1024 1440x900; do
  node "$IMP_HOME/scripts/detect.mjs" "file://<页面>.html" --viewport $vp
done
```

截图人工审查的判断标准：布局是否按媒体查询坍缩为单列、有无横向滚动、文字是否溢出、触控目标是否 ≥44px。布局级的响应式打分由 2.2 的 `audit`（Responsive 维度：固定宽度/横向滚动/断点缺失/触达尺寸，0-4 分）负责。

**d) 截图人工核查**：配合截图人工审查**关键接缝处的局部裁切**（不要只看缩略全图——局部间距问题在缩略图里不可见，实测教训）。**截图方式实测教训两条**：① 不要用 Chrome CLI 的 `--screenshot --window-size=390` 截移动端图——CLI 截图有最小窗宽（约 500px）伪影，390 的移动视口是假的。移动端截图必须用 puppeteer `setViewport` / CDP 设备模拟等真实模拟方式（2026-08-12 某生产项目实测：CLI 截图显示整页溢出 P0，真实模拟下无溢出——以真实模拟结果为准）。② fullPage 截图**不会触发滚动**——用 IntersectionObserver 做 scroll-reveal 的页面，截出来折叠线以下全空白（不是 bug，是伪影），且 position:sticky/fixed 元素会在长图里重复出现。正确姿势：先用 page.evaluate 模拟滚动全程触发 IO，再截 fullPage（2026-08 A/B 试点实测误报过一次大回归）。

### 2.4 豁免（误报处置）

detector 的通用 slop 规则**不认识 DESIGN.md**——被 DESIGN.md 批准的 token 可能命中通用规则（实测：`overused-font` 命中批准字体、`side-tab` 命中签名组件、`cream-palette` 命中批准底色）。处理原则：**被 DESIGN.md 批准的，是"决策，不是缺陷"**；命中 `design-system-*` 四条规则的**一律不豁免**——那才叫漂移，只能改代码或走 Phase 3 改规范。

**豁免前置条件**：豁免前先确认该决策已记录在 DESIGN.md（全局 token 在 frontmatter，组件级决策在 `## Components`）；没记录就先回流备案再豁免，reason 里注明"见 DESIGN.md"。没有备案的豁免等于放水。

**豁免方式按规则类型分**：

- **有值规则**（`overused-font` 等通用规则）：`hook-admin.mjs ignore-value <rule> "<值>" --reason "..."`。
- **无值规则**（`cream-palette`、`gray-on-color`、`cramped-padding`、`side-tab` 等）：`ignore-value` 按值写永远匹配不上（实测）。全项目故意决策用 `hook-admin.mjs ignore-rule <id> --reason "..."`；单文件用 `ignore-value <id> "*" --file <路径>`。

**豁免写在哪**：`.impeccable/config.json` 放在**运行 detector / 安装 hook 的那个项目根**——hook 从会话工作目录读配置，不是从被审文件所在目录读（实测踩坑：豁免写进子项目目录，hook 在父目录触发时看不到）。**file 作用域的路径写"相对 hook 工作目录"的形式**；hook 消息里展示的长路径是显示形式不是匹配形式，不确定时两种形式都写进 `files` 数组。

**两个豁免配套坑（实测确认）**：

- **URL 模式扫描豁免不到**：`ignoreValues` 的 `files` 匹配只对文件/源码模式生效，**对 URL 模式（浏览器引擎扫描）不生效**——豁免不了 URL 扫描的 finding。URL 扫描结果以人工研判 / 备案为准（备案前置条件见上）。
- **豁免配置要随仓库走**：若项目把 `.impeccable/` 整体 gitignore，豁免配置就不随仓库走，团队成员各跑各的、finding 口径不一。需要团队共享豁免时，**别把 `config.json` 忽略掉**（只忽略其余产物即可，如 `.impeccable/critique/`）。

### 2.5 修复回流（谁建的谁修）

- 营销页的问题 → 回流给 **Taste** 修；产品页的问题 → 回流给 **interface-design** 修。
- 修复时把 finding 原文 + DESIGN.md 一起交给生产者。
- 修完**必须复评**：重跑 critique + 2.3 硬门禁，分数留档（critique 自带 trend）。
- P0/P1 未清零不算完成。

---

## Phase 3：迭代与规范演进

- **每次 UI 变更都经过本工作流**：读 DESIGN.md → Phase 1 路由 → 构建 → Phase 2 审查。不绕过。
- **规范演进的入口分两类**：token 类全局规范（颜色/字体/字号/圆角/间距）唯一入口是改 DESIGN.md frontmatter——用户确认的设计变更 → 直接编辑 frontmatter 对应字段 → 重跑 `uupm_to_design.py --from-design DESIGN.md --tokens-css <token文件>`——它会从 frontmatter **同时再生正文里 `<!-- zedui:generated:* -->` 标记内的 token 表格和 tokens.css**，三层同步，不存在"frontmatter 改了正文还是旧值"的窗口。**重同步与 Phase 0 落盘跑同一强度的契约校验**：手改时误删必需色角色、删掉 `scale.base`/`scale.2xl`、写出非法 CSS key 都会被拒绝并逐项列出（草案期才用 `--allow-incomplete` 放宽）→ 重跑 detector 确认现有代码与新规范的兼容情况，漂移处回流生产者修。marketing/product dials 不是 token，保存在 Overview 的 dial 表（人工区）——调整时经用户确认后直接更新该表，不走 frontmatter。
- 正文标记区以外的内容（风格意图、策略说明、`## Components`）是人工维护区，脚本永不触碰；interface-design 沉淀的组件规范只追加进 `## Components` 节；全局 token 的变更只能由用户拍板后改 frontmatter。
- 旧版脚本（v0.4 之前）生成的 DESIGN.md 没有 generated 标记，`--from-design` 会拒绝并提示——用原始 JSON 加 `--force` 重新生成一次即可迁入新格式。

---

## 硬性规则（任何阶段都适用）

1. 项目里没有经用户确认的 DESIGN.md，**不动工**任何页面。
2. **永远只有一份规范文件**。禁止创建 `.interface-design/system.md`、MASTER.md 或任何平行规范（UUPM 的 `--persist` 不要用）。
3. Impeccable **只审不修**；修复永远回流给生产者。
4. 审查不通过（detector 有 design-system-* finding 或 critique 有 P0）**不交付**。
5. DESIGN.md 两处结构不许手写改动：frontmatter 的 YAML 子集结构（嵌套 map、无列表、字符串加引号——detector 与桥接脚本的解析器只吃这个子集），以及正文 `<!-- zedui:generated:* -->` 标记内的 token 表格（frontmatter 的派生视图，改了会被下次 `--from-design` 覆盖）。加颜色加字号随便加，结构与标记别动。**字号不在 heading/body 角色上单独记录**——标题/正文字号约定取 `scale.2xl` / `scale.base`，防止同一事实存两份、改阶梯后一边 stale。
6. **token 唯一定义层铁律**：颜色/字体/字号/圆角/间距的字面值只许出现在 token 定义层（DESIGN.md frontmatter → 生成的 tokens.css）；组件与页面代码只许引用 token 变量（`var(--accent)` 等），不许写字面值。机械兜底分两层：detector 的 `design-system-*` 四条规则覆盖字体/色板/圆角/字号（实测边界：box-shadow 值内等位置会漏、±6 容差会放行近似色，见 2.3a）；间距字面值由 `token_lint.py` 覆盖（见 2.3b）。两层都有盲区，交付前按 2.3 的人工补网收口——不要把任何一层当成全覆盖保证。

## 资源速查（路径 = 环境探测节解析出的 HOME 变量）

| 用途 | 位置 |
|---|---|
| UUPM 检索脚本 | `$UUPM_HOME/scripts/search.py` |
| UUPM 知识库数据 | `$UUPM_HOME/data/` |
| 桥接脚本（UUPM JSON → DESIGN.md；DESIGN.md → 正文同步 + tokens.css） | `$ZEDUI_HOME/scripts/uupm_to_design.py` |
| 间距/token 字面值 lint | `$ZEDUI_HOME/scripts/token_lint.py` |
| 环境全链路体检 | `$ZEDUI_HOME/scripts/doctor.py`（优先用 `--skill-home <skill>=<path>` 把五个已解析 HOME 显式传入；无参自动发现只是 fallback） |
| Impeccable 上下文引导（每 session 一次） | `$IMP_HOME/scripts/context.mjs` |
| Impeccable detector CLI（公开 facade，源码级 + 浏览器引擎共用） | `$IMP_HOME/scripts/detect.mjs`（旧版回退 `scripts/detector/detect-antipatterns.mjs`） |
| Impeccable 豁免管理 | `$IMP_HOME/scripts/hook-admin.mjs` |
| Taste skill 完整能力 | `$TASTE_HOME/SKILL.md` |
| interface-design skill 完整能力 | `$ID_HOME/SKILL.md` |
| Impeccable skill 完整能力 | `$IMP_HOME/SKILL.md` |
