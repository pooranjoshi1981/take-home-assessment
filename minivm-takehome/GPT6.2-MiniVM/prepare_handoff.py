"""Build a local, text-only submission from committed source and one VS Code session.

Usage: python prepare_handoff.py WORKSPACE_STORAGE_DIR SESSION_UUID NEW_DIRECTORY
The destination must not exist. No history is rewritten and no network is used.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
BASE = 'minivm-takehome/'
ALLOWED = ['.gitattributes', '.gitignore', 'SUBMISSION.md', *(BASE + p for p in
           ('optimize', 'evaluate', 'docs', 'examples', 'skill', 'GPT6.2-MiniVM'))]
SECRET = re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{32,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9_-]{40,}|Bearer [A-Za-z0-9._-]{30,}')


def git(repo, *args, data=None):
    return subprocess.run(['git', '-C', str(repo), *args], input=data, stdout=subprocess.PIPE,
                          check=True).stdout


def inspect(data, name):
    if b'\x00' in data or any(c < 32 and c not in (9, 10, 13) for c in set(data)):
        raise ValueError(f'non-text input: {name}')
    data.decode('utf-8-sig')
    if SECRET.search(data):
        raise ValueError(f'possible credential in {name}; inspect privately before sharing')


def counters(journal):
    requests = []
    for line in journal.splitlines():
        entry = json.loads(line); key = entry.get('k', []); value = entry.get('v')
        if entry['kind'] == 0:
            requests = list(value.get('requests', []))
        elif key == ['requests'] and entry['kind'] == 2:
            i = entry.get('i', len(requests)); requests[i:i+entry.get('n', 0)] = value
        elif len(key) == 3 and key[0] == 'requests' and key[2] in ('promptTokens', 'completionTokens'):
            requests[key[1]][key[2]] = value
    return {k: sum(r.get(k, 0) or 0 for r in requests) for k in ('promptTokens','completionTokens')}


def prepare(storage, sid, dest):
    folder = unquote(urlparse(json.loads((storage/'workspace.json').read_bytes())['folder']).path)
    if os.name == 'nt': folder = folder.lstrip('/')
    if Path(folder).resolve() != ROOT:
        raise ValueError('workspaceStorage directory does not belong to this assignment')
    if dest.exists(): raise ValueError('choose a new destination; existing files are not replaced')
    if git(ROOT, 'status', '--porcelain', '--', *ALLOWED).strip():
        raise ValueError('commit pending submission source changes before packaging')
    branch = git(ROOT, 'symbolic-ref', 'HEAD').decode().strip()
    stream = git(ROOT, 'fast-export', '--show-original-ids', f'--refspec={branch}:refs/heads/submission', branch, '--', *ALLOWED)
    inspect(stream, 'filtered history')
    # Stage privately and publish only after validation. The replay repository
    # lives outside the delivery tree: no .git objects, hooks or config are sent.
    with tempfile.TemporaryDirectory(dir=dest.parent) as temp:
        tmp = Path(temp); replay = tmp/'replay'; replay.mkdir(); out = tmp/'out'; out.mkdir()
        git(replay, 'init', '-q'); git(replay, 'fast-import', '--quiet', data=stream)
        git(replay, 'fsck', '--full', '--no-dangling'); ref = 'refs/heads/submission'
        commits = git(replay, 'rev-list', ref).splitlines(); checked = set()
        for commit in commits:
            for entry in git(replay, 'ls-tree', '-rz', commit.decode()).split(b'\0'):
                if not entry: continue
                meta, path = entry.split(b'\t', 1); mode, typ, oid = meta.split(); name = path.decode()
                if (mode not in (b'100644', b'100755') or not any(name == p or name.startswith(p+'/') for p in ALLOWED)
                        or Path(name).suffix.lower() in ('.pdf','.exe','.pyc','.zip') or Path(name).name == '.DS_Store'):
                    raise ValueError(f'unexpected historical path: {name}')
                if oid not in checked:
                    inspect(git(replay, 'cat-file', 'blob', oid.decode()), name); checked.add(oid)
        for entry in git(replay, 'ls-tree', '-rz', ref).split(b'\0'):
            if not entry: continue
            meta, path = entry.split(b'\t', 1); mode, _, oid = meta.split(); target = out/path.decode()
            target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(git(replay, 'cat-file', 'blob', oid.decode()))
            if mode == b'100755': target.chmod(0o755)
        (out/'history.fi').write_bytes(stream)
        raw = out/'raw-sessions'; files = []
        for rel in (f'chatSessions/{sid}.jsonl', f'GitHub.copilot-chat/transcripts/{sid}.jsonl',
                    f'GitHub.copilot-chat/debug-logs/{sid}', f'chatEditingSessions/{sid}',
                    f'GitHub.copilot-chat/chat-session-resources/{sid}'):
            item = storage/rel
            if item.is_dir(): files.extend(p for p in item.rglob('*') if p.is_file())
            elif item.is_file(): files.append(item)
        journal = Path('chatSessions')/(sid+'.jsonl')
        if storage/journal not in files: raise ValueError('original chat journal missing')
        hashes = {}
        for src in sorted(files):
            if not src.resolve().is_relative_to(storage.resolve()): raise ValueError('external session link')
            rel = src.relative_to(storage); contents = src.read_bytes(); inspect(contents, rel)
            target = raw/rel; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(contents)
            digest = hashlib.sha256(contents).hexdigest()
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest: raise ValueError('copy mismatch')
            hashes[rel.as_posix()] = digest
        manifest = dict(session=sid, snapshot_utc=datetime.now(timezone.utc).isoformat(),
                        source_head=git(ROOT,'rev-parse','HEAD').decode().strip(), commits_replayed=len(commits),
                        historical_text_blobs=len(checked), history_sha256=hashlib.sha256(stream).hexdigest(),
                        recorded_tokens=counters((raw/journal).read_bytes()), raw_sha256=hashes)
        (out/'evidence-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf8')
        shutil.move(out, dest)
        print(f'{dest}: {len(commits)} commits replayed, {len(checked)} text blobs, {len(files)} raw files; {manifest["recorded_tokens"]}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('storage', type=Path); parser.add_argument('session', type=UUID)
    parser.add_argument('destination', type=Path); args = parser.parse_args()
    prepare(args.storage.resolve(), str(args.session), args.destination.resolve())