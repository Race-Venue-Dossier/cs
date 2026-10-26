"""Encrypted data store.

Everything in data/ (course data, Dropbox file list and status, and the Dropbox link in data/config.json) is kept
in the repository only as data.enc: a tar.gz of data/, encrypted with AES-256-GCM, key from PAGE_PASSWORD via
PBKDF2-SHA256 (600 000 rounds). data/ itself is never committed (.gitignore).

  PAGE_PASSWORD=... python build/vault.py unlock   # data.enc -> data/
  PAGE_PASSWORD=... python build/vault.py lock     # data/ -> data.enc
"""
import os, sys, io, tarfile, secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data'); VAULT = os.path.join(ROOT, 'data.enc')
MAGIC = b'KSV1'; ITER = 600000


def key(pw, salt):
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(pw.encode('utf-8'))


def lock(pw):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as t:
        for r, ds, fs in os.walk(DATA):
            ds.sort()
            for f in sorted(fs):
                p = os.path.join(r, f); a = os.path.relpath(p, ROOT)
                ti = t.gettarinfo(p, a); ti.mtime = 0; ti.uid = ti.gid = 0; ti.uname = ti.gname = ''
                with open(p, 'rb') as fh: t.addfile(ti, fh)
    salt = secrets.token_bytes(16); iv = secrets.token_bytes(12)
    blob = MAGIC + salt + iv + AESGCM(key(pw, salt)).encrypt(iv, buf.getvalue(), MAGIC)
    open(VAULT, 'wb').write(blob)
    print('locked data/ -> data.enc (%d kB)' % (len(blob) // 1024))


def unlock(pw):
    blob = open(VAULT, 'rb').read()
    assert blob[:4] == MAGIC, 'data.enc: unknown format'
    salt, iv, ct = blob[4:20], blob[20:32], blob[32:]
    try:
        raw = AESGCM(key(pw, salt)).decrypt(iv, ct, MAGIC)
    except Exception:
        sys.exit('data.enc: wrong password (secret PAGE_PASSWORD)')
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as t:
        for m in t.getmembers():
            assert m.isfile() and m.name.startswith('data/') and '..' not in m.name.split('/'), m.name
        t.extractall(ROOT, filter='data')
    print('unlocked data.enc -> data/')


if __name__ == '__main__':
    pw = os.environ.get('PAGE_PASSWORD', '')
    if not pw: sys.exit('PAGE_PASSWORD is not set')
    {'lock': lock, 'unlock': unlock}[sys.argv[1]](pw)
