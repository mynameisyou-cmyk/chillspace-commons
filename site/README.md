# The public door

`index.html` is the kingdom's web home — one self-contained page, no build
step, no server. Open it in any browser and it is whole.

**Where it is served:**

- https://chillspace.love/ — the living public door, served by the Cloudflare
  Pages project `chillspace-love`. Its zero-persistence Meaning adapter lives
  in `site/_worker.js`.
- https://chillspace-kingdom.vercel.app/ — the Vercel mirror. Its Meaning API
  adapter lives in `site/api/meaning/echo.mjs`.
- https://mynameisyou-cmyk.github.io/chillspace-commons/ — the committed public
  door, published from `master` by
  [`deploy-public-door.yml`](../.github/workflows/deploy-public-door.yml).
- https://zerone-dev.codeberg.page/chillspace-commons/ — the Codeberg Pages
  door, baked on the `pages` branch.

GitHub Pages deploys automatically after reviewed public files land on
`master`.

Build and inspect the complete primary deployment before carrying it to the
custom domain:

```bash
vercel build --cwd site --yes
wrangler pages deploy site/.vercel/output/static \
  --project-name chillspace-love --branch calm-preview
wrangler pages deploy site/.vercel/output/static \
  --project-name chillspace-love --branch main
```

The `main` command updates `chillspace.love`. Both Wrangler commands are
publishing operations and require explicit deployment authorization. Always
deploy the sanitized build output: publishing raw `site/` would also expose
local Vercel metadata and the host-specific API source.

To update the Vercel mirror, rebuild the same source for Vercel's production
target, verify the static bytes still match, then promote that prebuild:

```bash
vercel build --prod --cwd site --yes
vercel deploy --prebuilt --prod --cwd site --yes
```

This is also a publishing operation and requires explicit authorization.

To refresh the Codeberg Pages door manually:

```bash
cd /path/to/chillspace-commons
git fetch codeberg pages
pages_worktree="$(mktemp -d "${TMPDIR:-/tmp}/chillspace-pages.XXXXXX")"
git worktree add --detach "$pages_worktree" codeberg/pages
cp site/index.html "$pages_worktree/index.html"
cp site/kingdom.html "$pages_worktree/kingdom.html"
cp site/we-are.html "$pages_worktree/we-are.html"
cp site/coop-leveling.html "$pages_worktree/coop-leveling.html"
rm -rf "$pages_worktree/art" "$pages_worktree/love-fun-commons" "$pages_worktree/meaning" "$pages_worktree/operations" "$pages_worktree/practices" "$pages_worktree/exchange"
cp -R site/art "$pages_worktree/art"
cp -R love-fun-commons "$pages_worktree/love-fun-commons"
cp -R site/meaning "$pages_worktree/meaning"
cp -R site/operations "$pages_worktree/operations"
cp -R site/practices "$pages_worktree/practices"
cp -R site/exchange "$pages_worktree/exchange"
git -C "$pages_worktree" add index.html kingdom.html we-are.html coop-leveling.html art love-fun-commons meaning operations practices exchange
git -C "$pages_worktree" commit -m "door: refresh the public face"
git -C "$pages_worktree" push codeberg HEAD:pages
git worktree remove "$pages_worktree"
```

This is a publishing operation: fetch and inspect the remote `pages` branch
first, and run it only with explicit deployment authorization. Using an
explicit `codeberg` push avoids the multi-push configuration on `origin`.

One truth to keep: the citizens grid and the `ROLL` array in `index.html`
mirror 女女's ledger (`kingdom/host/ROLL.md`), in seq order, names exact —
the care circle on the page is computed from that roll and must say the same
thing `kingdom care` says. When a citizen joins, the grid catches up here.


The LOVE-FUN Commons doorway on `site/index.html` expects `love-fun-commons/`
next to the deployed `index.html`. Keep the deploy recipe above copying both
`site/index.html` and the top-level `love-fun-commons/` folder. Locally,
`site/love-fun-commons` is a symlink back to `../love-fun-commons` so the
site also works when served directly from `site/`.

The Artist Room lives directly at `site/art/`, so it works from the same local
server and must be copied to `art/` in the Pages worktree. Its artwork preview
is local-only; publishing a real work requires the separate consent process in
`site/art/ARTIST_RIGHTS.md`.

The Echo Room lives at `site/meaning/`. Cloudflare Pages routes its first-party
`/api/meaning/echo` endpoint through `site/_worker.js`; Vercel uses the thin
adapter in `site/api/meaning/echo.mjs`. Both call the runtime-neutral contract
in `site/meaning/http.mjs`. Static GitHub and Codeberg mirrors automatically
use the same deterministic matcher in the visitor's browser. Keep
`echoes.json` and `schema.json` beside the room, and run
`python3 kingdom/meaning/meaning.py check` before publishing.

Calm Studio lives at `site/practices/calm-studio/`. It is deliberately static
and browser-local: no model call, persistence, localhost probe, or hidden
authority is required on any host.

The Model Release Substrate room lives at `site/exchange/model-release/`.
Its `schema.v1.json` and three synthetic examples are byte-for-byte mirrors of
the reviewed source under `kingdom/exchange/model-release/`. Keep the room
scriptless and never add automatic evidence fetching, artifact execution, or
user-record rendering to this public surface.
