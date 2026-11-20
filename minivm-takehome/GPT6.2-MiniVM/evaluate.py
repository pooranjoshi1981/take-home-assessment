"""Differential evaluator. Uses the supplied MiniVM as the reference interpreter."""
import argparse
import asyncio
import json
import os
import re
import signal
import shutil
import sys
import tempfile
import time
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / 'examples'
VM = ROOT / 'bin' / ('minivm-windows-x86_64.exe' if os.name == 'nt' else 'minivm')
MIB = 1024 ** 2
TYPES = ['INT INT INT STR', 'INT INT INT', 'INT STR INT', 'NUM INT',
         'STR NUM', 'INT NUM INT', 'INT NUM STR', 'STR INT INT']


def tables(rows, keys=(1, 1, 2, None)):
    columns = [dict(name=n, type=t) for n, t in zip(('id', 'amt', 'tag'), ('INT', 'NUM', 'STR'))]
    return {'sales': dict(columns=columns, key=['id'], rows=rows),
            'lookup': dict(columns=[dict(name='k', type='INT')], rows=[[k] for k in keys])}


def cases(tmp, schema):
    for i, types in enumerate(TYPES, 1):
        name = f'q{i:04}'
        yield name, types.split(), True, EX/'programs'/f'{name}.mini', EX/'data.json', EX/'schema.json'
    varied = tables([[1, '90.00', '01'], [2, '130.00', '1'], [3, '130.0', '001'], [4, None, None]])
    filtered = 'LOAD a, sales.amt\nGT mask, a, 100.00\nIDX ix, mask\nGATHER a, a, ix\nOUT a'
    for name, types, ordered, data, program in [
        ('stale-min', ['NUM'], False, varied, filtered),
        ('empty', ['NUM'], False, tables([], []), filtered),
        ('join-bag', ['STR'], False, varied, 'LOAD a, sales.id\nLOAD b, lookup.k\nHJOIN l, r, a, b\nLOAD t, sales.tag\nGATHER t, t, l\nOUT t'),
        ('stable-ties', ['STR', 'NUM'], True, varied, 'LOAD a, sales.amt\nLOAD t, sales.tag\nSORT i, a DESC NL\nGATHER t, t, i\nGATHER a, a, i\nOUT t, a'),
    ]:
        src, dataset = tmp/f'{name}.mini', tmp/f'{name}.json'
        src.write_text(program + '\n', encoding='utf8')
        dataset.write_text(json.dumps(data), encoding='utf8')
        yield name, types, ordered, src, dataset, schema


def equal(a, b, kind):
    if kind not in ('NUM', 'INT') or a is None or b is None:
        return type(a) is type(b) and a == b
    if not all(type(v) in (str, int) and re.fullmatch(r'-?[0-9]{1,40}(?:\.[0-9]{1,28})?', str(v)) for v in (a, b)):
        return False
    x, y = Fraction(a), Fraction(b)
    return abs(x - y) * 1_000_000 <= abs(x)


def compare(ref, got, types, ordered):
    for obj in (ref, got):
        if not (isinstance(obj, dict) and type(obj.get('ncols')) is int and obj['ncols'] == len(types)
                and type(obj.get('cycles')) is int and obj['cycles'] >= 0 and isinstance(obj.get('rows'), list)
                and all(isinstance(r, list) and len(r) == len(types) for r in obj['rows'])):
            raise ValueError('invalid MiniVM result shape or cycles')
    left, right = ref['rows'], got['rows']
    if len(left) != len(right):
        raise ValueError(f'expected {len(left)} rows, got {len(right)}')

    def match(i, j):
        return all(equal(a, b, t) for a, b, t in zip(left[i], right[j], types))

    # For the tiny unordered fixtures, find a bijection, not a greedy match:
    # two distinct reference values may have overlapping tolerance intervals.
    owners = {}

    def assign(i, seen):
        for j in range(len(right)):
            if j not in seen and match(i, j):
                seen.add(j)
                if j not in owners or assign(owners[j], seen):
                    owners[j] = i
                    return True
        return False

    for i in range(len(left)):
        if not (match(i, i) if ordered else assign(i, set())):
            raise ValueError(f'row {i}: no match for {left[i]!r}')


