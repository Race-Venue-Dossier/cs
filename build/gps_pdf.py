"""PDF export of the GPS course-setting analysis (training courses, from season 26/27 on).

Page 1 holds a text layer like
    <title> · 28.10.2026
    Course: <title> · 40 Tore            (French export: "· 35 Portes")
    Distanz Offset Winkel Gefälle D Gefälle         (Distance Décalage Angle Pente D pente)
    1 8.87 – – 50.25 –
    2 9.81 2.16 26.81 48.52 0.80
    ...
Pitch is given in % (tangent), angle and offset in the slope, exactly like the GPS sheets the workshop read from
screenshots (layout B). The rows go through the same conversion (gps_course.py) as those sheets.
"""
import os, re, json, math, unicodedata
import gps_course as G
import course

NUM = r'(-?\d+(?:\.\d+)?|–|-)'
# a row: gate number + 5 values; the map legend is sometimes appended to a row ("Drehwinkel [°] Esri World Imagery")
ROW = re.compile(r'^(\d+)\s+' + r'\s+'.join([NUM] * 5) + r'(?:\s.*)?$')
HEAD = re.compile(r'^Course:\s*(.+?)\s*·\s*(\d+)\s*(Tore|Portes|Gates)\b', re.I)
DATE = re.compile(r'·\s*(\d{2})\.(\d{2})\.(\d{4})\s*$')

# venue names as used on the page (+ nation): data/page/venues.json, inside the encrypted data store (it names the
# team's training venues). Unknown venues keep their name from the folder, nation left empty.
_V = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'page', 'venues.json')
VENUES = [tuple(v) for v in json.load(open(_V, encoding='utf-8'))] if os.path.exists(_V) else []


def fnum(t):
    t = t.replace('−', '-')
    return None if t in ('–', '-') else float(t)


def is_gps_pdf_text(text):
    return bool(text) and any(HEAD.match(l.strip()) for l in text.split('\n')[:6])


def venue_of(*names):
    """first name that contains a known venue wins (title before file name before folders:
    a folder name can contain two venues)"""
    for n in names:
        s = unicodedata.normalize('NFC', n).lower()
        for k, v, nat in VENUES:
            if k in s: return v, nat
    return None, ''


def disc_of(title, rows):
    t = ' ' + re.sub(r'[_\-.]', ' ', title.lower()) + ' '
    has = lambda d: re.search(r'(?<![a-z])%s(?![a-z])' % d, t) is not None
    if has('gs') and not has('sl'): return 'GS'
    if has('sl') and not has('gs'): return 'SL'
    ds = sorted(r['d'] for r in rows if r['d'])
    return 'GS' if ds and ds[len(ds) // 2] > 16 else 'SL'


def label_of(title, path):
    s = (title + ' ' + os.path.basename(path)).lower()
    m = re.search(r'(?:sl|gs)\s*([12])\b|\b([12])\s*(?:part|teil|sect|ses)', s)
    if m: return 'Teil %s' % (m.group(1) or m.group(2))
    if re.search(r'\b2\.?\s*(?:sess|session)', s): return '2. Session'
    return ''


def from_pdf(path, rel):
    """-> (disc, course) ; raises when the file is not a readable GPS course-setting export.
    rel: path of the file in Dropbox (folder names help to find venue and label)."""
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        text = '\n'.join((p.extract_text() or '') for p in pdf.pages)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    hm = next((HEAD.match(l) for l in lines[:6] if HEAD.match(l)), None)
    assert hm, 'not a GPS course-setting export'
    title, n_gates = hm.group(1), int(hm.group(2))
    dm = next((DATE.search(l) for l in lines[:3] if DATE.search(l)), None)
    assert dm, 'no date in the header'
    date = '%s-%s-%s' % (dm.group(3), dm.group(2), dm.group(1))
    raw = []
    for l in lines:
        m = ROW.match(l)
        if m:
            n = int(m.group(1)); v = [fnum(x) for x in m.groups()[1:]]
            raw.append((n, v))
    assert [n for n, _ in raw] == list(range(1, len(raw) + 1)), 'rows not numbered 1..N'
    assert len(raw) == n_gates, 'header says %d rows, found %d' % (n_gates, len(raw))
    rows = []
    for n, (d, o, a, s, ds) in raw:
        rows.append({'d': d, 'o': o, 'a': a, 'p': None if s is None else 100 * math.sin(math.atan(s / 100.0))})
    disc = disc_of(title, rows)
    venue, nat = venue_of(title, os.path.basename(rel), *reversed(os.path.dirname(rel).split('/')))
    if not venue:
        venue = re.split(r'[\s_]+', os.path.basename(os.path.dirname(rel)) or title)[0].capitalize()
    gates, fin = G.gps_course(rows, 2, os.path.basename(path), G.infer_types_sl if disc == 'SL' else G.infer_types_gs)
    c = {'kind': 'T', 'season': course.season(date), 'date': date, 'venue': venue, 'nat': nat, 'series': '', 'tc': False,
         'run': 0, 'label': label_of(title, rel), 'piste': '', 'setter': '', 'src': 'G', 'file': os.path.basename(rel),
         'gates': gates, 'fin': fin}
    c['m'] = course.metrics(c)
    assert c['m']['nreg'] >= 5, 'too few regular gates to compute values'
    return disc, c
