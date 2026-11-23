# Project Knowledge Protocol

## 第一原则
任何非平凡代码修改，**先根据项目事实识别现有能力、模块归属、契约、不变量、已接受 ADR 与适用工程规则**，然后才设计/实现。不得用假设代替对代码、配置和测试的核实。

## 入口
- 项目知识地图：`docs/knowledge/README.md`
- 机器索引：`docs/knowledge/registry.json`
- 任务上下文模板：`docs/knowledge/templates/context-package.md`
- 功能计划模板：`docs/knowledge/templates/feature-plan.md`
- 技能目录：`.agents/skills/`
- 若在套件源码仓库开发套件本身，从 `docs/README.md` 进入，运行知识命令时显式指定 `--registry docs/self/registry.json`。上面的通用索引随安装器交给目标项目使用。

## 阶段协议
0. 首次建档、项目资料缺失或大版本后需要梳理资料时，使用 `project-bootstrap`。没有指定模式时按增量优化处理，先检查已有资料，再依据证据补齐缺口。
1. 开发前：使用 `task-context`；无法识别关键安全或一致性约束时，不得自作主张实施高风险变更。
2. 设计前：使用 `design-gate` 比对不变量、架构依赖和 ADR。需要跨阶段追踪的功能，用已有功能记录或功能计划模板保存范围、取舍与验收条件。设计与原有决策冲突时提出新决策，不直接覆盖旧记录。
3. 开发中：小步修改、尽可能自动测试，不为了过 CI 而删除或弱化测试。
4. 合并前：使用 `knowledge-sync` 检查影响；提交代码、测试、必要文档在同一 PR。知识变更由有权人员确认。
5. 故障后：使用 `incident-learning` 将证据与推测分离；需经核实、批准才能升级为强制规则。
6. 阶段性：使用 `knowledge-audit` 清理错误、失效、冲突和重复知识。
7. 项目交接或介绍时：使用 `project-view`，并为关键主张提供证据链接。
8. 要采用仓库外的编程规范时，使用 `standards-intake` 核对来源、现行约束和适用范围，经确认后纳入开发检索。

## 强制约束
- `AGENTS.md` 与 Skill 仅提供 Agent 行为指导，**不是强制安全边界**；安全和关键业务约束需要代码机制、测试、CI/审查兜底。
- **事实 As-Is / 目标 To-Be / 验证 Evidence 必须分开。** 不得将 proposal 写成已实现，不能声称未经执行的测试已通过。
- 只读取当前任务相关文档，按索引逐层加载；不向上下文灌入所有资料。
- 如果项目文档与真实代码冲突，标记冲突并核实，不得不经审批修改高风险代码或项目不变量。
- 重要设计决策保留历史，使用 supersedes 关系，不删旧 ADR。

## 完成报告
列出：关联项目事实、适用 Invariants / ADR / Rules、代码变更、实测证据、知识新增/修订/弃用、尚未确认事项。
