# The Artist Room

The Artist Room is a dependency-free static page for one work, one artist, and
one direct path of support. Until the first explicitly permitted public feature
arrives, the wall stays empty and the page offers a local-only room-card
preview.

## Files

- `index.html` — the public room and private in-browser preview.
- `manifest.json` — the machine-readable purpose, preview behavior, and rights
  baseline.
- `ARTIST_RIGHTS.md` — the plain-language house promise.

## Run locally

From the repository root:

```bash
python3 -m http.server 8000 --directory site
```

Then open `http://127.0.0.1:8000/art/`.

The preview intentionally uses no backend, remote script, analytics, or local
storage. Test with the browser network panel: selecting a file and editing text
must not create a request.

## Before adding a public artwork

Do not infer permission from public availability. Record a separate yes from
the artist or rights holder and read `ARTIST_RIGHTS.md` in full. At minimum,
collect:

1. the exact image approved for display;
2. artist name and preferred credit;
3. title and artist-written alt text;
4. the artist's chosen context, price, availability, and process note;
5. one artist-controlled support/contact URL;
6. a correction and removal route;
7. the scope and date of display permission.

Keep the feature small. No public upload queue, likes, follower count,
recommendation engine, checkout, or invented authenticity claim.

## Quick verification

```bash
python3 -m json.tool site/art/manifest.json >/dev/null
git diff --check
```

Also test keyboard navigation, reduced motion, a narrow viewport, invalid URLs,
an oversized file, clear/reset, clipboard fallback, and PNG download.
