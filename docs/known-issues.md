# Known Issues

Runtime bugs in Neural Dive. Architectural debt lives in
[`tech-debt.md`](tech-debt.md).

Last reviewed: 2026-08-15.

## Active Issues

None currently known.

## Reporting a Bug

Please report at <https://github.com/qyearsley/neural-dive/issues> and include:

- Python version (`python3 --version`), OS, and terminal emulator
- Steps to reproduce
- Expected vs actual behaviour
- Any error message or screenshot

## Resolved

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
Fixed by assembling a loaded game in one pass, so floor entities are generated
exactly once.

Covered by `test_loading_preserves_randomly_placed_entities` in
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
