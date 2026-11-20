"""Regenerate the eight sample artifacts with the current optimizer."""
import json
from pathlib import Path

from optimize import optimize

HERE = Path(__file__).resolve().parent
EXAMPLES = HERE.parent / 'examples'
DEST = HERE / 'optimized-examples'


def build():
    schema = json.loads((EXAMPLES / 'schema.json').read_bytes())
    DEST.mkdir(exist_ok=True)
    for i in range(1, 9):
        name = f'q{i:04}.mini'
        source = (EXAMPLES / 'programs' / name).read_text(encoding='utf-8')
        (DEST / name).write_bytes(optimize(source, schema).encode('utf-8'))


if __name__ == '__main__':
    build()