"""Common course-setting reference for all three tools (Gate-to-Gate, this course-setting page, Race Venue Dossier).
ref.json gets "sets": one reference per gender | discipline | kind (R = race runs, T = training runs), e.g. "W|SL|R".

Sources (each run counted once, key gender|discipline|date|run):
  1. this page (men's races and trainings, survey PDFs and GPS sheets)          - always first for the men
  2. Race Venue Dossier ksruns.json (key figures per race run, 25/26 with angles) - public, key figures only
  3. Gate-to-Gate kurs/rennkurse.json (race courses incl. new race days)          - figures computed here with metrics()
Same rule for every run as course.metrics(): regular open gates only (open, neighbours open, distance of the gate and its
neighbours within +/-20 % of the course median, offset and angle measured); pitch = vertical drop / course length.
Training runs are published as aggregated values only (no venues, no dates)."""
import json, math, urllib.request

KEYS = ['dist', 'off', 'ang', 'sd', 'pit', 'comb', 'len', 'n', 'z0', 'z1', 'z2', 'z3']
RVD_URL = 'https://race-venue-dossier.github.io/rvd/ksruns.json'
GTG_URL = 'https://gate-to-gate.github.io/gtg-app/kurs/rennkurse.json'


def fetch(url):
    import os
    loc = os.environ.get('REF_LOCAL_' + ('RVD' if 'rvd' in url else 'GTG'))   # local test: read a file instead
    if loc: return json.load(open(loc, encoding='utf-8'))
    try:
        with urllib.request.urlopen(urllib.request.Request(url + '?t=1', headers={'Cache-Control': 'no-cache'}), timeout=30) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        print('  source not reachable:', url, e); return None


def deg(p): return math.degrees(math.atan(max(0.0, float(p or 0)) / 100))
def zone(p):
    d = deg(p); return 0 if d < 13.5 else 1 if d <= 18.9 else 2 if d <= 24 else 3
def quant(s, q):
    p = (len(s) - 1) * q; i = int(math.floor(p)); f = p - i
    return s[i] * (1 - f) + s[i + 1] * f if i + 1 < len(s) else s[i]


def metrics(gates):
    """Gate-to-Gate course (type/dist/offset/pitch/angle) -> key figures, rule of course.metrics()"""
    G = [g for g in gates if g.get('type') != 'Finish']; F = [g for g in gates if g.get('type') == 'Finish'][:1]
    if len(G) < 3: return None
    f = lambda v: None if v is None or v == '' else float(v)
    G = [{'t': g.get('type') or 'Open', 'd': f(g.get('dist')), 'o': f(g.get('offset')), 'a': f(g.get('angle')), 'p': f(g.get('pitch'))} for g in G]
    F = [{'d': f(g.get('dist')), 'p': f(g.get('pitch'))} for g in F]
    segs = G + F; m = {'n': len(G)}
    m['len'] = sum(s['d'] or 0 for s in segs); vd = sum((s['d'] or 0) * (s['p'] or 0) / 100 for s in segs)
    m['pit'] = 100 * vd / m['len'] if m['len'] else None
    base = sorted(g['d'] for i, g in enumerate(G) if g['t'] == 'Open' and i > 0 and G[i - 1]['t'] == 'Open' and g['d'])
    reg = []
    if base:
        med = quant(base, .5); lo, hi = med * .8, med * 1.2; rng = lambda v: v is not None and lo <= v <= hi
        for i, g in enumerate(G):
            if (g['t'] == 'Open' and g['o'] is not None and g['a'] is not None and 0 < i < len(G) - 1 and G[i - 1]['t'] == 'Open'
                    and G[i + 1]['t'] == 'Open' and rng(g['d']) and rng(G[i + 1]['d']) and (i <= 1 or rng(G[i - 1]['d']))): reg.append(g)
    mean = lambda a: sum(a) / len(a) if a else None
    ds = [g['d'] for g in reg]; m['nreg'] = len(reg); m['dist'] = mean(ds)
    m['sd'] = math.sqrt(sum((v - m['dist']) ** 2 for v in ds) / len(ds)) if ds else None
    m['off'] = mean([abs(g['o']) for g in reg]); m['ang'] = mean([abs(g['a']) for g in reg])
    m['comb'] = 100 * sum(1 for g in G if g['t'] != 'Open') / len(G)
    z = [0, 0, 0, 0]
    for g in G:
        if g['p'] is not None: z[zone(g['p'])] += 1
    m.update(z0=z[0], z1=z[1], z2=z[2], z3=z[3])
    return m