async def execute(command, args, timeout, cap):
    # Windows CreateProcess does not dispatch POSIX shebang scripts. Git Bash
    # supplies sh on PATH when running the assignment's two shell entry points.
    if os.name == 'nt' and Path(command).is_file() and not Path(command).suffix:
        with Path(command).open('rb') as script:
            if script.readline(128).strip() == b'#!/bin/sh':
                args = (command, *args)
                command = shutil.which('sh') or 'sh'
    proc = await asyncio.create_subprocess_exec(command, *args, stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, start_new_session=os.name == 'posix')
    size = 0

    async def read(stream):
        nonlocal size
        buf = bytearray()
        while chunk := await stream.read(65536):
            size += len(chunk)
            if size > cap:
                raise ValueError('subprocess output limit exceeded')
            buf.extend(chunk)
        return bytes(buf)

    try:
        out, err, code = await asyncio.wait_for(asyncio.gather(read(proc.stdout), read(proc.stderr), proc.wait()), timeout)
    except (TimeoutError, asyncio.TimeoutError, ValueError) as exc:
        try:
            if os.name == 'posix':
                os.killpg(proc.pid, signal.SIGKILL)
            else:
                proc.kill()
        except ProcessLookupError:
            pass
        if isinstance(exc, ValueError):
            raise
        raise ValueError('subprocess timeout') from exc
    return code, out, err


def checked(result):
    code, out, err = result
    if code:
        raise ValueError(f'exit {code}: {err[:500].decode(errors="replace")}')
    return out


async def evaluate(optimizer, run=execute, log=print, now=time.monotonic):
    end = now() + 119

    async def call(cmd, args, seconds, cap):
        remaining = end - now()
        if remaining <= 0:
            raise ValueError('total deadline exceeded')
        return await run(cmd, args, min(seconds, remaining), cap)

    async def vm(*args):
        return await call(VM, args, 10, 16*MIB)

    passed = skipped = saved = 0
    stage = 'schema setup'
    with tempfile.TemporaryDirectory(prefix='minivm-eval-') as folder:
        tmp = Path(folder)
        try:
            sample, schema = tmp/'sample.json', tmp/'edge-schema.json'
            sample.write_text(json.dumps(tables([[1, '120.00', '01'], [2, '150.00', '1']])), encoding='utf8')
            schema.write_bytes(checked(await vm('--schema', sample)))
            for name, types, ordered, src, data, sch in cases(tmp, schema):
                stage = f'{name} reference'
                original = await vm(src, data)
                if original[0] == 1:
                    log(f'SKIP {stage}: {original[2][:500].decode(errors="replace")}')
                    skipped += 1
                    continue
                ref = json.loads(checked(original))
                if src.parent == EX/'programs':
                    compare(json.loads((EX/'expected'/f'{name}.json').read_bytes()), ref, types, ordered)
                stage = f'{name} optimizer'
                rewrite = checked(await call(optimizer, (src, sch), 1, 5*MIB))
                if len(rewrite) > 4*MIB:
                    raise ValueError('program exceeds 4 MiB')
                stage = f'{name} candidate'
                candidate = tmp/f'{name}-candidate.mini'
                candidate.write_bytes(rewrite)
                got = json.loads(checked(await vm(candidate, data)))
                compare(ref, got, types, ordered)
                delta = ref['cycles'] - got['cycles']
                saved += delta
                passed += 1
                log(f"PASS {name}; cycles {ref['cycles']} -> {got['cycles']}; saved {delta}")
            if not passed or now() >= end:
                raise ValueError('no successful reference runs or total deadline exceeded')
            log(f'Correctness: {passed} passed, {skipped} skipped. Net cycles saved: {saved}.')
        except (OSError, ValueError) as exc:
            raise ValueError(f'{stage}: {exc}') from exc


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('optimizer', type=Path)
    try:
        asyncio.run(evaluate(parser.parse_args().optimizer.resolve()))
    except ValueError as error:
        sys.exit(str(error))