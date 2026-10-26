"""Turn one MBCD survey PDF (men's SL or GS race) into a course record, exactly as the original
build scripts did (sl_races.py / gs_races.py -> sl_build.py / gs_build.py).

Rules kept from the original pipeline:
- figures (hairpin, vertical combination, delay) and gates far outside the normal range never enter
  the values of the regular open gates (see metrics(): only Open gates between Open gates, within
  +/-20 % of the median distance, count as regular)
- GS: a pitch cell left blank in the survey (read as 0) is filled with the mean of its neighbours and flagged
"""
import os, re, math, statistics as st
import ks_lib

RANGE = 0.20
RX = re.compile(r'(\d{4}-\d{2}-\d{2})_(.+?)_+(WC|OWG|WSC)_(Men|Women)_((?:TC-)?(?:SL|GS))_(\d)Run')
VEN = {'Adelbolden-': 'Adelboden', 'Kitzbuehel': 'Kitzbühel', 'Kitzbuhel': 'Kitzbühel', 'WENGEN': 'Wengen',
       'Saalbach-Hinterglem': 'Saalbach', 'Palisades-Tahoe': 'Palisades Tahoe', 'Sun-Valley': 'Sun Valley',
       'Madonna-di-Campiglio': 'Madonna di Campiglio', 'Alta-Badia': 'Alta Badia', 'Val-d-Isere': "Val d'Isère",
       'Kranjska-Gora': 'Kranjska Gora', 'Soelden': 'Sölden', 'Beaver-Creek': 'Beaver Creek',
       'Copper': 'Copper Mountain', 'Are': 'Åre', 'Cortina': "Cortina d'Ampezzo"}
ks_lib.NAT.update({'Adelboden': 'SUI', 'Saalbach': 'AUT', 'Palisades Tahoe': 'USA', 'Sun Valley': 'USA',
                   'Aspen': 'USA', 'Wengen': 'SUI', 'Hafjell': 'NOR'})


def season(date):
    y, m = int(date[:4]), int(date[5:7]); a = y if m >= 7 else y - 1
    return '%02d/%02d' % (a % 100, (a + 1) % 100)


def name_info(fn):
    """None if the file name is not a survey document of the expected form."""
    b = os.path.basename(fn)
    m = RX.match(re.sub(r'(-\d+| \(\d+\))(?=\.pdf$)', '', b, flags=re.I))
    if not m: return None
    disc = 'SL' if 'SL' in m.group(5) else 'GS'
    return {'file': b, 'date': m.group(1), 'venueRaw': VEN.get(m.group(2), m.group(2)), 'series': m.group(3),
            'gen': 'M' if m.group(4) == 'Men' else 'W', 'discRaw': m.group(5), 'disc': disc, 'run': int(m.group(6))}


def metrics(c):
    G = c['gates']; segs = G + ([c['fin']] if c['fin'] else []); m = {}
    m['n'] = len(G); m['len'] = sum(s['d'] for s in segs); m['vd'] = sum(s['d'] * s['p'] / 100 for s in segs)
    m['pitch'] = 100 * m['vd'] / m['len']; m['pmax'] = max(s['p'] for s in segs)
    base = sorted(g['d'] for i, g in enumerate(G) if g['t'] == 'Open' and i > 0 and G[i - 1]['t'] == 'Open')

    def quant(s, q):
        p = (len(s) - 1) * q; i = int(math.floor(p)); f = p - i
        return s[i] * (1 - f) + s[i + 1] * f if i + 1 < len(s) else s[i]
    med = quant(base, .5); lo, hi = med * (1 - RANGE), med * (1 + RANGE); reg = []
    for i, g in enumerate(G):
        ok = (g['t'] == 'Open' and 0 < i < len(G) - 1 and G[i - 1]['t'] == 'Open' and G[i + 1]['t'] == 'Open'
              and lo <= g['d'] <= hi and lo <= G[i + 1]['d'] <= hi and (i <= 1 or lo <= G[i - 1]['d'] <= hi))
        if ok: reg.append(g)
    m['nreg'] = len(reg)
    ds = [g['d'] for g in reg]; os_ = [abs(g['o']) for g in reg]; as_ = [abs(g['a']) for g in reg]
    m['d'] = st.mean(ds); m['dsd'] = st.pstdev(ds); m['dmin'] = min(ds); m['dmax'] = max(ds)
    m['o'] = st.mean(os_); m['omax'] = max(os_); m['a'] = st.mean(as_)
    m['nDel'] = sum(g['t'] == 'Delayed' for g in G); m['nHp'] = sum(g['t'] == 'Hairpin' for g in G) / 2
    runs = 0; k = 0
    for g in G:
        if g['t'] == 'V.Comb': k += 1
        else:
            if k: runs += 1
            k = 0
    if k: runs += 1
    m['nVc'] = runs
    return m


def from_pdf(path, name=None):
    """Course record for the page data set; raises on anything that does not look like an MBCD survey.
    name: the document's original file name when `path` is a temporary copy."""
    import pdfplumber
    info = name_info(name or path)
    assert info, 'file name not recognised'
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages) >= 2, 'expected table page + plan page'
        G = ks_lib.parse_table(pdf.pages[0]); pl = ks_lib.parse_plan(pdf.pages[1])
    assert G and G[-1]['type'] == 'Finish', 'last table row is not the finish'
    ks_lib.VENUE.setdefault(info['venueRaw'], info['venueRaw'])
    ks_lib.NAT.setdefault(ks_lib.VENUE[info['venueRaw']], '')
    c = ks_lib.build(info, G, pl)
    assert c['disc'] == info['disc']
    gates = []
    for g in c['gates']:
        gates.append({'n': g['n'], 't': g['t'], 'd': g['d'], 'o': g['o'], 'p': g['p'], 'a': g['a'], 'x': g.get('x', 0),
                      'y': g.get('y', 0), 'c': g.get('c', 'r'), 'w': g.get('w'), 'cd': g.get('cd'),
                      'fl': (1 if g.get('a0') else 0) | (2 if g.get('o0') else 0)})
    if c['disc'] == 'GS':
        for i in range(1, len(gates) - 1):
            if gates[i]['p'] == 0 and gates[i - 1]['p'] >= 5 and gates[i + 1]['p'] >= 5:
                gates[i]['p'] = round((gates[i - 1]['p'] + gates[i + 1]['p']) / 2, 1); gates[i]['fl'] |= 16
    out = {'kind': 'R', 'season': season(c['date']), 'date': c['date'], 'venue': c['venue'], 'nat': c['nat'],
           'series': c['series'], 'tc': bool(c.get('tc')), 'run': c['run'], 'label': '', 'piste': '', 'setter': '',
           'src': 'M', 'file': c['file'], 'gates': gates, 'fin': c['fin'], 'recon': False}
    out['m'] = metrics(out)
    assert out['m']['nreg'] >= 5, 'too few regular gates to compute values'
    return c['gen'], c['disc'], out


def key(c):
    """identity of a race run, used to avoid double entries"""
    return (c['kind'], c['date'], int(c['run']), bool(c.get('tc')))
