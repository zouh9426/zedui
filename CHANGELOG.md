# CHANGELOG

本项目所有值得记录的变更都写在这里。格式约定：每条目回答两个问题——**改了什么**、**为什么这么改（决策理由）**。

## [0.4.1] - 2026-08-15

compatibility / release-hardening patch：第一轮修四处已确认问题（无架构变更）；第二轮追加 doctor 宿主对齐与 A/B 试点回流修复，其中包含一个 schema 小增补（`typography.mono` 可选角色）与 token_lint 边界修正；第三/四轮为验收打回修复与发布后审计收尾（tag 定版时一并并入）。

### 第四轮（zedcheck Heavy 审计收尾 + CI 红线拓宽）

- **zedcheck Heavy 全项目审计收尾**：① SKILL.md 三处命名统一为品牌小写（frontmatter description 的 `UI-UX-Pro-Max` → `ui-ux-pro-max`，26/242 行 `ZedUI 硬门禁` → `zedui 硬门禁`）——0.3.2 已确立"skill 名引用统一品牌小写"，这三处是漏网；② COMPATIBILITY.md 头部版本标签 v0.4.0 → v0.4.1 并注明 Heavy 复测——契约在 v0.4.1 工作树上实测不变，旧标签会让下一名 Agent 误以为 v0.4.1 未验证；③ `.gitignore` 补 `__pycache__/` 与 `.pytest_cache/`——本地跑测试/脚本必然产生这两类缓存，此前靠 pytest 内部自忽略兜底，根因修复防反复。审计本体（83 单测、doctor 全链路、桥接三层一致、token_lint 边界）未发现行为缺陷。理由：一致性缺陷虽小，但 skill 的读者是下游 Agent，命名/版本标签的口径不一是最低成本的误导源。
- **no-private-paths 检查模式拓宽**：原 grep 只查 `/Users/...` 一种形态，home 相对写法（`~/…`）和 Linux/Windows 用户目录形态全部漏网（v0.4.0 的历史残留正是从此洞漏入、事后靠重写历史清除）。现覆盖五类形态；`[D]`/`[U]` 字符类写法保证检查器自身与规则描述文字不自命中。理由：隐私红线的事前闸门必须比"事后改写历史"便宜。

### 第三轮（验收打回修复）

- **authoritative HOME 的"来源"语义修正（文档层）**：第二轮的 SKILL.md/SETUP 把"agent 按候选目录扫描出的路径"直接称作"宿主实际选定的路径"——但目录扫描本身就是和 doctor 自动发现同源的推断，这么写等于把推断误称成事实，正是 --skill-home 要防的那类假安全感。现两档区分：宿主主动暴露的加载注册表（会话 skill 列表等）才是真 authoritative，显式传入；扫描推断的路径可传但需如实认识其性质，拿不准就让 doctor 无参自动发现、以 `[auto-discovered]` 标注为准。SKILL.md 环境探测节与 SETUP 双语 Step 5 第 4 项同步修正，doctor 代码行为不变（它本来就不判断来源真伪，只如实标注）。理由：机制修对了但文档把语义说过头，使用者照样会误信。
- **token_lint 的 Tailwind 定位类百分比误报**：`top-[50%]` / `inset-x-[10%]` 等 Tailwind 定位 arbitrary 类此前仍按全量正则抓百分比，与第二轮刚确立的"定位百分比是摆放不是间距"规则自相矛盾。现 Tailwind 定位前缀（top/right/bottom/left/inset/inset-x/inset-y）与 CSS 定位属性同规则：绝对长度照抓、百分比放行；间距类百分比（`p-[5%]`）照抓。新增 3 条回归测试。理由：规则刚立就在相邻路径上自相矛盾，是最伤门禁可信度的一类残留。

### 第二轮追加（doctor 宿主对齐 + A/B 试点回流）

