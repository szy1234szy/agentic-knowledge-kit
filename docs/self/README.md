# 知识套件自身的项目资料

第一次打开请先读 [从这里开始](../README.md)，用一个实际例子了解套件怎样辅助开发。需要查细节时再打开以下两份常读文档。

- [项目说明与编码导航](project-understanding.md) 讲项目用途、核心流程、技术决策和边界。
- [工程手册](engineering-guide.md) 集中介绍安装、升级、开发、知识同步和发布验证。

## 按任务查知识

智能体从 [自用索引](registry.json) 按 ID、路径和关系定位资料。一份文档可以承载多个记录，检索结果会标明对应章节。开发前用 `context` 查事实与约束，交付前用 `impact` 找待复核的资料。命令从套件根目录运行。

`records/` 保存需要独立追溯的决策、约束、故障和验收记录，可随主文档的链接或索引结果打开。

~~~powershell
python scripts/knowledge.py --registry docs/self/registry.json assets --core
python scripts/knowledge.py --registry docs/self/registry.json context --id GUIDE-KIT-UNDERSTANDING
python scripts/knowledge.py --registry docs/self/registry.json context scripts/knowledge.py --id FEAT-KIT-REVIEW-SCOPE
python scripts/knowledge.py --registry docs/self/registry.json impact scripts/knowledge.py scripts/test_knowledge.py
python scripts/knowledge.py --registry docs/self/registry.json review --all --kind architecture
python scripts/knowledge.py --registry docs/self/registry.json validate --strict
~~~
