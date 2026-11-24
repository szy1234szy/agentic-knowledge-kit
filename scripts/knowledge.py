#!/usr/bin/env python3
"""校验项目知识索引，并按代码路径或记录关系查询候选知识。"""
import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import tokenize
from collections import Counter, defaultdict, deque
from datetime import date
from fnmatch import translate
from graphlib import CycleError, TopologicalSorter
from pathlib import Path, PureWindowsPath
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / 'docs/knowledge/registry.json'
KINDS = {'feature', 'module', 'capability', 'invariant', 'adr', 'rule', 'incident', 'evidence',
         'architecture', 'operations', 'quality', 'guide'}
STATES = {'proposed', 'accepted', 'implemented', 'verified', 'superseded', 'deprecated', 'unknown'}
REL = {'constrained_by', 'implements', 'motivated_by', 'decided_by', 'enforced_by',
       'verified_by', 'supersedes', 'related_to', 'depends_on'}
HISTORICAL = {'superseded', 'deprecated'}
IMPORTANCE = {'core': 0, 'standard': 1, 'low': 2}
ARCHIVE = 'docs/knowledge/archive/'
LIVE_REFERENCES = {'depends_on', 'constrained_by', 'decided_by', 'verified_by', 'enforced_by', 'implements'}
AUDITED_SCOPES = {'rule', 'invariant', 'architecture', 'operations', 'quality', 'guide'}


def load(registry=REG):
    """读取第一版索引结构。"""
    return parse_registry(registry.read_text(encoding='utf-8-sig'))


def parse_registry(body):
    """解析工作区或 Git 基线中的索引文本。"""
    data = json.loads(body.removeprefix('\ufeff'))
    if (not isinstance(data, dict) or type(data.get('schema_version')) is not int
            or data['schema_version'] != 1 or not isinstance(data.get('records'), list)):
        raise ValueError('Invalid registry schema')
    return data['records']


def local_path(value):
    """统一路径分隔符，并拒绝绝对路径、盘符和上级目录。"""
    if not isinstance(value, str) or not value.strip() or '\x00' in value:
        return None
    normalized = value.replace('\\', '/')
    if PureWindowsPath(normalized).anchor or '..' in normalized.split('/'):
        return None
    return '/'.join(part for part in normalized.split('/') if part not in ('', '.')) or None


def existing_file(value):
    """校验引用的文件存在且解析后仍在项目范围内。"""
    path = ROOT / value
    try:
        return path.resolve().is_relative_to(ROOT) and path.is_file()
    except (OSError, RuntimeError):
        return False


def iso_date(value):
    """解析索引使用的公历日期，拒绝简写和无效日期。"""
    if isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    return None


def archived(record):
    """通过独立存放路径识别归档记录，保留原工程状态。"""
    return (local_path(record.get('path')) or '').startswith(ARCHIVE)


def external_draft(record):
    """外来规范只有在明确采纳后才进入任务的日常检索。"""
    return 'origin' in record and record.get('status') not in ('accepted', 'verified')


def importance(record):
    """旧索引默认使用标准优先级，核心资产在同层候选中优先。"""
    return IMPORTANCE[record.get('asset', {}).get('importance', 'standard')]


def record_location(record):
    """在共用文档中给出具体章节，方便按任务选读。"""
    section = record.get('section')
    return f"{record['path']} (section: {section})" if section else record['path']


def check_asset(record):
    """校验可选的维护元数据和归档理由。"""
    asset = record.get('asset', {})
    if not isinstance(asset, dict):
        return ['asset must be an object']
    errors = []
    level = asset.get('importance', 'standard')
    if not isinstance(level, str) or level not in IMPORTANCE:
        errors.append('asset.importance must be core, standard or low')
    for field in ('last_reviewed', 'last_used'):
        if field in asset and iso_date(asset[field]) is None:
            errors.append(f'asset.{field} must be a valid YYYY-MM-DD date')
    if 'reviewed_commit' in asset:
        commit = asset['reviewed_commit']
        if not isinstance(commit, str) or not re.fullmatch(r'[0-9a-fA-F]{7,64}', commit):
            errors.append('asset.reviewed_commit must be a Git commit hash')
    reason = asset.get('archive_reason')
    if archived(record):
        if not isinstance(reason, str) or not reason.strip():
            errors.append('archived asset requires asset.archive_reason')
        if level == 'core':
            errors.append('archived asset cannot be marked core')
    elif 'archive_reason' in asset:
        errors.append(f'asset.archive_reason requires a document under {ARCHIVE}')
    return errors