def season(d):
    y, mo = int(d[:4]), int(d[5:7]); a = y if mo >= 7 else y - 1; return '%02d/%02d' % (a % 100, (a + 1) % 100)
def r3(v): return None if v is None or not isinstance(v, (int, float)) or not math.isfinite(v) else round(v, 3)


def aggregate(runs, labels=True):
    ref = {'n': len(runs)}
    lab = lambda r: '%s %s · L%s' % (r.get('venue', ''), str(r.get('date', ''))[:4], r.get('run'))
    for k in KEYS:
        pr = [r for r in runs if r.get(k) is not None]
        if not pr: ref['nG' if k == 'n' else k] = None; continue
        mi = min(pr, key=lambda r: r[k]); ma = max(pr, key=lambda r: r[k])
        ref['nG' if k == 'n' else k] = {'avg': r3(sum(r[k] for r in pr) / len(pr)), 'min': r3(mi[k]), 'max': r3(ma[k]), 'n': len(pr)}
        if labels: ref['nG' if k == 'n' else k].update(minL=lab(mi), maxL=lab(ma))
    ss = sorted(r['season'] for r in runs if r.get('season'))
    if ss: ref['from'], ref['to'] = ss[0], ss[-1]
    return ref


def build(ref, train):
    """ref: the existing ref.json dict (men's race runs of this page in ref['disc']); train: {disc: [key figures]} of this page's trainings"""
    rvd = fetch(RVD_URL) or {}; gtg = fetch(GTG_URL) or {}
    runs = {}   # gen|disc -> {date|run: run}
    src_n = {'cs': 0, 'rvd': 0, 'gtg': 0}
    def put(gen, disc, r, src):
        if r is None: return
        b = runs.setdefault(gen + '|' + disc, {}); k = '%s|%s' % (r['date'], int(r['run']))
        if k in b:   # run already there: only fill missing values (e.g. angles of GS 25/26)
            for x in KEYS:
                if b[k].get(x) is None and r.get(x) is not None: b[k][x] = r[x]
            return
        o = {'date': r['date'], 'run': int(r['run']), 'venue': r.get('venue', ''), 'season': r.get('season') or season(r['date']), 'src': src}
        for x in KEYS + ['nreg']: o[x] = r3(r.get(x)) if isinstance(r.get(x), float) else r.get(x)
        b[k] = o; src_n[src] += 1
    for d, D in (ref.get('disc') or {}).items():
        for r in D.get('runs') or []: put('M', d, r, 'cs')
    for r in (rvd.get('runs') or []): put(r['gen'], r['disc'], r, 'rvd')
    for c in (gtg.get('courses') or []):
        m = metrics(c.get('gates') or [])
        if m: m.update(date=c['date'], run=c['run'], venue=c.get('venue', '')); put(c['gen'], c['disc'], m, 'gtg')
    sets = {}
    for key, b in sorted(runs.items()):
        L = sorted(b.values(), key=lambda r: (r['date'], r['run']))
        sets[key + '|R'] = {'ref': aggregate(L), 'runs': L}
    for d, T in (train or {}).items():
        if T: sets['M|%s|T' % d] = {'ref': aggregate(T, labels=False)}   # trainings: aggregated values only
    print('  sets:', ', '.join('%s %d' % (k, v['ref']['n']) for k, v in sets.items()), '| new runs from', src_n)
    return sets
