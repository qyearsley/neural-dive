#!/usr/bin/env bash
# Fail if uv.lock references anything other than public PyPI.
#
# uv records the index it resolved against in uv.lock. If uv runs with
# UV_DEFAULT_INDEX / UV_INDEX_URL pointing at an internal mirror, every sdist
# and wheel URL in the lockfile is rewritten to that mirror. This is a public
# repo, so that would leak internal hostnames -- and the URLs would be
# unresolvable for anyone else.
#
# Note that `uv run` and `uv sync` rewrite uv.lock, so this can reappear at any
# time if the environment points elsewhere. To regenerate cleanly:
#
#   UV_DEFAULT_INDEX=https://pypi.org/simple uv lock
#
set -euo pipefail

LOCKFILE="uv.lock"
ALLOWED_HOSTS="pypi.org files.pythonhosted.org"

[ -f "$LOCKFILE" ] || exit 0

hosts=$(grep -oE 'https://[^/"]+' "$LOCKFILE" | sed 's|https://||' | sort -u)

status=0
while IFS= read -r host; do
    [ -n "$host" ] || continue
    case " $ALLOWED_HOSTS " in
        *" $host "*) ;;
        *)
            echo "error: $LOCKFILE references a non-public index host: $host" >&2
            status=1
            ;;
    esac
done <<<"$hosts"

if [ "$status" -ne 0 ]; then
    echo >&2
    echo "Allowed hosts: $ALLOWED_HOSTS" >&2
    echo "Regenerate with: UV_DEFAULT_INDEX=https://pypi.org/simple uv lock" >&2
fi

exit "$status"
