"""从当前资料和代码构建发布包，并在解压副本上验证。"""
import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]


def main():
    """由 README 版本命名发布包，验证通过后替换目标 ZIP。"""
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    match = re.search(r'^\*\*(v\d+\.\d+(?:\.\d+)?)\*\*', readme, re.MULTILINE)
    if not match:
        raise SystemExit('README.md must declare a version near the top')
    version = match[1]
    target = ROOT / f'agentic-knowledge-kit-{version}.zip'
    files = [ROOT / name for name in ('README.md', 'AGENTS.md', 'install.py')]
    for folder in ('.agents', '.github', 'docs', 'examples', 'scripts'):
        files.extend(path for path in (ROOT / folder).rglob('*')
                     if path.is_file() and '__pycache__' not in path.parts and path.suffix.lower() != '.zip')

    with TemporaryDirectory(dir=ROOT) as directory:
        workspace = Path(directory)
        staged = workspace / 'release.zip'
        prefix = Path('agentic-knowledge-kit')
        with ZipFile(staged, 'w', ZIP_DEFLATED) as archive:
            for path in sorted(files):
                archive.write(path, prefix / path.relative_to(ROOT))
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
