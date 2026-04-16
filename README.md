# mgimferrer.github.io

Personal academic homepage for **Martí Gimferrer**, built with plain HTML, CSS, and a tiny sprinkle of vanilla JavaScript. No build step, no frameworks, nothing to compile — just open `index.html` in a browser or push to GitHub Pages.

## Live URL

After deployment, the site will be served at:

**https://mgimferrer.github.io/**

## File structure

```
.
├── index.html          # The page itself — all content lives here.
├── style.css           # Forest-green + cream theme, responsive layout.
├── script.js           # Mobile nav toggle and footer year.
├── .nojekyll           # Tells GitHub Pages to skip Jekyll processing.
├── assets/
│   ├── favicon.svg     # Tab icon.
│   ├── portrait.svg    # Placeholder portrait — replace with your own photo.
│   └── cv.pdf          # (You add this.) Linked from the CV section.
└── README.md
```

## Deploy to your existing `mgimferrer/mgimferrer.github.io` repo

You already have the user-site repo at `https://github.com/mgimferrer/mgimferrer.github.io`, so there's nothing to create — you just need to push these files to it.

From a terminal, in a folder where you want the clone to live:

```bash
# 1. Clone your repo.
git clone https://github.com/mgimferrer/mgimferrer.github.io.git
cd mgimferrer.github.io

# 2. Copy the template files into the clone. From this template folder, for example:
#    (adjust the source path to wherever you saved the template)
cp -r /path/to/WEBPAGE-MGIMFERRER/. .

# 3. Commit and push.
git add .
git commit -m "Add personal homepage template"
git push origin main      # or 'master' — whichever branch the repo uses
```

If the repo already has files on it that you want to keep, merge by hand instead of overwriting.

### Enable GitHub Pages (only if it isn't already)

Pages is usually on by default for a `username.github.io` repo. If the site doesn't appear at https://mgimferrer.github.io/ after a minute or two:

1. Go to the repo → **Settings** → **Pages**.
2. **Source:** "Deploy from a branch".
3. **Branch:** `main` (or whichever branch you pushed to), folder `/ (root)`.
4. Click **Save**. Wait a minute, then reload the site.

Every subsequent `git push` redeploys automatically.

## Editing

All text lives in `index.html` — find the section you want to change, edit the content, push. Things to personalise first:

- The hero intro (`<section id="home">`).
- "Quick facts" sidebar in the About section.
- Research theme titles and descriptions.
- Publications list — replace with your own entries or paste from BibTeX.
- News timeline — add or remove `<li>` entries as you go.
- CV education/appointments, and drop your real `cv.pdf` into `assets/`.
- Contact links (Scholar, ORCID, address).

For styling, edit the CSS variables at the top of `style.css`:

```css
--cream:       #f6f1e4;   /* background */
--forest:      #2f5d3a;   /* primary accent */
--forest-deep: #1f4228;   /* hover / strong */
--gold:        #b88a3d;   /* warm accent */
```

Changing just those four values reskins the whole site.

## Preview locally — use a local server (important)

Opening `index.html` directly via the file system (`file://...`) can cause some in-browser previews or sandboxes to show an unstyled page because they don't always resolve the relative paths to `style.css`, `script.js`, and the SVGs. The reliable way to preview is to run a tiny local server:

```bash
cd mgimferrer.github.io
python3 -m http.server 8000
# then open http://localhost:8000 in your browser
```

That resolves all relative paths the same way GitHub Pages will.

## Notes

- Fonts are loaded from Google Fonts (Inter for body text, Cormorant Garamond for headings). If you want a fully offline build, host them yourself or remove the `<link>` tags in `index.html`.
- The site is responsive and includes a mobile nav toggle, a skip-to-content link, and respects `prefers-reduced-motion`.
- Custom domain? Add a `CNAME` file with your domain and configure DNS per GitHub's docs.
