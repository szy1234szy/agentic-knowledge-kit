#!/usr/bin/env python3
"""将套件安装到项目，或显式升级工具和工作流。"""
import argparse
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# 升级替换工具入口，缺失的资产模板和归档导航按需补齐。
TOOLS = ('scripts/knowledge.py', 'scripts/test_knowledge.py')
SKILLS = tuple(path.relative_to(ROOT) for path in sorted(ROOT.glob('.agents/skills/*/SKILL.md')))
ADDITIVE_ASSETS = {
    Path('docs/knowledge/archive/README.md'),
    Path('docs/knowledge/asset-management.md'),
    Path('docs/knowledge/standards-intake.md'),
    *(Path('docs/knowledge/templates') / f'{name}.md' for name in
      ('feature-plan', 'architecture', 'feature-reference', 'engineering-reference', 'project-understanding')),
}


def copy_file(source, destination):
    """先写同目录临时文件，再替换目标文件，避免半写入。"""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as handle:
        staged = Path(handle.name)
    try:
        shutil.copy2(source, staged)
        staged.replace(destination)
    finally:
        staged.unlink(missing_ok=True)


def main():
    """按维护模式复制文件，已有项目知识默认保留。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--upgrade', action='store_true', help='replace kit scripts and skills, and add missing asset templates')
    mode.add_argument('--overwrite', action='store_true', help='replace all kit files including project knowledge')
    parser.add_argument('--dry-run', action='store_true', help='check destinations and show actions without writing')
    args = parser.parse_args()
    target = args.target.resolve()
    if not target.is_dir() or target == ROOT:
        parser.error('target must be an existing directory other than the kit itself')
    if not (target / '.git').exists():
        print('WARN: .git not found in target')

    assets = [Path(path) for path in (*TOOLS, *SKILLS)]
    if args.upgrade:
        assets.extend(sorted(ADDITIVE_ASSETS))
    else:
        assets.extend(map(Path, ('AGENTS.md', '.github/workflows/knowledge.yml')))
        assets.extend(path.relative_to(ROOT) for path in sorted((ROOT / 'docs/knowledge').rglob('*'))
                      if path.is_file())
    actions = []
    try:
        # 写入前验证整批目标，避免目录冲突时留下混合版本。
        for relative_path in assets:
            source, destination = ROOT / relative_path, target / relative_path
            if not source.is_file():
                raise ValueError(f'missing kit source: {relative_path}')
            if not destination.resolve().is_relative_to(target):
                raise ValueError(f'destination is outside the project: {relative_path}')
            for ancestor in relative_path.parents:
                parent = target / ancestor
                if parent.exists() and not parent.is_dir():
                    raise ValueError(f'expected a directory: {ancestor}')
            if destination.exists() and not destination.is_file():
                raise ValueError(f'expected a file: {relative_path}')
            replace = args.overwrite or (args.upgrade and relative_path not in ADDITIVE_ASSETS)
            skip = destination.is_file() and (not replace or destination.read_bytes() == source.read_bytes())
            actions.append((relative_path, destination, skip))

        for relative_path, destination, skip in actions:
            if not skip and not args.dry_run:
                copy_file(ROOT / relative_path, destination)
            print('SKIP' if skip else 'WOULD COPY' if args.dry_run else 'COPY', relative_path)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    copied = sum(not skip for _, _, skip in actions)
    label = 'Would copy' if args.dry_run else 'Copied'
    print(f'{label}={copied}, skipped={len(actions) - copied}')


if __name__ == '__main__':
    main()
