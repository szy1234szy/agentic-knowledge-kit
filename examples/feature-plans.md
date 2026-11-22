# 功能计划实例

## FEAT-KIT-PLAN 功能计划与追溯

### 需求与范围

让开发者能保存一项功能的技术方案和验收结果，并查询当前状态、前置功能和受变更影响的计划。本次覆盖仓库内的技术计划、状态与依赖可见性。排期、工时和外部任务系统集成留给后续需求。

### 项目事实与方案

现有 Feature 记录已有 ID、状态、路径和知识关系。为需要规划的 Feature 增加可选 `plan` 元数据，方案、实施顺序和验收详情仍保存在 Markdown。以 `depends_on` 关联前置功能，复用索引校验与双向查询。

### 验收与证据

| 验收项 | 实测 |
| --- | --- |
| AC-01 可按状态查看功能计划并发现未验证前置 | `test_plans_filter_and_review_prerequisites` 通过 |
| AC-02 依赖自环或互环校验失败 | `test_feature_dependencies_reject_cycles` 通过 |
| AC-03 约束改动能找到关联的功能计划 | `test_impact_recovers_plan_when_related_constraint_changes` 通过 |

实现见 [查询与校验脚本](../scripts/knowledge.py) 和 [计划模板](../docs/knowledge/templates/feature-plan.md)。在完成上述验收后将索引状态设为 `verified`。

## FEAT-DEMO-LINKS 检查工程文档链接

演示提案。目标是输出失效的仓库内 Markdown 链接及其来源文件。前置功能 `FEAT-KIT-PLAN` 已验证。验收方法待定义。

## FEAT-DEMO-RENAME 文档重命名影响清单

演示提案。目标是从原文档路径列出可能需要更新的引用。前置功能 `FEAT-DEMO-LINKS` 尚待验证。