- **doctor 支持显式 authoritative Skill HOME（宿主对齐，防"检了 A 副本、宿主跑 B 副本"的假绿）**：新增 `--skill-home <skill>=<path>`（可重复、可只传部分）。显式路径优先于自动发现，且 fail-closed 校验（路径存在 / 是目录 / 含 SKILL.md / frontmatter `name:` 匹配），无效即 critical failure、**不退回自动发现**——显式路径的含义是"宿主实际加载这份"，它坏了却偷跑另一份等于再造假绿。未显式指定的 skill 继续自动发现。理由：doctor 自己硬编码的候选目录顺序不可能精确复制 Kimi Code / Claude Code / Codex 各自（且会演化的）loader precedence；编排层本来就先解析五个 HOME，把解析结果传进来才能让 doctor 体检"宿主真正会用的那一份"。
- **自动发现补齐 project scope + 多副本文案诚实化**：候选目录新增 `<project>/.kimi-code/skills/` 和 `<project>/.claude/skills/`（项目级优先顺序保持）；解析输出标注来源（`[explicit]` / `[auto-discovered]`）；多副本 warning 改为明确声明"自动发现选的第一命中不保证等于宿主实际选择，请用 --skill-home 指定"。理由：fallback 可以方便，但不能让人误以为它等于宿主的真实选择。
- **fake UUPM probe 测试补强**：测试树的 fake search.py 从"忽略 argv"改为断言 probe 真的传入了位置查询词 + `--design-system` + `--json`——doctor 以后误删这些参数时测试直接红，而不是假成功。
- **DESIGN.md schema 补 mono 字体角色（SSOT 裂缝修复，A/B 试点实测驱动）**：代码密集型 UI 必然用等宽栈（代码块/endpoint/key/日志），但 schema 只有 heading/body 两个字体角色——detector 的 `design-system-font` 把未登记的 mono 栈报漂移，design-system-* 又不许豁免，生产者被迫在页面 `:root` 自建第二 token 定义点。现桥接脚本端到端支持 `typography.mono`（JSON 字符串或 `{fontFamily}` 形态均可）→ frontmatter → 正文 generated 块 → tokens.css 的 `--font-mono`；frontmatter 里 mono 存在但为空时 strict 重同步报错。SKILL.md 0.3 确认项新增第 5 条（mono 栈）。理由：唯一token定义层是铁律，铁律覆盖不到的合法需求只会逼出地下通道。
- **token_lint 两个边界修正（A/B 试点实测驱动）**：① 新增行内豁免——行内注释含 `token-lint-ignore` 即跳过该行（可 grep 审计），此前已 disposition 的合法 finding 无机械出口，exit code 永远 1，"全绿"信号失真；② 定位属性（top/right/bottom/left/inset 系列）只抓绝对长度字面值，百分比不再报——`top: 50%` 居中、装饰光晕 `top: -20%` 是摆放不是间距节奏，此前会把生产者逼成"为过门禁改写等价怪写法"。间距属性上的百分比（`padding: 5%`）照抓。SKILL.md 2.3b 同步。
- **SKILL.md 补四条实测记录**：① 宿主 skill 注入是会话快照，skill 更新后需新开会话（否则拿到旧工作流）；② 浏览器引擎扫全量 DOM 含 hidden 视图，可见性类 finding 需人工甄别；③ fullPage 截图不触发 IntersectionObserver（scroll-reveal 页面截出空白下半页）且 sticky 元素在长图中重复——先模拟滚动全程再截；④ detector exit 2 = 有 finding 而非出错（两个执行者都误判过）。SETUP 双语 Step 5 第 4 项改为显式 `--skill-home` 调用；README 双语各加一句说明。

### 第一轮（2026-08-15 早些时候）

- **doctor 的 UUPM 检查 fail-closed 化（假绿修复）**：此前 `ui-ux-pro-max` 的 SKILL.md 能解析、但 `$UUPM_HOME/scripts/search.py` 完全缺失时，[4/6] 只输出 warning 并以 "optional" 跳过真实契约探测——最终仍可 "All critical checks passed." 并 exit 0，而 ZedUI Phase 0 的核心链路必须调用 search.py，这等于把残缺安装判健康。现改为：标准路径存在则照旧真实 probe；标准路径不存在但在 `$UUPM_HOME` 内找到**唯一**候选时，输出 upstream path drift 的 warning 后用该脚本继续真实 probe；找到**多个**候选无法可靠判定入口时拒绝猜测、直接 critical failure；完全找不到任何 search.py 时 critical failure、doctor 返回非 0。理由：体检工具对核心依赖缺失放水，比没有体检更危险——它让"装完了"的确认失真。
- **doctor 回归测试基础设施修正**：`test_doctor.py` 的 fake 完整 skill 树此前故意不提供 UUPM search.py，把"缺失只 warning"锁成了正常路径。现完整安装包含一个真正响应 `--design-system --json` probe 的 fake search.py（返回满足桥接契约的最小合法 JSON，不 mock probe 本身）；新增 4 条回归：标准路径 probe 成功 exit 0、完全无 search.py 必须 exit 1 且报 critical、唯一 fallback 候选 warning 后真实 probe 通过、多候选 ambiguity fail-closed。理由：测试锁错行为比没有测试更糟。
- **critique 评分表述与 upstream 当前协议对齐**：SKILL.md Phase 2.1 原写"Nielsen 启发式 40 分制"，但 Impeccable 4.1.1 的 critique 协议允许启发式在确实不适用时标 n/a、分母按 applicable maximum 重算（8 项适用为 /32）。现改为版本兼容表述：评分细节以 Impeccable 自己的 critique 协议为准，zedui 不写死分母。理由：编排层硬编码 upstream 规则细节，upstream 一变就成错误指令——这条原则在 0.4.0 的版本契约里已确立，此处是漏网的一处。
- **SKILL.md 顶部 workflow 总览与 Phase 3 对齐**：顶部原写"规范演进只通过修改 DESIGN.md frontmatter"，与 Phase 3 的实际分工（token 类走 frontmatter；marketing/product dials 属 Overview 人工区）冲突，会误导执行者把 dials 塞进 frontmatter。现改为三句分述：UI 变更走 Phase 1 → 2；token 类演进走 frontmatter；dials 按 Phase 3 更新 Overview 的 dial 表。schema 不变，不产生第二份 SSOT。理由：同一文件两处对同一流程说法不一致，执行者必然二选一踩错。
- **SETUP 双语编号修正**：Step 5 自检第 1 项原写"不代替第 4 步的全链路体检"，但真正的 doctor 体检是 Step 5 内部的第 4 项（Step 4 是浏览器引擎配置）。中英文同步改为指向"下方第 4 项 doctor"。纯文案修正。

