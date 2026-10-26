import pdfplumber, re, json, sys, os, glob, collections, logging, math, hashlib
logging.disable(logging.CRITICAL)
TYPES = ('Open', 'Hairpin', 'V.Comb', 'Delayed', 'Finish', 'Start')

def num(t):
    t = t.replace('−', '-')
    try: return float(t)
    except ValueError: return None

def cluster_rows(words, tol=6.0):
    ws = sorted(words, key=lambda w: (w['top'] + w['bottom']) / 2)
    rows = []
    for w in ws:
        c = (w['top'] + w['bottom']) / 2
        if rows and abs(c - rows[-1]['c']) <= tol:
            rows[-1]['w'].append(w); n = len(rows[-1]['w'])
            rows[-1]['c'] = (rows[-1]['c'] * (n - 1) + c) / n
        else:
            rows.append({'c': c, 'w': [w]})
    return rows

def parse_table(page):
    rows = cluster_rows(page.extract_words())
    hdr = next(r for r in rows if {'No', 'Type', 'Distance'} <= {w['text'] for w in r['w']})
    hx = {w['text']: w['x0'] for w in hdr['w']}
    is_sl = 'Width' in hx
    mid = lambda a, b: (hx[a] + hx[b]) / 2
    bounds = [('no', -1), ('dist', mid('Type', 'Distance')), ('offset', mid('Distance', 'Offset')),
              ('pitch', mid('Offset', 'Pitch')), ('angle', mid('Pitch', 'Angle'))]
    if is_sl:
        bounds += [('width', hx['Width'] - 12), ('cdist', (hx['Width'] + hx['Dist']) / 2 + 8)]
    gates = []
    for r in rows:
        if r['c'] <= hdr['c'] + 3: continue
        rec = collections.defaultdict(list); typ = []
        for w in sorted(r['w'], key=lambda w: w['x0']):
            if num(w['text']) is None:
                typ.append(w['text']); continue
            col = 'no'
            for name, b in bounds:
                if w['x0'] >= b: col = name
            rec[col].append(w['text'])
        if not typ or typ[0] not in TYPES: continue   # axis tick rows
        g = {'type': ' '.join(typ)}
        for k in ('no', 'dist', 'offset', 'pitch', 'angle', 'width', 'cdist'):
            v = rec.get(k)
            if v:
                assert len(v) == 1, (k, v, r['c'])
                g[k] = num(v[0])
            else: g[k] = None
        gates.append(g)
    return gates

def parse_plan(page):
    words = page.extract_words()
    marks = []
    for c in page.curves:
        if len(c['pts']) != 18: continue
        col = tuple(round(v, 2) for v in (c.get('non_stroking_color') or ()))
        xs = [p[0] for p in c['pts']]; ys = [p[1] for p in c['pts']]
        marks.append(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, col))
    vl = sorted({round(l['x0'], 2) for l in page.lines if abs(l['x0'] - l['x1']) < 0.01 and abs(l['bottom'] - l['top']) > 300})
    hl = sorted({round(l['top'], 2) for l in page.lines if abs(l['top'] - l['bottom']) < 0.01 and abs(l['x1'] - l['x0']) > 300})
    nums = [(w['x0'], w['x1'], w['top'], num(w['text'])) for w in words if num(w['text']) is not None]
    ymax = max(n[2] for n in nums)
    xt = sorted([(n[0], n[3]) for n in nums if abs(n[2] - ymax) < 4])
    xmin = min(n[1] for n in nums)
    yt = sorted([(n[2], n[3]) for n in nums if abs(n[1] - xmin) < 6 and abs(n[2] - ymax) >= 4])
    return {'marks': marks, 'vl': vl, 'hl': hl, 'xt': xt, 'yt': yt}

def meta_from_name(fn):
    b = os.path.basename(fn)
    m = re.match(r'(\d{4}-\d{2}-\d{2})_(.+?)_(WC|OWG)_(Men|Women)_((?:TC-)?(?:GS|SL))_(\d)Run', b)
    assert m, b
    return {'file': b, 'date': m.group(1), 'venueRaw': m.group(2), 'series': m.group(3),
            'gen': 'M' if m.group(4) == 'Men' else 'W', 'discRaw': m.group(5), 'run': int(m.group(6))}

VENUE = {'Soelden': 'Sölden', 'Val-d-Isere': "Val d'Isère", 'Beaver-Creek': 'Beaver Creek', 'Alta-Badia': 'Alta Badia',
         'Kranjska-Gora': 'Kranjska Gora', 'Madonna-di-Campiglio': 'Madonna di Campiglio', 'Spindleruv-Mlyn': 'Špindlerův Mlýn',
         'Kitzbuhel': 'Kitzbühel', 'Are': 'Åre', 'Copper': 'Copper Mountain', 'Cortina': "Cortina d'Ampezzo"}
