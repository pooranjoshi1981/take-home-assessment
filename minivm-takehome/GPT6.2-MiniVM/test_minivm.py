import asyncio
import json
import subprocess
import sys
import unittest
from pathlib import Path

import evaluate as ev
from optimize import optimize


def result(rows, width=1):
    return dict(rows=rows, ncols=width, cycles=50)


class ComparisonTests(unittest.TestCase):
    def test_numeric(self):
        for a, b, good in [('-100', '-100.0001', True), ('100', '100.00010000000000000000000001', False),
                           (0, '-0.000', True), (0, '0.0000000000000000000000000001', False),
                           ('0.00001', '0.00001001', False), (None, 0, False), (1, True, False),
                           (10**20, str(10**20+1), True)]:
            self.assertEqual(ev.equal(a, b, 'NUM'), good)

    def test_shape_and_spelling(self):
        for a, b in [(result([['01']]), result([['1']])), (result([]), result([], 2)),
                     (result([['x']]), result([[]]))]:
            with self.assertRaises(ValueError):
                ev.compare(a, b, ['STR'], True)
        with self.assertRaises(ValueError):
            ev.compare(result([['a','b']], 2), result([['b','a']], 2), ['STR','STR'], True)

    def test_multiset(self):
        ev.compare(result([['x'], ['x'], ['y']]), result([['y'], ['x'], ['x']]), ['STR'], False)
        ev.compare(result([['1.0000005'], ['1']]), result([['1'], ['1.0000014']]), ['NUM'], False)
        with self.assertRaises(ValueError):
            ev.compare(result([['x'], ['x'], ['y']]), result([['x'], ['y'], ['y']]), ['STR'], False)


class DriverTests(unittest.IsolatedAsyncioTestCase):
    async def drive(self, fault=None):
        logs, originals = [], {}
        edges = {'empty': result([]), 'stale-min': result([['130.00'], ['130.0']]),
                 'join-bag': result([['01'], ['01'], ['1']]),
                 'stable-ties': result([['1','130.00'], ['001','130.0'], ['01','90.00'], [None,None]], 2)}

        async def run(cmd, args, timeout, cap):
            file, arg = args
            if file == '--schema':
                self.assertEqual(json.loads(arg.read_bytes())['sales']['rows'][0][1], '120.00')
                self.tmp = arg.parent
                return 0, b'{"sample_min":120}', b''
            name = file.stem.removesuffix('-candidate')
            if cmd == 'optimizer':
                self.assertEqual(timeout, 1)
                if name == 'stale-min':
                    self.assertEqual(json.loads(arg.read_bytes())['sample_min'], 120)
                return 0, file.read_bytes(), b''
            self.assertEqual(timeout, 10)
            expected = edges.get(name) or json.loads((ev.EX/'expected'/f'{name}.json').read_bytes())
            if file.stem == name:
                originals[name] = file.read_bytes(), arg
                if fault == 'reference' and name == 'q0001':
                    return 1, b'', b'VM error'
            else:
                self.assertEqual((file.read_bytes(), arg), originals[name])
                expected = dict(expected, cycles=expected['cycles'] + 1)
                if fault == name:
                    if name == 'empty':
                        return 1, b'', b'VM error'
                    if name == 'stable-ties':
                        expected['rows'] = expected['rows'][::-1]
                    elif name == 'join-bag':
                        expected['rows'] = expected['rows'][1:]
                    else:
                        expected['rows'] = [[r[1]] for r in json.loads(arg.read_bytes())['sales']['rows']]
            return 0, json.dumps(expected).encode(), b''

        try:
            await ev.evaluate('optimizer', run, logs.append)
        finally:
            self.assertFalse(self.tmp.exists())
        return logs[-1]

    async def test_identity_and_skip(self):
        self.assertIn('12 passed, 0 skipped. Net cycles saved: -12', await self.drive())
        self.assertIn('11 passed, 1 skipped', await self.drive('reference'))

    async def test_defects(self):
        for fault in ('empty', 'stale-min', 'join-bag', 'stable-ties'):
            with self.assertRaisesRegex(ValueError, fault+' candidate'):
                await self.drive(fault)

    async def test_deadline(self):
        times = iter((0, 118.75, 119))

        async def run(cmd, args, seconds, cap):
            self.assertEqual(seconds, 0.25)
            return 0, b'{}', b''
        with self.assertRaisesRegex(ValueError, 'deadline'):
            await ev.evaluate('optimizer', run=run, now=times.__next__)

    async def test_real_process(self):
        async def child(code, timeout, cap):
            return await ev.execute(sys.executable, ['-c', code, 'a b'], timeout, cap)
        self.assertEqual((await child('import sys;print(sys.argv[1])', 3, 100))[1].strip(), b'a b')
        with self.assertRaisesRegex(ValueError, 'timeout'):
            await child('import time;time.sleep(5)', .15, 100)
        with self.assertRaisesRegex(ValueError, 'output limit'):
            await child('print("x"*101)', 3, 100)
        self.assertEqual(subprocess.run([sys.executable, ev.__file__], capture_output=True).returncode, 2)


class OptimizerTests(unittest.TestCase):
    def test_quoted_and_reassigned(self):
        text = "LOAD a, t.id\nLOAD dead, t.id\nCAT a, a, 'a; it''s, b'\nOUT a, a\n"
        self.assertEqual(optimize(text, {}), text.replace('LOAD dead, t.id\n', ''))

    def test_declared_order_not_stats(self):
        text = 'LOAD a, T.Id\nSORT i, a ASC NF\nOUT i\n'
        self.assertEqual(optimize(text, {'t': {'sorted': ['ID']}}), text.replace('SORT i, a ASC NF', 'IOTA i, a'))
        self.assertEqual(optimize(text, {'t': {'stats': {'sorted': ['id']}}}), text)

    def test_unknown_passthrough(self):
        text = 'LOAD unused, t.id\nFUTURE a, unused\nOUT a\n'
        self.assertEqual(optimize(text, {}), text)