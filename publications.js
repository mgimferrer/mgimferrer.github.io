/**
 * publications.js
 * Dynamically injects TOC (graphical abstract) images into the publication list.
 *
 * Strategy (in order):
 *  1. Load data/tocs.json (DOI → filename, pre-fetched by scripts/fetch-tocs.py).
 *     If a local file exists for this DOI, use assets/tocs/<filename>.
 *  2. Fallback: query the Crossref API for a publisher-provided image link.
 *  3. If no image is available at all, render the entry without a thumbnail.
 *     A broken <img> is never shown.
 *
 * Parity layout (set by .pub-even / .pub-odd classes on <li>):
 *  odd  → image on the LEFT  (flex-direction: row)
 *  even → image on the RIGHT (flex-direction: row-reverse)
 */

(async function () {
  'use strict';

  // ── 1. Load local manifest ────────────────────────────────────────────────
  let manifest = {};
  try {
    const r = await fetch('data/tocs.json');
    if (r.ok) manifest = await r.json();
  } catch (_) {
    // No manifest yet — run scripts/fetch-tocs.py to generate it.
  }

  // ── 2. Process each publication entry ────────────────────────────────────
  const items = document.querySelectorAll('.pub-list li[data-doi]');

  for (const li of items) {
    const doi = li.dataset.doi;
    const pubRef = li.querySelector('.pub-ref');
    if (!pubRef) continue;

    const imgSrc = await resolveImage(doi, manifest);
    if (!imgSrc) continue; // No image — render as plain citation, no thumbnail.

    injectImage(li, pubRef, imgSrc, doi);
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  /**
   * Resolve the best available image URL for a DOI.
   * Returns a URL string, or null if nothing is available.
   */
  async function resolveImage(doi, manifest) {
    // 1. Local pre-fetched image
    if (manifest[doi]) {
      return `assets/tocs/${manifest[doi]}`;
    }

    // 2. Crossref API fallback — some publishers register image links there
    try {
      const url = `https://api.crossref.org/works/${encodeURIComponent(doi)}`
                + `?mailto=marti.gimferrerandres%40uni-goettingen.de`;
      const r = await fetch(url, { signal: AbortSignal.timeout(6000) });
      if (r.ok) {
        const data = await r.json();
        const links = data?.message?.link ?? [];
        // Prefer explicit image/png or image/jpeg links
        const imgLink = links.find(
          l => /^image\//i.test(l['content-type'] ?? '')
        );
        if (imgLink?.URL) return imgLink.URL;
      }
    } catch (_) {
      // Network error or timeout — skip fallback silently.
    }

    return null;
  }

  /**
   * Wrap pubRef in a .pub-row div with the TOC image.
   * Removes the row entirely if the image fails to load (never show broken img).
   */
  function injectImage(li, pubRef, imgSrc, doi) {
    const row = document.createElement('div');
    row.className = 'pub-row';

    const img = document.createElement('img');
    img.src = imgSrc;
    img.alt = `Graphical abstract for ${doi}`;
    img.className = 'pub-toc-img';
    img.loading = 'lazy';
    img.decoding = 'async';

    // Safety net: if image fails to load, unwrap back to plain citation.
    img.addEventListener('error', () => {
      row.replaceWith(pubRef);
    }, { once: true });

    row.appendChild(img);
    row.appendChild(pubRef.cloneNode(true));
    pubRef.replaceWith(row);
  }
})();