def check(records, *, allow_missing_documents=False):
    """校验字段、记录文件、关系目标与替代链。"""
    errors, warnings, by_id = [], [], {}
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f'record[{index}] is not an object')
            continue
        rid = record.get('id')
        if not isinstance(rid, str) or not rid.strip():
            errors.append(f'record[{index}] missing id')
            continue
        if rid in by_id:
            errors.append(f'duplicate id {rid}')
        by_id[rid] = record
        for field, choices in (('kind', KINDS), ('status', STATES)):
            value = record.get(field)
            if not isinstance(value, str) or value not in choices:
                errors.append(f'{rid}: invalid {field}')

        if 'plan' in record:
            plan = record['plan']
            if record.get('kind') != 'feature' or not isinstance(plan, dict):
                errors.append(f'{rid}: plan must be an object on a feature record')
            else:
                for field in ('title', 'owner'):
                    if field == 'owner' and field not in plan:
                        continue
                    value = plan.get(field)
                    if not isinstance(value, str) or not value.strip():
                        errors.append(f'{rid}: plan.{field} must be a non-empty string')
        if 'origin' in record:
            origin = record['origin']
            if record.get('kind') != 'rule' or not isinstance(origin, dict):
                errors.append(f'{rid}: origin must be an object on a rule')
            else:
                for field in ('source', 'revision', 'locator'):
                    if field == 'source' or field in origin:
                        value = origin.get(field)
                        if not isinstance(value, str) or not value.strip():
                            errors.append(f'{rid}: origin.{field} must be a non-empty string')
                if record.get('status') in ('accepted', 'verified') and not record.get('scope'):
                    errors.append(f'{rid}: adopted external rule requires scope')

        path = local_path(record.get('path'))
        if not path:
            errors.append(f'{rid}: invalid relative path')
        elif not existing_file(path):
            # 保留旧路径供影响分析使用，完整性校验仍要求记录文件存在。
            (warnings if allow_missing_documents else errors).append(f'{rid}: missing file {path}')
        if 'section' in record and (not isinstance(record['section'], str) or not record['section'].strip()):
            errors.append(f'{rid}: section must be a non-empty Markdown heading')
        elif 'section' in record and path and not path.lower().endswith('.md'):
            errors.append(f'{rid}: section requires a Markdown file')
        errors.extend(f'{rid}: {issue}' for issue in check_asset(record))

        for field in ('scope', 'evidence'):
            values = record.get(field, [])
            if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
                errors.append(f'{rid}: {field} must be a list of strings')
                continue
            for value in values:
                if field == 'scope' and not local_path(value):
                    errors.append(f'{rid}: invalid scope {value!r}')
    replacements = TopologicalSorter()
    dependencies = TopologicalSorter()
    for rid, record in by_id.items():
        edges = record.get('relations', [])
        if not isinstance(edges, list):
            errors.append(f'{rid}: relations must be a list')
            continue
        for edge in edges:
            if not isinstance(edge, dict):
                errors.append(f'{rid}: invalid relation {edge}')
                continue
            relation, target = edge.get('type'), edge.get('target')
            if (not isinstance(relation, str) or relation not in REL
                    or not isinstance(target, str) or target not in by_id):
                errors.append(f'{rid}: invalid relation {edge}')
                continue
            if (relation in LIVE_REFERENCES and record.get('status') not in ('superseded', 'deprecated')
                    and not archived(record) and archived(by_id[target])):
                errors.append(f'{rid}: {relation} references archived asset {target}')
            if (relation in {'constrained_by', 'enforced_by'}
                    and record.get('status') in ('accepted', 'implemented', 'verified')
                    and not archived(record) and external_draft(by_id[target])):
                errors.append(f'{rid}: {relation} references unadopted external rule {target}')
            if relation == 'supersedes':
                replacements.add(rid, target)
            elif relation == 'depends_on':
                if record.get('kind') != 'feature' or by_id[target].get('kind') != 'feature':
                    errors.append(f'{rid}: depends_on must connect feature records: {target}')
                else:
                    dependencies.add(rid, target)
    for relation, graph in (('supersedes', replacements), ('depends_on', dependencies)):
        try:
            graph.prepare()
        except CycleError as error:
            errors.append(f'{relation} cycle: ' + ' -> '.join(error.args[1]))
    return errors, warnings


def evidence_issue(value, symbols):
    """检查文件证据、行号范围和可识别的 Python 定义锚点。"""
    reference, _, anchor = value.removeprefix('file:').partition('#')
    candidate = local_path(reference)
    if not candidate or not existing_file(candidate):
        return f'invalid or missing evidence file {reference}'
    if line_range := re.fullmatch(r'L(\d+)(?:-L?(\d+))?', anchor):
        start, end = int(line_range[1]), int(line_range[2] or line_range[1])
        try:
            with (ROOT / candidate).open('rb') as source:
                if 1 <= start <= end and any(number == end for number, _ in enumerate(source, 1)):
                    return None
        except OSError:
            return f'cannot read evidence file {candidate}'
        return f'evidence line out of range {reference}#{anchor}'
    if not candidate.endswith('.py') or not all(part.isidentifier() for part in anchor.split('.')):
        return None
    if candidate not in symbols:
        try:
            with tokenize.open(ROOT / candidate) as source:
                tree = ast.parse(source.read())
            # 累积定义的作用域，区分不同测试类中同名的方法。
            found, pending = set(), [(tree, '')]
            while pending:
                node, prefix = pending.pop()
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    prefix += node.name
                    found.update((node.name, prefix))
                    prefix += '.'
                pending.extend((child, prefix) for child in ast.iter_child_nodes(node))
            symbols[candidate] = found
        except (OSError, SyntaxError, UnicodeError, LookupError, RecursionError):
            symbols[candidate] = None
    if symbols[candidate] is None:
        return f'cannot parse Python evidence file {candidate}'
    if anchor not in symbols[candidate]:
        return f'missing Python evidence symbol {reference}#{anchor}'
    return None


