# Tech Debt

Architectural debt and maintainability issues identified for future cleanup.
Distinct from `known-issues.md` (runtime bugs).

Last audited: 2026-08-15.

---

## Highest Impact

### `Game` class is a forwarding facade
**File:** `neural_dive/game.py:201-390`

The `Game` class wraps 12 managers behind 21 backward-compatibility properties
that just forward to manager state. Every manager mutation flows through `Game`,
making it a God Object. Mocking is painful and new contributors have to trace
through the property layer to find where state actually lives.

**Direction:** stop forwarding. Have callers reach into the appropriate manager
directly (e.g., `game.player_manager.coherence` rather than `game.coherence`).
Remove the property layer once call sites are updated.

---

### `npc_manager.py` mixes concerns
**File:** `neural_dive/managers/npc_manager.py` (550 lines)

One manager handles generation, placement, movement AI, conversations, and
opinion tracking. Pathfinding changes risk breaking conversations.

**Direction:** split into focused units (e.g., `NPCSpawner`, `NPCMovement`,
`NPCRelationships`) so each concern is independently testable.

---

### `rendering.py` is monolithic
**File:** `neural_dive/rendering.py` (962 lines, 26 functions)

Map drawing, UI drawing, and overlay drawing are intermingled in one module.

**Direction:** split into `map_renderer.py`, `ui_renderer.py`,
`overlay_renderer.py`.

---

### Question renderers bypass the shared wrapping helpers
**File:** `neural_dive/question_renderers.py:103,120,162`

`rendering.py` has `_draw_wrapped_lines` and the `_draw_text_block`
wrap-then-draw wrapper, but the question renderers call `wrap_text` directly and
`print()` their own lines. That's why `tests/test_question_renderers.py` has to
capture stdout instead of using `TestBackend`.

**Direction:** route the question renderers through the backend and the shared
wrapping helpers, then convert their tests to assert on recorded draw calls.

---

## Notes

- Pruning of stale NPCs/questions completed 2026-05-21 (15 NPCs, 140 questions).
- Stale `data/npcs.json` and `data/questions.json` deleted; canonical lives at
  `data/content/algorithms/`.
- `data/levels.py` is described as a re-export shim, but it is load-bearing:
  `floor_entity_generator` imports `ZONE_TERMINALS` from it and `data_loader`
  falls back to its `PARSED_LEVELS`. Both hardcode the algorithms set, so terminal
  content and the level fallback ignore `content_set`.
- One-time migration scripts (`generate_questions.py`, `redistribute_questions.py`)
  removed.

## Open, low priority

- **`terminals.json` is authored but unwired.** Each content set ships a
  `terminals.json` with 10 reference entries (Big-O guide, SOLID, TCP, design
  patterns). No code reads it — terminal content comes from `ZONE_TERMINALS` in
  `levels.py`, which holds zone lore instead. Either wire the JSON up as a second
  terminal source or delete it; leaving both invites editing the wrong one.
- **`ItemPickedUp` is never published.** The event is defined in `events.py` and
  covered by tests, but no code emits it even though item pickup happens in
  `movement_controller`. Either publish it from `StateManager` or drop the event.

## Resolved

- **Loading a save constructed a `Game` and then mutated it into shape** —
  `_deserialize_game_state` used to call `Game(...)`, which built every manager
  and generated floor 1, then overwrite `current_floor`, replace five managers,
  rebuild the `EventBus` and `StateManager`, repair the collaborators that had
  captured the discarded managers, and regenerate the floor. Correctness depended
  on ordering that nothing enforced, and it caused three bugs (see
  `known-issues.md`): the "Not in a conversation" staleness, floor-1 saves losing
  every NPC, and floor-2+ saves coming back with floor 1's map.

  Construction is now one pass. `GameContext.create` builds the settings,
  content, floor manager, and player — positioned on the floor being restored —
  and `GameManagers` bundles the five managers a save restores.
  `Game.from_context(ctx, managers)` assembles from either a fresh or a restored
  set through the same `_assemble` path, wires the collaborators once the managers
  are final, and generates floor entities exactly once at the end.
  `wire_manager_dependencies` is private again, and `GameInitializer.initialize_stats`
  is gone (the stats it returned live in `StatsTracker`).

- **Dead code swept** — deleted `data_loader.list_content_sets` /
  `load_content_metadata`, `difficulty.get_all_difficulties`, the unused
  `Renderable` protocol, `themes.CYBERPUNK_LIGHT` and the `Theme` dataclass, and
  four unused `TERMINAL_*` constants in `config.py`. `get_theme()` no longer takes
  the two arguments it ignored. `content.json` metadata corrected (45 → 140
  questions, 5 → 3 floors, real topic list) — it is not read by any code.
- **`uv.lock` churn** — `uv run` re-resolved on every invocation and rewrote every
  URL to whatever index the environment pointed at, so running tests dirtied the
  tree and could leak an internal mirror into this public repo. The Makefile now
  exports `UV_FROZEN=1` and the pre-commit hooks prefix `env UV_FROZEN=1`;
  `make relock` regenerates against public PyPI when dependencies change.
- **Type errors in test files** — `make check` is now clean across all 70 files.
  `assertIsNotNone` / `assertIsInstance` don't narrow `Optional` or union types
  for mypy, so the affected call sites use plain `assert x is not None` /
  `assert isinstance(x, T)` instead. Empty collections in fixtures got
  annotations, and two tests that assigned `str` where an `InfoTerminal` or a
  `dict` was expected now build the real objects. `EventBus.subscribe` typing
  was left alone — narrowing at the call sites turned out to be enough.
- **Duplicated text wrapping in `rendering.py`** — consolidated into
  `_draw_wrapped_lines` plus the `_draw_text_block` convenience wrapper.
  `question_renderers.py` still has its own copies (see above).
- **Two competing pre-commit configs** — `.prek.yaml` used a schema prek cannot
  parse (`missing field 'repos'`), so it had never run; deleted. The remaining
  `.pre-commit-config.yaml` now shells out to the same uv commands as
  `make ci`, so the hooks and the Makefile can't drift apart.
- **`TestBackend` collection warning** — set `__test__ = False` so pytest stops
  trying to collect the helper as a test class.
- **`RenderBackend` protocol incomplete** — added `__getattr__` to the protocol
  so blessed-style attribute access (`move_xy`, `bold_black`, etc.) is typed;
  fixed `_identity` fallback in `BlessedBackend`. Production-code mypy errors
  dropped from ~134 to 0.
- **`validate_npc_layout_consistency` cried wolf** — `parse_level` now
  distinguishes single-letter NPC chars from multi-letter text labels
  (`"ARENA"`, `"INFRASTRUCTURE"`); validator includes `boss`/`helper`/`quest`
  NPC types. False-positive warnings eliminated.
- **State-unsafe state mutations** — deleted dead `show_terminal`/`show_snippet`
  methods on `StateManager` (uncalled, wrong types). Added `assert old_pos is
  not None` to narrow `move_player` event payload type.
- **CLAUDE.md outdated** — rewritten (1076 → ~150 lines) reflecting current
  manager layout, EventBus pattern, and dynamic floor requirements.
- **Missing tests for critical paths** — added
  `tests/test_answer_processor.py` (16 tests covering MC/text answers,
  rewards, victory detection, NPC opinions) and
  `tests/test_question_renderers.py` (13 tests covering all three
  `QuestionRenderer` strategies and the registry).
