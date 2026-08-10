---
name: zedui
description: 项目级 UI 规范编排工作流。项目开局时用 UI-UX-Pro-Max 定方向并生成唯一规范文件 DESIGN.md；随后按页面类型路由到 design-taste-frontend（营销/落地页）或 interface-design（产品页/后台/仪表盘）；每个页面完成后用 Impeccable 做审查（detector 硬校验 + critique 评审 + audit 审计），修复回流给生产者。Use when starting a new project's UI design, establishing or evolving DESIGN.md, building any UI page, or auditing UI consistency.
---

# zedui — UI 规范编排工作流

你不是在"做 UI"，你是在**编排四个 UI skill 的工作流**。四个 skill 各自的完整能力读它们自己的 SKILL.md，本文件只定义串联逻辑。

## 分工总览

| 角色 | Skill 名 | 职责 |
|---|---|---|
| 开局定方向 | `ui-ux-pro-max`（UUPM） | 从用户需求生成设计方向（风格/色板/字体/dial），数据驱动，不提问 |
| 营销面生产 | `design-taste-frontend`（Taste） | 落地页、定价页、关于页、博客、作品集、改版 |
| 产品面生产 | `interface-design` | Dashboard、后台、设置页、表单、数据界面、onboarding |
| 审查（只审不修） | `impeccable` | detector 硬校验 + critique 设计评审 + audit 技术审计 |

**唯一规范文件：项目根的 `DESIGN.md`。** 它是所有 skill 的唯一事实源（SSOT）。任何全局视觉决策只许写进 DESIGN.md，不许存在第二份规范文件（特别禁止创建 `.interface-design/system.md`）。

```
Phase 0 开局：提问 → UUPM 出方案 → 用户确认 → 桥接脚本生成 DESIGN.md
Phase 1 生产：按页面类型路由 → Taste / interface-design / UUPM 兜底，全部以 DESIGN.md 为规范
Phase 2 审查：detector 双层扫描（源码级 + 浏览器引擎）→ critique/audit → 修复回流 → 复评
迭代期：任何 UI 变更都走 Phase 1 → Phase 2；规范演进只通过修改 DESIGN.md
```

---

## 环境探测（每次会话先做，工具无关）

本 skill 不写死任何安装路径——不同 AI 工具（Kimi Code / Claude Code / Codex 等）的技能目录不同。**会话开始时先解析出五个 HOME 变量，之后本文所有命令里的 `$XXX_HOME` 都指解析结果。**

**解析规则（按 skill 名匹配，不是按目录名）**：在候选技能目录下逐层找 `SKILL.md`，读 frontmatter 的 `name:` 字段与目标 skill 名比对——目录名和 skill 名可能不一致（例如目录 `taste-skill/` 里装的 skill 名是 `design-taste-frontend`），按目录名找会漏。

候选技能目录（逐个检查存在的）：

- `~/.agents/skills/`（通用约定）
- `~/.kimi-code/skills/`（Kimi Code）
- `~/.claude/skills/`（Claude Code）
- `~/.codex/skills/`（Codex）
- 当前项目内的 `.agents/skills/`（项目级安装）
- 当前工具文档/配置声明的其他技能目录

需要解析的五个 HOME：

| 变量 | 对应 skill | 用途 |
|---|---|---|
| `$UUPM_HOME` | `ui-ux-pro-max` | `scripts/search.py` 检索脚本、`data/` 知识库 |
| `$TASTE_HOME` | `design-taste-frontend` | 营销面生产 |
| `$ID_HOME` | `interface-design` | 产品面生产 |
| `$IMP_HOME` | `impeccable` | detector / hook-admin / critique / audit |
| `$ZEDUI_HOME` | `zedui`（本 skill 自身） | `scripts/uupm_to_design.py` 桥接脚本 |

解析结果**显式告诉用户一行**（哪个 skill 在哪个路径）；任何一个解析不到，**停下来告知用户缺哪个、请参照项目 README/SETUP 安装**，不要静默跳过或瞎猜路径。

---

## Phase 0：开局定方向（新项目 / 无 DESIGN.md 时）

