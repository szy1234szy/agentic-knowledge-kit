# AgentOS 开发试点

基线为 AgentOS Runtime 提交 `bb1dfed`。试点在隔离副本中进行。选用的需求是按工具名称查询调用契约，供调用方读取已声明的工具元数据。

## 开发前检索

以 `agentos-execution/src/main/java/io/agentos/execution/tool/ToolRegistry.java` 为入口运行 `context`。检索从能力 `CAP-TOOL-001` 到契约约束 `INV-TOOL-001`，再到测试证据 `EVID-TOOL-001`。

| 记录 | 代码或测试中的依据 |
| --- | --- |
| `CAP-TOOL-001` | `ToolRegistry.find` 已能按名称查询，`InMemoryToolRegistry` 提供具体实现 |
| `INV-TOOL-001` | `ToolCallContract.from` 已能转换定义，构造时复制 schema 并检查正数超时与尝试次数 |
| `EVID-TOOL-001` | `ToolContractTest` 覆盖契约字段及未声明参数检查 |

## 设计与实现

在 `ToolRegistry` 增加默认方法 `findContract(String name)`，沿用 `find(name).map(AgentTool::definition).map(ToolCallContract::from)`。已知名称返回现有不可变契约，未知名称返回 `Optional.empty()`。方法只读取定义，执行策略继续走原有调用链。本次是兼容的接口增量，未产生新 ADR。

新增的 `looksUpAnExistingContractByName` 用例覆盖已知与未知名称。使用 Maven 3.9.12 运行以下离线命令，实测 3 项通过。

```sh
mvn -o -q -pl agentos-execution -am -Dtest=ToolContractTest -Dsurefire.failIfNoSpecifiedTests=false test
```

## 知识同步

`impact --base HEAD` 从接口变更定位到 `CAP-TOOL-001`，从测试变更反查到 `EVID-TOOL-001`。更新能力目录、能力记录和测试证据，复核现有不变量。更新后 3 条索引通过校验，再次运行 `context` 能找到新增测试方法。

本次验证覆盖一个模块的功能流程。AgentOS 原工作区保留试点前的状态，试点改动留在隔离副本。检索结果与设计遵循情况基于本次任务，尚无多轮独立对照的错误率数据。
