import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codex_cockpit import collector as c, panel, pricing, config, stats
from codex_cockpit.sessions import _is_codex


def row(kind, payload, stamp='2026-09-10T12:00:00Z'):
    return {'type': kind, 'timestamp': stamp, 'payload': payload}


def usage(inp=1000, out=100, cached=400, write=0, **extra):
    totals = dict(input_tokens=inp, output_tokens=out, cached_input_tokens=cached,
                  cache_write_input_tokens=write, reasoning_output_tokens=50)
    return row('event_msg', dict(type='token_count', info={
        'total_token_usage': totals, 'last_token_usage': totals,
        'model_context_window': 10000}, **extra))


class CodexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        for module, name, value in (
            (c, 'CODEX_DIR', root / 'codex'), (c, 'DATA_DIR', root / 'data'),
            (c, 'EVENTS_FILE', root / 'data/events.ndjson'),
            (c, 'STATE_FILE', root / 'data/state.json'),
            (panel, 'DATA_DIR', root / 'data'), (panel, 'SNAPSHOT', root / 'data/panel.json'),
            (panel, 'HISTORY', root / 'data/panel-history.ndjson'),
            (config, 'CONFIG_FILE', root / 'config.json'),
        ):
            p = patch.object(module, name, value); p.start(); self.addCleanup(p.stop)
        self.ctx = {}
        self.meta = row('session_meta', {'id': 'session-a', 'cwd': '/project', 'source': 'cli'})
        self.turn = row('turn_context', {'model': 'gpt-5.3-codex', 'effort': 'high'})
        c.parse_row(self.meta, self.ctx); c.parse_row(self.turn, self.ctx)

    def test_cache_and_reasoning_not_double_counted(self):
        e = c.parse_row(usage(write=100), self.ctx)
        self.assertEqual((e.i, e.r, e.cw, e.o, e.tokens), (500, 400, 100, 100, 1100))
        self.assertIsNone(c.parse_row(usage(write=100), self.ctx))
        self.assertEqual(c.parse_row(usage(1500, 200, 500, 150), self.ctx).tokens, 600)

    def test_incremental_partial_archive_and_truncate(self):
        path = c.CODEX_DIR / 'sessions/2026/test.jsonl'
        path.parent.mkdir(parents=True)
        prefix = '\n'.join(json.dumps(d) for d in (self.meta, self.turn, usage())) + '\n'
        path.write_text(prefix + json.dumps(usage(1500, 200, 500)))
        self.assertEqual(c.refresh()[1], 1)
        self.assertEqual(c.refresh()[1], 0)
        with path.open('a') as f: f.write('\n')
        events, new = c.refresh()
        self.assertEqual(new, 1)
        self.assertEqual(sum(e.tokens for e in events), 1700)
        self.assertEqual(events[-1].m, 'gpt-5.3-codex')
        archived = c.CODEX_DIR / 'archived_sessions/a.jsonl'
        archived.parent.mkdir(); path.rename(archived)
        self.assertEqual(c.refresh()[1], 0)
        archived.write_text(prefix)
        self.assertEqual(c.refresh()[1], 0)

    def test_weekly_primary_and_stale_observation(self):
        payload = usage(rate_limits={'primary': {'window_minutes': 10080,
            'used_percent': 23, 'resets_at': 9999999999}})['payload']
        panel.record_codex(payload, self.ctx, 200)
        payload['rate_limits']['primary']['used_percent'] = 80
        panel.record_codex(payload, self.ctx, 100)
        self.assertEqual(panel.window('week', now=300)['pct'], 23)
        self.assertIsNone(panel.window('block', now=300))
        self.assertIsNone(panel.window('week', now=10000000000))
        self.assertEqual(panel.contexts()['session-a']['context_pct'], 11)

    def test_rate_only_event_does_not_emit_usage(self):
        c.parse_row(usage(), self.ctx)
        before = panel.contexts()
        self.assertIsNone(c.parse_row(row('event_msg', {'type':'token_count', 'info':None}), self.ctx))
        self.assertEqual(panel.contexts(), before)

    def test_unknown_models_and_custom_price(self):
        self.assertIsNone(pricing.resolve('gpt-future'))
        config.CONFIG_FILE.write_text(json.dumps({'model_prices': {'gpt-future': {
            'input':2, 'output':10, 'cached_input':0.2}}}))
        self.assertAlmostEqual(pricing.cost('gpt-future', 1000000, 0, 0, 0), 2)

    def test_process_detection(self):
        self.assertTrue(_is_codex(['/bin/codex']))
        self.assertFalse(_is_codex(['python', 'codex-cockpit']))
        self.assertFalse(_is_codex(['sh', '-c', 'codex']))

    def test_namespaces_are_independent(self):
        self.assertEqual(config.CONFIG_DIR.name, 'codex-cockpit')
        self.assertEqual(config.DEFAULTS['dashboard_port'], 8766)
        self.assertIn('-m codex_cockpit', Path('install.sh').read_text())
        self.assertNotIn('cc-cockpit', Path('install.sh').read_text())

    def test_model_change_and_counter_reset(self):
        c.parse_row(usage(), self.ctx)
        c.parse_row(row('turn_context', {'model':'gpt-5.5', 'effort':'low'}), self.ctx)
        e = c.parse_row(usage(2000, 200, 800), self.ctx)
        self.assertEqual((e.m, e.ef, e.tokens), ('gpt-5.5', 'low', 1100))
        self.assertEqual(c.parse_row(usage(100, 10, 20), self.ctx).tokens, 110)
        self.assertIsNone(c.parse_row([], self.ctx))
        self.assertIsNone(c.parse_row(row('event_msg', []), self.ctx))

    def test_bucket_preserves_tokens(self):
        e = c.parse_row(usage(), self.ctx)
        b = stats.Bucket(); b.add(e)
        self.assertEqual(b.as_dict()['tokens'], 1100)
        self.assertEqual(b.as_dict()['cache_hit_pct'], 40)


if __name__ == '__main__':
    unittest.main()