触发：项目里没有 DESIGN.md，且用户要做任何 UI。

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
- 输出是 JSON（结构见桥接脚本头部注释），包含 pattern/style/colors(10 角色)/typography/dials/spacing_scale/motion_snippet/anti_patterns。
- UUPM 检索 0 命中时它会明说用的是默认值——把这种不确定性如实转告用户，不要掩饰。

### 0.3 用户确认（硬性卡点，每次必停）

把方案摊开来给用户看，必须包含：

- 风格名 + 关键词 + 明暗支持
- 完整色板（10 角色，带 hex）
- 标题/正文字体
- 建议的 marketing / product 两组 dial 档位——**按风格倾向给建议，不要无脑用固定值**：极简/Linear 风建议 marketing 6/4/3、product 3/3/7；张扬/编辑风可用 marketing 8/6/4 起步
- 建议的圆角阶梯与字号阶梯（桥接脚本默认值，用户可改）
- 反模式清单（这个项目要避免什么）

**四个确认项（UUPM 数据的已知短板，逐项和用户确认）：**

1. **次级文字色**：UUPM 的 10 角色色板没有 body 次级文本灰，落地页/产品页都会需要。不够就当场补一个 `secondary_text` token。
2. **中性墨色**：UUPM 色板为营销页优化，foreground 常是品牌色（蓝色文字）。产品页正文用品牌色会很难看——确认正文是否改用中性色，标题才用 foreground。
3. **暗色 token**：UUPM JSON 只产出一套色值，明暗支持只是标注。项目要双模的话，当场补 `dark_*` 系列 token，否则 Taste 的双模强制会无 token 可用。
4. **CJK 字体栈（中文/双语项目必须确认）**：UUPM 的字体库全是 Latin 字体，**不含 CJK 字形**——中文内容会静默回退到系统默认宋体/黑体，字体决策等于半失效，且 detector 完全测不出这种回退（它只看 font-family 声明）。中文项目必须把 fontFamily 写成栈：`"EB Garamond, Noto Serif SC"`（Latin 字体在前管西文与数字，CJK 字体在后管中文），Google Fonts URL 同步加上 CJK family。

**用户明确说可以了才进入 0.4。有任何修改就调整后重新确认。**

### 0.3.1 调整机制

用户要改方案的某个局部（换 accent、改字体、调 dial）时：**直接编辑 UUPM 输出的 JSON 对应字段 → 把改动后的关键项重新给用户确认 → 再跑桥接脚本**。不要为局部微调重新检索（重新检索会换掉整套方案）。

### 0.4 落盘 DESIGN.md

用桥接脚本做机械转换（保证格式永远能被 Impeccable detector 解析）：

```bash
python3 "$ZEDUI_HOME/scripts/uupm_to_design.py" uupm_output.json \
  -o <项目根>/DESIGN.md \
  [--rounded "0px,4px,8px,12px,16px,24px"] \
  [--type-scale "12px,14px,16px,20px,24px,32px,40px,48px,64px"] \
  [--marketing-dials V,M,D] [--product-dials V,M,D]
```

DESIGN.md 生成后，Phase 0 完成。之后任何页面才可以动工。

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
5. 遵守你自己的 Pre-Flight 清单交付。

### 调用 interface-design 时的约束指令（必须包含）

1. **把项目根的 DESIGN.md 当作你的 system 文件**读取并遵守；**禁止创建 `.interface-design/system.md`**。
2. 全局 token（色/字/间距/圆角）以 DESIGN.md 为唯一来源；你内部的设计规则只补 DESIGN.md 没规定的执行细节。
3. 构建中沉淀的新组件规范（测量值、用法），**追加到 DESIGN.md 的 `## Components` 章节**（格式：组件名 / 关键测量值 / 何时用），复用 ≥2 次才收录。全局 token 的变更不许写这里——全局变更走"规范演进"流程（见 Phase 3）。
4. dial 三档用 DESIGN.md 里记录的 **product 组**。
5. **响应式与触达**：所有交互元素触达面积 ≥44×44px（你自己的 Polish 规则）；窄视口下 sidebar/多栏布局要有显式降级方案。
6. 构建后过你自己的 4 项自检（Swap/Squint/Signature/Token test）。

