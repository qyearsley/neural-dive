# Claude Development Guide for Neural Dive

Guidance for AI assistants working on this codebase. Project conventions are
enforced by `ruff` and `mypy`; this doc focuses on architecture and
project-specific patterns rather than restating generic Python style.

## Commands

```bash
make help          # All available targets
make dev-install   # Install dev dependencies (run once)

make check         # Lint + format-check + typecheck (run before pushing)
make test          # Run all tests
make fix           # Auto-fix lint and format

make run           # Launch the game
make run-debug     # Launch with a fixed seed (42) for reproducible debugging
```

## Layout

```
neural_dive/
├── __main__.py              # Entry point, game loop
├── game.py                  # Game class — facade over the managers below
├── game_builder.py          # Constructs Game and its managers
├── game_serializer.py       # Save/load state
├── data_loader.py           # Loads questions, NPCs, levels, snippets
├── data/
│   ├── content/algorithms/  # Canonical content (questions, NPCs, levels)
│   └── levels.py            # Re-export shim → content/algorithms/levels.py
├── managers/
│   ├── player_manager.py        # Coherence, knowledge, inventory
│   ├── npc_manager.py           # NPC generation, movement AI, opinions
│   ├── conversation_engine.py   # Active conversation state
│   ├── answer_processor.py      # Answer validation + reward/penalty fan-out
│   ├── floor_manager.py         # Current floor, completion checks
│   ├── floor_entity_generator.py # Spawn entities for a floor
│   ├── interaction_handler.py   # Player ↔ entity interaction dispatch
│   ├── movement_controller.py   # Tile-level movement validation
│   ├── quest_manager.py         # Main quest progress
│   ├── state_manager.py         # Centralised mutations + EventBus integration
│   └── stats_tracker.py         # Score, accuracy, time
├── events.py                # EventBus + typed event dataclasses
├── backends/
│   ├── backend.py           # RenderBackend protocol
│   ├── blessed_backend.py   # Real terminal backend
│   └── test_backend.py      # Captures draw calls for tests
├── rendering.py             # Map/UI/overlay drawing (long; see tech-debt)
├── question_renderers.py    # Strategy per QuestionType
├── entity_renderers.py      # Strategy per EntityType
├── models.py                # Question, Answer, Conversation dataclasses
├── entities.py              # Entity / Player / Stairs / InfoTerminal
└── tests/                   # pytest test suite
```

## Architecture notes

**Game as facade.** `Game` exposes ~24 forwarding properties to the underlying
managers (`game.coherence` → `player_manager.coherence`, etc.). New code should
prefer reaching the manager directly when feasible; the property layer is on
the cleanup list (`docs/tech-debt.md`).

**State changes flow through `StateManager` and emit events** on the
`EventBus`. This is how features like analytics, achievements, and replay are
plugged in. Mutations in `Game` directly are legacy; route new logic through
the appropriate manager + event.

**Content is loaded from `data/content/algorithms/`.** Old paths
(`data/npcs.json`, `data/questions.json`) were deleted; only the canonical
content set remains. `data/levels.py` is a thin re-export shim for legacy
imports — edit `data/content/algorithms/levels.py` instead.

**Floor requirements are dynamic**, computed by
`data_loader.compute_floor_requirements` from each NPC's `floor` and
`npc_type`. There is no static `FLOOR_REQUIRED_NPCS` config.

## Common patterns

### Loading data
```python
from neural_dive.data_loader import load_all_game_data

questions, npcs, levels, snippets = load_all_game_data()
```

### Creating a conversation
```python
from neural_dive.conversation import create_randomized_conversation

conv = create_randomized_conversation(
    npc_name="ALGO_SPIRIT",
    npc_data=npc_data["ALGO_SPIRIT"],
    questions=all_questions,
    seed=42,
    num_questions=3,
)
```

### Map access
```python
tile = game.game_map[y][x]   # y first, then x
height = len(game.game_map)
width = len(game.game_map[0])
```

### Configuration constants
Live in `neural_dive/config.py`. Use the named constant — don't inline magic
numbers (`STARTING_COHERENCE`, `MAX_COHERENCE`,
`CORRECT_ANSWER_COHERENCE_GAIN`, etc.).

## Adding new content

### A new NPC
1. Add an entry to `neural_dive/data/content/algorithms/npcs.json` with `char`,
   `color`, `floor`, `npc_type`, `greeting`, and a list of `questions` IDs.
2. Place the NPC's `char` in the appropriate floor layout in
   `neural_dive/data/content/algorithms/levels.py`. NPC chars must be single
   letters surrounded by non-letters (a run of two letters is parsed as a text
   label, not an NPC).
3. Run `uv run validate_questions.py` to confirm question references resolve.

### A new question
1. Edit `neural_dive/data/content/algorithms/questions.json` following the
   schema in `docs/question-guide.md`.
2. Reference its ID from one or more NPCs in `npcs.json`.
3. Run `uv run validate_questions.py`.

### A new question type
1. Add the variant to `QuestionType` in `question_types.py`.
2. Add a renderer (implementing the `QuestionRenderer` protocol) to
   `question_renderers.py` and register it in `_QUESTION_RENDERERS`.
3. Handle the new type in `AnswerProcessor.answer_text_question` /
   `answer_multiple_choice` (or add a new dispatch).
4. Add tests in `tests/test_question_renderers.py` and
   `tests/test_answer_processor.py`.

## Debugging

- **Reproducible runs:** `make run-debug` (fixed seed 42) or pass `seed=42` to
  `Game(...)`.
- **Inspect state:** `game.get_state()` returns a dict snapshot.
- **`make typecheck`** is currently noisy in test files but production code is
  clean. New mypy errors in `neural_dive/` (non-test) should be fixed before
  merging.

## Testing

The pytest suite covers all managers, rendering helpers, and answer processing.
Conventions:

- Manager tests instantiate the real manager when it's lightweight
  (`PlayerManager`, `StatsTracker`, `QuestManager`, `ConversationEngine`); use
  `Mock()` for the heavier `NPCManager` (see `tests/test_answer_processor.py`).
- Use `TestBackend` from `neural_dive.backends.test_backend` to verify
  rendering (it records draw calls and accepts blessed-style attribute access
  via `__getattr__`).
- Capture stdout with `redirect_stdout(io.StringIO())` for renderers that
  `print()` directly (see `tests/test_question_renderers.py`).
- Use fixed seeds for any test that exercises randomness.

## Pointers

- Open architectural debt: `docs/tech-debt.md`
- Runtime bugs: `docs/known-issues.md`
- Question authoring: `docs/question-guide.md`
- Content set authoring: `docs/content-guide.md`
- User-facing docs: `README.md`
