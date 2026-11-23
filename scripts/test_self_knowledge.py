import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'docs/self/registry.json'


class SelfKnowledgeTest(unittest.TestCase):
    """以套件自身资料验证实际入口能找到对应知识。"""

    def cli(self, *args):
        """从源码目录使用正式命令和自用索引。"""
        result = subprocess.run(
            [sys.executable, '-B', 'scripts/knowledge.py', '--registry', str(INDEX), *args],
            cwd=ROOT, capture_output=True, encoding='utf-8', env={**os.environ, 'PYTHONUTF8': '1'},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_self_index_and_core_workflows(self):
        """核心入口可以查回对应的架构、操作、开发或质量说明。"""
        self.assertIn('0 error(s)', self.cli('validate', '--strict'))
        for path, expected in (
            ('install.py', 'OPS-KIT-001'),
            ('scripts/knowledge.py', 'ARC-KIT-001'),
            ('.agents/skills/knowledge-sync/SKILL.md', 'GUIDE-KIT-001'),
            ('.agents/skills/standards-intake/SKILL.md', 'GUIDE-KIT-STANDARDS'),
            ('.github/workflows/knowledge.yml', 'QUALITY-KIT-001'),
            ('scripts/build_release.py', 'QUALITY-KIT-001'),
        ):
            with self.subTest(path=path):
                self.assertIn(f'- {expected} [', self.cli('context', path, '--depth', '0'))

    def test_install_test_impact_finds_current_consumers(self):
        """安装回归变动影响使用其证据的约束，审计计划保持独立。"""
        output = self.cli('impact', 'scripts/test_install.py')
        self.assertIn('- OPS-KIT-001 [', output)
        self.assertIn('- INV-KIT-001 [', output)
        self.assertIn('engineering-guide.md (section: 安装与升级)', output)
        self.assertIn('engineering-guide.md (section: 校验与发布)', output)
        self.assertNotIn('- FEAT-KIT-REVIEW-SCOPE [', output)
        self.assertNotIn('- INC-KIT-REVIEW-ENCODING [', output)

    def test_project_understanding_leads_to_decisions_and_constraints(self):
        """从项目理解入口可回到安装、检索决策和实际约束。"""
        output = self.cli('context', '--id', 'GUIDE-KIT-UNDERSTANDING', '--depth', '1')
        for rid in ('ARC-KIT-001', 'ADR-KIT-001', 'ADR-KIT-002', 'INV-KIT-001', 'QUALITY-KIT-001'):
            with self.subTest(record=rid):
                self.assertIn(f'- {rid} [', output)
