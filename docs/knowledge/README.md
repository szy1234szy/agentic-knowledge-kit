# 项目工程知识地图

## 给这个项目生成资料

用 Coding Agent 打开项目根目录，发送「用 `$project-bootstrap` 帮我生成这个项目的工程资料」。默认先复用已有资料，有缺口时原位完善一份项目说明，保留知识 ID 和有价值的人工内容。只有缺少合适的说明时才填写概览占位。专题可在本次点名，或在项目偏好中启用。用同一组问题验收生成前后的资料，例如「入口在哪」「要守住什么」「怎么验证」。[生成步骤、产出判断与验收标准](asset-generation.md)

开发新功能或修较复杂的 Bug 时，先用 `$task-context` 查实现、约束与验证入口，重要方案再用 `$design-gate` 做评审。验证代码改动后，用 `$knowledge-sync` 核对哪些知识需要同步。

需要让每次建档关注同样的功能或专题时，可以按需创建项目偏好文件。本次明确指定的范围优先。[项目偏好写法](asset-generation.md#保存项目的建档偏好)

## 先从这里开始
- `project/overview.md`：给人读的项目说明，包含用途、主线、模块职责、核心能力和编码入口。
- `registry.json`：可遍历的知识 ID 和引用索引。
- `records/`：Invariant、ADR、Rule、Feature、Incident、Evidence 的独立记录。
- `templates/`：标准模板。
- `views/`：可根据经过核实的记录生成项目介绍和作品集。
- `archive/`：退出日常维护、仍可追溯的历史资料。

了解项目或接手模块时，可用 [项目理解与编码导航模板](templates/project-understanding.md) 追踪一条真实流程，再从关键技术或 ADR 找到修改入口和测试证据。

先检查读者有哪些问题在现有资料里答不上来，再按 [资产生成与验收](asset-generation.md) 决定补正文、补链接或保留原状。

同一受众、同一阅读任务的内容优先写进现有文档的不同章节。独立决策、故障、复杂操作手册或验收证据有各自的用途和维护周期，可以单独保存。智能体从索引获取 ID、范围、关系和证据，按任务读取相应章节。

## 知识类型的职责
- **Feature**：对外行为、输入输出、异常和验收。
- **Invariant**：无论实现如何演进，都必须满足的业务/安全性质，需定义时效和边界。
- **ADR**：候选方案、取舍、结果，保留 superseded 历史。
- **Rule**：具体代码与审查约束，含正反例、作用范围、验证机制。
- **Incident**：事实、时间线、已证实根因与防复发措施，推测不能当事实。
- **Evidence**：代码路径、测试结果、运行记录（无敏感数据）。
- **Architecture**：现有模块关系、数据流、调用链和部署拓扑。[模板](templates/architecture.md)
- **Operations**：部署、配置、排障、迁移和回滚说明。[模板](templates/engineering-reference.md)
- **Quality**：测试与评估方法、质量判据、性能基线和已知限制。[模板](templates/engineering-reference.md)
- **Guide**：开发和维护的操作步骤、适用条件及验证入口。[模板](templates/engineering-reference.md)

## 记录原则
新知识记录先创建 Markdown，再向 `registry.json` 加索引。运行 `python scripts/knowledge.py validate` 验证索引。任务只按影响范围加载知识。`views/` 从登记记录及其证据派生。

## 索引字段与查询

| 字段 | 写法 |
| --- | --- |
| `id` | 稳定且唯一，例如 `RULE-001` |
| `kind`、`status` | 记录类型和当前生命周期状态 |
| `path` | 指向项目内记录文件的相对路径 |
| `section` | 文档内的可选 Markdown 标题，按标题原文填写。同一文件可登记多个 ID，查询时显示各自对应的章节 |
| `origin` | 外来规则的出处。包括必填的 `source`，以及可选的 `revision` 与 `locator`。项目确认采纳后以 `scope` 限定应用范围 |
| `scope` | 可选的根目录相对 glob 列表。用 `src/**/*.py` 覆盖多层目录，`*` 只匹配单段，`**` 可匹配零至多段。匹配区分大小写 |
| `evidence` | 证据引用列表。支持校验 Python 定义锚点，例如 `file:tests/test_example.py#ExampleTest.test_name`，以及文件行号或范围，例如 `file:docs/cases.md#L8-L12`。行号校验覆盖范围是否存在，行内内容和其他语言的符号仍需复核 |
| `relations` | 可选的 `{"type": "verified_by", "target": "EVID-001"}` 列表。查询支持正向和反向查看。功能之间可使用 `depends_on` |
| `plan` | Feature 可选的计划元数据，包含必填的 `title` 和可选的 `owner` |
| `asset` | 可选的维护信息。用 `importance` 标注 `core`、`standard` 或 `low`，用 `last_reviewed` 和 `last_used` 记录日期，格式为 `YYYY-MM-DD`。用 `reviewed_commit` 保存最近核实的 Git 提交哈希。归档时填写 `archive_reason` |

团队规范、旧项目经验或个人复盘手册按 [外部规范接入](standards-intake.md) 处理。先在当前项目核对规则的适用条件，再登记来源和采纳状态。

把已经定位的代码路径或已知 ID 传给 `context`。用输出的来源、状态及证据核实适用性，提案和历史记录可用于追溯背景。根目录下任意位置的目录可写成 `**/auth/**`，单个根目录下路径可直接写成 `src/auth/**`。

只有功能名或依赖名时，先用 `context --query "登记名称" --depth 1` 找已登记的 ID、标题或章节，再沿真实配置和调用路径核实。共享文档里的记录有 `section` 时，同步检查按各章节分别判断。

`verified` 记录需提供自身证据，或用 `verified_by` 引用带证据的已验证证据记录。严格校验要求其中至少有一个 `file:` 或 HTTP(S) 引用，并核对已验收功能计划的前置是否全部已验证。测试是否实际通过要对照运行结果。`validate --strict` 也会拦截已生效规则或不变量无法匹配项目文件的已声明范围。

## 从功能计划到验收

在功能记录里保存目标、范围、设计取舍和验收条件。新增的功能可从 [功能计划模板](templates/feature-plan.md) 开始，也可以在已有 Feature 记录上补充计划。用 `constrained_by` 指向约束、`decided_by` 指向决策、`depends_on` 指向前置功能。完成验证后补上证据引用和实测结果。

已交付功能可用 [功能现状模板](templates/feature-reference.md) 记录输入、处理、输出、状态转换和异常边界。已有功能计划时，优先在同一条 Feature 记录保留现状、后续计划和验收证据的链接。

计划沿用现有状态。待评审用 `proposed`，方案确认用 `accepted`，已实现待验收用 `implemented`，有验收证据后用 `verified`。状态由维护者根据实际结果更新。运行 `python scripts/knowledge.py plans --status proposed` 查看提案。列表会标记尚未验证的直接和间接前置功能，依赖环由校验拦截。历史计划可按具体状态查询。

## 资产维护

核心资产、复核周期和归档操作见 [工程资产维护与归档](asset-management.md)。