def workspace_files():
    """读取 Git 可见的现存文件，无 Git 时遍历项目文件。"""
    try:
        result = subprocess.run(
            ['git', '-C', str(ROOT), 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
            capture_output=True,
        )
        if result.returncode == 0:
            return set(result.stdout.decode('utf-8', errors='surrogateescape').split('\0')) - {''}
    except FileNotFoundError:
        pass
    files = set()
    for folder, directories, names in os.walk(ROOT):
        directories[:] = [name for name in directories if name not in {'.git', '__pycache__'}]
        for name in names:
            path = (Path(folder) / name).relative_to(ROOT).as_posix()
            files.add(path)
    return files


def markdown_content_lines(source):
    """保留正文行号，跳过围栏中的示例代码。"""
    return markdown_unfenced_lines(source.read_text(encoding='utf-8-sig').splitlines())


def markdown_unfenced_lines(lines):
    """遍历围栏外的 Markdown 行，保留原始行号。"""
    fence_pattern = re.compile(r'^ {0,3}(`{3,}|~{3,})(.*)$')
    fence = ''
    for number, line in enumerate(lines, 1):
        marker = fence_pattern.match(line)
        if fence:
            if marker and marker[1].startswith(fence) and not marker[2].strip():
                fence = ''
        elif marker:
            fence = marker[1]
        else:
            yield number, line


def markdown_heading(line):
    """提取 ATX 标题的正文。"""
    match = re.match(r'^ {0,3}#{1,6}[ \t]+(.+)$', line)
    return re.sub(r'[ \t]+#+[ \t]*$', '', match[1]).strip() if match else None


def markdown_sections(body):
    """提取唯一标题的正文及子章节内容，重复标题无法单独定位。"""
    lines = body.removeprefix('\ufeff').splitlines()
    headings = []
    sections = {}
    for number, line in markdown_unfenced_lines(lines):
        if title := markdown_heading(line):
            level = len(line.lstrip().split(maxsplit=1)[0])
            headings.append((number - 1, level, title))
    boundaries = []
    for start, level, title in reversed(headings):
        while boundaries and boundaries[-1][1] > level:
            boundaries.pop()
        end = boundaries[-1][0] if boundaries else len(lines)
        boundaries.append((start, level))
        while end > start + 1 and not lines[end - 1].strip():
            end -= 1
        sections[title] = None if title in sections else lines[start:end]
    return sections


def markdown_anchors(source):
    """构建常见的 GitHub 风格标题锚点，包含重复标题编号和显式 HTML 锚点。"""
    used = set()
    for _, line in markdown_content_lines(source):
        if title := markdown_heading(line):
            title = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', title)
            title = re.sub(r'<[^>]+>', '', title)
            slug = re.sub(r'[^\w\- ]', '', title.lower()).replace(' ', '-')
            suffix = 0
            anchor = slug
            while anchor in used:
                suffix += 1
                anchor = f'{slug}-{suffix}'
            used.add(anchor)
        used.update(re.findall(r'<a\s+(?:[^>]*?\s)?(?:id|name)=["\']([^"\']+)["\']', line, re.I))
    return used


def markdown_links(paths):
    """检查 Markdown 中常见的本地文件链接和引用式链接定义。"""
    inline = re.compile(r'(?<!\\)\[[^\]\n]*\]\(\s*(<[^>]+>|(?:\\.|[^\s()])+?)'
                        r'(?:\s+(?:"[^"]*"|\'[^\']*\'))?\s*\)')
    definition = re.compile(r'^ {0,3}\[[^\]]+\]:\s*(<[^>]+>|\S+)')
    errors, anchors = [], {}
    for path in paths:
        if not existing_file(path) or not path.lower().endswith('.md'):
            errors.append(f'{path}: expected an existing project Markdown file')
            continue
        source = ROOT / path
        for number, line in markdown_content_lines(source):
            line = re.sub(r'(`+).*?\1', '', line)
            destinations = [match[1] for match in inline.finditer(line)]
            if match := definition.match(line):
                destinations.append(match[1])
            for raw in destinations:
                value = re.sub(r'\\([()])', r'\1', raw.removeprefix('<').removesuffix('>'))
                if value.startswith('/') or re.match(r'^\w[\w+.-]*:', value):
                    continue
                destination, _, fragment = value.partition('#')
                local = unquote(destination.split('?', 1)[0])
                if not (local or fragment):
                    continue
                try:
                    target = (source.parent / local).resolve() if local else source
                    valid = target.is_relative_to(ROOT) and target.exists()
                except (OSError, ValueError, RuntimeError):
                    valid = False
                if not valid:
                    errors.append(f'{path}:{number}: invalid local link {raw}')
                elif fragment and target.suffix.lower() == '.md' and not re.fullmatch(r'L\d+(?:-L\d+)?', fragment):
                    try:
                        if target not in anchors:
                            anchors[target] = markdown_anchors(target)
                    except (OSError, UnicodeError) as error:
                        errors.append(f'{path}:{number}: cannot read Markdown headings in {raw}: {error}')
                    else:
                        if unquote(fragment) not in anchors[target]:
                            errors.append(f'{path}:{number}: missing Markdown anchor {raw}')
    return errors


def audit(records, strict=False):
    """核查证据及生效规则的范围。严格模式要求范围也能命中。"""
    errors, warnings, symbols, scope_hits, headings = [], [], {}, {}, {}
    by_id = {record['id']: record for record in records}
    files = None
    for record in records:
        rid, status = record['id'], record['status']
        if section := record.get('section'):
            path = local_path(record['path'])
            if path not in headings:
                try:
                    titles = (markdown_heading(line)
                              for _, line in markdown_content_lines(ROOT / path))
                    headings[path] = Counter(title for title in titles if title)
                except (OSError, UnicodeError) as error:
                    headings[path] = None
                    errors.append(f'{rid}: cannot read section headings from {path}: {error}')
            if headings[path] is not None and headings[path][section] == 0:
                errors.append(f'{rid}: missing Markdown section {section!r} in {path}')
            elif headings[path] is not None and headings[path][section] > 1:
                errors.append(f'{rid}: ambiguous Markdown section {section!r} in {path}')
        if status in HISTORICAL or archived(record):
            continue
        issues = errors if status == 'verified' else warnings
        references = [value for value in record.get('evidence', []) if value.strip()]
        if status == 'verified':
            linked = [ref for source in evidence_records(record, by_id) if source['status'] == 'verified'
                      for ref in source.get('evidence', []) if ref.strip()]
            if not (references or linked):
                errors.append(f'{rid}: verified without evidence')
            elif strict and not any(traceable_evidence(ref) for ref in (*references, *linked)):
                errors.append(f'{rid}: verified evidence requires a file: reference or HTTP(S) URL in strict mode')
            if strict and 'plan' in record:
                pending = unverified_prerequisites(record, by_id)
                if pending:
                    errors.append(f"{rid}: verified plan has unverified prerequisites: {', '.join(pending)}")
        for value in references:
            if not value.startswith('file:'):
                continue
            reference = local_path(value[5:].split('#', 1)[0])
            if reference and reference.startswith(ARCHIVE):
                issues.append(f'{rid}: active evidence references archived file {reference}')
            elif issue := evidence_issue(value, symbols):
                issues.append(f'{rid}: {issue}')

        if record['kind'] not in AUDITED_SCOPES or status not in {'accepted', 'implemented', 'verified'}:
            continue
        for scope in record.get('scope', []):
            if scope not in scope_hits:
                if files is None:
                    files = {path for path in workspace_files() if not path.startswith(ARCHIVE)}
                matches = compile_scope(scope)
                scope_hits[scope] = any(matches(path) and existing_file(path) for path in files)
            if not scope_hits[scope]:
                (errors if strict else warnings).append(f'{rid}: scope matches no project files: {scope}')
    return errors, warnings


def evidence_records(record, by_id):
    """从验证关系定位独立的证据记录。"""
    return [by_id[edge['target']] for edge in record.get('relations', [])
            if edge['type'] == 'verified_by' and by_id[edge['target']]['kind'] == 'evidence']


def traceable_evidence(reference):
    """判断证据是否有可追溯位置，网络引用只核对格式。"""
    if reference.startswith('file:'):
        return local_path(reference[5:].split('#', 1)[0]) is not None
    try:
        url = urlsplit(reference)
        return url.scheme in {'http', 'https'} and bool(url.hostname) and not any(char.isspace() for char in reference)
    except ValueError:
        return False


def connections(records):
    """构建双向关系索引，同时保留原始方向。"""
    neighbors = {record['id']: [] for record in records}
    for record in records:
        rid = record['id']
        for edge in record.get('relations', []):
            relation, target = edge['type'], edge['target']
            neighbors[rid].append(('->', relation, target))
            neighbors[target].append(('<-', relation, rid))
    return neighbors


def trace(records, rid):
    """展示指定记录和直接相连的记录。"""
    by_id = {record['id']: record for record in records}
    if rid not in by_id:
        print('Unknown ID:', rid, file=sys.stderr)
        return 2
    start = by_id[rid]
    print(f"{rid} [{start['kind']}/{start['status']}] {record_location(start)}")
    for arrow, relation, target in connections(records)[rid]:
        record = by_id[target]
        print(f"  {arrow} {relation} {arrow} {target} [{record['kind']}] {record_location(record)}")
    return 0


def path_matches(records, paths):
    """从适用范围、知识文档和文件证据识别直接命中。"""
    matches = {}
    for record in records:
        patterns = [compile_scope(scope) for scope in record.get('scope', [])]
        references = {local_path(record['path'])}
        references.update(local_path(value[5:].split('#', 1)[0])
                          for value in record.get('evidence', []) if value.startswith('file:'))
        hits = [path for path in paths if path in references or any(pattern(path) for pattern in patterns)]
        if hits:
            matches[record['id']] = hits
    return matches


def compile_scope(scope):
    """逐段匹配 glob，并让双星号消费零个或多个路径段。"""
    parts = local_path(scope).split('/')
    patterns = [None if part == '**' else re.compile(translate(part)) for part in parts]

    def matches(path):
        """用可到达的位置处理双星号，避免重复遍历相同分支。"""
        segments = path.split('/')
        positions = {0}
        for pattern in patterns:
            if not positions:
                return False
            if pattern is None:
                positions = set(range(min(positions), len(segments) + 1))
            else:
                positions = {index + 1 for index in positions
                             if index < len(segments) and pattern.fullmatch(segments[index])}
        return len(segments) in positions

    return matches


def git_output(*args):
    """读取 Git 原始输出，保留空格和非 ASCII 字符。"""
    result = subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr.decode('utf-8', errors='replace').strip())
    return result.stdout.decode('utf-8', errors='surrogateescape')


