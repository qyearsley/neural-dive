# Improvements

> **Status:** audited 2026-09-13 @ `6481c46`; spot-reviewed 2026-10-19 and
> 2026-11-12 (cleanup pass). Not a full re-audit since.

This file is the maintenance backlog: architectural debt, test gaps and doc
drift. Runtime bugs live in [`known-issues.md`](known-issues.md).

## At a glance

Nothing open.

## Working on these

- Tests: `make test` · Lint and types: `make check` · Content: `make validate`
- Everything at once: `make ci`
- Public repo. Never commit a work hostname, address, tool name or ticket ID.

## Settled

Verdict plus the one fact that stops an item being proposed again. The reasoning
is in the commit that made it.

- **Chase BFS and ambush guards now tested** (2026-11-18): wall detours, no
  path, `coherence <= 0` in `check_ambush`, and the overlay and Y/N gate, now
  `ambush_allowed()` in `input_handler.py`.
- **The player profile assumes one game process** (closed 2026-11-18). Two
  concurrent runs keep only the last writer's answers. Accepted: it is a
  single-player game. The write is atomic, and the per-answer write is
  deliberate so Ctrl-C keeps history.
- **Pre-commit skips a commit that touches only `ndive`** (closed 2026-11-18).
  `identify` does not tag its `uv run --script` shebang as Python. CI names
  `ndive` explicitly and catches it; a `files:` pattern per hook would need
  hand upkeep.
- **`GameBuilder` deleted 2026-11-12.** Only its own test used it; the game
  builds through `GameInitializer`, `GameContext` and `GameManagers`.
- **Nine unused event types deleted 2026-11-12.** Only `ItemPickedUp` is
  published. `EventBus.unsubscribe`, `clear_all` and `get_listener_count` went too.
- **Test-only methods deleted 2026-11-12:** `Conversation.advance_question` and
  `is_complete`, `NPCManager.get_conversation`, `ConversationEngine.is_active`,
  `FloorEntityGenerator.generate_all_entities`, and `config.MIN_TERMINAL_HEIGHT`.
  No production caller; `AnswerProcessor` marks completion itself.
- **Wrong-shape save crashed `--load`** (2026-10-19). Fixed;
  `test_load_a_save_of_the_wrong_shape_returns_none` guards it.
- **`StateManager` deleted 2026-10-03.** Nothing called it, and its events had no
  subscribers. Do not rebuild a central mutation layer.
- **`make relock` failed on `UV_FROZEN=`** (2026-09-26). uv 0.12 rejects an empty
  value; the target uses `env -u UV_FROZEN`.
- **CI now runs `uv lock --check`** (2026-09-26). `UV_FROZEN` alone does not
  catch a stale `uv.lock`.
- **`validate_questions.py` stays a report tool only** (2026-09-26).
  `TestQuestionNPCLinkage` in `test_content_integrity.py` already asserts the same
  checks and is stricter, so CI does not run the script.
- **The pytest hook runs on content-only commits** (2026-09-26).
  `types_or: [python, json]`.
- **`INTERACTION_RADIUS` lives in `config.py`** (2026-09-26), not in a manager.
- **`CLAUDE.md` managers tree lists the three NPC units** (2026-09-26), and cites
  an import name, not a line number.
- **Every renderer draws through the backend** (2026-09-13). `grep -c "print("`
  over the six rendering modules is zero. The colour-function helpers were
  deleted on purpose: they were a second way to draw that tests cannot record.
- **CI exists** (2026-09-05): ruff, mypy and pytest on Python 3.10 and 3.14, plus
  a lockfile-index job. The pre-commit hooks stay as faster feedback.
- **`terminals.json` deleted** (2026-09-05). No code read it; terminal text lives
  in `ZONE_TERMINALS` in `levels.py`.
- **`ItemPickedUp` is published** (2026-09-05) from `Game.move_player` via
  `MoveResult.picked_up`. `movement_controller` gets no event bus.
- **`data/levels.py` is not dead** (2026-08-30). Three call sites import it and
  each hardcodes the algorithms set; see `CLAUDE.md`. Making it follow
  `content_set` is still open work.
- **`Game` forwarding properties removed.** 235 call sites moved to the owning
  manager. Beware `getattr`/`hasattr` calls that keep working and return a default.
- **`npc_manager.py` split** into `NPCSpawner`, `NPCMovement` and
  `NPCRelationships`; tests in `test_npc_units.py`.
- **`rendering.py` split** into `map_renderer`, `ui_renderer`, `overlay_renderer`
  and `render_helpers`. Question renderers use `draw_wrapped_text`.
- **Load builds a `Game` in one pass** (`GameContext.create`, `GameManagers`,
  `Game.from_context`). Mutate-after-build caused three bugs in `known-issues.md`.
- **`uv.lock` churn.** `UV_FROZEN=1` in the Makefile and hooks stops an internal
  mirror leaking into the lockfile.
- **Test type errors.** `make check` is clean; `assertIsNotNone` does not narrow
  for mypy, so tests use plain `assert`.
- **Two pre-commit configs.** `.prek.yaml` had never run; deleted.
- **`RenderBackend` protocol** gained `__getattr__`, taking mypy errors from ~134
  to 0.
- **`validate_npc_layout_consistency` false alarms.** `parse_level` now tells NPC
  chars from text labels.
- **Dead code swept:** `list_content_sets`, `load_content_metadata`,
  `get_all_difficulties`, `Renderable`, `CYBERPUNK_LIGHT`, four `TERMINAL_*`
  constants.
- **Old data files and one-time scripts deleted:** `data/npcs.json`,
  `data/questions.json`, `generate_questions.py`, `redistribute_questions.py`.
  The canonical set is `data/content/algorithms/`.
- **Smaller items, done:** duplicated text wrapping, the `TestBackend` collection
  warning (`__test__ = False`), the 1076-line `CLAUDE.md`, and tests for
  `AnswerProcessor` and the question renderers.

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
