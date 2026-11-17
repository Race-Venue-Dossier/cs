"""Exports the reference values of the men's race runs as ref.json (read by the Gate-to-Gate tool, so that both
pages show the same numbers). Read from the built page (_build/page.html), i.e. exactly the values the page shows.

Only aggregated values and one line of key figures per race run are written - no gates, no training courses,
no Dropbox data. Zones: gates by pitch at the gate (flat < 13.5 deg, medium 13.5-18.9, steep 18.9-24, very steep > 24).
"""
import os, sys, json
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, '_build', 'page.html')
OUT = os.path.join(ROOT, 'ref.json')

JS = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'export_ref.js'), encoding='utf-8').read()

with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page()
    pg.goto('file://' + PAGE); pg.wait_for_function('()=>window.__KS&&__KS.all', timeout=30000); pg.wait_for_timeout(300)
    ref = pg.evaluate(JS)
    br.close()

# plausibility: both disciplines, enough runs, no gate data
for d in ('SL', 'GS'):
    r = ref['disc'][d]
    assert r['ref']['n'] >= 10 and len(r['runs']) == r['ref']['n'], (d, r['ref']['n'])
    assert all('gates' not in x for x in r['runs'])
    assert all(r['ref'][k] for k in ('dist', 'off', 'sd', 'comb', 'z0', 'z1', 'z2', 'z3')), d
txt = json.dumps(ref, ensure_ascii=False, separators=(',', ':'))
assert len(txt) < 200_000, len(txt)
old = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
# the time stamp alone is no change: keep the file when the values are the same
strip = lambda t: json.dumps({k: v for k, v in json.loads(t).items() if k != 'updated'}, sort_keys=True) if t else ''
if strip(old) != strip(txt):
    open(OUT, 'w', encoding='utf-8').write(txt + '\n')
    print('ref.json written: SL %d, GS %d race runs' % (ref['disc']['SL']['ref']['n'], ref['disc']['GS']['ref']['n']))
else:
    print('ref.json unchanged')