def git_commit(base):
    """把用户给出的 Git 基线解析为提交哈希。"""
    return git_output('rev-parse', '--verify', '--end-of-options', base + '^{commit}').strip()


def git_paths(base):
    """读取指定基线到工作区的变化，含删除、重命名前后路径和未跟踪文件。"""
    commit = git_commit(base)
    tracked = git_output('diff', '--relative', '--no-renames', '--name-only', '-z', commit, '--')
    untracked = git_output('ls-files', '--others', '--exclude-standard', '-z', '--', '.')
    return sorted(set((tracked + untracked).split('\0')) - {''})


def git_file(commit, path):
    """读取基线文件。基线中没有该路径时返回 None。"""
    repo_path = git_output('rev-parse', '--show-prefix').rstrip('\n') + path
    present = git_output('--literal-pathspecs', 'ls-tree', '--full-tree', '-z', commit, '--', repo_path)
    return git_output('show', f'{commit}:{repo_path}') if present else None


def registry_baseline(registry, commit, paths):
    """索引变化时读取 Git 基线，保留已删除记录。"""
    if not registry.resolve().is_relative_to(ROOT):
        return None
    path = registry.resolve().relative_to(ROOT).as_posix()
    if path not in paths:
        return None
    previous_body = git_file(commit, path)
    previous_records = parse_registry(previous_body) if previous_body is not None else []
    if any(not isinstance(record, dict) or not isinstance(record.get('id'), str) for record in previous_records):
        raise ValueError('baseline registry contains invalid record IDs')
    return {record['id']: record for record in previous_records}


