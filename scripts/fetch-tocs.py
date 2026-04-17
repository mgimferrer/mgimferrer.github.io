#!/usr/bin/env python3
"""
Download TOC (graphical abstract) images for all publications.

Writes images to images/tocs/ and a manifest to data/tocs.json.
The manifest maps DOI -> filename so publications.js can find local images.

Strategy
--------
Each publisher exposes its graphical abstract via the og:image meta tag,
but bot-protection varies.  This script uses two HTTP clients:

  • requests       — for publishers that allow plain HTTP (RSC, Beilstein)
  • cloudscraper   — Cloudflare-bypass client for ACS and Wiley

Publisher coverage:
  10.1039/  RSC                  requests + og:image  (confirmed: small GIF)
  10.3762/  Beilstein            requests + og:image  (confirmed: landscape PNG)
  10.1021/  ACS                  cloudscraper + og:image  (social.jpeg = graphical abstract)
  10.1002/  Wiley                cloudscraper + og:image  (cms/asset CDN image = TOC)
  10.1016/  Elsevier             cloudscraper + og:image  (try; validated by aspect ratio)
  10.1080/  Taylor & Francis     cloudscraper + og:image  (try; validated by aspect ratio)

Skipped publishers (og:image is NOT the graphical abstract):
  10.1038/  Nature Portfolio  — og:image is a random article figure, not a TOC
  10.1007/  Springer          — og:image is a first-page PDF render
  10.1063/  AIP Publishing    — 403 even with Cloudflare bypass; no solution
  10.3897/  Pensoft / RIO     — og:image is a journal logo or article icon
  10.1126/  Science           — no graphical abstract
  10.1147/  IBM               — no graphical abstract

Validation rules (applied to every downloaded image):
  • Aspect ratio: skip if height > 1.3 × width (portrait → not a TOC)
  • Min dimensions: skip if width < 100 px or height < 50 px
  • Max dimensions: skip if width > 2000 px or height > 2000 px
  • Min file size: skip if < 5 KB (icon / placeholder)
  • Content type: skip if text/html (login page / error page)
  • URL filter: skip if URL contains logo|favicon|icon|banner|placeholder|cover

Usage (from repo root):
    pip install requests cloudscraper Pillow
    python3 scripts/fetch-tocs.py

Re-runnable: already-downloaded images are skipped.
"""

import io
import json
import os
import re
import time

import requests
import cloudscraper
from PIL import Image

# ── Config ────────────────────────────────────────────────────────────────────

ORCID_ID   = '0000-0001-5222-2201'
MAILTO     = 'marti.gimferrerandres@uni-goettingen.de'
OUTPUT_DIR = 'assets/tocs'
MANIFEST   = 'data/tocs.json'

REPO_PREFIXES = ('10.3204/', '10.25625/', '10.17877/', '10.5281/')

DOI_BLOCKLIST = {
    '10.31080/asop.2023.06.0639',
    '10.2478/srj-2025-0001',
}

# ── Publisher routing ─────────────────────────────────────────────────────────
#
# 'direct'  — use plain requests (no Cloudflare on these sites)
# 'cf'      — use cloudscraper (Cloudflare-protected sites)
# None      — skip entirely (og:image is not the graphical abstract)

PUBLISHER_STRATEGY = {
    '10.1039/': 'direct',   # RSC — og:image is graphical abstract (small GIF ~189 px)
    '10.3762/': 'direct',   # Beilstein — og:image is graphical abstract (landscape PNG)
    '10.1021/': 'cf',       # ACS — og:image social.jpeg is graphical abstract (1200×628)
    '10.1002/': 'cf',       # Wiley — og:image CDN asset is TOC image (landscape JPEG)
    '10.1016/': 'cf',       # Elsevier — try; validated by aspect ratio
    '10.1080/': 'cf',       # Taylor & Francis — try; validated by aspect ratio
    # Skipped:
    '10.1038/': None,       # Nature — og:image is a random data figure
    '10.1007/': None,       # Springer — og:image is first-page PDF rendering
    '10.1063/': None,       # AIP — 403 even with Cloudflare bypass
    '10.3897/': None,       # Pensoft/RIO — og:image is journal logo/icon
    '10.1126/': None,       # Science — no graphical abstract
    '10.1147/': None,       # IBM — no graphical abstract
}

