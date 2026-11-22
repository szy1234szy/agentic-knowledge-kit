---
name: knowledge-audit
description: 定期或重要版本后审核项目知识的过期、重复、矛盾、失效文件引用和未经证实的记录，保持知识可信、轻量和可发现。
---

# knowledge-audit

## 适用原则
本 Skill 只负责自己的生命周期职责；其他知识类型与审批边界由项目 `AGENTS.md` 和 `docs/knowledge/README.md` 规定。


## 步骤
1. 用 `python scripts/knowledge.py validate --strict` 检查索引、已验证证据、替代链和生效规则的适用路径。路径未命中时，核对文件迁移、生成时机和检出范围。
   用 `python scripts/knowledge.py links` 检查知识目录里的 Markdown 相对链接，迁移其他文档时可传入具体文件。
2. 用 `assets --core` 定位优先核实的资料，用 `assets --review` 查看逾期、待补日期和归档候选。对照 Git、代码、配置和实测结果核实高频记录。Python 以外的证据锚点按对应语言核实。
   用 `python scripts/knowledge.py review` 复核核心资料，用 `review --id ID` 限定记录。根据输出打开变化的证据并逐项核对正文主张。重叠候选先比较用途、受众和维护责任，再决定是否保留、合并或归档。全量正文查重用 `review --all`。
3. 标记 accepted 规则缺少执行检查的风险；建议增加测试或合理记录人工门禁。
4. 优先修订仍被使用的资产。经确认已退出日常维护的低频、过时或重复记录，按 `docs/knowledge/asset-management.md` 检查依赖并归档。保留 ID，修改索引路径并填写 `asset.archive_reason`。有替代资料时先更新当前记录的引用。
5. 输出错误、警告、待人工决策和已验证的精简项。合并重复内容时保留有效 ID，更新索引路径和章节，并复查受影响的链接。

