# 项目说明与编码导航

想先体验一次查询，打开 [从这里开始](../README.md)。本页讲它如何工作，动手装套件或写功能时可直接查 [工程手册](engineering-guide.md)。

本页随 `v0.24` 源码发布，可用 Git 标签定位源码。正式 ZIP 根目录的 `SOURCE-REVISION` 记录完整提交哈希。普通 ZIP 解压目录可按文件查询，涉及 Git 基线的检查需要仓库历史。

## 问题

假设你刚修了安装逻辑，安装测试也通过了。你需要判断升级说明、限制和验收资料是否要改。套件让这些内容能从测试路径查回，开发者可以对照实际改动复核，并更新原有章节。

## 对象

| 对象 | 职责与状态 |
| --- | --- |
| 目标仓库和安装器 | 保留目标现有资料，按需提供空白索引、模板和可复用 Skill。入口见 [install.py](../../install.py)。 |
| Markdown 记录与 registry.json | Markdown 保存功能、约束、决策和证据详情。索引保存稳定 ID、类型、状态、路径及关联。状态由维护者根据证据更新。 |
| CLI 与 Skill | CLI 查询和校验登记事实，Skill 指导 Agent 按任务搜证、设计、验证和维护文档。入口见 [脚本](../../scripts/knowledge.py) 和 [项目协议](../../AGENTS.md)。 |
| 审阅者与验证证据 | 项目测试、Git 变更及评审支撑验收。维护者判断结论、批准状态变化并决定归档。 |

## 关系

~~~mermaid
flowchart LR
    Task["需求或变更路径"] --> Context["任务上下文"]
    Repo["代码、配置与测试"] --> Context
    Registry["知识索引与记录"] --> Context
    Context --> Design["设计与验收条件"]
    Design --> Build["实现与项目测试"]
    Build --> Diff["影响分析"]
    Diff --> Sync["复核并更新文档与证据"]
    Sync --> Registry
~~~

例如，`scripts/test_install.py` 有变动时，`impact` 会把你带到《工程手册》的「安装与升级」「校验与发布」和安装不变量。工具先找到引用这份测试的证据记录，再沿 `verified_by` 追到使用该证据的资料。[证据反查实测](records/verification-impact.md)

首次建档从目标项目的现有阅读入口找资料，优先原位补缺。开发时可用已登记名称或相关正文定位候选，再沿索引关系和调用链核实。共享 Markdown 的同步检查按登记章节比对，关键资产需要逐条复核依据。

## 机制

| 编码时关心什么 | 技术与决策依据 | 修改与验证入口 |
| --- | --- | --- |
| 安装后为何保持目标项目独立 | 升级复制脚本、Skill 和缺失的模板，已有内容按安装规则保留。自用资料通过显式备用索引选择，取舍见 [ADR-KIT-001](records/adr-001.md)。 | [安装器](../../install.py) · [安装隔离和冲突回归](../../scripts/test_install.py) |
| 从一个路径如何找相关资料 | 脚本匹配记录范围、文档及文件证据，再沿登记关系遍历。context 提供开发前候选，impact 额外提示直接证据的当前使用方。取舍见 [ADR-KIT-002](records/adr-002.md)。 | [CLI 的 context、impact 和 path_matches](../../scripts/knowledge.py) · [检索回归](../../scripts/test_knowledge.py) |
| 为什么测试证据与文档验证要分别检查 | audit 检查路径、证据锚点和计划依赖。严格校验通过后，仍需运行项目业务测试核实行为。 | [校验入口](../../scripts/knowledge.py) · [套件 CI](../../.github/workflows/knowledge.yml) · [校验与发布](engineering-guide.md#校验与发布) |
| 如何把外部编程规范带进本次开发 | 先登记来源、条款和作用范围，已采纳且匹配范围的规则随任务上下文加载，待审规则可按 ID 查阅。 | [接入规范](engineering-guide.md#接入编程规范) · [规则示例](records/external-code-review-proposal.md) |
| 如何从提交判断资料要不要复核 | `impact` 返回可能受影响的知识；`sync-check` 检查本次变更有没有对应更新或复核说明；`review` 可对照上次基线看登记关系和证据变动。 | [同步实现](../../scripts/knowledge.py) · [开发与知识同步](engineering-guide.md#开发与知识同步) |
| 文档越来越多时怎么保持可用 | assets 将优先级和复核时间用于日常整理，review 按登记范围和证据提供线索。归档文件保留 ID 并可以显式回查。 | [资产维护](../knowledge/asset-management.md) · [归档与保护测试](../../scripts/test_knowledge.py) |

## 边界

当前可管理架构、功能、决策、规约、运维、质量和证据资料。可以按 ID、路径和关系查约束与测试，追踪功能计划的前置依赖，按类型复核资料，保留独立归档和历史回查。核心命令和验证方法见 [工程手册](engineering-guide.md)。

- 影响分析按文件匹配。多个测试放在同一文件时，可能提示多条资料。跨模块依赖仍要沿实际调用链核对。
- 名称检索从已登记的 ID、章节或计划标题出发，无结果时补查相关登记正文。关键资产需提交本次逐 ID 的复核理由及证据，评审负责核对主张。
- 证据校验支持 Python 定义和文件行范围。Java 方法及外部网页内容由维护者或项目测试核实。
- 查重能发现去除空白差异后的相同正文。旧编码文档提示后跳过，语义相近的资料仍需复核。
- 本地发行目录通过显式路径查影响。Git 工作区可用历史提交做变更与漂移检查。跨项目效果和长期维护成本仍需真实任务评估。

## 反馈

执行下列命令可以复现安装测试路径的查询。实现改动后，先复核关联资料，再把实测结果写回原有功能、证据或故障记录。维护过程见 [开发与知识同步](engineering-guide.md#开发与知识同步)。

~~~powershell
python scripts/knowledge.py --registry docs/self/registry.json context --id GUIDE-KIT-UNDERSTANDING
python scripts/knowledge.py --registry docs/self/registry.json impact scripts/test_install.py
python scripts/knowledge.py --registry docs/self/registry.json validate --strict
~~~
