# Improvements

> **Status: audited 2026-09-13 against `main` @ `6481c46`, which is still HEAD.**
> Renamed from `tech-debt.md` on 2026-09-18, when every personal repo moved to
> the same backlog convention. Content is unchanged apart from this header and
> the section names.

This file is the maintenance backlog: architectural debt, test gaps and doc
drift. Runtime bugs live in [`known-issues.md`](known-issues.md).

## At a glance

1. The player profile assumes one game process at a time — S · open, low priority

## Working on these

- Tests: `make test` · Lint and types: `make check` · Content: `make validate`
- Everything at once: `make ci`
- Public repo. Never commit a work hostname, address, tool name or ticket ID.

## 1. The player profile assumes one game process at a time

**S · open, low priority**

`neural_dive/player_profile.py` reads `~/.neural_dive/profile.json` at startup
and rewrites the whole file after every answer. The write itself is atomic (temp
file plus `os.replace`), so the file is never half-written, but two concurrent
runs would still end with whichever finished last — the other run's answers are
lost.

Fine for a single-player terminal game; worth knowing before anything else
starts writing that file. The per-answer write is also deliberate: a run killed
with Ctrl-C must not lose its history, and the file is a couple of KB.

## Notes

- Pruning of stale NPCs/questions completed 2026-05-21. The counts that note
  used to quote (15 NPCs, 140 questions) were a snapshot of that day, not a
  target; the content set is 16 NPCs and 180 questions now. `make validate`
  prints the live figures, so do not restate them here.
- Stale `data/npcs.json` and `data/questions.json` deleted; canonical lives at
  `data/content/algorithms/`.
- `data/levels.py` is described as a re-export shim, but it is load-bearing:
  `floor_entity_generator` imports `ZONE_TERMINALS` from it and `data_loader`
  falls back to its `PARSED_LEVELS`. Both hardcode the algorithms set, so terminal
  content and the level fallback ignore `content_set`.
- One-time migration scripts (`generate_questions.py`, `redistribute_questions.py`)
  removed.

## Settled

One line each: the verdict and the fact that stops it being rediscovered. The
reasoning behind each is in the commit that made it.

- **Every renderer is on the backend** (2026-09-13). All six rendering modules
  draw through `backend.draw_text` / `draw_with_bg`; `grep -c "print("` over them
  is zero. This is what the twelve `@unittest.skip`s in
  `test_rendering_backend.py` were waiting for -- all gone, no skips left, and
  two had been asserting the wrong thing, which being skipped had hidden. The
  colour-*function* helpers (`get_color_func`, `draw_wrapped_lines`,
  `draw_text_block`, `entity_renderers._resolve_style`) are deleted on purpose:
  keeping them would leave a second, unrecordable way to draw. Verified cell by
  cell against a real `BlessedBackend` in a pty.
- **CI exists** (2026-09-05). ruff, mypy, pytest and `validate_questions.py` on
  push and pull request, over a 3.10/3.14 matrix -- the two ends of the declared
  range, neither of which had ever been run. Lockfile-index check is a second
  job. The pre-commit hooks stay, as the faster feedback.
- **`terminals.json` was authored and unwired** (deleted 2026-09-05). 147 lines
  no code read, with four separate places documenting that it was unused.
  `ZONE_TERMINALS` in `levels.py` is the one place terminal text lives.
- **`ItemPickedUp` had no publisher** (2026-09-05). `MoveResult` grew a
  `picked_up` field and `Game.move_player` publishes from there, rather than
  giving `movement_controller` an event bus.
- **`CLAUDE.md` called `data/levels.py` a dead re-export shim** (2026-08-30). It
  is load-bearing; the three live call sites are named there now. The hardcoded
  content set behind it is still open -- see `## Notes`.
- **`Game` was a forwarding facade** -- 21 properties and 16 setters gone, 235
  call sites migrated across 16 modules, driven by mypy. Two traps a regex sweep
  would have missed: `Game`'s own assignments would have silently created
  shadowing attributes holding a second copy of the conversation state, and five
  `getattr`/`hasattr` accesses would have kept working while quietly returning
  the default.
- **`npc_manager.py` mixed five concerns in 558 lines** -- split into
  `NPCSpawner`, `NPCMovement` and `NPCRelationships`, with `NPCManager` a
  268-line composition root. `tests/test_npc_units.py` covers the three units
  without building a `Game` (19 tests).
- **Question renderers bypassed the shared wrapping helpers** and printed their
  own lines -- they draw through `render_helpers.draw_wrapped_text` now, which
  takes a colour *name* so `TestBackend` records each line as a `DrawCall`.
- **`rendering.py` was 962 lines** -- split into `map_renderer`, `ui_renderer`,
  `overlay_renderer` and `render_helpers`. `rendering.py` is 99 lines and owns
  the frame's draw order.
- **Loading a save built a `Game` and then mutated it into shape**, with
  correctness depending on ordering nothing enforced. It caused three bugs, all
  in `known-issues.md`. Construction is one pass now: `GameContext.create`,
  `GameManagers`, `Game.from_context`.
- **`uv.lock` churn** -- `uv run` re-resolved every invocation and rewrote each
  URL to whatever index the environment pointed at, which could leak an internal
  mirror into this public repo. `UV_FROZEN=1` in the Makefile and the hooks;
  `make relock` regenerates against public PyPI.
- **Type errors in test files** -- `make check` is clean across all 70.
  `assertIsNotNone` / `assertIsInstance` do not narrow for mypy; the call sites
  use plain `assert` instead. `EventBus.subscribe` typing was left alone.
- **Two competing pre-commit configs** -- `.prek.yaml` used a schema prek cannot
  parse, so it had never run; deleted. The remaining config shells out to the
  same uv commands as `make ci`, so hooks and Makefile cannot drift.
- **`RenderBackend` protocol incomplete** -- added `__getattr__` so blessed-style
  attribute access is typed. Production mypy errors went ~134 to 0.
- **`validate_npc_layout_consistency` cried wolf** -- `parse_level` now tells
  single-letter NPC chars from multi-letter text labels (`"ARENA"`).
- **Dead code swept** -- `data_loader.list_content_sets` / `load_content_metadata`,
  `difficulty.get_all_difficulties`, the `Renderable` protocol,
  `themes.CYBERPUNK_LIGHT` and its `Theme` dataclass, four `TERMINAL_*` constants,
  and the dead `show_terminal` / `show_snippet` on `StateManager`.
- **Duplicated text wrapping in `rendering.py`** -- consolidated, then superseded
  entirely by `render_helpers.draw_wrapped_text`.
- **`TestBackend` collection warning** -- `__test__ = False`.
- **`CLAUDE.md` outdated** -- rewritten, 1076 to ~150 lines.
- **Missing tests for critical paths** -- `tests/test_answer_processor.py` (16)
  and `tests/test_question_renderers.py` (13).

## Not looked at

Content quality beyond what `make validate` checks. The game has not been played
end to end since `6481c46`; the renderer conversion was verified by rendering
four frames through a real `BlessedBackend` into a pty and diffing cells, which
is not the same as playing it.

One pre-existing commit, `ef78d50` ("first commit", 2025-11-11), carries the work
email address. Rewriting it means rewriting every commit after it and
force-pushing a public repo, and would not remove anything — GitHub keeps
orphaned commits reachable by SHA. Left alone deliberately.

---

`S` under an hour · `M` half a day · `L` more, or needs a decision. State is
`open`, `decision owed`, or `blocked on <thing>`. Every claim carries its
evidence and a date; say so when something was not verified.