# ── Validation thresholds ─────────────────────────────────────────────────────

MIN_WIDTH_PX       = 100
MIN_HEIGHT_PX      = 50
MAX_WIDTH_PX       = 4000
MAX_HEIGHT_PX      = 4000
MAX_PORTRAIT_RATIO = 1.3    # skip if height / width > this
MIN_FILE_BYTES     = 5 * 1024  # 5 KB

# Target display width for saved images (2× CSS display width for Retina)
RESIZE_WIDTH = 360

# ── HTTP clients ──────────────────────────────────────────────────────────────

_DIRECT_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

_CF_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

# Single shared cloudscraper instance (preserves session/cookies across requests)
_cf_scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'darwin', 'desktop': True}
)


def http_get(url, use_cf=False, timeout=20):
    """GET url using direct requests or cloudscraper. Returns Response or None."""
    try:
        if use_cf:
            return _cf_scraper.get(url, headers=_CF_HEADERS, timeout=timeout)
        else:
            return requests.get(url, headers=_DIRECT_HEADERS, timeout=timeout,
                                allow_redirects=True)
    except Exception:
        return None

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_dois():
    """Fetch all article DOIs from OpenAlex."""
    api_headers = {'User-Agent': f'cchembio-website/1.0 (mailto:{MAILTO})'}
    r = requests.get(
        f'https://api.openalex.org/authors?filter=orcid:{ORCID_ID}&mailto={MAILTO}',
        headers=api_headers, timeout=15,
    )
    r.raise_for_status()
    author_id = r.json()['results'][0]['id'].replace('https://openalex.org/', '')

    dois = []
    cursor = '*'
    while cursor:
        url = (
            f'https://api.openalex.org/works'
            f'?filter=authorships.author.id:{author_id},type:article'
            f'&per_page=200&cursor={cursor}&mailto={MAILTO}'
        )
        r = requests.get(url, headers=api_headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        for w in data.get('results', []):
            raw = (w.get('doi') or '').strip()
            doi = re.sub(r'^https?://doi\.org/', '', raw, flags=re.I).lower().strip()
            if not doi:
                continue
            if any(doi.startswith(p) for p in REPO_PREFIXES):
                continue
            if doi in DOI_BLOCKLIST:
                continue
            dois.append(doi)
        cursor = data.get('meta', {}).get('next_cursor')
    return dois


def publisher_strategy(doi):
    """Return ('direct'|'cf'|None, prefix_matched) for this DOI."""
    for prefix, strategy in PUBLISHER_STRATEGY.items():
        if doi.startswith(prefix):
            return strategy, prefix
    # Unknown publisher: try cloudscraper as a best-effort attempt
    return 'cf', None


def get_og_image(doi, use_cf):
    """
    Resolve DOI to publisher landing page and extract og:image URL.
    Returns an image URL or None.
    """
    r = http_get(f'https://doi.org/{doi}', use_cf=use_cf)
    if not r or not r.ok:
        return None

    html = r.text

    for pat in (
        r'<meta\s[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']',
        r'<meta\s[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']',
    ):
        m = re.search(pat, html, re.I)
        if m:
            url = m.group(1).strip()
            # Skip obvious non-TOC images
            if re.search(r'logo|favicon|icon|banner|placeholder|cover', url, re.I):
                continue
            return url

    return None


