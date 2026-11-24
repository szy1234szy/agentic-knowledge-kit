# Project-Grounded Agentic Engineering Kit (PGAE Kit)

**v0.25** 面向现有代码库，提供工程资产生成与管理、开发前知识检索、功能计划、变更同步、外部规范接入和故障学习。工具需要 Python 3.11 及以上版本。按 Git 基线检查影响或复核证据时还需要 Git。

第一次拿去用，打开 [工程手册中的 Skill 使用指南](docs/self/engineering-guide.md#skill-使用指南)。里面有给老项目建档的可复制指令、各阶段的调用时机和交付检查。想先看本套件的实际案例，打开 [从这里开始](docs/README.md)。

建档时从一项真实读者任务出发，先写验收问题，再追代码与测试证据，最后决定补章节、补链接或保留原状。[项目资产的生成与验收](docs/knowledge/asset-generation.md)

向 `$project-bootstrap` 指定「只审查」「增量优化」或「指定重写」。默认原位增量优化，保留既有知识 ID 和有价值的人工内容。

需要长期关注特定功能或专题时，可以为目标仓库保存 [建档偏好](docs/knowledge/asset-generation.md#保存项目的建档偏好)。本次明确指令优先，未设置偏好时沿用最小建档。

## 快速开始

1. 在本套件目录运行 `python install.py /path/to/your-repo`。安装保留目标的已有文件。若目标已有 `AGENTS.md`，将本套件的知识入口和开发协议按需合入原文件。
2. 在项目根目录运行 `python scripts/knowledge.py validate`。
3. 用 Coding Agent 打开目标项目，发送「用 `$project-bootstrap` 帮我生成这个项目的工程资料」。默认复用可信资料，有缺口时只完善一份项目说明。专题可在本次点名，或由项目偏好启用。
4. 每次非简单开发，先运行 `$task-context`，再运行 `$design-gate`。
5. 实施并验证代码后运行 `$knowledge-sync`。
6. 故障或重复错误运行 `$incident-learning`；阶段性运行 `$knowledge-audit`。
7. 面试/介绍时使用 `$project-view`，严禁将计划、未验证的能力说成事实。

从旧版本迁移时，在本套件目录执行 `python install.py /path/to/your-repo --upgrade`。此模式更新同名脚本、Skill 和套件操作指南，并补齐缺失模板。安装输出的 `Usage guide` 指向目标项目内的新版指南。目标的知识索引、已有项目文档、`AGENTS.md` 和 CI 配置保持原样。[套件操作指南](.agents/skills/project-bootstrap/references/kit-usage.md)

安装或升级前可追加 `--dry-run` 查看拟复制文件和目标目录冲突。安装器会在写入前检查整批目标，复制时逐文件替换，并跳过内容相同的文件。

## 了解项目及编码入口

用 `$project-view` 从一次真实任务出发，按「问题 → 对象 → 关系 → 机制 → 边界 → 反馈」说明项目。结合 [项目理解模板](docs/knowledge/templates/project-understanding.md) 找到关键技术、当前决策、实现入口及验证方法。套件自身已有一份可查询的 [项目理解与编码导航](docs/self/project-understanding.md)。

项目说明和工程手册面向阅读任务组织。需要驱动开发时，智能体通过索引中的 ID、范围、关系和证据按任务定位。多个记录可共用同一份 Markdown，并用 `section` 指向各自的标题。

从 v0.10 升级后，已有 `validate --strict` 的 CI 会检查已验证记录的证据格式，以及已验收功能计划的前置状态。若旧记录只有文字摘要，请补上文件或运行记录链接。前置功能未通过验收时按实际情况调整计划状态。

## 开发时怎么用

```sh
# 定位代码入口后，按路径检索并沿双向关系查找约束和证据
python scripts/knowledge.py context src/orders/service.py --id CAP-ORDER-001

# 查看某条记录的直接关联
python scripts/knowledge.py trace RULE-ORDER-001

# 验证完成后，用任务开始时的提交检查变更影响
python scripts/knowledge.py impact --base HEAD

# 工作区混有其他任务时，指定本次变更路径
python scripts/knowledge.py impact src/orders/service.py tests/test_orders.py
```

`context` 接受路径、重复的 `--id` 和 `--query`。手上只有模块或业务名称时，可用 `context --query "RabbitMQ" --depth 1`。结果先列现行记录的 ID、章节或计划标题命中，再补充其他已登记正文的命中。默认展开两层，可用 `--depth` 调整。检索遇到历史记录时会沿 `supersedes` 的反向关系找到替代它的决策。`impact --base` 比较指定提交与当前工作区的净变化，并纳入未忽略的未跟踪文件。`HEAD` 适用于改动尚未提交时，已经提交的任务应传开始时的提交。候选结果需继续用实际调用链、契约和测试核实。

知识文档删除或迁移后，查询仍会显示旧路径和相关记录，并把缺失文件列为警告。修复索引后运行 `validate`，完整性校验会拒绝仍指向缺失文件的记录。

被改动的文件命中独立证据记录时，`impact` 还会标出通过 `verified_by` 使用它的现行资料。提示按文件匹配，复核时打开本次 Git Diff 确认具体哪条测试或实现发生变化。

## 审计与 CI

`validate` 检查已验证记录的证据引用，缺失文件、缺少证据、Python 定义锚点失效或行号越界会返回非零退出码。对于已生效的规则、不变量、架构、运维、质量和指南记录，声明的范围未命中任何现行文件时会告警。`validate --strict` 将该告警纳入 CI 门禁。范围检查以 Git 可见文件为准，无 Git 时读取本地项目文件。

严格模式还要求已验证记录可追溯到 `file:` 引用或 HTTP(S) 记录，也可以沿 `verified_by` 找到这种证据。已验收的功能计划要求直接和间接前置均已验证。HTTP(S) 只检查格式，实际运行结果继续由测试及评审确认。

运行 `python scripts/knowledge.py links` 检查知识目录中常见的 Markdown 相对链接、引用式定义与标题锚点。也可指定文件，例如 `links README.md docs/knowledge/README.md`。错误会标明来源文件和行号。网页、Obsidian 专用链接和自定义渲染器生成的锚点由相应工具复核。

`sync-check --base <开始提交>` 提示受影响的资料。普通记录按登记章节或文件检查。受影响的现行不变量和核心资产都要求本次逐 ID 更新的 `reason` 和 `evidence`。删除、归档或降级时仍按基线中的原 ID 提供复核。新安装的 PR 工作流使用 `--strict`，读取本次修改的 `docs/knowledge/review.json`；升级保留已有工作流。[复核格式与实例](.agents/skills/project-bootstrap/references/kit-usage.md#改完后复核)

运行以下命令可直接体验示例索引，或阅读 [试点与故障回放](examples/README.md)。

```sh
python scripts/knowledge.py --registry examples/registry-example.json context --id RULE-DEMO-001
```

测试、CI 和负责人的评审负责执行门禁。`AGENTS.md` 指引 Agent 的工作顺序，查询工具检查已登记的结构与引用。

## 管理工程资产规模

```sh
python scripts/knowledge.py assets --core
python scripts/knowledge.py assets --kind operations
python scripts/knowledge.py assets --review
python scripts/knowledge.py assets --archived
python scripts/knowledge.py review
python scripts/knowledge.py review --id ARC-EXECUTION
python scripts/knowledge.py review --kind operations
python scripts/knowledge.py review --all
```

给高频或关键的资产标记 `asset.importance: core`，日常检索时优先关注。基于人工记录的核实和使用时间，定期筛出待复核与归档候选。确认后在 Git 中把资料移到 `docs/knowledge/archive/` 并保留索引 ID。常规任务检索、影响查询、计划列表和链接检查会省略归档资料。仍被现行记录作为决策、约束、验收证据或前置依赖使用的资料，需先迁移引用。[资产维护与归档步骤](docs/knowledge/asset-management.md)

`review` 默认复核核心资料。若登记了 `asset.reviewed_commit`，会显示自该提交以来变动的登记路径、文档和证据。如果索引文件在仓库内，还会按 ID 比较状态、证据、范围、来源和关系。全量复核可提示同类资产的相同 Markdown 正文。由维护者查看原文、核对主张并决定是否合并。

`review --kind operations` 只复核现行运维记录，可与 `--all` 联用做正文查重。全量正文查重遇到无法读取的文件时会报告路径并继续。知识套件也用本工具管理自身的功能计划、故障和验证结果。[套件自用项目资料](docs/self/README.md)

## 接入原有编程规范

将团队规范或旧项目守则交给 `$standards-intake`。它会结合当前项目提炼可执行条款，登记原资料、项目内适用范围、例外和验证方法。提案可以显式查阅。负责人确认后，采纳的规则才会按路径进入日常开发上下文。[外部规范接入说明](docs/knowledge/standards-intake.md)

## 规划与跟踪功能

用 [功能计划模板](docs/knowledge/templates/feature-plan.md) 记录目标、范围、设计取舍、验收条件及交付结果。在索引的 Feature 记录里补充 `plan.title`，可以另外登记 `plan.owner`。用 `depends_on` 关联前置功能，沿用现有状态追踪待评审、已接受、已实现和已验证。计划可以从约束、决策和变更路径反查。

```sh
python scripts/knowledge.py plans
python scripts/knowledge.py plans --status proposed
python scripts/knowledge.py context --id FEAT-ORDER-001
```

`plans` 会提示尚未验证的直接和间接前置，包括中间功能已验收后重新打开的上游依赖。`impact` 会额外列出与直接命中记录相连的非历史计划，供维护者复核。校验检查依赖目标和循环。优先级、排期、工时及外部任务状态由团队现有工具维护。[功能计划示例](examples/feature-plans.md)

## 最小数据模型

`docs/knowledge/registry.json` 是**索引**，不是业务真相；源代码、配置、测试及实际行为仍是现状证据。记录以 Markdown 保存，支持 ID、状态、依赖关系、证据和适用范围。

关系可选：`constrained_by`, `implements`, `motivated_by`, `decided_by`, `enforced_by`, `verified_by`, `supersedes`, `related_to`, `depends_on`。

Status: `proposed`, `accepted`, `implemented`, `verified`, `superseded`, `deprecated`, `unknown`。在未核实当前代码时不要写 verified。

## 推荐运行关口

`Feature Request → Context Package → Design Gate → Code/Test → Knowledge Diff → Review/CI → Merge`。
事故则是 `Evidence → RCA → Invariant → ADR(如有取舍) → Rule/Pattern → Test → Replay`。

## 设计来源

思想参考 Compound Engineering 的知识沉淀/刷新、OpenSpec 的增量规格与归档、BMAD 的证据核实式项目上下文、Agent Skills 的渐进式披露；本仓库为独立原创的最小集成示例，非上述项目的官方实现。

## 工程实施限制

- 不提供持续后台运行、自动观察所有代码修改或自动发布。
- 不会自动保证适用规则百分之百检索成功：关键约束需要强制的测试/PR 关口。
- 公司项目必须遵守内部保密及外部模型数据使用政策。
- 当前验证覆盖 AgentOS 单模块开发试点、套件故障回放和跨模块决策替代链的回归场景。真实跨模块任务的总体召回率和 Agent 在多次开发中的错误率仍待评估。

[v0.5–v0.9 版本记录](docs/self/records/releases-v0.5-v0.9.md)
