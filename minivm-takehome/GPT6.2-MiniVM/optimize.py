"""Conservative straight-line MiniVM optimizer; unknown syntax passes through."""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

OPS = set('LOAD FILL IOTA IDX GATHER SLICE OUT SORT TOPK NLJOIN HJOIN GROUP GALL GID GFIRST GCOUNT GCOUNTV GSUM GMIN GMAX ADD SUB MUL DIV IDIV MOD NEG WRAP TRUNC EQ NE LT LE GT GE IS AND OR NOT ISNULL NVL IF NULLIF NULLIFE UPPER RTRIM TRIM LEFT SUBSTR LEN CAT YEAR MONTH DAY DOW DATEADD DATEDIFF'.split())
REG = r'[A-Za-z_][A-Za-z_0-9]*'
TOKENS = re.compile(r"'(?:[^']|'')*'|[^';,]+|[,;]")


def optimize(text, schema):
    plan, loads, writes = [], {}, Counter()
    tables = {k.lower(): v for k, v in schema.items()}
    for line in text.split('\n'):
        parts, pos = [''], 0
        for token in TOKENS.finditer(line):
            if token.start() != pos:  # unmatched quote
                return text
            pos = token.end()
            t = token.group()
            if t == ';':
                break
            if t == ',':
                parts.append('')
            else:
                parts[-1] += t
        else:
            if pos != len(line):
                return text
        head = parts[0].split(None, 1)
        if not head and len(parts) == 1:
            continue
        if len(head) != 2 or head[0].upper() not in OPS:
            return text
        op = head[0].upper()
        args = [head[1].strip(), *(p.strip() for p in parts[1:])]
        count = 0 if op == 'OUT' else 2 if op in ('HJOIN', 'NLJOIN') else 1
        dest, inputs = args[:count], args[count:]
        if not inputs or not all(re.fullmatch(REG, d) for d in dest):
            return text
        uses = [a.split()[0] for a in inputs if re.fullmatch(REG + r'(?:\s+\w+)*', a)]
        replacement = None
        if op == 'SORT':
            keys = [re.fullmatch(rf'({REG})\s+ASC\s+NF', a, re.I) for a in inputs]
            if all(keys):
                cols = [loads.get(k[1]) for k in keys if k]
                if all(cols) and len({c[0] for c in cols}) == 1:
                    ordered = tables.get(cols[0][0], {}).get('sorted', [])
                    if [c[1] for c in cols] == [s.lower() for s in ordered[:len(cols)]]:
                        uses = uses[:1]
                        replacement = f'IOTA {dest[0]}, {uses[0]}'
        for d in dest:
            loads.pop(d, None)
            writes[d] += 1
        if op == 'LOAD' and re.fullmatch(rf'{REG}\.{REG}', inputs[0]):
            loads[dest[0]] = inputs[0].lower().split('.')
        plan.append((op, dest, uses, line, replacement))
    if not plan or plan[-1][0] != 'OUT' or any(p[0] == 'OUT' for p in plan[:-1]):
        return text
    live, kept, changed = set(), [], False
    for op, dest, uses, line, replacement in reversed(plan):
        # Retain overwrites even when dead: a smaller replacement can release
        # a large old column before the VM checks its register budget.
        if op == 'OUT' or any(d in live or writes[d] > 1 for d in dest):
            live.difference_update(dest)
            live.update(uses)
            kept.append(replacement or line)
            changed |= replacement is not None
        else:
            changed = True
    return '\n'.join(reversed(kept)) + '\n' if changed else text


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('program', type=Path)
    parser.add_argument('schema', type=Path)
    args = parser.parse_args()
    sys.stdout.buffer.write(optimize(args.program.read_bytes().decode(),
                                     json.loads(args.schema.read_bytes())).encode())