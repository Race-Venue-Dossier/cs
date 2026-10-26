"""Daily Dropbox check.

Downloads the shared Dropbox folder (as zip via the shared link), compares every file with data/manifest.json
and handles what is new or changed:

- MBCD survey PDF of a men's SL/GS race (name like 2026-01-11_Adelboden_WC_Men_SL_2Run.pdf)
    -> read automatically, same rules as the original pipeline, stored in data/auto/<SL|GS>/
    -> skipped as 'duplicate' if that race run is already in the data set
- other course documents (GPS sheets / screenshots, Excel, PDFs in another layout)
    -> 'pending': listed on the page and in an issue; they need the OCR + visual check done in a session
- everything else (women's races, videos, timing files, ...) -> 'ignored'

The first run (no manifest yet, or --baseline) records what is there as known: those files are covered
by the base data set built in the workshop. Survey PDFs of a season newer than the base data are still
processed on that run (e.g. a race of the season that has just started), and so is every file changed
in Dropbox after the copy the base data were built from (BASE_SOURCES).

Usage: python build/sync_dropbox.py [--zip local.zip] [--baseline]
Writes data/manifest.json, data/status.json, data/auto/**; prints a summary and, on GitHub,
sets the step outputs `changed`, `pending` and `added`.
"""
import os, sys, io, json, hashlib, zipfile, datetime, unicodedata, tempfile, argparse, urllib.request, traceback

B = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(B); DATA = os.path.join(ROOT, 'data')
sys.path.insert(0, B)
import course

def dropbox_url():
    """shared link of the coach's folder: from DROPBOX_URL or data/config.json (inside the encrypted data store)"""
    u = os.environ.get('DROPBOX_URL') or load(os.path.join(DATA, 'config.json'), {}).get('dropbox_url')
    if not u: raise SystemExit('no Dropbox link: set DROPBOX_URL or dropbox_url in data/config.json')
    return u if 'dl=1' in u else u + ('&' if '?' in u else '?') + 'dl=1'


REVIEW_EXT = {'.jpg', '.jpeg', '.png', '.heic', '.xlsx', '.xls', '.xlsm', '.pdf', '.csv'}
# date of the Dropbox copy the base data set was built from; on the first run, files changed after it are handled as new
BASE_SOURCES = (2026, 10, 8)
SKIP_NAMES = {'.ds_store', 'thumbs.db', 'desktop.ini'}


def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def load(p, default):
    try:
        return json.load(open(p, encoding='utf-8'))
    except FileNotFoundError:
        return default


def save(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=True); f.write('\n')


def download(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'course-setting-sync'})
    with urllib.request.urlopen(req, timeout=600) as r:
        blob = r.read()
    if not blob.startswith(b'PK'):
        raise SystemExit('Dropbox did not return a zip (link changed or folder no longer shared?)')
    return blob


def entries(zf):
    for zi in zf.infolist():
        if zi.is_dir(): continue
        p = unicodedata.normalize('NFC', zi.filename).lstrip('/')
        base = os.path.basename(p)
        if not base or base.lower() in SKIP_NAMES or base.startswith('._') or '__MACOSX' in p: continue
        yield p, zi


def existing_keys():
    K = {'SL': set(), 'GS': set()}
    for d in K:
        for c in load(os.path.join(DATA, 'base', 'courses_%s.json' % d.lower()), []):
            K[d].add(course.key(c))
        for f in os.listdir(os.path.join(DATA, 'auto', d)) if os.path.isdir(os.path.join(DATA, 'auto', d)) else []:
            K[d].add(course.key(load(os.path.join(DATA, 'auto', d, f), None)))
    return K


def sk(season):
    return int(season[:2])


def newest_season():
    S = [c['season'] for d in ('sl', 'gs') for c in load(os.path.join(DATA, 'base', 'courses_%s.json' % d), [])]
    return max(S, key=sk)


def newer_survey(path, newest):
    """survey PDF of a season the base data set does not cover yet (processed even on the first run)"""
    info = course.name_info(path) if path.lower().endswith('.pdf') else None
    return bool(info) and sk(course.season(info['date'])) > sk(newest)