def registry_delta(records, previous):
    """按 ID 对比仍在当前索引中的有效字段。"""
    if previous is None:
        return {}
    fields = ('kind', 'status', 'path', 'section', 'scope', 'evidence', 'relations', 'plan', 'origin')
    changes = {}
    for record in records:
        rid = record['id']
        if rid not in previous:
            changes[rid] = ['new record']
        elif difference := [field for field in fields if record.get(field) != previous[rid].get(field)]:
            changes[rid] = difference
    return changes


def registry_changes(records, registry, base, paths):
    """按 ID 对比基线中的有效内容，忽略核实时间等维护元数据。"""
    return registry_delta(records, registry_baseline(registry, git_commit(base), paths))


def impact(records, paths):
    """列出直接命中的记录，以及通过证据或计划关系需要复核的资产。"""
    print('Path-based candidate records (requires semantic review):')
    current = sorted((record for record in records if not archived(record) and not external_draft(record)),
                     key=importance)
    hits = path_matches(current, paths)
    for record in current:
        if record['id'] in hits:
            print(f"- {record['id']} [{record['kind']}/{record['status']}] {record_location(record)}"
                  f" | {', '.join(hits[record['id']])}")
    if hits:
        for record, reason in linked_impact(records, current, hits):
            print(f"- {record['id']} [{record['kind']}/{record['status']}] {record_location(record)} | {reason}")
    if not hits:
        print('- none from path patterns; still inspect semantic/data/permission impact manually')
    return 0


def linked_impact(records, current, hits):
    """反查直接证据的使用者，以及关联现行知识的计划。"""
    neighbors = connections(records)
    evidence_hits = {record['id'] for record in current if record['kind'] == 'evidence' and record['id'] in hits}
    for record in current:
        rid = record['id']
        if rid in hits or record['status'] in HISTORICAL:
            continue
        evidence = list(dict.fromkeys(target for arrow, relation, target in neighbors[rid]
                                     if arrow == '->' and relation == 'verified_by' and target in evidence_hits))
        if evidence:
            yield record, f"linked evidence to review via {', '.join(evidence)}"
        elif 'plan' in record:
            reasons = list(dict.fromkeys(target for _, _, target in neighbors[rid] if target in hits))
            if reasons:
                yield record, f"linked plans to review via {', '.join(reasons)}"


def sync_reviews(path, commit):
    """读取本次确实新增或修改的逐条复核，并检查结构化证据地址。"""
    source = (ROOT / path).read_text(encoding='utf-8-sig')
    previous_body = git_file(commit, path)
    previous = json.loads(previous_body.removeprefix('\ufeff')) if previous_body is not None else {}
    entries = json.loads(source)
    if not isinstance(entries, dict) or not isinstance(previous, dict):
        raise ValueError('review file must map record IDs to review entries')
    symbols = {}
    reviewed = {}
    for rid, entry in entries.items():
        if rid in previous and entry == previous[rid]:
            continue
        if isinstance(entry, str) and entry.strip():
            reviewed[rid] = False
            continue
        if not isinstance(entry, dict) or entry.keys() != {'reason', 'evidence'}:
            raise ValueError(f'{rid}: review entry requires a reason and traceable evidence')
        reason, evidence = entry['reason'], entry['evidence']
        if (not isinstance(reason, str) or not reason.strip() or not isinstance(evidence, list) or not evidence
                or not all(isinstance(ref, str) and traceable_evidence(ref) for ref in evidence)):
            raise ValueError(f'{rid}: review entry requires a reason and traceable evidence')
        for ref in evidence:
            if ref.startswith('file:') and (issue := evidence_issue(ref, symbols)):
                raise ValueError(f'{rid}: {issue}')
        reviewed[rid] = True
    return reviewed


def protected_record(record):
    """判断记录是否属于需要证据复核的现行资产。"""
    return (record['status'] in {'accepted', 'implemented', 'verified'}
            and record['kind'] not in {'evidence', 'incident'}
            and not archived(record) and not external_draft(record)
            and (record['kind'] == 'invariant' or importance(record) == 0))


def sync_check(records, registry, base, review_file=None, strict=False):
    """检查变更命中的资产，并要求关键资产有本次复核及证据。"""
    commit = git_commit(base)
    paths = set(git_paths(commit))
    reviewed = {}
    if review_file:
        review_path = local_path(review_file)
        if not review_path or review_path not in paths or not existing_file(review_path):
            raise ValueError('review file must be a project file changed since the base')
        reviewed = sync_reviews(review_path, commit)
        paths.remove(review_path)
    # 作为证据的测试仍属于检查输入，修改普通 Markdown 只作为同步结果。
    inputs = sorted(path for path in paths if not path.lower().endswith('.md')
                    and not path.startswith('docs/knowledge/'))
    if registry.resolve().is_relative_to(ROOT):
        index_path = registry.resolve().relative_to(ROOT).as_posix()
        inputs = [path for path in inputs if path != index_path]
    current = [record for record in records if not archived(record) and record['status'] not in HISTORICAL
               and not external_draft(record)]
    hits = path_matches(current, inputs)
    related = {record['id'] for record, _ in linked_impact(records, current, hits)} if hits else set()
    baseline = registry_baseline(registry, commit, paths)
    changed_records = registry_delta(records, baseline)
    previous_protected = {rid: record for rid, record in (baseline or {}).items()
                          if protected_record(record)}
    current_protected = {record['id'] for record in current if protected_record(record)}
    withdrawn = previous_protected.keys() - current_protected
    former_hits = path_matches(previous_protected.values(), inputs)
    sections_by_path = {}
    pending = []
    for rid in sorted(withdrawn):
        if not reviewed.get(rid):
            pending.append(rid)
            print(f'- {rid} | evidence-backed review required after removal or downgrade of protected '
                  f'{record_location(previous_protected[rid])}')
    for record in current:
        rid = record['id']
        if rid in withdrawn or record['kind'] in {'evidence', 'incident'}:
            continue
        if rid not in hits and rid not in related and rid not in former_hits:
            continue
        if rid in current_protected:
            if not reviewed.get(rid):
                pending.append(rid)
                print(f'- {rid} | evidence-backed review required for {record_location(record)}')
            continue
        if rid in reviewed or rid in changed_records:
            continue
        path = local_path(record['path'])
        if path in paths and existing_file(path):
            if not (section := record.get('section')):
                continue
            if path not in sections_by_path:
                previous = git_file(commit, path)
                before = markdown_sections(previous) if previous is not None else {}
                after = markdown_sections((ROOT / path).read_text(encoding='utf-8-sig'))
                sections_by_path[path] = before, after
            before, after = sections_by_path[path]
            if after.get(section) is not None and (section not in before or
                   before[section] is not None and before[section] != after[section]):
                continue
        pending.append(rid)
        print(f'- {rid} | review {record_location(record)}')
    print(f'{len(pending)} affected record(s) without a document, index update or review note')
    return int(strict and bool(pending))


