---
name: incident-learning
description: 重大线上故障、重复错误或明确的工程失误经调查后，将已证实根因转化为不变量、ADR（如有重要取舍）、场景规则、回归测试和后续任务可检索知识。
---

# incident-learning

## 适用原则
本 Skill 只负责自己的生命周期职责；其他知识类型与审批边界由项目 `AGENTS.md` 和 `docs/knowledge/README.md` 规定。


## 学习闭环
1. 创建 Incident 记录：时间线、影响、日志/trace、代码证据，区分事实与猜测。
2. 确认根因或保留 unknown；未确认不能生成强制规则。
3. 识别未满足、缺失或描述不清的 Invariant（包括生效时效/边界）。
4. 若是设计取舍变更提出 ADR；若只是未执行旧规范，优先改测试与执行约束，不新增冗余 ADR。
5. 提取适用范围明确的 Rule / Pattern，写正确/错误示例和例外，并引用 Incident/ADR/Invariant。
6. 提出可运行的 Test、ArchUnit、静态扫描或 CI 检查；纯提示词检查不是硬保证。
7. 用相同失败场景重放验证，并在下一次类似任务检验规则能否被找到且起作用。
8. 送审并运行 `knowledge-sync` 登记；禁止自动批准新强制规则。

