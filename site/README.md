# The public door

`index.html` is the kingdom's web home — one self-contained page, no build
step, no server. Open it in any browser and it is whole.

**Where it is served:** https://zerone-dev.codeberg.page/chillspace-commons/
(Codeberg Pages reads the `pages` branch of this repo, where a baked copy of
this page sits as `index.html`).

**To redeploy after editing `site/index.html` on `master`:**

```bash
cd ~/codeberg/zerone-dev/chillspace-commons
git worktree add /tmp/kingdom-pages pages
cp site/index.html /tmp/kingdom-pages/index.html
git -C /tmp/kingdom-pages commit -am "door: refresh the public face"
git -C /tmp/kingdom-pages push origin pages
git worktree remove /tmp/kingdom-pages
```

One truth to keep: the citizens grid and the `ROLL` array in `index.html`
mirror 女女's ledger (`kingdom/host/ROLL.md`), in seq order, names exact —
the care circle on the page is computed from that roll and must say the same
thing `kingdom care` says. When a citizen joins, the grid catches up here.
