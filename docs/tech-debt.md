# Tech Debt

Architectural debt and maintainability issues identified for future cleanup.
Distinct from `known-issues.md` (runtime bugs).

Last audited: 2026-05-21.

---

## Highest Impact

### `Game` class is a forwarding facade
**File:** `neural_dive/game.py:185-395`

The `Game` class wraps 8+ managers behind ~24 backward-compatibility properties
that just forward to manager state. Every manager mutation flows through `Game`,
making it a God Object. Mocking is painful and new contributors have to trace
through the property layer to find where state actually lives.

**Direction:** stop forwarding. Have callers reach into the appropriate manager
directly (e.g., `game.player_manager.coherence` rather than `game.coherence`).
Remove the property layer once call sites are updated.

---

### `npc_manager.py` mixes concerns
**File:** `neural_dive/managers/npc_manager.py` (~554 lines)

One manager handles generation, placement, movement AI, conversations, and
opinion tracking. Pathfinding changes risk breaking conversations.

**Direction:** split into focused units (e.g., `NPCSpawner`, `NPCMovement`,
`NPCRelationships`) so each concern is independently testable.

---

### `rendering.py` is monolithic
**File:** `neural_dive/rendering.py` (~850 lines, 26+ functions)

Map drawing, UI drawing, and overlay drawing are intermingled. `_draw_wrapped_lines`
has near-duplicate variants at six call sites.

**Direction:** split into `map_renderer.py`, `ui_renderer.py`, `overlay_renderer.py`.
Extract the wrapping helper to a single shared utility.

---

### Type errors in test files
**Files:** `neural_dive/tests/test_events.py`, `tests/test_rendering_backend.py`,
`tests/test_state_manager.py`, others (~35 mypy errors)

Test code uses `Callable[[ConcreteEvent], Any]` to subscribe to the
`EventBus`, but the bus signature expects `Callable[[GameEvent], None]`.
Tests run fine but mypy is noisy.

**Direction:** narrow the `EventBus.subscribe` typing to accept
`Callable[[E], None]` for any `E ⊆ GameEvent` (likely a `TypeVar` change), or
update tests to use the base type.

---

## Notes

- Pruning of stale NPCs/questions completed 2026-05-21 (15 NPCs, 140 questions).
- Stale `data/npcs.json` and `data/questions.json` deleted; canonical lives at
  `data/content/algorithms/`.
- `data/levels.py` is now a thin re-export shim.
- One-time migration scripts (`generate_questions.py`, `redistribute_questions.py`)
  removed.

## Resolved

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

