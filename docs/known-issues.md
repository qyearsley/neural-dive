# Known Issues

Runtime bugs in Neural Dive. Architectural debt lives in
[`tech-debt.md`](tech-debt.md).

Last reviewed: 2026-09-10.

## Active Issues

None currently known.

## Reporting a Bug

Please report at <https://github.com/qyearsley/neural-dive/issues> and include:

- Python version (`python3 --version`), OS, and terminal emulator
- Steps to reproduce
- Expected vs actual behaviour
- Any error message or screenshot

## Resolved

### A hint token let you pick an answer that was not on screen

**Affected:** every multiple choice question answered after spending a hint.

The renderer skips the indices in `eliminated_answers`, but the input handler
accepted `"1"`-`"4"` unconditionally. Pressing the number of an eliminated
option therefore submitted an answer the player could not see, and the
`answer_key_hint` footer ("Press 1/3/4") disagreed with what the game accepted.
The same hardcoded range would have made a five-option question unanswerable.

`ConversationHandler._handle_multiple_choice_question` now builds the accepted
keys from the question's own answers minus the eliminated indices. A number key
outside that set is swallowed rather than acted on, so the numbering of the
options that remain does not shift.

Covered by `TestAnswersMustBeOnScreen` in `tests/test_input_handler.py`.

### `Q` and `L` ended a run on one keystroke

**Affected:** every run.

`Q` quit immediately and `L` loaded the save over the current run, both without
confirmation and both from keys that sit next to the movement keys. `q` also
meant "leave this conversation", so the game taught the habit that killed the
run.

Both now arm a confirmation instead of acting: the next key either confirms with
`Y` or cancels. Any key resolves the prompt, so it cannot strand the player, and
the prompts fit the message line at the minimum window width. `q` inside a
conversation now closes the conversation in every stage except while a short
answer is being typed, where it is a letter an answer may need ("queue",
"quicksort").

Covered by `TestDestructiveKeysAskFirst` and `TestExitKeysMatchTheFooter` in
`tests/test_input_handler.py`.

### Three overlays, three dismissal contracts

**Affected:** the inventory, snippet, and info terminal panels.

Inventory closed on ESC or `V`, snippets on ESC or `S`, and the info terminal on
*any* key. Enter, Space and `q` were reported as handled by the first two and
then did nothing, while a keystroke aimed at the map threw the terminal text
away mid-sentence.

There is one contract now: ESC, Enter, Space, `q`, and the key that opened the
panel close it; everything else is swallowed. The new help overlay uses it too.

Covered by `TestOneDismissalContract` in `tests/test_input_handler.py`.

### A yes/no question could disarm its own exit key

**Affected:** yes/no questions.

Any letter other than `y` or `n` fell through to the text-input path and landed
in `text_input_buffer`. The `X` exit is guarded by an empty buffer, so a single
stray keystroke left ESC as the only way out of a question that never reads the
buffer at all. Yes/no questions no longer collect typed text.

Covered by `TestExitKeysMatchTheFooter` in `tests/test_input_handler.py`.

### Loading a save re-rolled each NPC's questions, and could soft-lock the run

**Affected:** every save, most severely unseeded ones.

The save recorded only `completed` and `current_question_idx` per conversation.
On load, `NPCManager.__init__` drew a fresh question set and a fresh count. The
content of a conversation therefore changed on every load. Worse, a reload could
produce a two-question conversation while the saved index sat at 2. The NPC then
reported "Conversation completed!" without ever being added to `npcs_completed`,
so its floor requirement could never be met and the run could not continue.

Two changes fix it. `NPCManager.to_dict` now records the drawn question ids and
each question's answer order, and `from_dict` rebuilds that exact conversation
from the authored pool. And `AnswerProcessor._mark_complete` sets `completed`,
adds the NPC to `npcs_completed`, and credits the quest together, so a
conversation can never be marked complete without being counted.

A save that predates the new field still loads: the index is clamped to the
length of the conversation. A recorded question id the content set no longer
defines is skipped, and a save whose questions have all disappeared falls back
to the fresh draw.

Covered by `TestConversationsSurviveALoad` in `tests/test_npc_manager.py` and
`TestCompletedAlwaysMeansCounted` in `tests/test_answer_processor.py`.

### One hint token hid an answer slot for the rest of the run

**Affected:** every run in which a hint token was used.

`ConversationEngine.eliminated_answers` holds answer *indices*, and the renderer
skips them. Nothing on the live path ever cleared the set: `Game.interact`
assigned `active_conversation` directly instead of calling
`start_conversation`, and `AnswerProcessor` advanced the question index without
touching it. The three engine methods that did clear it had no non-test callers.
So a hint spent on one question hid that index on every question after it, on
every NPC after it. When a later question's correct answer landed on that index,
the player saw three options and no right one.