def unverified_prerequisites(record, by_id):
    """沿前置功能链查找待验证项，每个依赖只检查一次。"""
    pending = deque([record])
    seen, unmet = {record['id']}, []
    while pending:
        for edge in pending.popleft().get('relations', []):
            target = edge['target']
            if edge['type'] != 'depends_on' or target in seen:
                continue
            seen.add(target)
            prerequisite = by_id[target]
            status = prerequisite['status']
            if status != 'verified':
                unmet.append(f'{target} ({status})')
            pending.append(prerequisite)
    return unmet


def plans(records, status=None):
    """列出已登记的功能计划及未验证的直接和间接前置功能。"""
    by_id = {record['id']: record for record in records}
    found = False
    for record in sorted(records, key=importance):
        plan = record.get('plan')
        current = record['status']
        if archived(record) or plan is None or (current != status if status else current in HISTORICAL):
            continue
        found = True
        unmet = unverified_prerequisites(record, by_id)
        print(f"- {record['id']} [{current}] {plan['title']} | {record_location(record)}")
        if 'owner' in plan:
            print(f"    owner: {plan['owner']}")
        if unmet:
            print(f"    prerequisite review: {', '.join(unmet)}")
    if not found:
        print('No feature plans match.')
    return 0


def review(records, ids, review_all=False, *, kind=None, registry=REG):
    """按记录列出证据漂移与重叠线索，保留人工核实结论的步骤。"""
    current = {record['id']: record for record in records
               if not archived(record) and record['status'] not in HISTORICAL
               and (kind is None or record['kind'] == kind)}
    missing = [rid for rid in ids if rid not in current]
    if missing:
        raise ValueError('Unknown, historical or excluded asset ID: ' + ', '.join(missing))
    selected = [current[rid] for rid in dict.fromkeys(ids)] if ids else [
        record for record in sorted(current.values(), key=importance)
        if review_all or kind is not None or importance(record) == 0
    ]
    if not selected:
        print('No assets to review. Select --id or --all if no core assets are registered.')
        return 0

    by_id = {record['id']: record for record in records}
    baselines, symbols = {}, {}
    for record in selected:
        rid = record['id']
        print(f"- {rid} [{record['kind']}/{record['status']}] {record_location(record)}")
        sources = [record, *evidence_records(record, by_id)]
        for source in sources:
            for value in source.get('evidence', []):
                issue = evidence_issue(value, symbols) if value.startswith('file:') else None
                print(f"    {source['id']} evidence: {value} | {issue or 'compare claim with source'}")
        baseline = record.get('asset', {}).get('reviewed_commit')
        if not baseline:
            print('    no reviewed commit; verify the current evidence and record a baseline')
            continue
        if baseline not in baselines:
            try:
                baselines[baseline] = (git_paths(baseline), None)
            except (OSError, ValueError) as error:
                baselines[baseline] = ([], str(error))
        paths, problem = baselines[baseline]
        if problem:
            print(f'    baseline {baseline} unavailable: {problem}')
            continue
        # 比较索引内容可发现关系改动，即使被引用文件本身未变化。
        index_key = (baseline, 'index')
        if index_key not in baselines:
            try:
                baselines[index_key] = (registry_changes(records, registry, baseline, paths), None)
            except (OSError, ValueError) as error:
                baselines[index_key] = ({}, str(error))
        changes, index_problem = baselines[index_key]
        if index_problem:
            print(f'    registry baseline unavailable: {index_problem}')
        for source in sources:
            if source['id'] in changes:
                print(f"    registry changed for {source['id']}: {', '.join(changes[source['id']])}")
        hits = path_matches(sources, paths)
        changed = sorted({path for matches in hits.values() for path in matches})
        if changed:
            print(f"    changed since {baseline}: {', '.join(changed)}")
        elif not index_problem and not any(source['id'] in changes for source in sources):
            print(f'    no registered path changes since {baseline}; verify claims against current behavior')

    # 同类资产共享登记依据时给出候选，不根据路径相似度自动合并。
    groups, document_digests = defaultdict(set), {}
    for rid, record in current.items():
        for field in ('scope', 'evidence'):
            for value in record.get(field, []):
                if field == 'scope' or (value.startswith('file:') and traceable_evidence(value)):
                    groups[(record['kind'], field, value)].add(rid)
        path = local_path(record['path'])
        groups[(record['kind'], 'document', record_location(record))].add(rid)
        if review_all and path.lower().endswith('.md') and existing_file(path):
            # 全量审计才读取正文，日常复核只使用已登记的引用。
            if path not in document_digests:
                try:
                    body = (ROOT / path).read_text(encoding='utf-8-sig')
                    document_digests[path] = hashlib.sha256(' '.join(body.split()).encode('utf-8')).hexdigest()
                except (OSError, UnicodeError) as error:
                    # 单个文件无法读取时保留其他文档的查重结果。
                    document_digests[path] = None
                    print(f'WARN: {path}: Markdown text review skipped: {error}', file=sys.stderr)
            if document_digests[path] is not None:
                groups[(record['kind'], 'text', document_digests[path])].add(rid)
    selected_ids = {record['id'] for record in selected}
    for (kind, field, value), ids in sorted(groups.items()):
        if len(ids) > 1 and ids & selected_ids:
            if field == 'text':
                documents = {current[rid]['path'] for rid in ids}
                if len(documents) < 2:
                    continue
                value = 'matching Markdown text'
            print(f"Overlap candidate [{kind}/{field}] {value}: {', '.join(sorted(ids))}")
    return 0