## [0.4.0] - 2026-08-14

外部审计（对照四个上游 skill 当前真实接口逐条核验）后的架构级修复：SSOT 机制闭环、Impeccable 4.0.4 协议适配、桥接脚本 fail-closed 化、补测试与体检工具。

- **SSOT 自相矛盾修复（最大架构 bug）**：此前桥接脚本把 token 值同时写进 DESIGN.md frontmatter 和正文表格，而 `--from-design` 只重生成 tokens.css、正文永不回写——Phase 3 改几次 frontmatter 后，"唯一规范文件"内部就出现两套不一致的值（frontmatter 新、正文旧），生产方 LLM 可能读到旧值。现引入 `zedui-design-schema-v1`：正文 token 表格（colors / typography / spacing / rounded 四块）包进 `<!-- zedui:generated:* -->` 标记成为 frontmatter 的派生视图，`--from-design` 从 frontmatter **同时再生正文标记块和 tokens.css**，标记外内容（风格意图、`## Components` 等人工区）脚本永不触碰；frontmatter 新增 `google_fonts_url` / `css_import` 两个字段使字体加载提示也能被同步再生。旧版无标记文件跑 `--from-design` 会被拒绝并给出迁移指引（用原 JSON 加 `--force` 重新生成一次）。理由：SSOT 不能靠"记得同步两份拷贝"维持——0.3.5 消灭了代码侧的第二份拷贝，这一版消灭文档内部的第二份拷贝。
- **Phase 2 重排以适配 Impeccable 4.0.4 协议（上游接口漂移）**：① 新增 2.0——每 session 先跑一次 `context.mjs` 并遵循其指令（`CONTEXT_STALE` / `MANUAL_DETECTOR_REQUIRED` 等），此前 zedui 完全跳过这一硬协议步骤；② critique 提前到 detector 结果之前——上游明文规定 Assessment A（主观设计判断）必须先于 detector findings 进入父上下文完成、A/B 必须是互不可见的隔离子代理、detector 由 Assessment B 自己运行；zedui 旧顺序（先 detector 再 critique）直接锚定设计判断，违反协议。原 2.1/2.2 的 detector 实操知识下沉为 2.3「ZedUI 硬门禁」（漂移清零 / 间距 lint / 浏览器引擎 / 多端视口 / 截图人工核查），2.4 豁免、2.5 修复回流顺延。理由：编排 skill 的生命力取决于跟住上游协议——这次漂移本身就是"没有版本契约"的直接后果（见 COMPATIBILITY.md）。
- **间距字面值兜底（假保证修复）**：硬性规则 6 此前声称"组件层字面值必然成为 finding"，但上游 detector 的 design-system 比对只有 font/color/radius/font-size 四条 allowlist，**不覆盖 spacing**——`padding: 17px` 永远成不了 finding。新增 `scripts/token_lint.py`：扫描组件层样式的 margin/padding/gap/inset 等 23 个间距属性，长度字面值且不含 `var()` 即报 finding（生成物与 `--exclude` 豁免），作为硬性规则 6 的间距层机械兜底；规则 6 与 2.3 措辞改为如实描述两层兜底的各自边界，删除"必然"式无支撑保证。理由：文档里的强保证必须有对应的机械 enforcement，否则比不写更危险——它让人放弃人工检查。
- **桥接脚本 fail-closed 化**：新增 `validate_design_system()`——缺 11 色角色（副本缺 `cta` 等必需角色时必须 0.3 补齐）、缺标题/正文字体、字号阶梯 <6 档（此前硬编码取 `2xl`/`base`，短阶梯静默产出 TBD）、缺任一组 dial（marketing 此前只能 CLI 传入，忘传静默 TBD），严格模式一律报错不落盘；`--allow-incomplete` 显式豁免才写 TBD。JSON fallback 的 product dials 补上与 CLI 一致的 1–10 范围校验。理由：工作流把"DESIGN.md 存在"当作"规范已确认"，语法合法但满是 TBD 的文件比没有文件更糟。
- **frontmatter 解析器与上游对齐**：key/value 切分从 `partition(":")` 改为与 impeccable `findTopLevelColon()` 同构的状态机（引号内冒号、转义、引号外行内注释都能正确处理），`--from-design` 模式的 frontmatter 校验同步增强（非标量值拒绝——裸写未加引号的 hex 会被 YAML 注释规则吃掉值，现在给出明确报错）。理由：两个工具读同一份 frontmatter，解析行为不一致就是互操作性 bug；"机械转换保证可解析"的承诺需要解析器本身够格。
- **token 生成加固**：CSS 变量名加字符集校验（含空格等非法 key 报错而非生成废 CSS）、值加单行/无 `;{}` 校验、两处写盘改原子写（临时文件 + os.replace，构建全部完成前不落盘）。另修复本轮重构引入、由新增测试抓获的阶梯变量名双前缀回归（`--text---2xl` → `--text-2xl`）。理由：生成物的正确性不能依赖输入恰好干净。
- **新增 22 例 unittest 测试套件 + Python 矩阵 CI**：`scripts/tests/test_uupm_to_design.py` 覆盖 golden（双向）、round-trip（改 frontmatter 三层同步）、CJK 字体栈、quoted key / YAML 边界、extra token 透传、自定义阶梯、dial 越界（CLI/JSON 两路）、incomplete fail-closed、短阶梯、非法 CSS key、无标记旧文件、原子写/--force；新增 `.github/workflows/tests.yml` 在 Python 3.8 / 3.11 / 3.13 跑 unittest + token_lint 冒烟 + py_compile。理由：0.3.x 的 CHANGELOG 显示桥接脚本已进入"靠人工回归不可靠"的复杂度——quoted key、3.8 兼容、迁移丢值、CJK URL 都是真实修过的边界；没有测试，每次改动都在赌。
- **新增 `scripts/doctor.py` 环境体检 + `COMPATIBILITY.md` 版本契约**：doctor 把 SKILL.md「环境探测」节机器化（五个 skill HOME 按 frontmatter `name:` 解析、项目级优先先命中先用、跟随符号链接、重复安装提示），另查 impeccable 版本（对 4.0.4 基线）、关键脚本存在性、zedui 脚本可编译、项目侧 DESIGN.md 可解析 / 标记齐全 / tokens.css 与 frontmatter 同步。COMPATIBILITY.md 落档 v0.4.0 实测的上游版本与接口契约（impeccable 4.0.4 的 context.mjs 每 session 协议与 critique A/B 隔离；taste 的 Honesty rule 与 next/font 条款；interface-design 的 system.md 读写闭环；UUPM 的 `--design-system --json` 契约），本机安装契约以 doctor 体检为准。理由：本次审计暴露的所有协议漂移（context.mjs 缺位、critique 顺序冲突）都源于"装的是 upstream latest 却没有 tested-version 契约"——没有基线就没有漂移检测。
- **SKILL.md 编排层其余修正**：① 环境探测补"项目级优先、先命中先用"的重复安装裁决（此前五个候选目录只列顺序无优先级声明）；② 缺 skill 处置从"缺一全停"改为按任务链懒判定（纯营销项目缺 interface-design 可继续，路由到才必须装）；③ 豁免章节矛盾修复——前文"design-system-* 没有豁免"与后文把 design-system-* 放进 ignore-value 示例并存，现统一为"四条 design-system 规则一律不豁免"；④ Taste 约束指令补官方设计系统例外（Material/Fluent/Carbon 走官方包，不拿 DESIGN.md token 强刷官方组件，例外本身记录进 DESIGN.md）与字体加载条款（生产环境 next/font 或 self-host，`css_import` 仅开发期便利）；⑤ interface-design 约束第 1 条补明 system.md 保存环节的落点重定向到 `## Components`；⑥ "10 色角色"表述修正为 11 必需角色口径（色板输出版本中性化在第三轮收尾）；⑦ 删除/弱化全部无支撑的绝对化措辞（"100% stable"、"机械保证"等），README 双语同步。理由：编排层文档的每一处失真都是使用方 agent 的错误指令。
- **README 双语同步**：README.en.md 残留的 Workflow 代码块与结构树注释中文化清理；双语 README 更新 Phase 2 顺序、fail-closed 行为、`--from-design` 正文同步、新增脚本条目。SETUP 双语无相关内容，未动。
- **发布前审计第二轮修复（2026-08-15）**：① **typography 冗余事实源删除**——frontmatter 不再记录 `heading.fontSize`/`body.fontSize`（它们就是 `scale.2xl`/`scale.base` 的第二份拷贝，改阶梯必 stale），标题/正文字号约定取 scale 档位，SKILL.md 硬性规则 5 写明约定；② **fail-closed 统一强度**——`validate_token_contract()` 单一契约同时服务 Phase 0 落盘与 Phase 3 `--from-design` 重同步（此前重同步不查 11 色角色、不查 base/2xl 存在，"初次严格、日后变松"恰好放过了最易被手改弄坏的阶段）；③ **token_lint 加固**——`var(` 整项放行漏洞修复（先剥离 var() 引用再逐 token 扫描，`var(--space-sm) 17px`、`calc(var(--space-md) + 3px)` 必报）、补 18 个 logical properties（margin/padding/inset 的 inline/block 系列）、React 裸数字内联样式（`padding: 17` 即 px）、Tailwind arbitrary 间距类（`p-[17px]`/`-m-[4px]`/scroll-m* 等，Taste 默认 Tailwind v4 故非冷门）、目录遍历默认 prune node_modules/.next/dist/build/coverage/vendor 等；④ **doctor 真实契约化**——新增正文 generated block 与 frontmatter 的逐字节一致性比对（手改表格必被抓）、UUPM 探测从 `--help` 升级为真实执行最小 `--design-system --json` 并验证 schema、detector 入口改认公开 facade `scripts/detect.mjs`、版本报告区分 tested baseline / installed / contract；⑤ **上游接口跟进**——SKILL.md 的 context 引导改为有目标时必传 `--target`（上游明文要求），detector 命令全部切换到公开 facade；COMPATIBILITY.md 记录"上游已发 4.1.1、本地基线 4.0.4、升级注意点"。审计中"本机 impeccable 仍为 4.0.4（4.1.1 是上游仓库当日新发，非本地漂移）"维持原判；另一条"UUPM 未引入 semantic palette"的结论当时只探测了本机副本，证据不足（第三轮已核实改正，见下条）。测试从 22 例增至 51 例（桥接 24 + token_lint 18 + doctor 9）。
- **发布前审计第三轮修复（2026-08-15）**：① **type scale ≥6 真正落实**——契约此前只查 `base`/`2xl` 存在，手改成只剩 5 档（含这两者）也能过；strict 模式现要求总档数 ≥6，含回归测试；② **UUPM provenance 改正**——经 `gh api` 独立核实，public upstream main（a38d04c，2026-08-13）确已输出 16 个 semantic roles（`on_secondary`/`card`/`card_foreground`/`muted_foreground`/`on_destructive` 等）+ 遗留 `cta`/`text`/`on_cta`，第二轮"semantic palette 已证伪"是只探本机副本导致的错误结论，已改正：COMPATIBILITY.md 明确区分本机实测副本与 public upstream，SKILL.md 全部色板描述版本中性化；连带真 bug 已修——新版 UUPM 对未填充色槽输出空字符串，严格契约会把空值 extras 误拦，现空值 extras 自动丢弃、有值 extras 照常透传（新增 16-role fixture 测试锁定）；③ **doctor 的 UUPM probe 与桥接共用 schema**——probe 不再维护"只查 3 个色角色"的弱 schema，改为复用桥接的 `COLOR_ROLES` 做 key 级校验（缺 `cta` 等任一必需角色**键**即 probe 失败）；同时校准了一个实测发现的误报：UUPM 知识库未命中时对部分色槽输出**空字符串**（本机实测 "contract probe" 查询即触发），空值是数据不是 schema（0.3 确认环节补齐），probe 只报注不误红；doctor 定位写明"全链路安装体检，只对本机安装副本负责、可以比运行时 lazy 解析严格"；④ **token_lint 两个缺口**——目标文件读取失败此前打印错误后仍可能返回 OK（硬门禁不可靠），现累计读错并以 exit 2 收场；长度单位补 dvh/dvw/svh/svw/lvh/lvw/vmin/vmax；⑤ **措辞精确化**——SKILL.md"三层永远一致"改为"同步命令成功后三层一致；每文件原子替换（非两文件事务），异常由 doctor 检出恢复"。测试从 51 例增至 59 例。

