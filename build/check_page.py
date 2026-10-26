"""Smoke test of the page before it is published: both disciplines, every tab, phone and desktop width.
Fails on any script error, on a tab that draws nothing, or when the page shows a different number of
courses than the data set holds."""
import os, sys, json, glob
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA = os.path.join(ROOT, 'data')
want = {d: len(json.load(open(DATA + '/base/courses_%s.json' % d.lower()))) + len(glob.glob(DATA + '/auto/%s/*.json' % d))
        for d in ('SL', 'GS')}
errors = []; problems = []
# default: the plain page from build_page.py; with --encrypted: index.html, opened with PAGE_PASSWORD
ENC = '--encrypted' in sys.argv
PAGE = 'index.html' if ENC else os.path.join('_build', 'page.html')
PW = os.environ.get('PAGE_PASSWORD', '') if ENC else ''
if ENC and not PW: sys.exit('PAGE_PASSWORD not set')
with sync_playwright() as p:
    br = p.chromium.launch()
    for vw in (1400, 390):
        pg = br.new_page(viewport={'width': vw, 'height': 900})
        pg.on('pageerror', lambda e: errors.append('%dpx: %s' % (vw, e)))
        pg.on('console', lambda m: m.type == 'error' and errors.append('%dpx console: %s' % (vw, m.text)))
        pg.goto('file://' + os.path.join(ROOT, PAGE)); pg.wait_for_timeout(600)
        if PW:
            if not pg.locator('#pw').count(): problems.append('%dpx: no password form' % vw)
            if 'course' in (pg.content().lower().split('<script>')[0]) and pg.evaluate('()=>typeof __KS') != 'undefined':
                problems.append('%dpx: page readable without password' % vw)
            pg.fill('#pw', 'wrong-' + PW); pg.click('#go'); pg.wait_for_timeout(2500)
            if pg.evaluate("()=>document.getElementById('err')&&document.getElementById('err').textContent") != 'Wrong password.':
                problems.append('%dpx: wrong password not rejected' % vw)
            pg.fill('#pw', PW); pg.click('#go')
            pg.wait_for_function('()=>window.__KS', timeout=30000); pg.wait_for_timeout(600)
        tabs = pg.eval_on_selector_all('.tabs .tab', 'b=>b.map(x=>x.dataset.tab||x.getAttribute("data-t")||x.textContent.trim())')
        n_tabs = pg.eval_on_selector_all('.tabs .tab', 'b=>b.length')
        for d in ('SL', 'GS'):
            pg.evaluate('d=>__KS.setDisc(d)', d); pg.wait_for_timeout(200)
            have = pg.evaluate('()=>__KS.courses.length')
            if have != want[d]: problems.append('%dpx %s: page has %d courses, data %d' % (vw, d, have, want[d]))
            for i in range(n_tabs):
                pg.locator('.tabs .tab').nth(i).click(); pg.wait_for_timeout(250)
                svgs = pg.evaluate('()=>document.querySelectorAll(".page svg").length')
                if svgs < 2: problems.append('%dpx %s tab %d (%s): nothing drawn' % (vw, d, i, tabs[i] if i < len(tabs) else '?'))
        if vw == 390:
            over = pg.evaluate('()=>document.documentElement.scrollWidth-window.innerWidth')
            if over > 2: problems.append('390px: page scrolls sideways by %dpx' % over)
        pg.close()
    br.close()
for e in errors: print('ERROR', e)
for q in problems: print('PROBLEM', q)
print('checked%s: SL %d, GS %d courses, %d tabs' % (' (encrypted, opened with password)' if ENC else '', want['SL'], want['GS'], n_tabs))
sys.exit(1 if errors or problems else 0)
