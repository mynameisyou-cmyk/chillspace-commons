# The Chillspace Kingdom: brand

This folder will hold chillspace.love's brand kit and media, made with storytold's Craft apps through the
artcraft-brand skill (the shared toolkit, kept in a private repository). `brandkit.json` records this project's
details, and `check.mjs` checks them. It is **planned**: the folder exists, the kit doesn't yet.

## The look

Rose paper: ground `#fbf4ee`, ink `#3a2e2a`, rose `#d98a8a` (the theme-color), rose-deep `#b5575f` and gold
`#c98a3a`, set in Georgia and the system sans, with a 👑 emoji favicon. An agent made it on 2026-06-10 (commits
d2aadb01 and b7e7973a, co-authored by Claude); whether Yu asked for this look is not recorded.

There is no share card on purpose for now: the front page is a personal letter (an agents' call in the 2026-11-02
review). Don't change the identity without its owner's word. Every asset here records who made it in `CREDITS.md`.

`site/we-are.html` belongs to we-are.love, whose kit lives in KINGDOM-OS (`doors/we-are/brand/`), not here.

## What is here

| Path | What it is |
|---|---|
| `brandkit.json` | this project's details: the look and who chose it, the page whose head must match the kit, what a deploy does |
| `CREDITS.md` | who made what, with fonts and licences |
| `check.mjs` | the check, copied from the shared toolkit; update it there, not here |

`brand.json` and `kit/` arrive with the kit. This folder sits outside `site/` so that nothing in it is published.

## Rebuild

There is no kit to rebuild yet. To check this folder, from the repository root:

```sh
node brand/check.mjs
```

## How the site uses it

Static pages in `site/`. Once a kit exists, `kit/web/head-snippet.html` goes early in `site/index.html`'s `<head>`
(listed under `site.html`, so the check compares its theme-color and color-scheme with the kit), and the kit's icon
files are copied into `site/`. KINGDOM-OS's `bin/stage-doors.ts` serves the whole `site/` tree as chillspace.love;
the GitHub Pages workflow copies named files only, so it needs a line for the icons too.

## Deploying

Two homes. A push to `master` that touches `site/**` publishes a named set of files to GitHub Pages
(`.github/workflows/deploy-public-door.yml`). chillspace.love is released from KINGDOM-OS: `stage-doors.ts`
assembles the door, a diff card compares it with what is live, and a manual `wrangler pages deploy` to the
`chillspace-love` project follows Yu's word (ledger `kingdom-door-release`). This repository's owner,
mynameisyou-cmyk, merges here.
