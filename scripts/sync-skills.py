#!/usr/bin/env python3
"""Mirror the public v3 skills subtree at one immutable source commit."""
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
import urllib.request

SOURCE = 'nocobase/nocobase'
REF = 'v3-develop'
# Compatibility until the source rename lands; the new name passes through unchanged.
ALIASES = {'nocobase-plugin-development': 'nocobase-app-plugin-development'}


def api(path):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'nocobase-skills-v3-sync', 'X-GitHub-Api-Version': '2022-11-28'}
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = f'Bearer {token}'
    request = urllib.request.Request(f'https://api.github.com/repos/{SOURCE}/{path}', headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def snapshot(get=api):
    commit = get(f'commits/{REF}')
    root = get('git/trees/' + commit['commit']['tree']['sha'])
    skill_tree = next(item for item in root['tree'] if item['path'] == 'skills' and item['type'] == 'tree')
    tree = get('git/trees/' + skill_tree['sha'] + '?recursive=1')
    if tree.get('truncated'):
        raise ValueError('Truncated skills tree; refusing a partial synchronization')
    entries = tree['tree']
    names = {item['path'].split('/')[0] for item in entries if re.fullmatch(r'[^/]+/SKILL.md', item['path'])}
    if not names:
        raise ValueError('No skills found; refusing to empty distribution')
    files = {}
    size = 0
    for item in entries:
        parts = PurePosixPath(item['path']).parts
        if not parts or parts[0] not in names:
            continue
        if item['type'] == 'tree':
            continue
        if any(part in ('.', '..') for part in item['path'].split('/')) or item['path'].startswith('/'):
            raise ValueError('Unsafe source path')
        if item['type'] != 'blob' or item['mode'] not in ('100644', '100755'):
            raise ValueError('Symlinks and submodules are not supported in distributed skills')
        size += item.get('size', 0)
        if size > 50 * 1024 * 1024:
            raise ValueError('Skills exceed the 50 MiB synchronization budget')
        blob = get('git/blobs/' + item['sha'])
        if blob['encoding'] != 'base64':
            raise ValueError('Unexpected blob encoding')
        content = base64.b64decode(blob['content'])
        digest = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
        if digest != item['sha']:
            raise ValueError('Blob checksum mismatch')
        name = ALIASES.get(parts[0], parts[0])
        dest = '/'.join((name, *parts[1:]))
        if dest in files:
            raise ValueError('Distribution name collision: ' + dest)
        if parts[-1] == 'SKILL.md' and len(parts) == 2:
            text = content.decode('utf-8')
            match = re.match(r'\A---\r?\n(.*?)\r?\n---', text, re.S)
            if not match or not re.search(r'^name: ' + re.escape(parts[0]) + r'\s*$', match[1], re.M):
                raise ValueError('Skill name must match its source directory: ' + item['path'])
            if name != parts[0]:
                text = text.replace('name: ' + parts[0], 'name: ' + name, 1)
            content = text.encode('utf-8')
        if name != parts[0] and parts[1:] == ('agents', 'openai.yaml'):
            content = content.replace(('$' + parts[0]).encode(), ('$' + name).encode())
        files[dest] = (content, int(item['mode'][-3:], 8))
    return commit['sha'], skill_tree['sha'], files


def sync(root, get=api):
    # Fetch and validate everything before touching the previous complete mirror.
    commit, tree, files = snapshot(get)
    root = Path(root)
    marker = root / '.sync-source.json'
    old = json.loads(marker.read_text()) if marker.exists() else {}
    if old.get('tree') == tree and old.get('aliases') == ALIASES:
        commit = old['commit']  # Unrelated source changes must not produce mirror commits.
    with tempfile.TemporaryDirectory(prefix='skills-sync-', dir=root) as temp:
        staged = Path(temp) / 'skills'
        staged.mkdir()
        for path, (content, mode) in files.items():
            target = staged / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            target.chmod(mode)
        backup = Path(temp) / 'previous'
        target = root / 'skills'
        if target.exists():
            target.rename(backup)
        try:
            staged.rename(target)
        except BaseException:
            if backup.exists():
                backup.rename(target)
            raise
    marker.write_text(json.dumps({'repository': SOURCE, 'ref': REF, 'commit': commit, 'tree': tree, 'aliases': ALIASES}, indent=2) + '\n')
    print(f'Synchronized {len(files)} files from {SOURCE}@{commit[:12]} (skills tree {tree[:12]})')


if __name__ == '__main__':
    sync(Path(__file__).resolve().parents[1])
