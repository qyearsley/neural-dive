# Helper Scripts

One repo check lives here. To add or edit questions, see the
[Question Guide](../docs/question-guide.md). To check content, run
`make validate`.

## check-lockfile-index.sh

Fails if `uv.lock` references anything other than public PyPI. `uv run` and
`uv sync` rewrite the lockfile using whatever index the environment points at, so
an internal mirror can leak into this public repo. Runs as a pre-commit hook
(`no-internal-index-in-lockfile`); run it directly with:

```bash
scripts/check-lockfile-index.sh
```

The Makefile and the hooks set `UV_FROZEN=1`, which stops uv writing `uv.lock` at
all, so this should not trigger in normal use. If it does — usually from a bare
`uv run` — regenerate with:

```bash
make relock
```

## See Also

- [Question Authoring Guide](../docs/question-guide.md) — how to write good questions
- [Main README](../README.md) — project overview and setup
