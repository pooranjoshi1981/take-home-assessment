"""Cost model for the bundled fixtures only, not a general MiniVM interpreter.

Validate both the ordered output and exact cost of every original against
the shipped VM results before reporting calculated optimized costs.
"""
import json
import operator
import re
from datetime import date
from decimal import Decimal

from build_examples import DEST, EXAMPLES


def size(x):
    return len(x.encode()) if isinstance(x, str) else 0


def sort_positions(keys, registers):
    columns = [(registers[r], d, n) for r, d, n in (k.split() for k in keys)]
    count = len(columns[0][0])
    cost = 2 * count

    def before(i, j):
        nonlocal cost
        for col, direction, nulls in columns:
            a, b = col[i], col[j]
            cost += 2 + min(size(a), size(b))
            if a == b:
                continue
            if a is None or b is None:
                return (a is None) == (nulls == 'NF')
            return (a < b) == (direction == 'ASC')
        return True

    def merge(rows):
        if len(rows) <= 1:
            return rows
        mid = len(rows) // 2
        a, b = merge(rows[:mid]), merge(rows[mid:])
        i = j = 0
        ordered = []
        while i < len(a) and j < len(b):
            if before(a[i], b[j]):
                ordered.append(a[i]); i += 1
            else:
                ordered.append(b[j]); j += 1
        return ordered + a[i:] + b[j:]

    positions = merge(list(range(count)))
    return positions, cost


OPS = {'GT': operator.gt, 'GE': operator.ge, 'LT': operator.lt, 'EQ': operator.eq,
       'MUL': operator.mul, 'SUB': operator.sub, 'LEFT': lambda s, n: s[:n],
       'CAT': operator.add, 'UPPER': str.upper, 'RTRIM': lambda s: s.rstrip(' '),
       'YEAR': lambda d: d.year, 'MONTH': lambda d: d.month, 'DOW': date.isoweekday}


def element(op, v):
    if op == 'NVL': return v[0] if v[0] is not None else v[1]
    if op == 'NULLIFE': return None if v[0] == '' else v[0]
    if op == 'IS': return v[0] == v[1]
    if op == 'IF': return v[1] if v[0] else v[2]
    if op == 'AND': return False if False in v else None if None in v else True
    if op == 'OR': return True if True in v else None if None in v else False
    fn = OPS[op]
    return None if None in v else fn(*v)


def literal(a):
    if a.startswith("'"): return a[1:-1].replace("''", "'")
    if a.startswith('#'): return date.fromisoformat(a.strip('#'))
    return Decimal(a) if '.' in a else int(a)


