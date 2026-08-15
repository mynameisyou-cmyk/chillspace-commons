#!/bin/sh
# Grok SessionStart entry. Relative to this file so plugin install stays portable.
set +x
set +v
umask 077
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$HERE/../grok_wake.py"