- **发布前审计第四轮（2026-08-15，docs/integration-only）**：① **SETUP 双语第 5 步接入 doctor**——推荐安装入口的自检链此前停留在 v0.3.x（三项 --help 冒烟即宣布完成，且优先调用内部 detect-antipatterns.mjs），现改为 detect.mjs 公开入口 + 以 `doctor.py` 全链路体检收尾，critical 全过才算安装完成（否则 v0.4.0 的兼容安全网被推荐安装流程绕过）；② COMPATIBILITY.md 头尾残留的"上游漂移以 doctor 为准"与中部"离线体检只对本机安装负责"的矛盾统一为后者口径（CHANGELOG 旧条目同步）；③ Phase 3 补 dial 演进路径——"规范演进唯一入口是 frontmatter"精确化为 token 类走 frontmatter、marketing/product dials 属 Overview 人工区经确认直接更新（不改 schema）。纯文档与安装链修复，无代码改动。

## [0.3.7] - 2026-08-12

全量审计（脚本实测 + 文档交叉核对 + 某生产项目试点回流）后的集中修复。

- **桥接脚本四个边界 bug 修复**：① 带引号的 frontmatter key（如 `"20": "20px"`）此前会生成 `--text-"20"` 非法 CSS 变量名（浏览器静默丢弃整条声明），现 key 与值一样剥引号；② 一处 PEP 584 dict union（Python 3.9+）改回 3.8 兼容写法，与文档"Python 3"承诺对齐；③ `--tokens-css` 父目录不存在时裸 traceback，现自动 makedirs；④ `--from-design` 与 `-o`/位置参数同用从此前静默忽略改为友好报错。理由：前三者都是"按文档正常用法就会踩中"的边界缺陷，手改 frontmatter 是 Phase 3 规范演进的正式路径，不能靠用户避让。
- **README/SETUP 文档对齐**：README（中英）补上 0.3.5 引入的 token 唯一定义层（此前头条功能在门面完全缺席）；README.en.md 两处链接从指向中文 SETUP.md 改为 SETUP.en.md；SETUP.en.md 两处中文占位符残留英文化。理由：门面与 CHANGELOG 记录的功能状态脱节会误导新接入者。
- **SKILL.md 补三条实测教训**：① 2.2.1——Chrome CLI `--screenshot --window-size=390` 有约 500px 最小窗宽伪影，移动端截图必须用 puppeteer setViewport / CDP 设备模拟等真实模拟（2026-08-12 某生产项目实测：CLI 截图呈现"整页溢出"假象，真实模拟下无溢出）；② 2.3——ignoreValues 的 files 匹配对 URL 模式浏览器扫描不生效、`.impeccable/` 被整体 gitignore 时豁免配置不随仓库走；③ 2.1——design-system-color 实测只抓部分属性位置的字面值（box-shadow 值内等会漏），detector 清零后需人工 grep 补网。理由：三条都是试点中真实踩过并付出过排查成本的坑，不进文档就会再踩。
- **SKILL.md 补六处流程缺口（0.0/0.3/0.4/2.1）**：① 0.0 迁移落盘前把旧文档全部圆角/字号值对照桥接脚本默认阶梯，缺的显式 `--rounded` / `--type-scale` 传参——默认阶梯不含旧值时旧值被静默丢弃，detector 随后把页面旧值报成漂移（2026-08-12 某模拟项目实测：旧值 6px 圆角不显式传参即被丢弃）；② 0.0 补建议 token（dark_*、secondary_text 等）前对照页面实现值——design-system-color 有颜色通道容差（±6），建议值接近既有实现色会把未登记色"洗白"成色板内不再报漂移；③ 0.0 无样式入口形态（纯内联样式/无全局 CSS/无 :root 块）时 tokens.css 落项目根或样式目录并在 PROJECT_INDEX 登记"未接入，留待页面改版时启用"，不算漏步；④ 0.3 CJK 确认项补 Google Fonts URL 一致性——UUPM 输出 URL 可能含 heading/body 之外的字体（实测出现过 Cinzel），design-system-font 比对 URL 必报 finding；CJK 栈落地需同步改 JSON 的 heading/body/google_fonts_url/css_import 四个字段；⑤ 0.4 补 `--tokens-css` 落盘目录指引（Next.js 用 app/、普通前端用 css/ 或 styles/、无样式目录先落根）；⑥ 2.1 检测边界补颜色通道容差（±6）——与色板近似的未登记色判为色板内静默通过，临界色值需人工复核。理由：全在模拟项目实测中暴露的"文档没说导致执行时踩坑"场景，补文档即可让迁移/确认/落盘路径不再依赖执行者自己撞出来。
- **桥接脚本 tokens.css 头注释可移植性**：`Single source of truth` 行不再嵌 `-o` 的绝对路径（JSON 模式）或相对名（--from-design 模式），统一取 basename——同一项目两种模式重生成产物逐字节一致（实测 JSON 模式 `-o /abs/path/DESIGN.md` + `--from-design DESIGN.md` 往返 tokens.css byte-identical）。理由：两模式产物仅注释行不同会污染 diff、干扰"生成物可比对"的机械保证。

