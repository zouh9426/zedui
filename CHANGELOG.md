# CHANGELOG

本项目所有值得记录的变更都写在这里。格式约定：每条目回答两个问题——**改了什么**、**为什么这么改（决策理由）**。

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
