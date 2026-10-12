import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('sync_skills', Path(__file__).resolve().parents[1] / 'scripts/sync-skills.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture(content, commit='commit1', tree='tree1'):
    entries, blobs = [], {}
    for name, value in content.items():
        data, mode = value if isinstance(value, tuple) else (value, '100644')
        sha = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        entries.append({'path': name, 'type': 'blob', 'mode': mode, 'sha': sha, 'size': len(data)})
        blobs['git/blobs/' + sha] = {'encoding': 'base64', 'content': base64.b64encode(data).decode()}
    records = {'commits/v3-develop': {'sha': commit, 'commit': {'tree': {'sha': 'root'}}}, 'git/trees/root': {'tree': [{'path': 'skills', 'type': 'tree', 'sha': tree}]}, 'git/trees/' + tree + '?recursive=1': {'tree': entries}, **blobs}
    return records


class SyncTests(unittest.TestCase):
    def test_alias_references_modes_deletion_and_noop(self):
        data = {'nocobase-plugin-development/SKILL.md': b'---\nname: nocobase-plugin-development\ndescription: Test\n---\n[Guide](references/a.md)\n', 'nocobase-plugin-development/references/a.md': b'Guide', 'nocobase-plugin-development/scripts/a.sh': (b'#!/bin/sh\n', '100755'), 'README.md': b'Not a Skill'}
        with tempfile.TemporaryDirectory() as root:
            module.sync(root, fixture(data).__getitem__)
            skill = Path(root) / 'skills/nocobase-v3-plugin-development'
            self.assertIn('name: nocobase-v3-plugin-development', (skill / 'SKILL.md').read_text())
            self.assertTrue((skill / 'scripts/a.sh').stat().st_mode & 0o111)
            self.assertFalse((Path(root) / 'skills/README.md').exists())
            module.sync(root, fixture(data, commit='unrelated').__getitem__)
            self.assertEqual(json.loads((Path(root) / '.sync-source.json').read_text())['commit'], 'commit1')
            del data['nocobase-plugin-development/references/a.md']
            module.sync(root, fixture(data, commit='commit2', tree='tree2').__getitem__)
            self.assertFalse((skill / 'references/a.md').exists())

    def test_download_failure_preserves_previous_mirror(self):
        data = {'one/SKILL.md': b'---\nname: one\ndescription: Test\n---\n'}
        with tempfile.TemporaryDirectory() as root:
            module.sync(root, fixture(data).__getitem__)
            before = (Path(root) / '.sync-source.json').read_bytes()
            broken = fixture(data, tree='broken')
            broken['git/trees/broken?recursive=1']['tree'][0]['sha'] = 'missing'
            with self.assertRaises(KeyError):
                module.sync(root, broken.__getitem__)
            self.assertTrue((Path(root) / 'skills/one/SKILL.md').exists())
            self.assertEqual((Path(root) / '.sync-source.json').read_bytes(), before)

    def test_truncated_empty_and_symlink_sources_rejected(self):
        for case in ('truncated', 'empty', 'symlink'):
            with self.subTest(case=case):
                data = fixture({'one/SKILL.md': b'---\nname: one\n---\n'})
                tree = data['git/trees/tree1?recursive=1']
                if case == 'truncated': tree['truncated'] = True
                if case == 'empty': tree['tree'] = []
                if case == 'symlink': tree['tree'][0]['mode'] = '120000'
                with self.assertRaises(ValueError): module.snapshot(data.__getitem__)


if __name__ == '__main__':
    unittest.main()
