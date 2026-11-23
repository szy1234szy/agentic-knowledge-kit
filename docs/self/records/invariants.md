# 项目不变量

## 目标项目的知识边界

`INV-KIT-001` 适用于新安装和升级。新安装使用通用索引，目标已有索引、文档和 CI 按升级规则保留。套件自身资料通过自用索引读取。

新安装的边界由 `test_install_keeps_target_index_independent_from_kit` 验证。目标保留已有资料的场景可按 [工程手册](../engineering-guide.md#安装与升级) 在临时项目复跑。修改安装文件清单时同时复核这两个场景。

## 审计保持只读

`INV-KIT-REVIEW-READONLY` 适用于 `review` 和 `review --all`。工具输出证据和重叠候选，原记录和正文的改动由维护者审核后执行。回归 `test_review_all_finds_matching_markdown_in_distinct_files` 核查两种模式的文档内容和记录在执行前后一致。

## 坏文档不影响其余查重结果

`INV-KIT-REVIEW-ISOLATION` 适用于全量正文查重。单份 Markdown 无法读取时按文件警告，其他可读文档继续查重。回归 `test_review_all_continues_after_unreadable_markdown` 核查警告出现一次，并保留其他文档的重复候选。[故障复盘](incident-review-encoding.md)

## 从证据变更找当前使用方

`INV-KIT-IMPACT-EVIDENCE` 适用于按路径做影响分析。直接命中证据后，通过 `verified_by` 引用它的现行资产进入待复核清单。普通关联与历史记录按其各自的规则处理。回归 `test_impact_finds_current_assets_that_use_changed_evidence` 核对命中和排除规则。[功能记录](feature-impact-evidence.md)

[安装回归](../../../scripts/test_install.py) · [知识工具回归](../../../scripts/test_knowledge.py)