`Game.interact` and `Game.exit_conversation` now go through the engine, and
`AnswerProcessor` calls `clear_eliminated_answers` on every question transition.

Covered by `TestHintEliminationsAreScopedToOneQuestion` in
`tests/test_game_core.py` and `TestEliminatedAnswersDoNotOutlastTheirQuestion`
in `tests/test_answer_processor.py`.

### Collected items came back, so hint tokens were unlimited

**Affected:** every run that re-entered a floor, and every load.

`Game._generate_floor` cleared and rebuilt `item_pickups` from scratch, and it
runs on every stairs transition. Nothing recorded which pickups were gone.
Floor 2's player start `(2, 2)` is next to its up-stairs `(3, 1)`, so stepping
up and back down restocked the floor as often as the player liked.

Items are now generated once per floor and kept in `Game._floor_items`. The
list the player walks over is the cached list, so a pickup removes itself for
good. The save records the cache, so a load restores what is left rather than
regenerating it.

Covered by `TestCollectedItemsStayCollected` in `tests/test_game_core.py`.

### After a load, NPC positions and wander state stopped being saved

**Affected:** every save taken after a load, or after re-entering a floor.

`NPCSpawner._build` always constructed a new `Entity` but only appended it to
`all_npcs` when the name was new. `NPCManager.to_dict` serializes `all_npcs`.
So from the second generation of a floor onward, the live `npcs` list and
`all_npcs` held different objects for the same NPC: the wandering AI moved one
and the save file wrote the other. The `NPCSpawner` docstring claimed the
opposite.

`_build` now returns the existing `Entity` for a known NPC, so there is exactly
one object per NPC and it keeps its position and wander state.

Covered by `TestNPCPositionsKeepBeingSaved` in `tests/test_game_core.py`.

### `--seed` did not make question selection reproducible

**Affected:** `make run-debug` and any `--seed` run.

`create_randomized_conversation` drew its question sample, its question order,
and its answer order from the module-level `random`, not from the game's seeded
generator. Only the question *count* was seeded, so two identically seeded games
asked different questions depending on what else in the process had touched
`random`. `use_hint_token` had the same problem.

Worse, passing `seed=` to `randomize_answers` or `create_randomized_conversation`
called `random.seed()` on the process-wide generator, reseeding every other
random draw in the program.

Both functions now take an `rng` argument, and a `seed` builds a private
`random.Random` for that call instead of reseeding the process.
`ConversationEngine` takes the game's generator for hint eliminations.

Seeded output has shifted: a given seed no longer produces the questions it did
before this fix. That is expected — the old output depended on global state.

Covered by `TestSeededQuestionSelectionIsReproducible` in
`tests/test_npc_manager.py`, `TestSeedingIsLocal` in `tests/test_conversation.py`,
and `TestHintEliminationUsesTheGameGenerator` in
`tests/test_conversation_engine.py`.

### Smaller fixes

- **The quest completion bonus was awarded on every interaction.**
  `InteractionHandler._handle_quest_npc` read `get_completion_bonus()` and paid
  it each time, with no claimed flag, so holding Space at a quest NPC would have
  been unlimited coherence. No quest NPCs ship in the current content, so it
  could not fire in a real run. `QuestManager.claim_completion_bonus()` now pays
  once and records it in the save. Covered by `TestQuestBonusIsAwardedOnce` in
  `tests/test_interaction_handler.py`.
- **`NPCDefeated` always reported "specialist".**
  `StateManager.complete_conversation` read `npc_info.get("type")`, but
  `data_loader` stores that key as `npc_type`. Covered by
  `test_npc_defeated_reports_the_real_npc_type` in `tests/test_state_manager.py`.
- **`StateManager.change_floor` did not rebuild the floor.** It assigned
  `floor_manager.current_floor`, the same shape as the floor-2 map bug below. It
  now calls `generate_floor` and regenerates the floor's entities. Covered by
  `test_changing_floor_brings_the_new_floors_map_and_entities` in
  `tests/test_state_manager.py`.

### "Time Played" counted wall-clock time, including time the game was closed

**Affected:** every run resumed from a save, and any run spanning a system clock change.

`StatsTracker` kept a `start_time` wall-clock timestamp and reported
`time.time() - start_time`. The timestamp was serialized as an absolute value and
restored verbatim, so the clock never stopped: saving a run, quitting, and
resuming the next day added the whole night to the victory screen's Time Played.
The same reading also drifted with the system clock — stepping it back an hour
(NTP, DST, sleep/wake) made `get_time_played()` return a negative number.