def context_query_reasons(records, queries):
    """先列名称命中，再补充其他已登记正文的命中。"""
    current = [record for record in records if record['status'] not in HISTORICAL]
    names = {}
    for record in current:
        searchable = (record['id'], record.get('section', ''), record.get('plan', {}).get('title', ''))
        matched = [query for query in queries if any(query.casefold() in value.casefold()
                   for value in searchable)]
        if matched:
            names[record['id']] = 'name: ' + ', '.join(matched)

    documents = {}
    for record in current:
        rid = record['id']
        if rid in names:
            continue
        path = local_path(record['path'])
        if not path or not path.lower().endswith('.md'):
            continue
        if path not in documents:
            documents[path] = [], {}
            if existing_file(path):
                try:
                    body = (ROOT / path).read_text(encoding='utf-8-sig')
                    documents[path] = body.splitlines(), markdown_sections(body)
                except (OSError, UnicodeError) as error:
                    print(f'WARN: cannot search Markdown body {path}: {error}', file=sys.stderr)
        lines, sections = documents[path]
        if section := record.get('section'):
            lines = sections.get(section) or []
        prose = '\n'.join(line for _, line in markdown_unfenced_lines(lines)).casefold()
        matched = [query for query in queries if query.casefold() in prose]
        if matched:
            names[rid] = 'body: ' + ', '.join(matched)
    return names


def context(records, paths, ids, depth, queries=()):
    """按路径、ID、名称和已登记正文选取候选，沿双向关系展开。"""
    by_id = {record['id']: record for record in records}
    unknown = [rid for rid in ids if rid not in by_id]
    if unknown:
        raise ValueError('Unknown ID: ' + ', '.join(unknown))

    current = sorted((record for record in records if not archived(record)
                      and not external_draft(record)), key=importance)
    hits = path_matches(current, paths)
    neighbors = connections(records)
    reasons = dict.fromkeys(ids, 'explicit ID')
    for rid, matched_paths in hits.items():
        reasons.setdefault(rid, ', '.join(matched_paths))
    if queries:
        for rid, reason in context_query_reasons(current, queries).items():
            reasons.setdefault(rid, reason)
    queue = deque((rid, 0, reason) for rid, reason in reasons.items())
    seen = {rid for rid, _, _ in queue}
    print('Context candidates (verify scope, current behavior, and evidence before use):')
    if not queue:
        print('- no matches; locate project paths or supply --id or --query')
    while queue:
        rid, distance, reason = queue.popleft()
        record = by_id[rid]
        status = record['status']
        archive_note = ' | archived' if archived(record) else ''
        print(f"- {rid} [{record['kind']}/{status}] {record_location(record)} | {reason}{archive_note}")
        if origin := record.get('origin'):
            print(f"    external source: {origin['source']}"
                  + (f" ({origin['revision']})" if 'revision' in origin else ''))
        for evidence in record.get('evidence', []):
            print(f'    evidence: {evidence}')

        if distance == depth:
            continue
        for arrow, relation, target in neighbors[rid]:
            if (archived(by_id[target]) or external_draft(by_id[target])) and target not in ids:
                continue
            # 历史记录自动追向替代它的记录，其余旧关系按显式 ID 查阅。
            if status in HISTORICAL and rid not in ids and (arrow, relation) != ('<-', 'supersedes'):
                continue
            if target in seen:
                continue
            seen.add(target)
            reverse = '<-' if arrow == '->' else '->'
            queue.append((target, distance + 1, f'{reverse} {relation} {reverse} {rid}'))
    return 0


def assets(records, args):
    """列出当前资产、待复核事项或归档记录，供维护者判断。"""
    today = args.as_of
    blockers = set()
    if args.review:
        blockers = {edge['target'] for record in records if not archived(record)
                    and record['status'] not in HISTORICAL for edge in record.get('relations', [])
                    if edge['type'] in LIVE_REFERENCES}
    found = False
    for record in sorted(records, key=importance):
        meta = record.get('asset', {})
        level = meta.get('importance', 'standard')
        if (archived(record) != args.archived or (args.kind and record['kind'] != args.kind)
                or (args.core and level != 'core')):
            continue
        notes = []
        if args.review:
            reviewed = iso_date(meta.get('last_reviewed'))
            used = iso_date(meta.get('last_used'))
            if reviewed and (today - reviewed).days >= args.review_days:
                notes.append('review overdue')
            elif reviewed is None and meta and record['status'] not in HISTORICAL:
                notes.append('review date missing')
            candidate = (record['status'] in HISTORICAL
                         or (level == 'low' and used and (today - used).days >= args.idle_days))
            if candidate:
                if level == 'core' or record['id'] in blockers:
                    notes.append('retain: core or required by active asset')
                else:
                    notes.append('archive candidate')
            if not notes:
                continue
        if args.archived:
            notes.append(meta['archive_reason'])
        found = True
        notes.extend(f'{field}: {meta[field]}' for field in ('last_reviewed', 'last_used') if field in meta)
        detail = f" | {'; '.join(notes)}" if notes else ''
        print(f"- {record['id']} [{record['kind']}/{record['status']}/{level}] {record_location(record)}{detail}")
    if not found:
        print('No assets match.')
    return 0