## [0.3.6] - 2026-08-11

- **维护纪律修正：实测依据匿名化**。此前 0.3.4/0.3.5 等版本的 CHANGELOG、commit message、Release notes 在"实测依据"中含用户项目可识别信息（项目名/内部任务编号/项目内路径），已连 git 历史一起改写清除（rebase + force push + Release notes 修订）；AGENTS.md 红线新增第 4 条把匿名化固化为维护规则。理由：公开仓库里可识别信息与隐私同罪，仅靠"不含密钥"的标准不够。

## [0.3.5] - 2026-08-11

结构性防漂移：token 定义层从"靠人同步的两份拷贝"改为"DESIGN.md 单源 + 机械派生"。

- **桥接脚本新增 tokens.css 输出**：`uupm_to_design.py` 加 `--tokens-css`（JSON 模式随 DESIGN.md 一起生成）与 `--from-design`（反解既有 DESIGN.md frontmatter 单独重新生成，Phase 3 规范演进路径）两种模式；输出 `:root` CSS 自定义属性（colors/字体/type-scale/rounded/spacing），带"生成物禁止手改"头注释。反解器是 frontmatter 子集的独立解析器，与生成器互为往返（实测 JSON 直出与 DESIGN.md 反解产物逐字节一致）。理由：某生产项目实测暴露的根因是"同一事实两份定义（规范文档 + 代码 token 层），靠人保持同步"——规范文档记录的一个焦点色从未在代码中实现过，漂移自规范诞生起隐形存在。任何靠"记得同步"维持的一致性都会漂移；结构性修法是消灭第二份拷贝，让代码侧 token 层只能从 DESIGN.md 机械派生。
- **硬性规则新增第 6 条「token 唯一定义层铁律」**：字面值只许出现在 token 定义层，组件/页面代码只许引用 token 变量；tokens.css 永不手改。铁律成立后漂移空间收缩到"声明处字面值"——恰好是 detector design-system-* 规则的既有覆盖范围，无需新增任何检查点（不自检加行、不加发版扫描）。Taste / interface-design 的约束指令各补一条引用变量要求。SKILL.md 顶部 SSOT 段、0.4 落盘、0.0 迁移落盘、Phase 3 规范演进四处流程同步。理由：同一条根因的另一半——只生成 token 层而不约束使用，组件照样可以绕开它写字面值。