The tracker now banks `accumulated_seconds` and measures the current session from
a `time.monotonic()` reading taken at construction, so `get_time_played()` is
banked time plus this session's elapsed time. `to_dict` writes the running total
instead of a timestamp, and `from_dict` resumes from it. Time spent in menus,
overlays, and conversations still counts — those are where the game is played,
not idle time.

Saves written in the old format carry only `start_time`. That records when the run
began in real-world terms, not how long it was played, so there is nothing to
recover from it: such a save loads with its play-time total at zero rather than
importing hours the player spent away. The pre-fix portion of that run's time is
lost; everything after the load is measured correctly.

Covered by `TestTimeTracking` and `TestTimeAcrossSaveAndLoad` in
`tests/test_stats_tracker.py`, plus
`test_loading_a_save_does_not_count_the_time_the_game_was_closed` and
`test_loading_an_old_format_save_does_not_report_wall_clock_time` in
`tests/test_game_core.py`.

### Loading a save from floor 2 or deeper restored floor 1's map

**Affected:** every save taken below floor 1.

The loaded game reported the right floor number and placed that floor's NPCs and
entities, but the walls were floor 1's. NPCs and stairs ended up in places the
layout didn't allow.

The deserializer assigned `game.current_floor`, which forwards to
`FloorManager.current_floor` — a plain attribute that updates the number without
rebuilding the map. `FloorManager.from_dict` did regenerate the map, but the
serializer never called it. Fixed by having `GameContext.create` position the
floor manager with `generate_floor(start_floor, player)` before any entity
generation, so the map, the player's start position, and the floor number are
established together.

Covered by `test_loading_a_deeper_save_restores_that_floors_map` in
`tests/test_game_core.py`.

### Randomly placed items moved when a save was loaded

**Affected:** saves taken with random placement (`random_npcs=True`, the default).

Item pickups came back on different tiles than the save recorded, because the
deserializer generated the floor twice and each pass drew from the game's RNG.
The first fix assembled a loaded game in one pass, so floor entities are
generated exactly once.

That fix only held for a *seeded* game. An unseeded save records `seed: null`,
so the load builds `random.Random(None)` and any re-rolled placement lands
somewhere else — which is every real run. The save now records the pickups
themselves, per floor, and a load restores them instead of redrawing them.

Covered by `test_loading_preserves_randomly_placed_entities` and
`test_an_unseeded_game_restores_its_entities_where_they_were` in
`tests/test_game_core.py`.

### Loading a floor-1 save produced a map with no NPCs

**Affected:** `Game.load_game` / `GameSerializer` for saves made on floor 1.

Loading a save taken on floor 1 restored a map with zero NPCs, so there was
nobody to talk to and the floor could never be completed. Saves from floor 2
and deeper were unaffected, which is why it went unnoticed.

`NPCManager._generate_from_level_data` placed NPCs by popping positions off
`level_data["npc_positions"]`, mutating the long-lived level data rather than a
copy. The deserializer regenerates the saved floor after `Game.__init__` has
already generated floor 1, so floor 1 got generated twice — and the second pass
found the position lists empty and placed nothing. Fixed by copying the
per-character position lists before consuming them, which makes floor
generation repeatable.

Covered by `test_loading_a_floor_one_save_keeps_the_npcs` and
`test_generating_a_floor_twice_places_the_same_npcs` in
`tests/test_game_core.py`.

### Answering any question in a loaded game said "Not in a conversation"

**Affected:** every game restored from a save (`L` in-game or `--load`).

After loading, talking to an NPC showed the greeting and the first question
normally, but any answer came back as "Not in a conversation." — the conversation
could never progress.

`GameSerializer` replaces the managers on the freshly built `Game`, but
`AnswerProcessor` had already captured the originals, so it validated against an
empty `ConversationEngine` while the renderer and input handler read the restored
one. The same staleness silently applied coherence, stats, and quest updates to
discarded managers. Fixed in 6eae393 by extracting
`Game.wire_manager_dependencies()` and calling it from the deserializer.

Covered by `test_load_rewires_managers_into_collaborators` and
`test_can_answer_questions_after_load` in `tests/test_game_core.py`.

### Phantom walls on level transition

**Affected:** floor transitions, most visibly floor 1 → floor 2.

Walls from the previous floor stayed on screen while the new floor's walls
failed to draw, leaving the map unreadable.

The cause was `term.clear` being concatenated as an attribute rather than
called, so the terminal buffer was never actually cleared. Fixed in
`neural_dive/rendering.py` by calling `term.clear()`.

To confirm it stays fixed: `make run-debug`, walk to the stairs on floor 1,
descend, and check that no floor-1 walls remain and that the new walls render.
