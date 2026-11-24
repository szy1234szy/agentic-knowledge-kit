# 工程手册

**安装、开发和发布都从这里查。** 首次接手先读 [项目说明与编码导航](project-understanding.md)，有具体任务时按下面的章节跳转。

- [Skill 使用指南](#skill-使用指南)
- [安装与升级](#安装与升级)
- [开发与知识同步](#开发与知识同步)
- [接入编程规范](#接入编程规范)
- [校验与发布](#校验与发布)

## Skill 使用指南

### 给一个老项目建档

按下文[安装套件](#安装与升级)，再用 Coding Agent 打开**目标项目根目录**。一句话就可以开始。

> 用 `$project-bootstrap` 帮我生成这个项目的工程资料。

如果只说「帮我生成项目资料」，目标仓库的 `AGENTS.md` 和 Skill 描述为 Agent 提供路由指引。点名 Skill 能把意图说清楚。如果使用的工具没有加载它，可要求 Agent 先读取目标项目的 `.agents/skills/project-bootstrap/SKILL.md`，再按步骤执行。安装完成后，由用户发起任务或由 Agent 按仓库指引选用 Skill。

1. **先检查已有资料。** Agent 读取项目 README、知识索引和相关说明，从一项常见工作选一条有代表性的流程。先问「核心入口在哪」「有哪些约束」「怎么验证」，看现有资料能答多少。
2. **从证据决定写什么。** 沿入口查实现、调用、配置和适用的测试或失败路径。现有资料能回答时直接引用。有缺口时，默认只完善一份 README 或项目概览。没有可用说明时才填 `docs/knowledge/project/overview.md`。中间件、故障影响或运维手册等专题可以按需点名，或在项目偏好中启用。专题仍优先补在已有文档。
3. **交付并验收。** 报告新增、原位更新和复用内容，同一组问题的前后答案，以及待核实事项。按实际检索需要更新索引，保留已有 ID 和人工说明。未找到历史决策依据或无法运行测试时，在对应位置注明。已接受或已验证的状态由负责人确认。[同一旧项目的前后走查](backlog.md#本轮验收记录)

`validate --strict` 和 `links` 用于检查索引、证据引用和文档链接。内容质量用读者任务检验，例如让新成员只从入口文档出发，找到实际改动入口和正确的验证方法。首轮结果的质量取决于选取的范围、项目留存的证据和实际核对的深度。[详细的资产生成与验收规则](../knowledge/asset-generation.md)

想先看建议，指定「只审查」。想重整一处资料，指定「只重写某文件或某章节」。不指定时按「增量优化」执行。[三种模式的示例指令](#怎样选择文档维护方式)

通用建档默认生成项目说明。点名功能契约或关键约束时，Agent 从同一次调查复用证据，按对应方法验收，并优先补到现有章节。[按用途生成三类常用资料](../knowledge/asset-generation.md#按用途生成三类常用资料)

### 给项目保存默认关注点

在目标项目按需创建 `docs/knowledge/generation-preferences.md`，填写关注功能、专题深度和验收问题。比如 Demo 只填写主要演示流程，关键业务可以为指定功能开启「失败行为与恢复｜深入」。以后同一句建档指令会沿用这份偏好，本次说「只补项目概览」就会跳过偏好专题。旧项目升级后，偏好由项目维护者按需创建；新版 Skill 能直接读取。[可复制的偏好示例](../knowledge/asset-generation.md#保存项目的建档偏好)

### 查某个中间件会影响哪些功能

> 用 `$project-bootstrap` 查这个项目的 Redis。列出每个实际用途、受影响的功能和 Redis 不可用时的表现。把能从代码确认的结论、实际验证和待核实项写进现有项目说明。

开发前可以用 `context --id <依赖或功能ID>` 从任一端找关联。修改调用路径后用 `impact <改动路径>` 找回需复核的章节。专题只在任务点名或偏好启用时执行。[产出及登记示例](../knowledge/asset-generation.md#中间件与故障影响) · [AgentOS 走查结果](backlog.md#中间件影响验收记录)

### 什么时候用哪个 Skill

| 你现在要做的事 | 调用 | 你会得到什么 |
| --- | --- | --- |
| 给旧项目建档，或补齐缺失的项目资料 | `$project-bootstrap` | 有证据的项目说明、必要资产及索引，以及本轮验收结果 |
| 接手或交接项目，想理解主流程与编码入口 | `$project-view` | 面向读者的项目说明、代表流程和证据入口 |
| 开始非简单功能、Bug 修复或重构 | `$task-context` | 当前实现、适用约束、决策和验证入口组成的任务上下文 |
| 评审重要方案、重构或一致性设计 | `$design-gate` | 对既有契约、架构边界和决策的核对，以及风险和验证要求 |
| 完成代码和测试，准备交付或合并 | `$knowledge-sync` | 本次变更影响的资产、应同步的内容和待复核事项 |
| 调查重大故障或重复错误 | `$incident-learning` | 已证实的根因、可复用防线和回归验证线索 |
| 阶段性清理过时、重复或矛盾的资料 | `$knowledge-audit` | 需要修复、合并、复核或归档的候选项 |
| 把已有团队编程规范接入当前项目 | `$standards-intake` | 带来源、适用范围、例外和验证办法的规则提案 |

一项开发任务通常从 `$task-context` 开始，重要设计用 `$design-gate`，实现并验证后用 `$knowledge-sync`。直接想补项目资料时，可以从 `$project-bootstrap` 开始。

## 安装与升级

**先在套件目录操作，再到目标项目验收。** 准备 Python 3.11 或以上版本，以及一个已存在的目标项目目录。把下面两个路径换成解压后的套件目录和你的项目目录。有 Git 时，先查看目标项目的工作区状态，便于识别安装差异。

~~~powershell
$kit = 'D:\downloads\agentic-knowledge-kit'
$target = 'D:\project\your-repo'
Set-Location -LiteralPath $kit
python --version
python .\install.py $target --dry-run
# 看过复制、跳过和冲突提示后，再执行安装
python .\install.py $target
Set-Location -LiteralPath $target
python scripts/knowledge.py validate --strict
python scripts/knowledge.py links
~~~

**怎样算成功。** 预览会输出 `Would copy=...` 和跳过数量。正式安装会输出 `Copied=...`。目标项目校验结果应有 `0 error(s)`，链接检查应有 `0 broken link(s)`。新建索引显示 `0 records` 属正常，已有索引按项目内容显示记录数。再执行目标项目相关测试，验证具体业务行为。

**升级旧版。** 在新版套件目录用 `python .\install.py $target --upgrade --dry-run` 看计划，再用 `python .\install.py $target --upgrade` 执行，最后重复目标目录中的两项校验。升级替换套件脚本、Skill 和套件使用指南，补齐缺失的模板。输出 `Usage guide` 指出新版说明的位置。目标已有索引、项目说明、`AGENTS.md` 和 CI 由目标项目继续维护。若目标在 Git 中，检查这些文件的 Diff 并把安装改动放在独立提交，便于审阅及回退。[当前套件指南](../../.agents/skills/project-bootstrap/references/kit-usage.md)

**遇到失败先看哪。** 若安装提示目标目录不存在、文件与目录冲突或路径越界，按报错中的路径核对，再重新运行预览。路径冲突在复制前检查。若安装成功但索引报错，到目标目录查看输出的记录 ID 和路径，核对该记录的文档、证据及范围后重跑校验。[安装脚本](../../install.py) · [安装测试](../../scripts/test_install.py) · [安装边界决策](records/adr-001.md)

## 开发与知识同步

1. 开发前用 `context` 从代码路径或功能 ID 找到相关资料，核对当前实现、决策和约束。
2. 写清需求范围、设计和验收条件；验证后记录实际结果。
3. 开发后用 `impact` 从本次变更路径找待复核的知识。有 Git 基线时可用 `--base`。
4. 更新真正改变的事实和证据，在同一 PR 里审阅代码、测试和文档。
5. 定期用 `assets --review` 或 `review` 检查过时资料。确认替代证据和引用后再归档。

套件自身使用 `--registry docs/self/registry.json`。其他目标项目使用已安装的项目索引。[证据反查开发计划](records/feature-impact-evidence.md) · [资产维护说明](../knowledge/asset-management.md)

在套件的 Git 工作区，开始任务时记下基线。完成后用同一基线复核索引和资料。

~~~powershell
$base = git rev-parse HEAD
# 完成变更并运行项目测试后
python scripts/knowledge.py --registry docs/self/registry.json impact --base $base
python scripts/knowledge.py --registry docs/self/registry.json sync-check --base $base
~~~

可以把这条指令直接给已打开目标仓库的 Codex：

> 用项目知识套件处理这项改动。先找出已有实现和必须遵守的约束，列出验收办法。完成实现并跑测试后，按变更路径反查受影响的知识，更新对应章节并写入实际测试结果。

有 Git 基线时可在 PR 中运行 `sync-check --base <开始提交>`。普通记录允许用字符串记录本次理由。受影响的不变量和核心资产需要本次更新的结构化复核，按 ID 写明 `reason` 和 `evidence`。删除、归档或降级时仍按原 ID 复核。新装项目的 PR 工作流读取本次改动的 `docs/knowledge/review.json`，本地可用 `--review-file` 指定。工具核对证据引用，评审仍要核对文档事实。

例如，从套件根目录复核安装变更时，可新建 `docs/review-this-task.json`，写下已核实的理由。请按实际检查结果填写。

~~~json
{
  "OPS-KIT-001": {
    "reason": "复跑旧项目升级，确认新版指南随工具更新，原有项目资料字节不变",
    "evidence": ["file:scripts/test_install.py#InstallerTest.test_upgrade_refreshes_guide_without_replacing_project_docs"]
  }
}
~~~

使用任务开始时保存的 `$base`，运行完整检查。仍有待复核记录时，严格模式会返回退出码 1。

~~~powershell
python scripts/knowledge.py --registry docs/self/registry.json sync-check --base $base --strict --review-file docs/review-this-task.json
~~~

### 怎样选择文档维护方式

向 `$project-bootstrap` 说明范围和模式。没有指定模式时，默认在已有文档里做增量优化。

| 模式 | 可以直接给 Codex 的指令 |
| --- | --- |
| 只审查 | 「只审查《工程手册》的安装部分，列出缺口和建议，先不修改。」 |
| 增量优化 | 「核对安装部分的命令与实际结果，原位补缺口，保留现有约束、人工说明和知识 ID。」 |
| 指定重写 | 「只重写《工程手册》的安装与升级章节，让新成员能照着执行，保留原知识 ID 和已确认的说明。」 |

### 如何验收同步说明

以「修改一处代码，同时命中同一手册中的安装和校验两节」为例。用下面三问复核这段说明。结果来自临时 Git 项目，修改了一个被两条记录共同引用的代码文件。

| 读者需要知道 | 实测结果和行动 |
| --- | --- |
| 完全没复核时怎么发现？ | `sync-check --base HEAD --strict` 列出两条待复核记录，退出码为 1。 |
| 只核实其中一项、无需改文档时，怎么留痕？ | 给 `--review-file` 传入本次改动的项目内 JSON，例如 `{"OPS":"已对照安装行为"}`。实测只清除 OPS，校验记录仍待复核。 |
| 只改了一节时会发生什么？ | 两条记录都有 `section` 时，只更新安装一节仍会提示校验章节待复核。经核对无需改动时，为校验章节的 ID 留下具体复核说明。没有登记章节的旧记录继续按文件判断。 |

生成新项目资料也按这种方式先确定读者要答的问题，再补最少的章节和验证证据。[资产生成与验收](../knowledge/asset-generation.md)

## 接入编程规范

把已有规范的路径交给 `$standards-intake`。它会核对当前项目已有规则、ADR、代码和测试，再登记适用条款、来源、范围和例外。正式采纳前可用 `trace` 检查提案。采纳后用涉及的路径跑 `context`，确认功能开发能检索到它。

《AI 代码修改与复盘规范》已用于演示如何提炼交付验收条款。当前是待确认的项目规则提案。[自用提案](records/external-code-review-proposal.md) · [接入步骤](../knowledge/standards-intake.md)

## 校验与发布

- 本地回归用 `python -m unittest discover -s scripts`，覆盖查询、索引、安装、锚点、归档、依赖和复核。
- 正式发布用 `python scripts/build_release.py --ref v0.26`，或传入对应的 Git 提交。ZIP 的 `SOURCE-REVISION` 记录版本及完整提交哈希。脚本从该 Git 快照打包，并在解压副本上检查文档入口、索引、链接和测试。省略 `--ref` 时输出独立的 `-preview.zip`，用于验证工作区改动。
- 在业务仓库运行结构校验后，继续执行项目测试和评审。网页内容和 Java 方法证据由维护者或项目工具核实。跨模块召回率及长期维护成本需要真实任务验证。
- 新安装的 CI 检查知识目录的本地链接与常见标题锚点。PR 使用严格同步，有待复核时检查失败。升级保留已有工作流。要限制合并，在托管仓库的分支规则中设为必需检查。
- 套件自用索引通过 `python scripts/knowledge.py --registry docs/self/registry.json validate --strict` 单独校验。共享 CI 默认检查目标项目的通用索引，本仓库还通过本地全量测试和发布验证复核自用资料。

[工具测试](../../scripts/test_knowledge.py) · [套件 CI](../../.github/workflows/knowledge.yml) · [自用资料入口验收](../../scripts/test_self_knowledge.py)
