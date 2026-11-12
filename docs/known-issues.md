# Known Issues

Runtime bugs in Neural Dive. Architectural debt lives in
[`improvements.md`](improvements.md).

Last reviewed: 2026-11-12.

## Active Issues

None currently known.

## Reporting a Bug

Please report at <https://github.com/qyearsley/neural-dive/issues> and include:

- Python version (`python3 --version`), OS, and terminal emulator
- Steps to reproduce
- Expected vs actual behaviour
- Any error message or screenshot

## Resolved

Each entry says what broke and names the test that guards it.

- **A hint token let you pick an answer that was not on screen.** The input
  handler accepted `1`-`4` even for eliminated options. Guarded by
  `TestAnswersMustBeOnScreen` (`test_input_handler.py`).
- **`Q` and `L` ended a run on one keystroke.** Both now ask for `Y` first.
  Guarded by `TestDestructiveKeysAskFirst` and `TestExitKeysMatchTheFooter`
  (`test_input_handler.py`).
- **Three overlays had three dismissal contracts.** All close on ESC, Enter,
  Space, `q`, or the opening key. Guarded by `TestOneDismissalContract`
  (`test_input_handler.py`).
- **A yes/no question could disarm its own exit key.** Stray letters filled the
  text buffer. Guarded by `TestExitKeysMatchTheFooter` (`test_input_handler.py`).
- **Loading a save re-rolled each NPC's questions and could soft-lock the run.**
  The save now records the drawn question ids and answer order. Guarded by
  `TestConversationsSurviveALoad` (`test_npc_manager.py`) and
  `TestCompletedAlwaysMeansCounted` (`test_answer_processor.py`).
- **One hint token hid an answer slot for the rest of the run.** Eliminated
  indices were never cleared between questions. Guarded by
  `TestHintEliminationsAreScopedToOneQuestion` (`test_game_core.py`) and
  `TestEliminatedAnswersDoNotOutlastTheirQuestion` (`test_answer_processor.py`).
- **Collected items came back, so hint tokens were unlimited.** Floor items are
  now generated once and cached. Guarded by `TestCollectedItemsStayCollected`
  (`test_game_core.py`).
- **After a load, NPC positions stopped being saved.** The live list and the
  saved list held different `Entity` objects. Guarded by
  `TestNPCPositionsKeepBeingSaved` (`test_game_core.py`).
- **`--seed` did not make question selection reproducible.** Selection used the
  global `random`. Guarded by `TestSeededQuestionSelectionIsReproducible`
  (`test_npc_manager.py`), `TestSeedingIsLocal` (`test_conversation.py`), and
  `TestHintEliminationUsesTheGameGenerator` (`test_conversation_engine.py`).
- **The quest completion bonus was paid on every interaction.** No shipped
  content has a quest NPC, so it could not fire. Guarded by
  `TestQuestBonusIsAwardedOnce` (`test_interaction_handler.py`).
- **"Time Played" counted time the game was closed.** The tracker now banks
  seconds and uses a monotonic clock. Guarded by `TestTimeTracking` and
  `TestTimeAcrossSaveAndLoad` (`test_stats_tracker.py`).
- **Loading a save from floor 2 or deeper restored floor 1's map.** Guarded by
  `test_loading_a_deeper_save_restores_that_floors_map` (`test_game_core.py`).
- **Randomly placed items moved on load.** The save now records the pickups.
  Guarded by `test_an_unseeded_game_restores_its_entities_where_they_were`
  (`test_game_core.py`).
- **Loading a floor-1 save produced a map with no NPCs.** Spawning consumed the
  shared level data. Guarded by `test_loading_a_floor_one_save_keeps_the_npcs`
  (`test_game_core.py`).
- **Answering in a loaded game said "Not in a conversation".** `AnswerProcessor`
  held the pre-load managers. Guarded by `test_can_answer_questions_after_load`
  (`test_game_core.py`).
- **Phantom walls on level transition.** `term.clear` was used as an attribute,
  not called. No test guards it; check by hand with `make run-debug`.
