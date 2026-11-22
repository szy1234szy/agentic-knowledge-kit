import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

INSTALLER = Path(__file__).resolve().parents[1] / 'install.py'


class InstallerTest(unittest.TestCase):
    """以空目录验证安装冲突预检和无写入预览。"""

    def install(self, target, *options):
        """调用安装器正常入口。"""
        return subprocess.run([sys.executable, str(INSTALLER), str(target), *options],
                              capture_output=True, text=True)

    def test_conflict_does_not_leave_partially_installed_tools(self):
        """后置目录冲突会在复制脚本之前报出。"""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / 'docs').write_text('existing file', encoding='utf-8')
            result = self.install(target)
            self.assertEqual(result.returncode, 2)
            self.assertIn('expected a directory: docs', result.stderr)
            self.assertFalse((target / 'scripts').exists())
            self.assertEqual((target / 'docs').read_text(encoding='utf-8'), 'existing file')

    def test_dry_run_and_identical_upgrade(self):
        """预览不写文件，重复升级跳过同内容的文件。"""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            preview = self.install(target, '--dry-run')
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertIn('WOULD COPY', preview.stdout)
            self.assertFalse(list(target.iterdir()))
            installed = self.install(target)
            self.assertEqual(installed.returncode, 0, installed.stderr)
            again = self.install(target, '--upgrade')
            self.assertEqual(again.returncode, 0, again.stderr)
            self.assertIn('Copied=0', again.stdout)

    def test_install_keeps_target_index_independent_from_kit(self):
        """新安装采用通用索引，安装目录里不应出现套件自身的记录。"""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            result = self.install(target)
            self.assertEqual(result.returncode, 0, result.stderr)
            index = (target / 'docs/knowledge/registry.json').read_text(encoding='utf-8')
            self.assertEqual(json.loads(index), {'schema_version': 1, 'records': []})
            self.assertFalse((target / 'docs/self').exists())
