# 索引校验故障回放

## INC-KIT-001

在 v0.1 中，向校验器传入含 `"relations": null` 的记录。实测抛出 `TypeError: 'NoneType' object is not iterable`。根因是直接遍历未经类型校验的关系字段。

以下代码保留了触发异常的最小逻辑，可以直接用 Python 重放。

```python
record = {"relations": None}
for relation in record.get("relations", []):
    print(relation)
```

## RULE-KIT-001 · 提案

解析未信任的索引字段时，先校验字段类型再读取或遍历字段。无效字段应返回带记录 ID 和字段名的诊断，让维护者一次看到同一索引中的多个错误。修复沿用原有数据模型和状态，未产生新的架构决策。

回归测试 `test_malformed_fields_report_errors` 验证列表类型的 `kind`、对象类型的 `status`、非字符串证据和空值关系均能被报告。运行 `python -m unittest discover -s scripts` 验证。

后续修改校验器时，以下查询会从代码路径找到规则提案，再沿来源关系找到原始故障。

```sh
python scripts/knowledge.py --registry examples/registry-replay.json context scripts/knowledge.py
```
