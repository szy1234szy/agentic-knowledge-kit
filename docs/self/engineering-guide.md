# 工程手册

**安装、开发和发布都从这里查。** 首次接手先读 [项目说明与编码导航](project-understanding.md)，有具体任务时按下面的章节跳转。

- [安装与升级](#安装与升级)
- [开发与知识同步](#开发与知识同步)
- [接入编程规范](#接入编程规范)
- [校验与发布](#校验与发布)

## 安装与升级

在解压后的套件目录运行。目标是已有项目目录，示例路径可替换。

~~~powershell
python install.py 'D:\project\your-repo' --dry-run
python install.py 'D:\project\your-repo'
~~~

默认安装保留同名文件，先检查整批目标，再逐文件复制。旧版用户在同一命令后加 `--upgrade`，可升级脚本和 Skill 并补齐缺失模板。原有项目知识、配置和 CI 由目标仓库继续维护。建议把安装改动放在独立 Git 提交，方便审阅和回退。

从目标项目根目录运行 `python scripts/knowledge.py validate --strict`，确认知识索引可用，再跑该项目的业务测试。[安装脚本](../../install.py) · [安装测试](../../scripts/test_install.py) · [安装边界决策](records/adr-001.md)

## 开发与知识同步

1. 开发前用 `context` 从代码路径或功能 ID 找到相关资料，核对当前实现、决策和约束。
2. 写清需求范围、设计和验收条件；验证后记录实际结果。
3. 开发后用 `impact` 从本次变更路径找待复核的知识。有 Git 基线时可用 `--base`。
4. 更新真正改变的事实和证据，在同一 PR 里审阅代码、测试和文档。
5. 定期用 `assets --review` 或 `review` 检查过时资料。确认替代证据和引用后再归档。

套件自身使用 `--registry docs/self/registry.json`。其他目标项目使用已安装的项目索引。[证据反查开发计划](records/feature-impact-evidence.md) · [资产维护说明](../knowledge/asset-management.md)

可以把这条指令直接给已打开目标仓库的 Codex：

> 用项目知识套件处理这项改动。先找出已有实现和必须遵守的约束，列出验收办法。完成实现并跑测试后，按变更路径反查受影响的知识，更新对应章节并写入实际测试结果。

有 Git 基线时可在 PR 中运行 `sync-check --base <开始提交>`。如经确认只调整内部实现，可提交本次修改的复核说明，从 JSON 记录 ID 和具体复核理由，再用 `--review-file` 供检查读取。该检查用于发现遗漏候选，事实是否准确由评审和实际测试确认。

## 接入编程规范

把已有规范的路径交给 `$standards-intake`。它会核对当前项目已有规则、ADR、代码和测试，再登记适用条款、来源、范围和例外。正式采纳前可用 `trace` 检查提案。采纳后用涉及的路径跑 `context`，确认功能开发能检索到它。

《AI 代码修改与复盘规范》已用于演示如何提炼交付验收条款。当前是待确认的项目规则提案。[自用提案](records/external-code-review-proposal.md) · [接入步骤](../knowledge/standards-intake.md)

## 校验与发布

- 本地回归用 `python -m unittest discover -s scripts`，覆盖查询、索引、安装、锚点、归档、依赖和复核。
- 发布时运行 `python scripts/build_release.py`。脚本从当前工作区打包，检查文档入口，并在解压副本上校验索引、链接和测试。升级后保留目标仓库原有知识和 CI。
- 在业务仓库运行结构校验后，继续执行项目测试和评审。网页内容和 Java 方法证据由维护者或项目工具核实。跨模块召回率及长期维护成本需要真实任务验证。
- 新安装的 CI 检查知识目录的本地链接与常见标题锚点，在 PR 中提示需要复核的知识。升级后的仓库可将检查接入现有工作流。

[工具测试](../../scripts/test_knowledge.py) · [套件 CI](../../.github/workflows/knowledge.yml) · [自用资料入口验收](../../scripts/test_self_knowledge.py)
