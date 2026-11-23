# 先看这里｜项目工程知识套件

**这个套件帮助 Coding Agent 依据仓库证据生成和维护项目资料。** 开发前可以从资料找到实现、决策和约束，验证改动后再复核受影响的内容。

例如，你要改安装逻辑。开发前先查已有的设计约定，知道升级时需要保留目标项目的索引和配置。改完并跑过安装测试后，可以从测试文件反查《工程手册》的安装、校验两节和对应的不变量，把验证结果补到原位。

## 按你现在要做的事看

| 我现在想…… | 打开这里 |
| --- | --- |
| 快速弄懂这套工具怎么工作 | [项目说明与编码导航](self/project-understanding.md)。先看「关系」的流程图，再看「机制」中改代码用得上的入口。 |
| 拿去管理 AgentOS 或其他项目 | [工程手册 → Skill 使用指南](self/engineering-guide.md#skill-使用指南)。从安装后的一句话建档开始。 |
| 给套件本身改功能或修 Bug | [工程手册 → 开发与知识同步](self/engineering-guide.md#开发与知识同步)。开始前查约束，完成后查受影响的资料。 |
| 让原来的编程规范指导当前项目 | [工程手册 → 接入编程规范](self/engineering-guide.md#接入编程规范)。先筛选适用条款，再由负责人确认。 |
| 看套件下一轮做什么 | [套件迭代待办](self/backlog.md)。查看优先顺序、验收条件和已完成的走查证据。 |

## 一分钟验证它到底能做什么

在**套件自己的目录**运行这两条。它们只读取现有资料，为本项目的实际例子。

~~~powershell
python scripts/knowledge.py --registry docs/self/registry.json context --id FEAT-KIT-IMPACT-EVIDENCE --depth 1
python scripts/knowledge.py --registry docs/self/registry.json impact scripts/test_install.py
~~~

第一条会返回该功能为什么做、要守住的约束和验证证据。第二条会把同一个测试路径追到《工程手册》的「安装与升级」「校验与发布」，并列出安装相关的不变量。这样可以直接看出**哪些内容值得读、改完该回到哪里更新**。

这两个目录的用途：

- [self](self/README.md) 保存套件自己的资料。两份主文档之外的 ADR、故障和验收细节，按需从链接查阅。
- [knowledge](knowledge/README.md) 提供给其他项目安装时使用的模板和知识骨架。目标项目完成建档后，这些位置会保存它自己的项目事实。
- 要维护这个 Git 仓库时，使用 `docs/self/registry.json`。装到其他项目后，使用该项目的 `docs/knowledge/registry.json`。