def validate_and_save(content, doi):
    """
    Validate image content against TOC criteria, resize, and save.
    Returns filename on success, or None on rejection.
    """
    try:
        img = Image.open(io.BytesIO(content))
        w, h = img.size

        # Dimension bounds
        if w < MIN_WIDTH_PX or h < MIN_HEIGHT_PX:
            return None, 'too small'
        if w > MAX_WIDTH_PX or h > MAX_HEIGHT_PX:
            return None, 'too large'

        # Aspect ratio: TOC figures are landscape or square
        if h > w * MAX_PORTRAIT_RATIO:
            return None, f'portrait ({w}×{h})'

        # Determine save format
        fmt = img.format or 'PNG'
        ext_map = {'JPEG': '.jpg', 'PNG': '.png', 'GIF': '.gif', 'WEBP': '.webp'}
        ext = ext_map.get(fmt, '.png')

        # Resize to target width (preserving aspect ratio)
        if w > RESIZE_WIDTH:
            new_h = round(h * RESIZE_WIDTH / w)
            img = img.resize((RESIZE_WIDTH, new_h), Image.LANCZOS)

        # Save
        stem = re.sub(r'[^a-z0-9._-]', '_', doi.lower())
        filename = stem + ext
        out_path = os.path.join(OUTPUT_DIR, filename)

        save_fmt = fmt
        if save_fmt == 'GIF':
            # Re-save resized GIF as PNG (Pillow GIF re-save loses animation frames)
            if w > RESIZE_WIDTH:
                ext = '.png'
                filename = stem + ext
                out_path = os.path.join(OUTPUT_DIR, filename)
                save_fmt = 'PNG'
            else:
                # No resize needed: write raw bytes to preserve exact GIF
                with open(out_path, 'wb') as f:
                    f.write(content)
                return filename, None

        if img.mode in ('RGBA', 'P') and save_fmt == 'JPEG':
            img = img.convert('RGB')

        img.save(out_path, save_fmt)
        return filename, None

    except Exception as e:
        return None, str(e)


def download_image(url, doi, use_cf):
    """
    Download url, validate it as a TOC image, and save.
    Returns (filename, error_reason) — filename is None on failure.
    """
    r = http_get(url, use_cf=use_cf)
    if not r or not r.ok or not r.content:
        return None, f'HTTP {r.status_code if r else "error"}'

    # Reject HTML responses (login pages, error pages)
    ct = r.headers.get('content-type', '').split(';')[0].strip()
    if 'html' in ct or 'text' in ct:
        return None, 'HTML response'

    # Reject tiny files
    if len(r.content) < MIN_FILE_BYTES:
        return None, f'too small ({len(r.content)} B)'

    return validate_and_save(r.content, doi)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    manifest = {}
    if os.path.exists(MANIFEST):
        with open(MANIFEST) as f:
            manifest = json.load(f)

    print('Fetching DOIs from OpenAlex…')
    dois = get_dois()
    print(f'Found {len(dois)} DOIs.\n')

    # Categorise by strategy
    by_strategy = {'direct': [], 'cf': [], 'skip': []}
    for doi in dois:
        s, pfx = publisher_strategy(doi)
        by_strategy[s or 'skip'].append((doi, pfx))

    print(f'Publisher strategy breakdown:')
    print(f'  direct (requests):     {len(by_strategy["direct"])}')
    print(f'  cf (cloudscraper):     {len(by_strategy["cf"])}')
    print(f'  skip:                  {len(by_strategy["skip"])}\n')

    found = skipped = missing = rejected = 0

    for strategy, doi_list in [('direct', by_strategy['direct']),
                                ('cf',     by_strategy['cf'])]:
        use_cf = (strategy == 'cf')
        label  = 'cloudscraper' if use_cf else 'direct'
        print(f'─── {label} publisher group ({len(doi_list)} DOIs) ───')

        for i, (doi, pfx) in enumerate(doi_list, 1):
            existing = manifest.get(doi)
            if existing and os.path.exists(os.path.join(OUTPUT_DIR, existing)):
                skipped += 1
                continue

            print(f'[{i}/{len(doi_list)}] {doi}', end='  ', flush=True)

            og_url = get_og_image(doi, use_cf)
            if not og_url:
                missing += 1
                print('no og:image')
                time.sleep(2 if use_cf else 1)
                continue

            filename, reason = download_image(og_url, doi, use_cf)
            if filename:
                manifest[doi] = filename
                found += 1
                print(f'OK → {filename}')
            else:
                rejected += 1
                print(f'REJECTED ({reason})  {og_url[:60]}…')

            # Polite rate limiting — longer delay for cloudscraper to avoid bans
            time.sleep(3 if use_cf else 1)

    with open(MANIFEST, 'w') as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    print(f'\nDone: {found} downloaded, {skipped} already present, '
          f'{missing} no og:image, {rejected} rejected by validation.')
    print(f'Manifest written to {MANIFEST}.')


if __name__ == '__main__':
    main()
