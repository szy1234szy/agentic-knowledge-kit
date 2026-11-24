# 项目工程知识套件使用指南

此指南随套件安装和升级。项目自己的事实和操作手册由仓库继续维护。以下命令在目标项目根目录运行。

## 生成和维护项目资料

在 Coding Agent 中发送「用 `$project-bootstrap` 帮我生成项目资料」。默认复用现有 README 或概览，有证据的缺口才在原位补充。沿同一条主流程检查实现入口、成功与失败结果，以及直接覆盖改动点的测试。要求「只审查」可得到只读建议，要求「只重写某一章节」可限定改动范围。

专题按需点名。例如「分析 Redis 影响登录中的哪些功能，检查它不可用时各功能的行为」。要长期启用某项专题，可以在 `docs/knowledge/generation-preferences.md` 中用「专题」二级标题和「功能或范围｜主题｜简要或深入」条目声明。

## 开发前查资料

~~~powershell
python scripts/knowledge.py context --query "RabbitMQ" --depth 1
~~~

查询同时返回登记名称和现行登记正文的匹配，名称优先。找到候选后，用真实配置、调用路径和测试核对。已知功能 ID 或代码路径时可以直接搜索。

## 改完后复核

~~~powershell
python scripts/knowledge.py impact --base HEAD
python scripts/knowledge.py sync-check --base HEAD --strict
~~~

`HEAD` 适用于改动尚未提交。已经提交时用任务开始时的提交。受影响的不变量和核心资产需要本次逐条复核。删除、归档或降级时，继续使用原 ID 说明原因并提供证据。新装项目的 PR 检查会读取本次变更中的 `docs/knowledge/review.json`，本地运行可用 `--review-file` 指定。示例中的 ID、原因和测试名需换成项目实测结果。

~~~json
{
  "INV-ORDER-001": {
    "reason": "核对重复提交分支和契约测试，确认同一订单只会写入一次",
    "evidence": ["file:tests/test_orders.py#test_duplicate_order"]
  }
}
~~~

旧项目升级会保留现有工作流。需要启用新版 PR 检查时，从本套件的 `.github/workflows/knowledge.yml` 合入同步步骤，并在仓库分支规则中设为必需检查。
