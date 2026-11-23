"""从 Git 版本或当前工作区构建发布包，并在解压副本上验证。"""
import argparse
import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
RELEASE_FILES = ('README.md', 'AGENTS.md', 'install.py')
RELEASE_FOLDERS = ('.agents', '.github', 'docs', 'examples', 'scripts')


def main():
    """解析源码基线、构建并验证 ZIP，最后替换目标文件。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ref', help='Git commit or tag to package; omit for a working tree preview')
    args = parser.parse_args()

    with TemporaryDirectory(dir=ROOT) as directory:
        workspace = Path(directory)
        source = ROOT
        revision = 'working-tree-preview'
        if args.ref:
            revision = subprocess.check_output(
                ['git', 'rev-parse', '--verify', '--end-of-options', args.ref + '^{commit}'],
                cwd=ROOT, text=True).strip()
            snapshot = workspace / 'source.zip'
            subprocess.run(['git', 'archive', '--format=zip', '-o', str(snapshot), revision,
                            '--', *RELEASE_FILES, *RELEASE_FOLDERS], cwd=ROOT, check=True)
            source = workspace / 'source'
            with ZipFile(snapshot) as archive:
                archive.extractall(source)

        readme = (source / 'README.md').read_text(encoding='utf-8')
        match = re.search(r'^\*\*(v\d+\.\d+(?:\.\d+)?)\*\*', readme, re.MULTILINE)
        if not match:
            raise SystemExit('README.md must declare a version near the top')
        version = match[1]
        suffix = '' if args.ref else '-preview'
        target = ROOT / f'agentic-knowledge-kit-{version}{suffix}.zip'
        files = [source / name for name in RELEASE_FILES]
        for folder in RELEASE_FOLDERS:
            files.extend(path for path in (source / folder).rglob('*')
                         if path.is_file() and '__pycache__' not in path.parts and path.suffix.lower() != '.zip')

        staged = workspace / 'release.zip'
        prefix = Path('agentic-knowledge-kit')

        def add_entry(archive, path, content):
            """固定 ZIP 元数据，避免检出时间和文件权限影响产物。"""
            info = ZipInfo((prefix / path).as_posix())
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content, compress_type=ZIP_DEFLATED)

        with ZipFile(staged, 'w', ZIP_DEFLATED) as archive:
            for path in sorted(files, key=lambda file: file.relative_to(source).as_posix()):
                add_entry(archive, path.relative_to(source), path.read_bytes())
            add_entry(archive, 'SOURCE-REVISION', f'version={version}\ncommit={revision}\n'.encode())
        with ZipFile(staged) as archive:
            if archive.testzip() is not None or (prefix / 'docs/README.md').as_posix() not in archive.namelist():
                raise SystemExit('Release archive is corrupt or missing the document entry')
            archive.extractall(workspace)
        package = workspace / prefix

        def verify(*args):
            """用解压副本运行已发布入口。"""
            subprocess.run([sys.executable, '-B', *args], cwd=package, check=True)

        verify('-m', 'unittest', 'discover', '-s', 'scripts')
        registries = [package / 'docs/knowledge/registry.json', package / 'docs/self/registry.json',
                      *sorted((package / 'examples').glob('registry-*.json'))]
        for registry in registries:
            verify('scripts/knowledge.py', '--registry', str(registry), 'validate', '--strict')
        documents = [str(path.relative_to(package)) for path in sorted((package / 'docs').rglob('*.md'))]
        verify('scripts/knowledge.py', 'links', 'README.md', *documents)
        staged.replace(target)
    print(f'Built and verified {target.name}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