## [0.3.4] - 2026-08-11

- **Phase 0 新增 0.0「既有规范迁移」分支**：项目已有 DESIGN.md 但不符合契约（指针文件/无 frontmatter/解析失败）、或无 DESIGN.md 但有旧设计规范文档时，不再走 0.1~0.4 重新定方向，而是"翻译而非重定"——旧文档决策逐项翻译成 UUPM JSON（禁改旧值、禁发明 token），四确认项照旧检查，用户确认卡点保留，桥接脚本落盘（`--force` 覆盖指针文件），detector 验证解析。理由：某生产项目实测——uiweft 时代的指针式 DESIGN.md + docs/design/ 下细则文档的分离形态，让 detector 的 `design-system-*` 硬校验无规范可比（Phase 2 裸奔）；旧 Phase 0 只覆盖"没有 DESIGN.md"的场景，带历史规范的项目接入无路径。

## [0.3.3] - 2026-08-11

端到端实测（模拟用户经 zedboot 建新产品走全流程）后的问题修复。

- **桥接脚本透传额外色 token**：`uupm_to_design.py` 的 frontmatter 与正文颜色表原先只渲染固定 11 键白名单（+`text`），0.3 确认环节按 SKILL.md 补进 JSON 的 `secondary_text` / `dark_*` 等 token 会被静默丢弃（实测复现）。改为白名单之后按 JSON 顺序透传其余颜色键（`text`/`notes` 仍按原特殊规则处理）。理由：SKILL.md 0.3/0.3.1 的流程是"改 JSON → 重跑桥接"，补充 token 必须能存活，否则确认环节形同虚设。
- **环境探测补 `find -L` 说明**：SKILL.md 解析规则与 SETUP 双语第 2 步补充"用 `find` 时加 `-L` 跟随符号链接"。理由：实测裸 `find` 不跟随符号链接，会把符号链接安装的 skill 整棵漏掉，按名识别逻辑本身没错但实现容易踩坑。

