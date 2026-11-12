# Improvements

> **Status:** audited 2026-09-13 @ `6481c46`; spot-reviewed 2026-10-19 and
> 2026-11-12 (cleanup pass). Not a full re-audit since.

This file is the maintenance backlog: architectural debt, test gaps and doc
drift. Runtime bugs live in [`known-issues.md`](known-issues.md).

## At a glance

1. The enemy chase and ambush paths have test gaps — S · open
2. The player profile assumes one game process at a time — S · open, low priority
3. Pre-commit hooks never run on a commit that only touches `ndive` — S · open, low priority

## Working on these

- Tests: `make test` · Lint and types: `make check` · Content: `make validate`
- Everything at once: `make ci`
- Public repo. Never commit a work hostname, address, tool name or ticket ID.

## 1. The enemy chase and ambush paths have test gaps

**S · open**

From a read of `d700b54` on 2026-10-19; no logic bug found.

- `NPCMovement._first_step_toward`, the BFS step, is untested. The chase test
  in `tests/test_npc_units.py` only checks the chase speed.
- The game-over branch in `answer_processor.py` ends the conversation directly,
  so the enemy is not stunned and stays adjacent. `check_ambush` guards this
  with `coherence <= 0`, and no test pins that guard.
- The `overlay_is_open` / `pending_confirm` gate in `__main__.py` runs only in
  real play.

Verify: a BFS test with a wall between enemy and player, and an ambush test at
zero coherence.

## 2. The player profile assumes one game process at a time

**S · open, low priority**

`neural_dive/player_profile.py` reads `~/.neural_dive/profile.json` at startup
and rewrites the whole file after every answer. The write itself is atomic (temp
file plus `os.replace`), so the file is never half-written, but two concurrent
runs would still end with whichever finished last — the other run's answers are
lost.

Fine for a single-player terminal game; worth knowing before anything else
starts writing that file. The per-answer write is also deliberate: a run killed
with Ctrl-C must not lose its history, and the file is a couple of KB.

## 3. Pre-commit hooks never run on a commit that only touches `ndive`

**S · open, low priority**

The ruff-check, ruff-format, mypy, and pytest hooks in
`.pre-commit-config.yaml` gate on `types: [python]` (pytest also on `json`,
since 2026-09-26). `identify`, the library `prek`/`pre-commit` use to tag
files, does not recognise `ndive`'s shebang
(`#!/usr/bin/env -S uv run --script`) as Python -- it tags the file `text` and
`executable` only. So a commit that edits `ndive` and nothing else skips every
local check; `.github/workflows/ci.yml` still catches it (it names `ndive`
explicitly in each `run:` line and does not filter by file type).

Fixing it would mean adding `ndive` to `files:` on each hook, which reopens the
exact trap `. ndive` was added to the Makefile's `lint` target to avoid: a
filename-based pattern that has to be kept in sync by hand as extensionless
scripts come and go, rather than by content sniffing. Found while verifying the
JSON-trigger fix below; not fixed here because it's a separate gate from the
one that fix targets.

## Settled

Verdict plus the one fact that stops an item being proposed again. The reasoning
is in the commit that made it.

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
