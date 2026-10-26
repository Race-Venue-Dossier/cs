"""Password protection for the published page.

The whole page (including all course data) is encrypted with AES-256-GCM; the key is derived from the password
with PBKDF2-SHA256 (600 000 rounds). The published index.html only holds the encrypted page and a small login
screen that decrypts it in the browser (WebCrypto). Without the password nothing of the content can be read,
not even in the page source.

Usage: PAGE_PASSWORD=... python build/encrypt.py [_build/page.html] [index.html]
"""
import os, sys, re, json, base64, secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITER = 600000

src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '_build', 'page.html')
dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'index.html')
pw = os.environ.get('PAGE_PASSWORD', '')
if not pw:
    sys.exit('PAGE_PASSWORD is not set - refusing to publish the page without password protection')

page = open(src, encoding='utf-8').read()
salt = secrets.token_bytes(16); iv = secrets.token_bytes(12)
key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(pw.encode('utf-8'))
ct = AESGCM(key).encrypt(iv, page.encode('utf-8'), None)
b64 = lambda b: base64.b64encode(b).decode()
blob = json.dumps({'s': b64(salt), 'i': b64(iv), 'n': ITER, 'c': b64(ct)})
m = re.search(r'<svg viewBox="[^"]+" role="img" aria-label="Swiss-Ski">.*?</svg>', page, re.S)
logo = m.group(0) if m else '<b>Swiss-Ski</b>'

html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<title>Course Setting Men</title>
<style>
:root{--ink:#14181f;--muted:#6b7785;--line:#e6e9ee;--bg:#f4f6f9;--surface:#fff;--field:#fff;--red:#DA291C;--red-d:#B11E14;
--font:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif}
@media (prefers-color-scheme:dark){:root{--ink:#eef1f6;--muted:#9aa6b4;--line:#39424f;--bg:#1b212b;--surface:#252d39;--field:#1f2630}}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;min-height:100dvh;display:grid;place-items:center;background:var(--bg);color:var(--ink);font-family:var(--font);
-webkit-font-smoothing:antialiased;padding:24px 16px calc(24px + env(safe-area-inset-bottom))}
.box{width:100%;max-width:380px;background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:28px 26px 24px;box-shadow:0 1px 2px rgba(20,24,31,.04),0 8px 24px rgba(20,24,31,.06)}
.logo svg{height:22px;width:auto;display:block}
h1{font-size:19px;margin:18px 0 4px;letter-spacing:-.01em}
p{margin:0 0 18px;color:var(--muted);font-size:13.5px;line-height:1.5}
label{display:block;font-size:11px;font-weight:800;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);margin-bottom:6px}
input[type=password]{width:100%;height:44px;border:1.4px solid var(--line);border-radius:10px;background:var(--field);color:var(--ink);font:16px var(--font);padding:0 12px;outline:none}
input[type=password]:focus{border-color:var(--red)}
.rem{display:flex;align-items:center;gap:8px;margin:12px 0 16px;font-size:13px;font-weight:500;letter-spacing:0;text-transform:none;color:var(--muted);cursor:pointer}
.rem input{width:16px;height:16px;accent-color:var(--red);margin:0}
button{width:100%;height:44px;border:0;border-radius:10px;background:var(--red);color:#fff;font:700 15px var(--font);cursor:pointer}
button:hover{background:var(--red-d)}button:disabled{opacity:.6;cursor:default}
.err{min-height:18px;margin-top:10px;font-size:13px;color:var(--red);font-weight:600}
</style>
</head>
<body>
<form class="box" id="f" autocomplete="on">
  <div class="logo">__LOGO__</div>
  <h1>Course setting · Men</h1>
  <p>Slalom and giant slalom. Please enter the password.</p>
  <label for="pw">Password</label>
  <input type="password" id="pw" name="password" autocomplete="current-password" required autofocus>
  <label class="rem"><input type="checkbox" id="rem" checked> Stay signed in on this device</label>
  <button id="go" type="submit">Open</button>
  <div class="err" id="err" role="alert"></div>
</form>
<script>
var E=__BLOB__,KEY='ks-key-'+E.s;
function u8(b){var s=atob(b),a=new Uint8Array(s.length);for(var i=0;i<s.length;i++)a[i]=s.charCodeAt(i);return a}
function b64(a){var s='';a=new Uint8Array(a);for(var i=0;i<a.length;i++)s+=String.fromCharCode(a[i]);return btoa(s)}
function open_(raw){
  return crypto.subtle.importKey('raw',raw,'AES-GCM',false,['decrypt'])
    .then(function(k){return crypto.subtle.decrypt({name:'AES-GCM',iv:u8(E.i)},k,u8(E.c))})
    .then(function(pt){return new TextDecoder().decode(pt)});
}
function show(h){document.open();document.write(h);document.close()}
function derive(pw){
  return crypto.subtle.importKey('raw',new TextEncoder().encode(pw),'PBKDF2',false,['deriveBits'])
    .then(function(k){return crypto.subtle.deriveBits({name:'PBKDF2',salt:u8(E.s),iterations:E.n,hash:'SHA-256'},k,256)});
}
var f=document.getElementById('f'),err=document.getElementById('err'),go=document.getElementById('go');
if(!window.crypto||!crypto.subtle){err.textContent='This browser cannot open the page (no WebCrypto).';go.disabled=true}
else{
  var saved=null;try{saved=localStorage.getItem(KEY)}catch(e){}
  if(saved)open_(u8(saved)).then(show).catch(function(){try{localStorage.removeItem(KEY)}catch(e){}});
}
f.addEventListener('submit',function(ev){
  ev.preventDefault();err.textContent='';go.disabled=true;go.textContent='Opening…';
  var raw;
  var rem=document.getElementById('rem').checked;
  derive(document.getElementById('pw').value).then(function(r){raw=r;return open_(r)}).then(function(h){
    if(rem){try{localStorage.setItem(KEY,b64(raw))}catch(e){}}
    show(h);
  },function(){
    go.disabled=false;go.textContent='Open';err.textContent='Wrong password.';
    var p=document.getElementById('pw');p.select();
  });
});
</script>
</body>
</html>
'''.replace('__LOGO__', logo).replace('__BLOB__', blob)
open(dst, 'w', encoding='utf-8').write(html)
print('encrypted page written: %s (%d kB)' % (os.path.relpath(dst, ROOT), len(html) // 1024))