## [0.3.2] - 2026-08-11

维护者本机部署模式改为"真源 + 符号链接"，AGENTS.md 部署位说明同步改写为真源纪律；frontmatter `name:` 及各处 skill 名引用统一为品牌大小写 `zedui`。

- **真源纪律**：`~/.kimi-code/skills/zedui` 由真实目录副本改为指向仓库 `zedui/` 的符号链接；原"Kimi Code 加载器不跟随符号链接"的踩坑记录在 v0.34.0 上经对照实验证伪（符号链接 skill 与真实目录 skill 均正常加载），rsync 副本模式废弃。理由：与 zedback / zedboot 真源纪律统一，消除副本漂移；公开安装指引（README/SETUP 的拷贝安装）面向普通用户，不受影响。
- **frontmatter `name: zedui` 改为 `name: zedui`**：skill 列表等以 `name:` 为显示名的场合此前显示小写 `zedui`，与品牌名 zedui 不一致（兄弟 skill zedboot 的 frontmatter 已是品牌大小写）。SKILL.md 环境探测表、SETUP 双语检测/安装表、README 双语触发语、AGENTS.md 正文同步替换；SKILL.md 与 SETUP 双语的 name 匹配规则补充"不区分大小写"，兼容改名前已安装的副本（`name: zedui`）。目录名 `zedui/` 与路径占位符保持小写不动（skill 按 frontmatter `name:` 识别，不挑目录名）。理由：品牌大小写统一；下游 zedboot 按 `name:` 检测本 skill，其匹配值需跟进同步为 `zedui`。

