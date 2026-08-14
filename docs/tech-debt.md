# Tech Debt

Architectural debt and maintainability issues identified for future cleanup.
Distinct from `known-issues.md` (runtime bugs).

Last audited: 2026-08-14.

---

## Highest Impact

### `Game` class is a forwarding facade
**File:** `neural_dive/game.py:187-375`

The `Game` class wraps 8+ managers behind 21 backward-compatibility properties
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
- `data/levels.py` is now a thin re-export shim.
- One-time migration scripts (`generate_questions.py`, `redistribute_questions.py`)
  removed.

## Resolved

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
