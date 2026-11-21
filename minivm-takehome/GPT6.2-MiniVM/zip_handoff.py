"""Archive an audited handoff snapshot with Unix permissions, even on Windows."""
import argparse
import os
from pathlib import Path
import stat
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

EXEC = {'minivm-takehome/' + s for s in ('optimize', 'evaluate',
        'GPT6.2-MiniVM/checks/identity', 'GPT6.2-MiniVM/checks/drop-duplicate')}


def build(source, destination):
    source, destination = source.resolve(), destination.resolve()
    if destination.is_relative_to(source) or not (source/'evidence-manifest.json').is_file():
        raise ValueError('expected audited source directory and external ZIP destination')
    files = sorted(source.rglob('*'))
    if not EXEC <= {p.relative_to(source).as_posix() for p in files if p.is_file()}:
        raise ValueError('missing launcher or evaluator helper')
    with tempfile.TemporaryDirectory(dir=destination.parent) as tmp:
        archive = Path(tmp)/'new.zip'
        with ZipFile(archive, 'w') as z:
            for path in [source, *files]:
                if path.is_symlink(): raise ValueError('unexpected symlink')
                rel = path.relative_to(source).as_posix()
                name = 'handoff' if path == source else 'handoff/' + rel
                directory = path.is_dir()
                mode = stat.S_IFDIR | 0o755 if directory else stat.S_IFREG | (0o755 if rel in EXEC else 0o644)
                entry = ZipInfo(name + ('/' if directory else ''))
                entry.create_system = 3  # Unix creator, not Windows/DOS
                entry.external_attr = (mode << 16) | (0x10 if directory else 0)
                z.writestr(entry, b'' if directory else path.read_bytes(), compress_type=ZIP_DEFLATED)
        with ZipFile(archive) as z:
            if z.testzip() is not None: raise ValueError('ZIP checksum error')
            for name in EXEC:
                entry = z.getinfo('handoff/' + name)
                if entry.create_system != 3 or entry.external_attr >> 16 != 0o100755:
                    raise ValueError(f'wrong mode: {name}')
        os.replace(archive, destination)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path); parser.add_argument('destination', type=Path)
    args = parser.parse_args(); build(args.source, args.destination)