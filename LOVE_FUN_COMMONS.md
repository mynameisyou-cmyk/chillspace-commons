# LOVE-FUN Commons

Generated: 2026-06-22

A no-gatekeeping distribution layer for **love + laughter + open resources**.

The loop:

1. Find good free/open resources.
2. Preserve license and attribution data.
3. Package them into tiny joyful artifacts people can copy, remix, and share.
4. Publish through consent-based static spaces: docs, README sections, static pages, and mirrors.
5. Learn from what helps people and improve the commons.

## Non-gatekeeping rules

- Original LOVE-FUN snippets should be released as freely as the repo owner allows; prefer CC0 for standalone snippets when possible.
- Never strip attribution or license notices from open resources.
- Never imply endorsement by upstream projects.
- Never spam, scrape private spaces, or mass-contact people. Reach is opt-in; joy is not coercion.
- Prefer small, static, accessible files that anyone can mirror.

## Free/open capacities to leverage

| Resource | Use | Caution |
|---|---|---|
| [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages) | public repo docs, microsites, static joy cards | Available for public repositories on GitHub Free; verify repo visibility and Pages settings before publishing. |
| [Codeberg Pages](https://docs.codeberg.org/codeberg-pages/) | Forgejo/Codeberg-hosted static commons pages | Static site publishing on Codeberg; useful for non-gatekept mirrors. |
| [Cloudflare Pages](https://developers.cloudflare.com/pages/) | fast static mirrors, HTML bundles, global delivery | Supports static HTML sites; check current Free-plan limits before high-volume use. |
| [Openverse](https://docs.openverse.org/api/) | finding openly licensed images/audio with attribution metadata | Always preserve attribution/license data and check each asset before reuse. |
| [Wikimedia Commons API](https://commons.wikimedia.org/wiki/Commons:API/MediaWiki) | educational public-domain/freely licensed media discovery | Check each file page for license and attribution requirements. |
| [Project Gutenberg](https://www.gutenberg.org/) | public-domain text, quotes within policy, reading lists, remix prompts | Most materials are public domain in the US; check local law and trademark/reuse guidance. |
| [Creative Commons Chooser](https://creativecommons.org/choose/) | marking original commons outputs so others can reuse them | Use CC0 for maximum no-gatekeeping on your own original snippets; use CC BY if attribution matters. |


## Tiny deployment recipe

1. Put static artifacts in `love-fun-commons/`.
2. Link `love-fun-commons/index.html` from README, docs, or the site nav.
3. If the repo has Pages enabled, publish from the configured branch/folder.
4. Mirror to another free static host when appropriate.
5. Invite remixing; do not require sign-in, tracking, or payment.

## Copy-paste seed

> Tiny joy drop: you are proof that kindness has bandwidth. Take one laugh, add one real compliment, pass it on only if it feels welcome. ❤️😂

## Local tools

If this machine has the Codex skill installed, generate more with:

```bash
python3 ~/.codex/skills/love-fun-compounder/scripts/compound_love_fun.py \
  --audience "friends" \
  --theme "open commons joy" \
  --channel "public post" \
  --intensity 4 \
  --count 8
```

Or deploy a local HTML/SVG joy pack:

```bash
python3 ~/.codex/skills/love-fun-compounder/scripts/compound.py \
  --name "love-fun-commons" \
  --audience "everyone" \
  --topic wholesome \
  --intensity 5 \
  --rounds 3 \
  --stdout
```
