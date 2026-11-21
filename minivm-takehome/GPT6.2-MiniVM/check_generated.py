"""Independent, seeded native VM checks; not part of the eight-query benchmark."""
import json
import os
import random
import subprocess
import tempfile
from pathlib import Path

from optimize import optimize

VM = Path(__file__).resolve().parents[1]/'bin'/('minivm-windows-x86_64.exe' if os.name == 'nt' else 'minivm')


def run():
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp); dataset = folder/'data.json'; plan = folder/'query.mini'
        for seed in range(6):
            rng = random.Random(seed); key, label = f'k{seed}', f's{seed}'
            rows = [[rng.choice([None, 0, 0, 2, 5]), str(i)] for i in range(0 if seed == 5 else 19)]
            table = {'columns': [{'name': key, 'type': 'INT'}, {'name': label, 'type': 'STR'}], 'rows': rows}
            if seed % 2 == 0:
                rows.sort(key=lambda r: (r[0] is not None, r[0])); table['sorted'] = [key]
            dataset.write_text(json.dumps({'t': table}), encoding='utf8')
            schema = json.loads(subprocess.check_output([VM, '--schema', dataset], timeout=10))
            source = (f'LOAD key{seed}, t.{key}\nLOAD name, t.{label}\nUPPER dead, name\n'
                      f'SORT ix, key{seed} ASC NF\nGATHER name, name, ix\nOUT name\n')
            rewritten = optimize(source, schema)
            if ('IOTA ix' in rewritten) != ('sorted' in table) or 'UPPER dead' in rewritten:
                raise ValueError(f'seed {seed}: rewrite precondition or dead-code removal failed')
            results = []
            for text in (source, rewritten):
                plan.write_bytes(text.encode()); results.append(json.loads(subprocess.check_output([VM, plan, dataset], timeout=10)))
            a,b = results
            if (a['ncols'],a['rows']) != (b['ncols'],b['rows']) or b['cycles'] >= a['cycles']:
                raise ValueError(f'seed {seed}: output mismatch or no savings')
            print(f'seed {seed}: {len(rows)} rows; sorted declaration={"sorted" in table}; outputs match')


if __name__ == '__main__':
    run()