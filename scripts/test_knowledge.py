import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from knowledge import (
    ROOT, assets, audit, check, compile_scope, context, git_paths, impact, markdown_links,
    path_matches, plans, registry_changes, review, sync_check,
)

class KnowledgeRegistryTest(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(check([]), ([], []))

    def test_shared_document_sections_are_searchable_and_checked(self):
        """同一文件的独立章节可分别定位，过时和不唯一的标题会报错。"""
        operations = {'id': 'OPS', 'kind': 'operations', 'status': 'implemented',
                      'path': 'guide.md', 'section': '安装与升级'}
        quality = {**operations, 'id': 'QUALITY', 'kind': 'quality', 'section': '质量检查'}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'guide.md').write_text(
                '# 手册\n## 安装与升级 ##\n~~~md\n## 示例标题\n~~~\n## 质量检查\n## 重复\n## 重复\n',
                encoding='utf-8')
            with patch('knowledge.ROOT', root):
                self.assertEqual(audit([operations, quality]), ([], []))
                errors, _ = audit([{**operations, 'section': '示例标题'}, {**quality, 'section': '重复'}])
        self.assertTrue(any('missing Markdown section' in error for error in errors))
        self.assertTrue(any('ambiguous Markdown section' in error for error in errors))
        output = io.StringIO()
        with redirect_stdout(output):
            context([operations, quality], ['guide.md'], [], 0)
        self.assertIn('guide.md (section: 安装与升级)', output.getvalue())
        self.assertIn('guide.md (section: 质量检查)', output.getvalue())
    def test_missing_relation_target(self):
        records=[{'id':'RULE-01','kind':'rule','status':'proposed','path':'AGENTS.md','relations':[{'type':'verified_by','target':'TEST-99'}]}]
        errors,_=check(records)
        self.assertTrue(any('relation' in error for error in errors))
    def test_duplicate(self):
        rec={'id':'INV-01','kind':'invariant','status':'accepted','path':'AGENTS.md'}
        errors,_=check([rec,rec])
        self.assertTrue(any('duplicate' in error for error in errors))
    def test_verified_without_evidence_fails(self):
        """已验证记录需要可追溯的证据引用。"""
        rec={'id':'FEAT-01','kind':'feature','status':'verified','path':'AGENTS.md'}
        errors, warnings = audit([rec])
        self.assertEqual(errors, ['FEAT-01: verified without evidence'])
        self.assertEqual(warnings, [])

    def test_evidence_checks_removed_files_and_python_symbols(self):
        """不同状态的证据失效分别报错和警告，合法的函数或类仍能引用。"""
        evidence = {'id': 'EVID', 'kind': 'evidence', 'status': 'verified',
                    'evidence': ['file:scripts/test_knowledge.py#test_empty',
                                 'file:scripts/test_knowledge.py#KnowledgeRegistryTest',
                                 'file:scripts/test_knowledge.py#removed_test',
                                 'file:scripts/removed_test.py', 'file:AGENTS.md#manual-review']}
        proposal = {**evidence, 'id': 'PROPOSAL', 'status': 'proposed',
                    'evidence': ['file:scripts/removed_test.py']}
        retired = {**proposal, 'id': 'OLD', 'status': 'superseded'}
        errors, warnings = audit([evidence, proposal, retired])
        self.assertEqual(len(errors), 2)
        self.assertTrue(any('missing Python evidence symbol' in error for error in errors))
        self.assertTrue(any('missing evidence file' in error for error in errors))
        self.assertEqual(len(warnings), 1)
        self.assertTrue(warnings[0].startswith('PROPOSAL:'))

    def test_verified_record_can_link_to_verified_evidence(self):
        """允许共享证据，同时拒绝仅靠互链声明已验证。"""
        source = {'id': 'EVID', 'kind': 'evidence', 'status': 'verified', 'evidence': ['file:AGENTS.md']}
        record = {'id': 'INV', 'kind': 'invariant', 'status': 'verified',
                  'relations': [{'type': 'verified_by', 'target': 'EVID'}]}
        self.assertEqual(audit([record, source]), ([], []))
        self.assertEqual(len(audit([record, {**source, 'evidence': []}])[0]), 2)

    def test_strict_verified_plans_require_evidence_and_completed_prerequisites(self):
        """严格模式拒绝占位证据和未验证的间接前置，同时兼容普通校验。"""
        upstream = {'id': 'UP', 'kind': 'feature', 'status': 'implemented'}
        middle = {'id': 'MID', 'kind': 'feature', 'status': 'verified', 'evidence': ['https://example.test/run/12'],
                  'relations': [{'type': 'depends_on', 'target': 'UP'}]}
        feature = {'id': 'PLAN', 'kind': 'feature', 'status': 'verified', 'evidence': ['test TODO'],
                   'plan': {'title': '功能'}, 'relations': [{'type': 'depends_on', 'target': 'MID'}]}
        self.assertEqual(audit([upstream, middle, feature]), ([], []))
        errors, _ = audit([upstream, middle, feature], strict=True)
        self.assertEqual(len(errors), 2)
        self.assertTrue(any('requires a file:' in error for error in errors))
        self.assertTrue(any('UP (implemented)' in error for error in errors))
        upstream.update(status='verified', evidence=['file:AGENTS.md'])
        feature['evidence'] = ['file:AGENTS.md']
        self.assertEqual(audit([upstream, middle, feature], strict=True), ([], []))

    def test_review_reports_linked_evidence_drift_and_overlap(self):
        """从核心记录找到关联证据的变更，只报告相关资料的重叠候选。"""
        current = {'id': 'CORE', 'kind': 'architecture', 'status': 'implemented', 'path': 'AGENTS.md',
                   'scope': ['scripts/**'], 'asset': {'importance': 'core', 'reviewed_commit': 'a' * 40},
                   'relations': [{'type': 'verified_by', 'target': 'EVID'}]}
        peer = {**current, 'id': 'PEER', 'path': 'README.md', 'asset': {}}
        source = {'id': 'EVID', 'kind': 'evidence', 'status': 'verified', 'path': 'README.md',
                  'evidence': ['file:install.py']}
        archive = {**peer, 'id': 'OLD', 'path': 'docs/knowledge/archive/old.md'}
        output = io.StringIO()
        with patch('knowledge.git_paths', return_value=['install.py', 'unrelated.txt']) as git:
            with redirect_stdout(output):
                review([archive, current, peer, source], [])
            git.assert_called_once_with('a' * 40)
        text = output.getvalue()
        self.assertIn('EVID evidence: file:install.py', text)
        self.assertIn(f"changed since {'a' * 40}: install.py", text)
        self.assertIn('CORE, PEER', text)
        self.assertNotIn('OLD', text)
        self.assertNotIn('unrelated.txt', text)

    def test_review_all_finds_matching_markdown_in_distinct_files(self):
        """两种审查模式保持记录和正文不变，全量复核还能查找相同正文。"""
        guide = {'id': 'A', 'kind': 'guide', 'status': 'implemented', 'path': 'a.md',
                 'asset': {'importance': 'core'}}
        second = {**guide, 'id': 'B', 'path': 'b.md', 'asset': {}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {root / 'a.md': b'# Guide\n\nOne step.\n', root / 'b.md': b'# Guide\nOne step.\n'}
            for path, content in files.items():
                path.write_bytes(content)
            records = [guide, second]
            baseline = json.dumps(records, sort_keys=True)
            with patch('knowledge.ROOT', root):
                for all_records in (False, True):
                    output = io.StringIO()
                    with redirect_stdout(output):
                        review(records, [], all_records)
                    self.assertEqual('matching Markdown text: A, B' in output.getvalue(), all_records)
                    self.assertEqual(json.dumps(records, sort_keys=True), baseline)
                    self.assertEqual({path: path.read_bytes() for path in files}, files)

    def test_review_kind_limits_selection_and_document_reads(self):
        """按类型复核普通记录，同时避免读取其他类型的 Markdown。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'ops.md').write_text('# Operations\n', encoding='utf-8')
            (root / 'guide.md').write_bytes(b'guide: \xff')
            records = [
                {'id': 'OPS', 'kind': 'operations', 'status': 'implemented', 'path': 'ops.md'},
                {'id': 'GUIDE', 'kind': 'guide', 'status': 'implemented', 'path': 'guide.md',
                 'asset': {'importance': 'core'}},
            ]
            with patch('knowledge.ROOT', root):
                for all_records in (False, True):
                    output, warnings = io.StringIO(), io.StringIO()
                    with redirect_stdout(output), redirect_stderr(warnings):
                        review(records, [], all_records, kind='operations')
                    self.assertIn('- OPS ', output.getvalue())
                    self.assertNotIn('- GUIDE ', output.getvalue())
                    self.assertEqual(warnings.getvalue(), '')
                with self.assertRaisesRegex(ValueError, 'excluded asset ID: GUIDE'):
                    review(records, ['GUIDE'], kind='operations')

    def test_review_all_continues_after_unreadable_markdown(self):
        """旧编码文件只报告一次，其他可读文档仍能完成查重。"""
        records = [{'id': rid, 'kind': 'guide', 'status': 'implemented', 'path': path}
                   for rid, path in [('OLD', 'old.md'), ('LEGACY', 'old.md'), ('A', 'a.md'), ('B', 'b.md')]]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'old.md').write_bytes(b'legacy: \xff')
            for name in ('a.md', 'b.md'):
                (root / name).write_text('# Same guide\n', encoding='utf-8')
            output, warnings = io.StringIO(), io.StringIO()
            with patch('knowledge.ROOT', root), redirect_stdout(output), redirect_stderr(warnings):
                self.assertEqual(review(records, [], True), 0)
            self.assertEqual(warnings.getvalue().count('old.md: Markdown text review skipped'), 1)
            self.assertIn('matching Markdown text: A, B', output.getvalue())

    def test_evidence_checks_qualified_python_symbol_and_line_range(self):
        """带类名的锚点必须命中对应类，行号范围必须落在文件内。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'test_demo.py').write_text(
                'class Other:\n    def test_case(self):\n        pass\n', encoding='utf-8')
            item = {'id': 'EVID', 'kind': 'evidence', 'status': 'verified',
                    'evidence': ['file:test_demo.py#Other.test_case', 'file:test_demo.py#Wrong.test_case',
                                 'file:test_demo.py#L1-L3', 'file:test_demo.py#L1-L4',
                                 'file:test_demo.py#L3-L1']}
            with patch('knowledge.ROOT', root):
                errors, warnings = audit([item])
            self.assertEqual(warnings, [])
            self.assertEqual(errors, [
                'EVID: missing Python evidence symbol test_demo.py#Wrong.test_case',
                'EVID: evidence line out of range test_demo.py#L1-L4',
                'EVID: evidence line out of range test_demo.py#L3-L1',
            ])

    def test_audit_flags_unmatched_active_scope(self):
        """检查同一记录下的每个 glob，历史和提案允许保留未来路径。"""
        rule = {'id': 'RULE', 'kind': 'rule', 'status': 'accepted',
                'scope': ['scripts/**/*.py', 'gone/**']}
        records = [rule, {**rule, 'id': 'OLD', 'status': 'superseded'},
                   {**rule, 'id': 'DRAFT', 'status': 'proposed'}]
        with patch('knowledge.workspace_files', return_value={'scripts/knowledge.py', 'gone/deleted.py'}):
            diagnostic = 'RULE: scope matches no project files: gone/**'
            self.assertEqual(audit(records), ([], [diagnostic]))
            self.assertEqual(audit(records, strict=True), ([diagnostic], []))

    def test_malformed_fields_report_errors(self):
        """重放 v0.1 畸形索引触发的未捕获异常。"""
        record = {'id': 'BAD-01', 'kind': [], 'status': {},
                  'path': 'AGENTS.md', 'evidence': [1], 'relations': None}
        errors, _ = check([record])
        self.assertEqual(len(errors), 4)
        for field in ('kind', 'status', 'evidence', 'relations'):
            self.assertTrue(any(field in error for error in errors))

    def test_supersedes_cycle(self):
        """检测替代链上的循环引用。"""
        a = {'id': 'ADR-A', 'kind': 'adr', 'status': 'accepted', 'path': 'AGENTS.md',
             'relations': [{'type': 'supersedes', 'target': 'ADR-B'}]}
        b = {**a, 'id': 'ADR-B', 'relations': [{'type': 'supersedes', 'target': 'ADR-A'}]}
        errors, _ = check([a, b])
        self.assertTrue(any('supersedes cycle' in error for error in errors))

    def test_feature_plan_metadata_and_dependencies(self):
        """旧功能记录仍有效，计划元数据和依赖端点需符合约定。"""
        old_feature = {'id': 'BASE', 'kind': 'feature', 'status': 'implemented', 'path': 'AGENTS.md'}
        feature = {**old_feature, 'id': 'NEXT', 'plan': {'title': '下一项功能'},
                   'relations': [{'type': 'depends_on', 'target': 'BASE'}]}
        self.assertEqual(check([old_feature, feature]), ([], []))
        invalid = {**feature, 'plan': {'title': ' ', 'owner': 42}}
        errors, _ = check([{**old_feature, 'kind': 'rule'}, invalid])
        for diagnostic in ('plan.title', 'plan.owner', 'depends_on must connect feature'):
            self.assertTrue(any(diagnostic in error for error in errors))
        errors, _ = check([old_feature, {**feature, 'kind': 'rule'}])
        self.assertTrue(any('plan must be an object on a feature' in error for error in errors))

    def test_feature_dependencies_reject_cycles(self):
        """自依赖和多个功能之间的循环依赖都无法通过校验。"""
        a = {'id': 'A', 'kind': 'feature', 'status': 'proposed', 'path': 'AGENTS.md',
             'relations': [{'type': 'depends_on', 'target': 'B'}]}
        for target in ('A', 'B'):
            with self.subTest(target=target):
                b = {**a, 'id': 'B', 'relations': [{'type': 'depends_on', 'target': target}]}
                errors, _ = check([a, b])
                self.assertTrue(any('depends_on cycle' in error for error in errors))

    def test_plans_filter_and_review_prerequisites(self):
        """列表只展示符合状态的计划，并随前置功能的验证状态更新。"""
        prerequisite = {'id': 'BASE', 'status': 'implemented'}
        target = {'id': 'NEXT', 'status': 'accepted', 'path': 'next.md',
                  'plan': {'title': '接续功能', 'owner': '工程组'},
                  'relations': [{'type': 'depends_on', 'target': 'BASE'}]}
        historical = {**target, 'id': 'OLD', 'status': 'superseded'}
        for status, expected in ((None, 'BASE (implemented)'), ('proposed', 'No feature plans match.'),
                                 ('accepted', 'BASE (implemented)'), ('superseded', '- OLD [')):
            output = io.StringIO()
            with redirect_stdout(output):
                plans([prerequisite, target, historical], status)
            self.assertIn(expected, output.getvalue())
            if status is None:
                self.assertNotIn('- OLD [', output.getvalue())
        output = io.StringIO()
        with redirect_stdout(output):
            plans([{**prerequisite, 'status': 'verified'}, target])
        self.assertIn('- NEXT [accepted]', output.getvalue())
        self.assertNotIn('prerequisite review', output.getvalue())

    def test_impact_recovers_plan_when_related_constraint_changes(self):
        """约束变更可反查引用它的功能计划。"""
        rule = {'id': 'RULE', 'kind': 'rule', 'status': 'accepted',
                'path': 'rule.md', 'scope': ['billing/**']}
        plan = {'id': 'FEAT', 'kind': 'feature', 'status': 'accepted', 'path': 'feature.md',
                'plan': {'title': '订单更新'},
                'relations': [{'type': 'constrained_by', 'target': 'RULE'}]}
        output = io.StringIO()
        with redirect_stdout(output):
            impact([rule, plan], ['billing/ledger.py'])
        self.assertIn('- RULE [rule/accepted]', output.getvalue())
        self.assertIn('- FEAT [feature/accepted] feature.md | linked plans to review via RULE', output.getvalue())

    def test_impact_finds_current_assets_that_use_changed_evidence(self):
        """证据文件变更可反查现行约束，普通关联与历史记录不扩大结果。"""
        evidence = {'id': 'EVID', 'kind': 'evidence', 'status': 'verified', 'path': 'evidence.md',
                    'evidence': ['file:tests/test_contract.py#test_rule']}
        current = {'id': 'RULE', 'kind': 'rule', 'status': 'accepted', 'path': 'rule.md',
                   'relations': [{'type': 'verified_by', 'target': 'EVID'}]}
        records = [evidence, current, {**current, 'id': 'DEPRECATED', 'status': 'deprecated'},
                   {**current, 'id': 'ARCHIVED', 'path': 'docs/knowledge/archive/rule.md'},
                   {**current, 'id': 'RELATED', 'relations': [{'type': 'related_to', 'target': 'EVID'}]}]
        output = io.StringIO()
        with redirect_stdout(output):
            impact(records, ['tests/test_contract.py'])
        result = output.getvalue()
        self.assertIn('- EVID [evidence/verified]', result)
        self.assertIn('- RULE [rule/accepted] rule.md | linked evidence to review via EVID', result)
        for rid in ('DEPRECATED', 'ARCHIVED', 'RELATED'):
            self.assertNotIn(f'- {rid} [', result)

    def test_plans_find_reopened_transitive_prerequisite_once(self):
        """中间功能仍为已验证时，也显示重新进入实施的上游功能。"""
        relation = lambda target: {'type': 'depends_on', 'target': target}
        upstream = {'id': 'ROOT', 'status': 'implemented'}
        left = {'id': 'LEFT', 'status': 'verified', 'relations': [relation('ROOT')]}
        right = {'id': 'RIGHT', 'status': 'verified', 'relations': [relation('ROOT')]}
        plan = {'id': 'NEXT', 'status': 'accepted', 'path': 'next.md', 'plan': {'title': '后续功能'},
                'relations': [relation('LEFT'), relation('RIGHT')]}
        output = io.StringIO()
        with redirect_stdout(output):
            plans([upstream, left, right, plan], 'accepted')
        self.assertEqual(output.getvalue().count('ROOT (implemented)'), 1)
        self.assertNotIn('LEFT (verified)', output.getvalue())

    def test_markdown_links_find_moved_documents_with_source_lines(self):
        """相对链接从文档位置解析，代码示例和远程链接不会触发误报。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'docs').mkdir()
            (root / 'a b.md').write_text('# Heading\n', encoding='utf-8')
            (root / 'docs/guide.md').write_text(
                '[ok](../a%20b.md#heading) [ok](<../a b.md> "title")\n'
                '[moved](missing.md)\n'
                '[ref]: moved.md\n'
                '`[example](bad.md)` [remote](https://example.test/x) [anchor](#section)\n'
                '```md\n[example](absent.md)\n```\n'
                '[outside](../../outside.md)\n## Section\n', encoding='utf-8')
            with patch('knowledge.ROOT', root):
                self.assertEqual(markdown_links(['docs/guide.md']), [
                    'docs/guide.md:2: invalid local link missing.md',
                    'docs/guide.md:3: invalid local link moved.md',
                    'docs/guide.md:8: invalid local link ../../outside.md',
                ])

    def test_markdown_links_detect_removed_headings(self):
        """核对本页、百分号编码和重复标题的 Markdown 链接。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'target.md').write_text('## 校验与发布\n## Retry Rules\n## Retry Rules\n', encoding='utf-8')
            (root / 'source.md').write_text(
                '## Current\n[ok](#current) [missing](#removed)\n'
                '[duplicate](target.md#retry-rules-1) [ok](target.md#%E6%A0%A1%E9%AA%8C%E4%B8%8E%E5%8F%91%E5%B8%83)\n'
                '[missing](target.md#retry-rules-2)\n', encoding='utf-8')
            with patch('knowledge.ROOT', root):
                self.assertEqual(markdown_links(['source.md']), [
                    'source.md:2: missing Markdown anchor #removed',
                    'source.md:4: missing Markdown anchor target.md#retry-rules-2',
                ])

    def test_external_draft_requires_adoption_before_driving_context(self):
        """外来规范须经过采纳和限定范围才能约束现行任务。"""
        rule = {'id': 'EXT', 'kind': 'rule', 'status': 'proposed', 'path': 'AGENTS.md',
                'origin': {'source': 'Team standard', 'revision': '1'}, 'scope': ['scripts/**']}
        feature = {'id': 'FEAT', 'kind': 'feature', 'status': 'accepted', 'path': 'README.md',
                   'scope': ['scripts/**'], 'relations': [{'type': 'constrained_by', 'target': 'EXT'}]}
        self.assertTrue(any('unadopted external rule' in error for error in check([rule, feature])[0]))
        for status, expected in (('proposed', False), ('accepted', True)):
            output = io.StringIO()
            with redirect_stdout(output):
                context([{**rule, 'status': status}], ['scripts/knowledge.py'], [], 1)
            self.assertEqual('external source: Team standard (1)' in output.getvalue(), expected)
        self.assertTrue(any('requires scope' in error for error in check([{**rule, 'status': 'accepted', 'scope': []}])[0]))

    @unittest.skipUnless(shutil.which('git'), 'Git is required for reviewing index and code changes')
    def test_git_registry_diff_and_sync_review(self):
        """基线索引关系变化与本次同步复核说明都能被识别。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            index = root / 'index.json'
            asset = {'id': 'DOC', 'kind': 'feature', 'status': 'implemented', 'path': 'feature.md',
                     'scope': ['app.py'], 'asset': {'importance': 'core'}}
            other = {'id': 'ADR', 'kind': 'adr', 'status': 'accepted', 'path': 'feature.md'}

            def git(*args):
                """运行测试仓库的 Git 命令。"""
                return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE).decode().strip()

            def save(records):
                """保存测试索引。"""
                index.write_text(json.dumps({'schema_version': 1, 'records': records}), encoding='utf-8')

            git('init', '-q')
            save([asset, other])
            (root / 'app.py').write_text('pass\n', encoding='utf-8')
            (root / 'feature.md').write_text('# Feature\n', encoding='utf-8')
            git('add', '.')
            git('-c', 'user.name=Kit Test', '-c', 'user.email=kit@example.test',
                '-c', 'commit.gpgsign=false', 'commit', '-qm', 'initial')
            baseline = git('rev-parse', 'HEAD')
            modified = {**asset, 'asset': {**asset['asset'], 'reviewed_commit': baseline},
                        'relations': [{'type': 'decided_by', 'target': 'ADR'}]}
            changed = [modified, other]
            save(changed)
            with patch('knowledge.ROOT', root), redirect_stdout(io.StringIO()) as output:
                self.assertEqual(registry_changes(changed, index, baseline, git_paths(baseline)), {'DOC': ['relations']})
                review(changed, [], registry=index)
                self.assertIn('registry changed for DOC: relations', output.getvalue())

                save([asset, other])
                (root / 'app.py').write_text('raise RuntimeError\n', encoding='utf-8')
                self.assertEqual(sync_check([asset, other], index, baseline, strict=True), 1)
                reasons = root / 'review.json'
                reasons.write_text('{"DOC":"Public behavior verified by the existing contract test"}', encoding='utf-8')
                self.assertEqual(sync_check([asset, other], index, baseline, 'review.json', strict=True), 0)

    @unittest.skipUnless(shutil.which('git'), 'Git is required for checking Markdown sections')
    def test_sync_check_reviews_shared_markdown_by_section(self):
        """正文和围栏示例按登记章节核对，旧的文件级记录继续有效。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            doc = root / 'guide.md'
            index = root / 'index.json'
            asset = {'kind': 'feature', 'status': 'implemented', 'path': 'guide.md', 'scope': ['app.py']}
            records = [{**asset, 'id': 'FIRST', 'section': 'First'},
                       {**asset, 'id': 'SECOND', 'section': 'Second'},
                       {**asset, 'id': 'WHOLE'}]
            original = '# Guide\n\n## First\n\n~~~sh\n# Second\nold-command\n~~~\n\n## Second\n\nOriginal text\n'

            def git(*args):
                """为同步回归准备实际 Git 基线。"""
                return subprocess.check_output(['git', '-C', str(root), *args],
                                               stderr=subprocess.PIPE, text=True).strip()

            git('init', '-q')
            doc.write_text(original, encoding='utf-8')
            (root / 'app.py').write_text('pass\n', encoding='utf-8')
            index.write_text(json.dumps({'schema_version': 1, 'records': records}), encoding='utf-8')
            git('add', '.')
            git('-c', 'user.name=Kit Test', '-c', 'user.email=kit@example.test',
                '-c', 'commit.gpgsign=false', 'commit', '-qm', 'initial')
            baseline = git('rev-parse', 'HEAD')
            (root / 'app.py').write_text('updated = True\n', encoding='utf-8')
            doc.write_text(original.replace('old-command', 'new-command'), encoding='utf-8')
            with patch('knowledge.ROOT', root), redirect_stdout(io.StringIO()) as output:
                self.assertEqual(sync_check(records, index, baseline, strict=True), 1)
                self.assertIn('- SECOND | review', output.getvalue())
                self.assertNotIn('- FIRST | review', output.getvalue())
                self.assertNotIn('- WHOLE | review', output.getvalue())
                (root / 'review.json').write_text('{"SECOND":"Verified the contract remains valid"}', encoding='utf-8')
                self.assertEqual(sync_check(records, index, baseline, 'review.json', strict=True), 0)
                doc.write_text(original.replace('old-command', 'new-command').replace('Original text', 'New behavior'),
                               encoding='utf-8')
                self.assertEqual(sync_check(records, index, baseline, strict=True), 0)
                doc.write_text(original.replace('## Second', '## Moved'), encoding='utf-8')
                self.assertEqual(sync_check(records, index, baseline, strict=True), 1)

    def test_context_searches_current_names_then_follows_relations(self):
        """按当前名称找到跨模块证据并排除停用记录。"""
        common = {'kind': 'feature', 'status': 'implemented', 'path': 'guide.md'}
        records = [{**common, 'id': 'CAP-INBOX', 'section': 'RabbitMQ inbox',
                    'relations': [{'type': 'verified_by', 'target': 'EVID-CONSUMER'}]},
                   {**common, 'id': 'EVID-CONSUMER', 'kind': 'evidence'},
                   {**common, 'id': 'OLD', 'status': 'deprecated', 'section': 'RabbitMQ previous'}]
        with redirect_stdout(io.StringIO()) as output:
            context(records, [], [], 1, ['rabbitmq'])
        result = output.getvalue()
        self.assertIn('name: rabbitmq', result)
        self.assertIn('EVID-CONSUMER', result)
        self.assertNotIn('- OLD ', result)

    def test_assets_review_protects_core_and_live_references(self):
        """将长期不用的低优先级资料列为候选，继续保护核心和仍需的资料。"""
        low = {'id': 'OLD', 'kind': 'guide', 'status': 'implemented', 'path': 'old.md',
               'asset': {'importance': 'low', 'last_used': '2023-01-01'}}
        required = {**low, 'id': 'REQUIRED'}
        core = {**low, 'id': 'CORE', 'asset': {'importance': 'core'}}
        current = {**low, 'id': 'CURRENT', 'relations': [{'type': 'implements', 'target': 'REQUIRED'}],
                   'asset': {'last_reviewed': '2025-01-01', 'last_used': '2025-01-01'}}
        args = SimpleNamespace(as_of=date(2025, 2, 1), review=True, archived=False, kind=None, core=False,
                               review_days=180, idle_days=365)
        output = io.StringIO()
        with redirect_stdout(output):
            assets([low, required, current, core], args)
        lines = output.getvalue().splitlines()
        self.assertTrue(lines[0].startswith('- CORE '))
        self.assertTrue(any(line.startswith('- OLD ') and 'archive candidate' in line for line in lines))
        self.assertTrue(any(line.startswith('- REQUIRED ') and 'retain:' in line for line in lines))
        self.assertFalse(any(line.startswith('- CURRENT ') for line in lines))

    def test_archive_preserves_history_without_polluting_current_queries(self):
        """默认检索只显示现行记录，显式 ID 仍能找回归档资料。"""
        old = {'id': 'OLD', 'kind': 'adr', 'status': 'superseded', 'path': 'docs/knowledge/archive/old.md',
               'scope': ['src/**'], 'asset': {'archive_reason': '已替代'}}
        current = {'id': 'CURRENT', 'kind': 'feature', 'status': 'accepted', 'path': 'AGENTS.md',
                   'scope': ['src/**'], 'plan': {'title': '当前计划'},
                   'relations': [{'type': 'supersedes', 'target': 'OLD'}]}
        records = [old, current]
        for query in (lambda: context(records, ['src/a.py'], [], 2),
                      lambda: impact(records, ['src/a.py'])):
            output = io.StringIO()
            with redirect_stdout(output):
                query()
            self.assertIn('- CURRENT ', output.getvalue())
            self.assertNotIn('- OLD ', output.getvalue())
        output = io.StringIO()
        with redirect_stdout(output):
            context(records, [], ['OLD'], 1)
        self.assertIn('| archived', output.getvalue())

    def test_archive_requires_reason_and_rejects_live_dependencies(self):
        """归档必须说明理由，并把现行前置关系迁到可用记录。"""
        historical = {'id': 'OLD', 'kind': 'feature', 'status': 'verified',
                      'path': 'docs/knowledge/archive/old.md',
                      'asset': {'archive_reason': '已替代', 'last_used': '2024-02-30'}}
        current = {'id': 'CURRENT', 'kind': 'feature', 'status': 'accepted', 'path': 'AGENTS.md',
                   'relations': [{'type': 'depends_on', 'target': 'OLD'}]}
        with patch('knowledge.existing_file', return_value=True):
            errors, _ = check([historical, current])
            self.assertTrue(any('last_used' in error for error in errors))
            self.assertTrue(any('references archived asset' in error for error in errors))
            errors, _ = check([{**historical, 'asset': {'importance': 'core'}}])
            self.assertTrue(any('archive_reason' in error for error in errors))
            self.assertTrue(any('cannot be marked core' in error for error in errors))

    def test_active_scopes_and_evidence_do_not_rely_on_archive(self):
        """归档路径不会让失效的运行范围通过，归档文件也不能作为当前证据。"""
        record = {'id': 'OPS', 'kind': 'operations', 'status': 'verified', 'path': 'AGENTS.md',
                  'scope': ['docs/**'], 'evidence': ['file:docs/knowledge/archive/example.md']}
        with patch('knowledge.workspace_files', return_value={'docs/knowledge/archive/example.md'}):
            errors, warnings = audit([record], strict=True)
        self.assertEqual(warnings, [])
        self.assertTrue(any('references archived file' in error for error in errors))
        self.assertTrue(any('scope matches no project files' in error for error in errors))

    def test_deleted_knowledge_document_is_visible_to_impact(self):
        """删掉文档会让校验失败，但影响查询仍能沿旧路径找回记录。"""
        deleted = 'docs/knowledge/records/deleted-regression.md'
        with tempfile.TemporaryDirectory() as directory:
            index = Path(directory) / 'registry.json'
            index.write_text(json.dumps({
                'schema_version': 1, 'records': [
                    {'id': 'RULE-DELETED', 'kind': 'rule', 'status': 'accepted', 'path': deleted}
                ],
            }), encoding='utf-8')
            cli = [sys.executable, '-B', str(ROOT / 'scripts/knowledge.py'), '--registry', str(index)]
            invalid = subprocess.run([*cli, 'validate'], capture_output=True, text=True)
            self.assertEqual(invalid.returncode, 1)
            self.assertIn('missing file', invalid.stderr)
            impact_result = subprocess.run([*cli, 'impact', deleted], capture_output=True, text=True)
            self.assertEqual(impact_result.returncode, 0)
            self.assertIn('RULE-DELETED', impact_result.stdout)
            self.assertIn('WARN:', impact_result.stderr)

    def test_root_scope_and_file_evidence(self):
        """验证多级路径、根目录范围和证据文件命中。"""
        matches = compile_scope(r'src\**\*.py')
        for path in ('src/app.py', 'src/core/app.py'):
            self.assertTrue(matches(path))
        self.assertFalse(matches('vendor/src/app.py'))
        self.assertFalse(compile_scope('src/*.py')('src/core/app.py'))
        record = {'id': 'R', 'path': 'docs/r.md', 'evidence': ['file:tests/test_a.py#test_run']}
        self.assertEqual(path_matches([record], ['tests/test_a.py']), {'R': ['tests/test_a.py']})

    def test_context_recovers_indirect_evidence(self):
        """从实现找到规则和第二层证据，且遵守展开层数。"""
        capability = {'id': 'CAP', 'kind': 'capability', 'status': 'implemented',
                      'path': 'cap.md', 'scope': ['src/**']}
        rule = {'id': 'RULE', 'kind': 'rule', 'status': 'accepted', 'path': 'rule.md',
                'relations': [{'type': 'constrained_by', 'target': 'CAP'},
                              {'type': 'verified_by', 'target': 'EVID'}]}
        evidence = {'id': 'EVID', 'kind': 'evidence', 'status': 'implemented', 'path': 'evid.md'}
        for depth, expected in ((1, False), (2, True)):
            output = io.StringIO()
            with redirect_stdout(output):
                context([capability, rule, evidence], ['src/core/app.py'], [], depth)
            self.assertIn('RULE [rule/accepted]', output.getvalue())
            self.assertEqual('EVID [evidence/implemented]' in output.getvalue(), expected)

    def test_cross_module_context_follows_replacement_but_not_old_rule(self):
        """从订单入口跨模块找回当前账务约束，旧决策的规则留给历史查阅。"""
        order = {'id': 'CAP-ORDER', 'kind': 'capability', 'status': 'implemented', 'path': 'order.md',
                 'scope': ['orders/**'], 'relations': [{'type': 'decided_by', 'target': 'ADR-OLD'}]}
        old = {'id': 'ADR-OLD', 'kind': 'adr', 'status': 'superseded', 'path': 'old.md',
               'relations': [{'type': 'related_to', 'target': 'RULE-OLD'}]}
        current = {'id': 'ADR-BILLING', 'kind': 'adr', 'status': 'accepted', 'path': 'billing.md',
                   'relations': [{'type': 'supersedes', 'target': 'ADR-OLD'},
                                 {'type': 'constrained_by', 'target': 'INV-BILLING'}]}
        records = [order, old, current,
                   {'id': 'RULE-OLD', 'kind': 'rule', 'status': 'deprecated', 'path': 'old-rule.md'},
                   {'id': 'INV-BILLING', 'kind': 'invariant', 'status': 'accepted',
                    'path': 'billing-inv.md', 'scope': ['billing/**']}]
        for depth, expected in ((0, set()), (2, {'ADR-BILLING'}), (3, {'ADR-BILLING', 'INV-BILLING'})):
            output = io.StringIO()
            with redirect_stdout(output):
                context(records, ['orders/checkout.py'], [], depth)
            recovered = {rid for rid in ('ADR-BILLING', 'INV-BILLING', 'RULE-OLD')
                         if f'- {rid} [' in output.getvalue()}
            self.assertEqual(recovered, expected)

    @unittest.skipUnless(shutil.which('git'), 'Git is required for the impact integration test')
    def test_git_paths_include_renames_and_untracked_files(self):
        """在临时 Git 仓库验证非 ASCII、空格和重命名路径。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def git(*args):
                """执行测试仓库操作。"""
                subprocess.run(['git', '-C', directory, *args], check=True, capture_output=True)

            git('init', '-q')
            old = root / 'old name.py'
            old.write_text('pass\n', encoding='utf-8')
            git('add', '.')
            git('-c', 'user.name=Kit Test', '-c', 'user.email=kit@example.test',
                '-c', 'commit.gpgsign=false', 'commit', '-qm', 'baseline')
            git('mv', old.name, '新 name.py')
            (root / 'untracked.py').write_text('pass\n', encoding='utf-8')
            with patch('knowledge.ROOT', root):
                self.assertCountEqual(git_paths('HEAD'), [old.name, '新 name.py', 'untracked.py'])


if __name__ == '__main__':
    unittest.main()
