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

### `RenderBackend` protocol is incomplete
**File:** `neural_dive/backends/backend.py:13-88`

The protocol omits methods that rendering code actually calls: `move_xy`,
`bold_black`, `home`, `clear`, etc. The blessed backend implements them, but the
type contract doesn't. This is the root of most of the ~134 mypy errors and means
type checking provides no real safety against backend swaps.

**Direction:** add the missing methods to `RenderBackend`, or refactor rendering
to only call protocol methods. Then chase down the mypy errors that remain.

---

### `validate_npc_layout_consistency` cries wolf
**File:** `neural_dive/data/content/algorithms/levels.py` (validation function)

Reports 30+ false-positive "unexpected chars" on every game start because it
treats letters in zone-title text (`"ARENA"`, `"INFRASTRUCTURE"`, `"PLAZA"`) as
NPC chars. Warnings are logged but never surfaced — the function defeats its own
purpose because nobody trusts the output.

**Direction:** make `parse_level` distinguish text labels from NPC chars
(e.g., reserved-word list, or a different character class for labels), or drop
the validator entirely.

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

### Missing tests for critical paths
**Files:** `neural_dive/managers/answer_processor.py` (365 lines),
`neural_dive/question_renderers.py` (332 lines)

No unit tests for answer validation, reward calculation, victory detection, or
question rendering. These are core gameplay paths — regressions only surface
during manual play.

**Direction:** add `tests/test_answer_processor.py` and
`tests/test_question_renderers.py`.

---

### Type-unsafe state mutations
**File:** `neural_dive/managers/state_manager.py:199, 207`

Methods assign string IDs to fields typed as `InfoTerminal | None` and
`dict | None`, breaking the type contract.

**Direction:** fix the assignments to match the declared types (or update the
types to match real usage).

---

### `CLAUDE.md` is post-refactor stale
**File:** `CLAUDE.md`

Documents pre-refactor architecture. No mention of `StateManager`, `EventBus`,
or the current mypy state. Onboarding doc actively misleads new contributors.

**Direction:** trim the file down to current reality. Cross-reference manager
responsibilities with the actual code.

---

## Notes

- Pruning of stale NPCs/questions completed 2026-05-21 (15 NPCs, 140 questions).
- Stale `data/npcs.json` and `data/questions.json` deleted; canonical lives at
  `data/content/algorithms/`.
- `data/levels.py` is now a thin re-export shim.
- One-time migration scripts (`generate_questions.py`, `redistribute_questions.py`)
  removed.
