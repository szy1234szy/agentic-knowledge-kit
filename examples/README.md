# 假设案例（非真实项目事实）

下面记录展示 `Incident → Invariant → ADR → Rule → Test/Evidence` 的结构和双向追溯，不代表你的实际系统已经发生或实现。

将 `registry-example.json` 内容迁移到自己项目之前，请用真实事故、决策、代码和测试替换所有示例字段。

## 实测案例

- [AgentOS 开发试点](agentos-pilot.md)记录从现有能力定位、约束审查到 Maven 测试和知识同步的全过程。
- [套件索引校验故障回放](registry-validation-replay.md)记录 v0.1 的复现、修复与下一次开发的检索路径。相关记录在独立的 `registry-replay.json` 中。

## v0.3 跨模块回归

订单入口引用一条已被替代的决策。账务模块的新决策用 `supersedes` 关联旧决策，并指向当前账务约束。以同一个订单代码路径为输入、展开深度设为 3，v0.2 找到 0/2 条预期记录，v0.3 找到 2/2 条，旧规则未进入结果。用 `python -m unittest discover -s scripts -k cross_module` 可重复运行当前版本的场景。

这个用例衡量已登记替代链上的检索行为。真实项目跨模块召回率需要用多项任务和独立标注的关键约束评估。

## v0.4 功能计划

[功能计划实例](feature-plans.md)保存本次功能的方案、实测验收项及两个演示提案。用以下命令查看状态、前置关系，以及改动如何影响已登记的计划。

```sh
python scripts/knowledge.py --registry examples/registry-plans.json plans
python scripts/knowledge.py --registry examples/registry-plans.json context --id FEAT-DEMO-RENAME
python scripts/knowledge.py --registry examples/registry-plans.json impact scripts/knowledge.py
```
