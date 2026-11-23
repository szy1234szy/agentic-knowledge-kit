# INC-KIT-REVIEW-ENCODING 全量查重遇到旧编码文档

## 问题与影响

全量查重以 UTF-8 读取 Markdown。接入旧项目后，输入可能包含其他编码的文档。单份文件读取失败可能中断整轮审计，其他文档的查重结果无法输出。

## 验证与处理

用 v0.11 发布包复现。准备一份含字节 0xFF 的 Markdown 和两份相同的 UTF-8 文档，运行 review --all。旧版返回 2，输出解码错误，重复文档结果丢失。

根因是正文读取的解码错误传播到命令顶层。修复把读取错误限制在单个文件，按路径警告一次并继续查重。当前版本对相同输入返回 0，报告跳过的文件并输出可读文档的重复候选。旧编码文档需要转换为 UTF-8 后再纳入正文查重。

在套件根目录可复跑定向回归。通过时应报告一项测试成功。

~~~powershell
python -m unittest discover -s scripts -p 'test_knowledge.py' -k review_all_continues_after_unreadable_markdown
~~~

相关约束见 [坏文档的隔离边界](invariants.md#坏文档不影响其余查重结果)。完整测试依据见 [实测记录](verification.md)。