### 冲突裁决

```
DESIGN.md ＞ skill 内部默认规则
```

skill 的内部规则全部是"DESIGN.md 没规定时的默认值"，不是与 DESIGN.md 平级的第二套规范。

---

## Phase 2：审查（Impeccable，只审不修）

触发：每个页面完成后；每次迭代完成后；用户要求"体检"时。

### 2.1 源码级扫描（detector CLI）

```bash
node "$IMP_HOME/scripts/detector/detect-antipatterns.mjs" --json <目标文件或目录>
```

- `design-system-font / design-system-color / design-system-radius / design-system-font-size` 四条规则会机械比对代码与 DESIGN.md frontmatter 声明的字体/色板/圆角/字号阶梯——**漂移即 finding**，这是整个工作流的硬保障。
- 同时会报约 60 条 slop/quality 规则（AI 味、排版等）。
- exit code 2 = 有发现。
- 不同版本的 Impeccable 目录布局可能不同——`scripts/detector/detect-antipatterns.mjs` 不存在时，在 `$IMP_HOME` 内搜索 `detect-antipatterns.mjs` 的实际位置再用（`hook-admin.mjs` 同理）。

**检测边界（实测确认）**：`design-system-color` 只检查**属性声明处的字面值**（`color: #00C853` 会被抓）；CSS 自定义属性的定义行（`--accent: #xxx`）和 `var()` 引用**不检查**。硬校验抓的是"绕过 token 手写字面值"这类最常见的漂移；token 定义层的正确性靠 0.3 确认和人工把关，不要误以为 detector 全能。

### 2.2 浏览器引擎扫描（有浏览器时必须跑）

源码级 CLI 只看文本，**看不见计算样式**——间距挤压、实际对比度、触摸目标、CJK 字体回退全部漏检（试点项目漏过一个 padding 被层叠覆盖的 bug，用户肉眼抓到）。同一 CLI 传 URL 即自动启用浏览器引擎（注意 `engines/browser/detect-url.mjs` 是库不是入口，直接跑它什么都不扫）：

```bash
# 首次准备：cd "$IMP_HOME" && PUPPETEER_SKIP_DOWNLOAD=1 npm i puppeteer
# 用系统 Chrome，免去下载 Chromium
export PUPPETEER_EXECUTABLE_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"  # macOS 示例；其他平台换成对应 Chrome/Chromium 可执行文件路径
node "$IMP_HOME/scripts/detector/detect-antipatterns.mjs" "file://<页面绝对路径>.html"
```

并配合截图人工审查**关键接缝处的局部裁切**（不要只看缩略全图——局部间距问题在缩略图里不可见，实测教训）。

**2.2.1 多端视口检查（手机 / 平板 / 桌面）**：detector 没有专门的响应式规则（实测：`--viewport` 参数有效，但固定宽度+无媒体查询的页面在手机视口下也能过扫描——它查不出布局坍缩问题）。所以多端适配检查 = **三档视口各跑一次浏览器引擎 + 每档截图人工审查**：

```bash
for vp in 390x844 768x1024 1440x900; do
  node "$IMP_HOME/scripts/detector/detect-antipatterns.mjs" "file://<页面>.html" --viewport $vp
done
```

截图人工审查的判断标准：布局是否按媒体查询坍缩为单列、有无横向滚动、文字是否溢出、触控目标是否 ≥44px。布局级的响应式打分由 2.4 的 `audit`（Responsive 维度：固定宽度/横向滚动/断点缺失/触达尺寸，0-4 分）负责。

### 2.3 豁免（误报处置）

detector 的通用 slop 规则**不认识 DESIGN.md**——被 DESIGN.md 批准的 token 可能命中通用规则（实测：`overused-font` 命中批准字体、`side-tab` 命中签名组件、`cream-palette` 命中批准底色）。处理原则：**被 DESIGN.md 批准的，是"决策，不是缺陷"**；命中 `design-system-*` 四条规则的**没有豁免**——那才叫漂移。