NAT = {'Sölden': 'AUT', 'Levi': 'FIN', 'Gurgl': 'AUT', 'Copper Mountain': 'USA', 'Tremblant': 'CAN', 'Beaver Creek': 'USA',
       "Val d'Isère": 'FRA', 'Courchevel': 'FRA', 'Alta Badia': 'ITA', 'Semmering': 'AUT', 'Kranjska Gora': 'SLO',
       'Madonna di Campiglio': 'ITA', 'Adelboden': 'SUI', 'Flachau': 'AUT', 'Wengen': 'SUI', 'Kronplatz': 'ITA',
       'Špindlerův Mlýn': 'CZE', 'Kitzbühel': 'AUT', 'Schladming': 'AUT', 'Bormio': 'ITA', "Cortina d'Ampezzo": 'ITA',
       'Åre': 'SWE', 'Hafjell': 'NOR'}
GREEN = (0.45, 0.77, 0.46); RED = (0.89, 0.29, 0.2)

def build(r, G, pl):
    fin = G[-1]; gates = G[:-1]
    venue = VENUE.get(r['venueRaw'], r['venueRaw'])
    c = {'file': r['file'], 'date': r['date'], 'venue': venue, 'nat': NAT[venue], 'series': r['series'], 'gen': r['gen'],
         'disc': 'SL' if 'SL' in r['discRaw'] else 'GS', 'tc': r['discRaw'].startswith('TC'), 'run': r['run'], 'src': 'pdf'}
    vl, hl = pl['vl'], pl['hl']
    xstep = (pl['xt'][1][1] - pl['xt'][0][1]); ystep = abs(pl['yt'][1][1] - pl['yt'][0][1])
    sx = (vl[1] - vl[0]) / xstep; sy = (hl[1] - hl[0]) / ystep
    assert abs(sx - sy) < 0.01 * sx, (r['file'], sx, sy)
    M = sorted(pl['marks'], key=lambda m: m[1])
    gm = [m for m in M if tuple(m[2]) != GREEN]; gr = [m for m in M if tuple(m[2]) == GREEN]
    assert len(gm) == len(gates) and len(gr) == 2, r['file']
    st, fi = gr[0], gr[1]
    # order gate markers along the course: chain from the start, next gate = marker whose plan distance
    # matches the table distance (projected to the horizontal) best. Sorting by Y fails on traverses.
    Q = [((m[0] - st[0]) / sx, (m[1] - st[1]) / sy, m[2]) for m in gm]
    cur = (0.0, 0.0); chain = []; pool = list(Q)
    for g in gates:
        exp = g['dist'] * math.cos(math.atan((g['pitch'] or 0) / 100))
        nxt = min(pool, key=lambda q: abs(math.hypot(q[0] - cur[0], q[1] - cur[1]) - exp))
        pool.remove(nxt); chain.append(nxt); cur = nxt
    P = [(0.0, 0.0)] + [(q[0], q[1]) for q in chain] + [((fi[0] - st[0]) / sx, (fi[1] - st[1]) / sy)]
    gl = []
    for i, g in enumerate(gates):
        assert g['no'] == i + 1
        d = {'n': i + 1, 't': g['type'], 'd': g['dist'], 'o': g['offset'] if g['offset'] is not None else 0.0,
             'p': g['pitch'] if g['pitch'] is not None else 0.0, 'a': g['angle'] if g['angle'] is not None else 0.0,
             'x': round(P[i + 1][0], 2), 'y': round(P[i + 1][1], 2), 'c': 'r' if tuple(chain[i][2]) == RED else 'b'}
        if g['offset'] is None: d['o0'] = 1
        if g['angle'] is None: d['a0'] = 1
        if g['width'] is not None: d['w'] = g['width']
        if g['cdist'] is not None: d['cd'] = g['cdist']
        gl.append(d)
    c['gates'] = gl
    c['fin'] = {'d': fin['dist'], 'p': fin['pitch'], 'x': round(P[-1][0], 2), 'y': round(P[-1][1], 2)}
    return c

def recon(gates, fin, bearing):
    th = 0.0; x = y = 0.0; P = []
    segs = gates + [fin]
    for i, g in enumerate(segs):
        h = g['d'] * math.sqrt(1 - (g['p'] / 100) ** 2)
        x += h * math.sin(th); y += h * math.cos(th); P.append((x, y))
        if i < len(gates): th -= math.radians(g['a'])
    b = math.atan2(P[-1][0], P[-1][1]); rot = b - bearing
    return [(px * math.cos(rot) - py * math.sin(rot), px * math.sin(rot) + py * math.cos(rot)) for px, py in P]

