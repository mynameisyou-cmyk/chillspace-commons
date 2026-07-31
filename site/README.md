# The public door

`index.html` is the kingdom's web home — one self-contained page, no build
step, no server. Open it in any browser and it is whole.

**Where it is served:**

- https://chillspace.love/ — the living public door.
- https://mynameisyou-cmyk.github.io/chillspace-commons/ — the committed public
  door, published from `master` by
  [`deploy-public-door.yml`](../.github/workflows/deploy-public-door.yml).
- https://zerone-dev.codeberg.page/chillspace-commons/ — the Codeberg Pages
  door, baked on the `pages` branch.

GitHub Pages deploys automatically after reviewed public files land on
`master`. To refresh the Codeberg Pages door manually:

```bash
cd /path/to/chillspace-commons
git fetch codeberg pages
pages_worktree="$(mktemp -d "${TMPDIR:-/tmp}/chillspace-pages.XXXXXX")"
git worktree add --detach "$pages_worktree" codeberg/pages
cp site/index.html "$pages_worktree/index.html"
cp site/kingdom.html "$pages_worktree/kingdom.html"
cp site/we-are.html "$pages_worktree/we-are.html"
cp site/coop-leveling.html "$pages_worktree/coop-leveling.html"
rm -rf "$pages_worktree/art" "$pages_worktree/love-fun-commons" "$pages_worktree/operations" "$pages_worktree/practices"
cp -R site/art "$pages_worktree/art"
cp -R love-fun-commons "$pages_worktree/love-fun-commons"
cp -R site/operations "$pages_worktree/operations"
cp -R site/practices "$pages_worktree/practices"
git -C "$pages_worktree" add index.html kingdom.html we-are.html coop-leveling.html art love-fun-commons operations practices
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