**豁免前置条件**：豁免前先确认该决策已记录在 DESIGN.md（全局 token 在 frontmatter，组件级决策在 `## Components`）；没记录就先回流备案再豁免，reason 里注明"见 DESIGN.md"。没有备案的豁免等于放水。

**豁免方式按规则类型分**：

- **有值规则**（`overused-font`、`design-system-*` 等）：`hook-admin.mjs ignore-value <rule> "<值>" --reason "..."`。
- **无值规则**（`cream-palette`、`gray-on-color`、`cramped-padding`、`side-tab` 等）：`ignore-value` 按值写永远匹配不上（实测）。全项目故意决策用 `hook-admin.mjs ignore-rule <id> --reason "..."`；单文件用 `ignore-value <id> "*" --file <路径>`。

**豁免写在哪**：`.impeccable/config.json` 放在**运行 detector / 安装 hook 的那个项目根**——hook 从会话工作目录读配置，不是从被审文件所在目录读（实测踩坑：豁免写进子项目目录，hook 在父目录触发时看不到）。**file 作用域的路径写"相对 hook 工作目录"的形式**；hook 消息里展示的长路径是显示形式不是匹配形式，不确定时两种形式都写进 `files` 数组。

### 2.4 设计评审与技术审计

- **critique**：Nielsen 启发式 40 分制 + P0-P3 问题清单，快照存 `.impeccable/critique/`。
- **audit**：无障碍/性能/主题/响应式/实现完整性 5 维 /20 分。
- 按 Impeccable 自己 SKILL.md 的命令协议调用；**只用它的审查类命令，不用 build/fix 类命令**（polish/shape/animate 等一律不用）。

### 2.5 修复回流（谁建的谁修）

- 营销页的问题 → 回流给 **Taste** 修；产品页的问题 → 回流给 **interface-design** 修。
- 修复时把 finding 原文 + DESIGN.md 一起交给生产者。
- 修完**必须复评**：重跑 2.1 + 2.2 扫描和 critique，分数留档（critique 自带 trend）。
- P0/P1 未清零不算完成。

---

## Phase 3：迭代与规范演进

- **每次 UI 变更都经过本工作流**：读 DESIGN.md → Phase 1 路由 → 构建 → Phase 2 审查。不绕过。
- **规范演进唯一入口是改 DESIGN.md**：用户确认的设计变更（换色、加字体、调圆角）→ 直接编辑 DESIGN.md frontmatter 对应字段 → 重跑 detector 确认现有代码与新规范的兼容情况，漂移处回流生产者修。
- interface-design 沉淀的组件规范只追加进 `## Components` 节；全局 token 的变更只能由用户拍板后改 frontmatter。

---

## 硬性规则（任何阶段都适用）

1. 项目里没有经用户确认的 DESIGN.md，**不动工**任何页面。
2. **永远只有一份规范文件**。禁止创建 `.interface-design/system.md`、MASTER.md 或任何平行规范（UUPM 的 `--persist` 不要用）。
3. Impeccable **只审不修**；修复永远回流给生产者。
4. 审查不通过（detector 有 design-system-* finding 或 critique 有 P0）**不交付**。
5. DESIGN.md 的 frontmatter 格式不许手写改动结构（嵌套 map、无列表、字符串加引号）——detector 的解析器只吃这个子集。加颜色加字号随便加，结构别动。

## 资源速查（路径 = 环境探测节解析出的 HOME 变量）

| 用途 | 位置 |
|---|---|
| UUPM 检索脚本 | `$UUPM_HOME/scripts/search.py` |
| UUPM 知识库数据 | `$UUPM_HOME/data/` |
| 桥接脚本（UUPM JSON → DESIGN.md） | `$ZEDUI_HOME/scripts/uupm_to_design.py` |
| Impeccable detector CLI（源码级 + 浏览器引擎共用） | `$IMP_HOME/scripts/detector/detect-antipatterns.mjs` |
| Impeccable 豁免管理 | `$IMP_HOME/scripts/hook-admin.mjs` |
| Taste skill 完整能力 | `$TASTE_HOME/SKILL.md` |
| interface-design skill 完整能力 | `$ID_HOME/SKILL.md` |
| Impeccable skill 完整能力 | `$IMP_HOME/SKILL.md` |