def run(plan, data):
    r = {}
    cycles = 0
    for line in plan.read_text(encoding='utf8').splitlines():
        # A quoted argument may contain commas, spaces or comment characters.
        tokens = re.findall(r"'(?:[^']|'')*'|;.*|[^\s,;']+", line)
        if tokens and tokens[-1].startswith(';'): tokens.pop()
        if not tokens: continue
        op, *args = tokens
        op = op.upper()
        cycles += 4
        if op == 'OUT':
            rows = [[str(x) if isinstance(x, Decimal) else x for x in row] for row in zip(*(r[a] for a in args))]
            return dict(ncols=len(args), rows=rows, cycles=cycles)
        dest, *args = args
        if op == 'LOAD':
            table, field = args[0].split('.')
            columns = data[table]['columns']; idx = next(i for i,c in enumerate(columns) if c['name'] == field)
            conv = {'NUM': Decimal, 'INT': int, 'DATE': date.fromisoformat, 'STR': str}[columns[idx]['type']]
            out = [None if row[idx] is None else conv(row[idx]) for row in data[table]['rows']]
            cycles += len(out)
        elif op in ('GATHER', 'IOTA', 'IDX', 'SLICE'):
            src = r[args[0]]
            if op == 'GATHER': out = [src[i] if i is not None else None for i in r[args[1]]]
            elif op == 'IOTA': out = list(range(len(src)))
            elif op == 'SLICE': out = src[:int(args[1])]
            else: out = [i for i, x in enumerate(src) if x is True]
            cycles += len(src if op == 'IDX' else out)
        elif op == 'SORT':
            out, cost = sort_positions([' '.join([args[i], args[i+1].upper(), args[i+2].upper()])
                                        for i in range(0, len(args), 3)], r)
            cycles += cost
        elif op in ('NLJOIN', 'HJOIN'):
            second, left, right = args
            a, b = r[left], r[right]
            pairs = [(i,j) for i,x in enumerate(a) for j,y in enumerate(b) if x is not None and x == y]
            if op == 'HJOIN': cycles += sum(6 + size(x) for x in a+b)
            else: cycles += sum(1 + min(size(x), size(y)) for x in a for y in b)
            cycles += 2 * len(pairs)
            r[dest], r[second] = [i for i,j in pairs], [j for i,j in pairs]
            continue
        elif op == 'GROUP':
            groups = {}
            for i, keys in enumerate(zip(*(r[a] for a in args))):
                groups.setdefault(keys, []).append(i)
                cycles += 6 + sum(map(size, keys))
            out = list(groups.values())
        elif op == 'GALL':
            out = [list(range(len(r[args[0]])))]; cycles += len(out[0])
        elif op in ('GFIRST', 'GCOUNT', 'GSUM', 'GMIN', 'GMAX'):
            out = []
            for group in r[args[0]]:
                cycles += len(group) * (1 if op == 'GFIRST' else 2)
                if op == 'GFIRST': out.append(group[0] if group else None)
                elif op == 'GCOUNT': out.append(len(group))
                else:
                    vals = [r[args[1]][i] for i in group if r[args[1]][i] is not None]
                    if op != 'GSUM': cycles += sum(map(size, vals))
                    fn = {'GSUM':sum, 'GMIN':min, 'GMAX':max}[op]
                    out.append(fn(vals) if vals else None)
        else:
            n = next(len(r[a]) for a in args if a in r)
            cols = [r[a] if a in r else [literal(a)] * n for a in args]
            out = []
            for vals in zip(*cols):
                x = element(op, vals); out.append(x)
                cycles += 2 if op in ('YEAR', 'MONTH', 'DOW') else 1
                if op in ('IS', 'EQ', 'LT', 'GE', 'GT'): cycles += min(map(size, vals))
                elif op not in ('IF', 'NVL', 'NULLIFE'): cycles += size(x) + sum(map(size, vals))
        r[dest] = out
    raise ValueError('missing OUT')


def calculate():
    data = json.loads((EXAMPLES/'data.json').read_bytes(), parse_float=Decimal)
    records = []
    for i in range(1, 9):
        name = f'q{i:04}'
        ref = json.loads((EXAMPLES/'expected'/f'{name}.json').read_bytes())
        original = run(EXAMPLES/'programs'/f'{name}.mini', data)
        if original != ref:
            raise ValueError(f'{name}: baseline {original["cycles"]} vs expected {ref["cycles"]}; rows match: {original["rows"] == ref["rows"]}')
        optimized = run(DEST/f'{name}.mini', data)
        if (optimized['ncols'], optimized['rows']) != (ref['ncols'], ref['rows']):
            raise ValueError(f'{name}: optimized rows or columns differ')
        records.append((name, original['cycles'], optimized['cycles']))
    return records


def report(records):
    lines = ['# Sample cycle comparison', '',
             'Calculated on the bundled example data using the documented MiniVM cost model; '
             'these are not native VM timings or new native VM measurements.', '',
             'All eight original cycle counts and ordered results matched the bundled expected JSON. '
             'Each optimized result matched the original, including column order and duplicate rows.', '',
             '| Plan | Original | Optimized | Saved | Reduction |', '|---|---:|---:|---:|---:|']
    totals = ('Total', sum(row[1] for row in records), sum(row[2] for row in records))
    for name, old, new in [*records, totals]:
        label = '**Total**' if name == 'Total' else f'[{name}]({name}.mini)'
        lines.append(f'| {label} | {old:,} | {new:,} | {old-new:,} | {(old-new)/old:.2%} |')
    lines.extend(['', 'To reproduce from the parent directory, run `python build_examples.py` '
                  'and then `python sample_cycles.py`. To confirm on the native VM, run '
                  '`./evaluate ./optimize` from the assignment root on Linux or macOS.'])
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    summary = report(calculate())
    (DEST/'cycles.md').write_bytes(summary.encode('utf-8'))
    print(summary, end='')