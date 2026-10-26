# Course setting – men's slalom and giant slalom

Interactive analysis of course settings (Swiss-Ski FEA). The page is `index.html`, published with GitHub Pages
and updated every morning from the coach's shared Dropbox folder.

## How the daily update works

`.github/workflows/update.yml` runs every day (and on demand via *Actions → Daily Dropbox update → Run workflow*).
It first opens the encrypted data store (`data.enc` → `data/`, see below), then:

1. `build/sync_dropbox.py` downloads the shared Dropbox folder and compares it with `data/manifest.json`.
   - **Survey PDFs (MBCD)** of men's SL/GS races, named like `2026-01-11_Adelboden_WC_Men_SL_2Run.pdf`, are read
     automatically with the same rules as the original pipeline (figures and gates far outside the normal range
     never count as regular open gates) and stored in `data/auto/SL|GS/`. A race run that is already in the
     data set is skipped as `duplicate`.
   - **GPS sheets / screenshots / Excel / other PDFs** are marked `pending`: the page lists them at the bottom as
     "under review"; the issue *Dropbox files under review* only gives the number. They need the OCR + visual check
     done in a working session; afterwards set their status in `data/manifest.json` to `reviewed`.
   - Women's races, videos and other files are `ignored`.
2. `build/build_page.py` builds the page (`_build/page.html`) from `data/base/` (the data set from the workshop, including all
   manual corrections), `data/auto/` and `data/status.json`.
3. `build/check_page.py` opens the page in a browser (both disciplines, every tab, desktop and phone width);
   `build/encrypt.py` encrypts it into `index.html`, which is tested again with the password.
   If anything fails, nothing is published and the current page stays online.
4. `data/` is encrypted again into `data.enc`; `data.enc` and `index.html` are committed; GitHub Pages serves `index.html`.

## Password

The published page is encrypted (AES-256-GCM, key from the password via PBKDF2-SHA256, 600 000 rounds) by
`build/encrypt.py`; the browser decrypts it after the password is entered ("stay signed in" keeps the derived key
in that browser). The password is never in the repository: the daily run reads it from the Actions secret
`PAGE_PASSWORD` (Settings → Secrets and variables → Actions). Without the secret the run stops before publishing.
A push of `index.html` publishes the committed (already encrypted) file as it is.

## Encrypted data

The repository is public, so no data is stored in readable form. Course data, the page template and texts, the Dropbox file
list and the Dropbox link (`data/config.json`) exist in the repository only as `data.enc` (tar.gz of `data/`, AES-256-GCM,
key from `PAGE_PASSWORD`). `data/` is in `.gitignore`. To work on the data locally:
`PAGE_PASSWORD=... python build/vault.py unlock`, and `... lock` before committing.

## Files

| Path | What |
|---|---|
| `index.html` | the published page, encrypted (English, self-contained, also works offline) |
| `data.enc` | everything below `data/`, encrypted |
| `data/base/` | courses and method figures from the workshop (`Werkstatt.zip`), frozen |
| `data/auto/` | courses added automatically from new survey PDFs |
| `data/manifest.json` | every Dropbox file with checksum and status (`baseline`, `added`, `duplicate`, `pending`, `reviewed`, `ignored`, `removed`) |
| `data/status.json` | last check and files under review (shown on the page) |
| `data/page/` | page template, page modules (`js/`) and English texts (`i18n_all_en.py`) – encrypted, they name training venues and dates |
| `build/` | build, sync, encryption and test scripts |

The Dropbox link is in `data/config.json` (encrypted; or set the `DROPBOX_URL` environment variable).
The full workshop (OCR scripts for GPS sheets, German page) is in `Werkstatt.zip` in the project folder on OneDrive.

## Local

```
pip install -r build/requirements.txt && python -m playwright install chromium
export PAGE_PASSWORD=...
python build/vault.py unlock
python build/sync_dropbox.py          # or --zip folder.zip
python build/build_page.py && python build/check_page.py
python build/encrypt.py && python build/check_page.py --encrypted
python build/vault.py lock
```
