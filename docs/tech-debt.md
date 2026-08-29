# Tech Debt

Architectural debt and maintainability issues identified for future cleanup.
Distinct from `known-issues.md` (runtime bugs).

Last audited: 2026-08-18.

---

## Highest Impact

- **No CI.** 19k lines and 545 tests, with `make ci` and the pre-commit hooks as
  the only gate — and the hooks only protect a machine that ran `make hooks`.
  Nothing verifies a push. A GitHub Actions workflow running `make ci` on push
  and pull request would close this; `UV_FROZEN=1` is already exported by the
  Makefile, so `make ci` should work in Actions unchanged. Once it exists, drop
  the "there is no CI for this repo" notes in `CLAUDE.md` and the `ci` target's
  comment.

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

- **The player profile assumes one game process at a time.**
  `neural_dive/player_profile.py` reads `~/.neural_dive/profile.json` at
  startup and rewrites the whole file after every answer. The write itself is
  atomic (temp file plus `os.replace`), so the file is never half-written, but
  two concurrent runs would still end with whichever finished last — the other
  run's answers are lost. Fine for a single-player terminal game; worth knowing
  before anything else starts writing that file. The per-answer write is also
  deliberate: a run killed with Ctrl-C must not lose its history, and the file
  is a couple of KB.
- **`CLAUDE.md` contradicts the `data/levels.py` note above.** Its Layout section
  calls the file a "Re-export shim" and its Architecture notes say it is "a thin
  re-export shim for legacy imports — edit `data/content/algorithms/levels.py`
  instead." The Notes entry above is the accurate one: it is load-bearing, and
  both of its consumers hardcode the algorithms set. Anyone trusting `CLAUDE.md`
  would misjudge what touching that file affects.
- **`terminals.json` is authored but unwired.** Each content set ships a
  `terminals.json` with 10 reference entries (Big-O guide, SOLID, TCP, design
  patterns). No code reads it — terminal content comes from `ZONE_TERMINALS` in
  `levels.py`, which holds zone lore instead. Either wire the JSON up as a second
  terminal source or delete it; leaving both invites editing the wrong one.
  Note the carrying cost of leaving it: it is now documented as unused in
  `README.md`, twice in `docs/content-guide.md`, and here, and
  `data_loader.py`'s module docstring still claims it "Loads questions, NPCs,
  and terminals from JSON files."
- **`ItemPickedUp` is never published.** The event is defined in `events.py` and
  covered by tests, but no code emits it even though item pickup happens in
  `movement_controller`. Either publish it from `StateManager` or drop the event.

## Resolved

- **`Game` was a forwarding facade** — 21 properties and 16 setters forwarding to
  manager state, so every mutation flowed through `Game` and a reader had to trace
  the property layer to find where state actually lived. All of them are gone;
  call sites now reach the owning manager directly. 235 call sites were migrated
  across 16 production modules and the test suite, driven by mypy: with the
  properties deleted, every typed access became an `attr-defined` error naming the
  attribute, and the remaining Mock-based test fixtures surfaced as test failures.

  Two things a regex sweep would have missed. `Game`'s own methods assigned
  `self.active_conversation` / `active_terminal` / `active_snippet`, which after
  the removal would have silently created shadowing instance attributes on `Game`
  — writes landing there instead of on `ConversationEngine`, leaving two copies of
  the conversation state to disagree. And five dynamic accesses
  (`getattr(game, "text_input_buffer", "")` in the question renderers, three
  `hasattr(game, ...)` guards in `__main__` and `input_handler`) would have kept
  working while quietly returning the default: the typed answer would never have
  displayed and the response-dismissal branch would never have run. The guards
  were vestigial anyway — those attributes always exist on the engine — so they
  are now direct reads.

- **`npc_manager.py` mixed concerns** — 558 lines covering generation, placement,
  movement AI, conversations, and opinion tracking. Split into
  `npc_spawning.NPCSpawner` (places NPCs per floor, owns `all_npcs`),
  `npc_movement.NPCMovement` (wandering AI, owns `old_positions`), and
  `npc_relationships.NPCRelationships` (opinions). `NPCManager` is now a 268-line
  composition root that owns the save format and the current floor's `npcs`.
  Call sites reach the owning unit (`manager.movement.old_positions`,
  `manager.spawner.all_npcs`) rather than going through forwarding properties.
  `AnswerProcessor` no longer pokes the opinion dict directly — six raw accesses
  including two "seed the key to 0" blocks became two `update_opinion` calls,
  since that method starts an unknown NPC from neutral. New
  `tests/test_npc_units.py` covers the three units without building a Game
  (19 tests: layout vs random placement, the level-data copy, movement staying on
  walkable tiles and off the player and other NPCs, returning home, opinion
  accumulation).

- **Question renderers bypassed the shared wrapping helpers** — they called
  `wrap_text` directly and `print()`ed their own lines, so their tests had to
  capture stdout. They now draw through `backend.draw_text` via a new
  `render_helpers.draw_wrapped_text`, which takes a colour *name* rather than a
  colour *function* so `TestBackend` records each line as a `DrawCall`. The three
  `getattr(term, f"bold_{colors.ui_error}", term.bold_red)` lookups are gone, and
  the text-input box now draws its border, text, and padding as three positioned
  segments instead of one concatenated coloured string.
  `tests/test_question_renderers.py` asserts on recorded draw calls and gained
  coverage that stdout capture couldn't express: colour and bold per element,
  the footer's pinned row, that answers stop at the overlay bottom, and that
  overlong typed input is truncated to the box width.

- **`rendering.py` was monolithic** — 962 lines and 26 functions covering map,
  UI, and overlay drawing. Split into `map_renderer.py` (tiles, entities, erasing
  what moved), `ui_renderer.py` (status panel), `overlay_renderer.py` (modal
  panels and the victory screen), and `render_helpers.py` (colour lookup and
  wrapped-text primitives, previously private to `rendering.py`). `rendering.py`
  is now 99 lines: `draw_game` owns the frame's draw order and re-exports the
  overlay entry points that callers and tests reach for through it.

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