def main():
    """解析参数并将索引错误统一报告给终端和 CI。"""
    parser = argparse.ArgumentParser(description='PGAE knowledge registry utility')
    parser.add_argument('--registry', type=Path, default=REG, help='alternate registry to read')
    subs = parser.add_subparsers(dest='cmd', required=True)
    validate_cmd = subs.add_parser('validate')
    validate_cmd.add_argument('--strict', action='store_true', help='enforce active scopes, traceable evidence and plan prerequisites')
    trace_cmd = subs.add_parser('trace')
    trace_cmd.add_argument('id')
    plans_cmd = subs.add_parser('plans', help='list feature plans and unverified prerequisites')
    plans_cmd.add_argument('--status', choices=sorted(STATES))
    assets_cmd = subs.add_parser('assets', help='list core, current, or archived knowledge assets')
    assets_mode = assets_cmd.add_mutually_exclusive_group()
    assets_mode.add_argument('--archived', action='store_true')
    assets_mode.add_argument('--review', action='store_true')
    assets_cmd.add_argument('--core', action='store_true')
    assets_cmd.add_argument('--kind', choices=sorted(KINDS))
    assets_cmd.add_argument('--review-days', type=int, default=180)
    assets_cmd.add_argument('--idle-days', type=int, default=365)
    assets_cmd.add_argument('--as-of', type=iso_date, default=date.today())
    review_cmd = subs.add_parser('review', help='review core records, evidence drift and overlap candidates')
    review_selection = review_cmd.add_mutually_exclusive_group()
    review_selection.add_argument('--id', action='append', default=[])
    review_selection.add_argument('--all', action='store_true')
    review_cmd.add_argument('--kind', choices=sorted(KINDS), help='limit review and overlap checks to one asset type')
    links_cmd = subs.add_parser('links', help='check relative links in project Markdown')
    links_cmd.add_argument('paths', nargs='*', help='Markdown files; defaults to docs/knowledge')
    impact_cmd = subs.add_parser('impact')
    impact_cmd.add_argument('paths', nargs='*')
    impact_cmd.add_argument('--base', help='compare a Git commit with the working tree')
    sync_cmd = subs.add_parser('sync-check', help='flag code changes with missing knowledge review')
    sync_cmd.add_argument('--base', required=True, help='Git baseline commit')
    sync_cmd.add_argument('--review-file', help='changed JSON mapping reviewed IDs to reasons or reason/evidence objects')
    sync_cmd.add_argument('--strict', action='store_true', help='fail when affected records need review')
    context_cmd = subs.add_parser('context')
    context_cmd.add_argument('paths', nargs='*')
    context_cmd.add_argument('--id', action='append', default=[])
    context_cmd.add_argument('--query', action='append', default=[],
                             help='match current names and registered Markdown content, with names first')
    context_cmd.add_argument('--depth', type=int, default=2)
    args = parser.parse_args()

    try:
        if args.cmd == 'links':
            documents = [local_path(path) for path in args.paths]
            if None in documents:
                raise ValueError('Use project-relative Markdown paths')
            if not documents:
                documents = sorted(path for path in workspace_files()
                                   if path.startswith('docs/knowledge/') and not path.startswith(ARCHIVE)
                                   and path.lower().endswith('.md')
                                   and existing_file(path))
            problems = markdown_links(dict.fromkeys(documents))
            for problem in problems:
                print('ERROR:', problem, file=sys.stderr)
            print(f'{len(set(documents))} Markdown file(s); {len(problems)} broken link(s)')
            return int(bool(problems))
        records = load(args.registry)
        errors, warnings = check(records, allow_missing_documents=args.cmd != 'validate')
        if args.cmd == 'validate' and not errors:
            audit_errors, audit_warnings = audit(records, strict=args.strict)
            errors.extend(audit_errors)
            warnings.extend(audit_warnings)
        for warning in warnings:
            print('WARN:', warning, file=sys.stderr)
        for error in errors:
            print('ERROR:', error, file=sys.stderr)
        if args.cmd == 'validate':
            print(f'{len(records)} records; {len(errors)} error(s); {len(warnings)} warning(s)')
        if errors or args.cmd == 'validate':
            return int(bool(errors))
        if args.cmd == 'trace':
            return trace(records, args.id)
        if args.cmd == 'plans':
            return plans(records, args.status)
        if args.cmd == 'review':
            return review(records, args.id, args.all, kind=args.kind, registry=args.registry)
        if args.cmd == 'sync-check':
            return sync_check(records, args.registry, args.base, args.review_file, args.strict)
        if args.cmd == 'assets':
            if args.as_of is None or min(args.review_days, args.idle_days) < 1:
                raise ValueError('Use a valid YYYY-MM-DD date and positive review/idle days')
            return assets(records, args)

        paths = [local_path(path) for path in args.paths]
        if None in paths:
            raise ValueError('Use project-relative paths')
        if args.cmd == 'impact':
            if args.base:
                paths.extend(git_paths(args.base))
            elif not paths:
                raise ValueError('Provide paths or --base')
            return impact(records, list(dict.fromkeys(paths)))
        queries = list(dict.fromkeys(query.strip() for query in args.query))
        if '' in queries or args.depth < 0 or not (args.id or paths or queries):
            raise ValueError('Provide paths, --id, or non-empty --query and use a non-negative --depth')
        return context(records, list(dict.fromkeys(paths)), args.id, args.depth, queries)
    except (OSError, ValueError) as error:
        print('ERROR:', error, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