def classify(path, blob, keys):
    """-> (status, note, disc, course or None)"""
    ext = os.path.splitext(path)[1].lower()
    info = course.name_info(path) if ext == '.pdf' else None
    if info:
        if info['gen'] != 'M':
            return 'ignored', "women's race (page covers men only)", None, None
        with tempfile.NamedTemporaryFile(suffix='.pdf') as t:
            t.write(blob); t.flush()
            try:
                gen, disc, c = course.from_pdf(t.name, os.path.basename(path))
            except Exception as e:
                return 'pending', 'survey PDF could not be read automatically: %s' % (str(e) or type(e).__name__)[:160], None, None
        c['file'] = os.path.basename(path)
        if course.key(c) in keys[disc]:
            return 'duplicate', 'race run already in the data set', disc, None
        return 'added', 'read automatically (%d gates, %d regular)' % (len(c['gates']), c['m']['nreg']), disc, c
    if ext in REVIEW_EXT:
        return 'pending', 'needs OCR / visual check in a session', None, None
    return 'ignored', 'not a course document', None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--zip', help='use a local zip instead of downloading')
    ap.add_argument('--baseline', action='store_true', help='record all current files as known, process nothing')
    a = ap.parse_args()

    blob = open(a.zip, 'rb').read() if a.zip else download(dropbox_url())
    zf = zipfile.ZipFile(io.BytesIO(blob))
    man_p = os.path.join(DATA, 'manifest.json'); st_p = os.path.join(DATA, 'status.json')
    man = load(man_p, {}); status = load(st_p, {})
    baseline = a.baseline or not man
    keys = existing_keys(); newest = newest_season()
    t = now(); added = []; new_pending = []; changed = False
    seen = set()
    for path, zi in sorted(entries(zf)):
        seen.add(path)
        data = zf.read(zi); sha = hashlib.sha1(data).hexdigest()
        old = man.get(path)
        if old and old['sha'] == sha:
            continue
        changed = True
        if baseline and not newer_survey(path, newest) and zi.date_time[:3] < BASE_SOURCES:
            man[path] = {'sha': sha, 'status': 'baseline', 'seen': t}
            continue
        try:
            stt, note, disc, c = classify(path, data, keys)
        except Exception:
            stt, note, disc, c = 'pending', 'error while reading: ' + traceback.format_exc().strip().splitlines()[-1][:160], None, None
        if old: note = 'changed in Dropbox; ' + note
        man[path] = {'sha': sha, 'status': stt, 'note': note, 'seen': t}
        if stt == 'added':
            fn = os.path.join(DATA, 'auto', disc, os.path.splitext(os.path.basename(path))[0] + '.json')
            c['dropbox'] = path
            save(fn, c); keys[disc].add(course.key(c))
            man[path]['course'] = os.path.relpath(fn, ROOT)
            added.append(path)
        elif stt == 'pending':
            new_pending.append(path)
    gone = [p for p in man if p not in seen and man[p].get('status') != 'removed']
    for p in gone:
        man[p]['status'] = 'removed'; changed = True
    pending = [{'path': p, 'note': v.get('note', ''), 'seen': v.get('seen')} for p, v in sorted(man.items()) if v['status'] == 'pending']
    status.update({'checked': t, 'files': len(seen), 'pending': pending, 'source': 'dropbox shared folder'})
    if added: status['last_added'] = {'at': t, 'files': added}
    save(man_p, man); save(st_p, status)

    print('files in Dropbox: %d | baseline: %s | added: %d | new pending: %d | pending total: %d | removed: %d'
          % (len(seen), baseline, len(added), len(new_pending), len(pending), len(gone)))
    for p in added: print('  + added   ', p)
    for p in new_pending: print('  ? pending ', p, '-', man[p]['note'])
    gh = os.environ.get('GITHUB_OUTPUT')
    if gh:
        with open(gh, 'a') as f:
            f.write('changed=%s\npending=%d\nadded=%d\nnew_pending=%d\n' % (str(changed or bool(added)).lower(), len(pending), len(added), len(new_pending)))
    # issue text for the files waiting for review
    # public issue text: count only, the file names stay in the encrypted data (listed on the protected page)
    with open(os.path.join(ROOT, 'pending.md'), 'w', encoding='utf-8') as f:
        f.write('%d new file(s) in the Dropbox folder could not be added automatically and wait for the OCR + visual check.\n'
                'The list is at the bottom of the (password protected) page. Updated %s.\n' % (len(pending), t[:10]))


if __name__ == '__main__':
    main()