## [0.3.1] - 2026-08-11

GitHub 仓库改名跟进。

- **GitHub 仓库 `zouh9426/uiweft` 改名 `zouh9426/zedui`**（大小写敏感，品牌名为 zedui），本地 remote 同步更新；SETUP.md / SETUP.en.md 中预写的克隆地址 `zouh9426/zedui` 修正为正确大小写 `zouh9426/zedui`。理由：品牌改名收尾，GitHub URL 大小写不敏感虽不影响克隆，但文档应与品牌大小写一致。

## [0.3.0] - 2026-08-11

品牌改名：skill 由 uiweft 更名为 zedui。

- **目录 `uiweft/` 改名 `zedui/`，frontmatter `name: uiweft` 改为 `name: zedui`**，SKILL.md 环境变量 `$UIWEFT_HOME` 同步改为 `$ZEDUI_HOME`，AGENTS.md / README / SETUP 及对应 .en 英文版全部文档同步替换。理由：品牌改名；历史 CHANGELOG 条目保留原名不动，不做篡改。

## [0.2.0] - 2026-08-07

开源发布 + 工具无关化改造。

- **SKILL.md 移除全部硬编码安装路径**（原 `~/.agents/skills/...`、`~/.kimi-code/skills/...`），新增「环境探测」一节：agent 会话开始时在候选技能目录（`~/.agents/skills/`、`~/.kimi-code/skills/`、`~/.claude/skills/`、`~/.codex/skills/`、项目级 `.agents/skills/`）中**按 SKILL.md frontmatter 的 `name:` 字段**解析五个 HOME 变量，全文命令改用 `$XXX_HOME` 占位。理由：开源后面向 Kimi Code / Claude Code / Codex 等所有工具，路径硬编码等于私有；且目录名与 skill 名可能不一致（如 `taste-skill/` 目录装的是 `design-taste-frontend`），必须按名解析。
- **新增 README.md（中文主门面）/ README.en.md**：项目介绍、前置依赖、安装指引、快速上手。理由：开源门面；中文为主是因为目标用户群是中文用户。
- **新增 SETUP.md / SETUP.en.md 安装引导提示词**：用户贴给自己的 AI agent 即可完成全套依赖检查与安装。理由：四个配套 skill 均为第三方依赖，手动安装门槛高，让 AI 代办最省事。
- **新增 LICENSE（MIT，Copyright (c) 2026 zouh9426）**。理由：MIT 的「保留版权声明」条款即署名保留，满足作者诉求；skill 类项目无专利考量，不需要 Apache-2.0 的重量。
- **新增 AGENTS.md**：迭代纪律（同步 GitHub、写日志、双语同步、无私有路径红线）。
- **新增 GitHub Actions 私有路径检查 CI**。理由：防止后续迭代把本地路径误提交到公开仓库（设计已消除必要性，CI 做兜底）。

## [0.1.0] - 2026-08-07

基线快照。从旧工作区（UIweave_Skill）迁入的原始版本，路径为硬编码、仅供历史留档，不建议新用户使用。

继承自旧工作区的核心架构决策（详见 README）：

- UIweft 定位为四个 UI skill 的**工作流编排层**，自身无设计/审查能力：UUPM 定方向 → Taste/interface-design 按页面类型生产 → Impeccable 只审不修。
- **单一 DESIGN.md 作 SSOT**（Impeccable 的 google-labs 规范格式，YAML frontmatter），禁止一切平行规范文件；冲突优先级 `DESIGN.md > skill 内部默认规则`。
- UUPM JSON → DESIGN.md 走 `uupm_to_design.py` 机械桥接，保证 detector 可解析格式 100% 稳定。
- 开局人工卡点：UUPM 不提问，提问由编排层做（≤5 问，含内容语言、图片生成能力检测）；方案确认后才落盘 DESIGN.md。
- 修复回流生产者；豁免前决策必须先备案进 DESIGN.md。
- 经三轮模拟试点（三个模拟项目）验证，累计修进 SKILL.md 9+ 处优化。
