# Known Issues

This document tracks known bugs and issues that need to be addressed in the Neural Dive codebase.

---

## Active Issues

### 1. Alternative Content Sets Show Empty Floors (CRITICAL)

**Status**: Not Fixed
**Priority**: High
**Reported**: 2025-11-14
**Affects**: All non-default content sets (Chinese HSK6, Geography, etc.)

#### Problem Description

When selecting alternative content sets (anything other than the default "Computer Science Algorithms"), the game loads but the first floor appears empty with no NPCs, making it impossible to progress:

- No NPCs spawn on floor 1
- Player cannot interact with anyone
- Cannot descend stairs (floor not complete without NPCs)
- Game becomes unplayable

#### Reproduction Steps

1. Start the game: `python3 -m neural_dive`
2. Select content set "2. Chinese HSK 6" (or any non-default)
3. Select any difficulty
4. Game loads but floor is empty
5. No NPCs visible on the map
6. Cannot progress

#### Investigation Findings

**Data Loading**:
- Content data loads successfully:
  - Questions: ✓ Loaded (5 questions for HSK6)
  - NPCs: ✓ Loaded (5 NPCs for HSK6)
  - Terminals: ✓ Loaded (3 terminals for HSK6)

**NPC Data Structure**:
```python
# Example NPC from chinese-hsk6/npcs.json
{
  "CHINESE_SCHOLAR": {
    "char": "文",
    "color": "red",
    "floor": 1,
    "npc_type": "specialist",
    "greeting": "你好！Welcome to...",
    "questions": ["vocab_arduous", "vocab_emerge", "vocab_profound"]
  }
}
```

**NPC Generation**:
- NPCManager receives correct data
- `game.npc_data` contains all 5 NPCs
- BUT `game.npcs` (actual spawned NPCs) is empty: `[]`
- `game.npc_manager.all_npcs` is also empty: `[]`

**Code Path**:
```
load_all_game_data('chinese-hsk6')
  → load_npcs(questions, 'chinese-hsk6')
    → Creates conversation objects ✓
    → Returns NPC data dictionary ✓

Game.__init__()
  → self.npc_data = loaded NPCs ✓
  → NPCManager initialized ✓
  → FloorManager.generate_floor(1) called
    → Should call NPCManager.generate_npcs_for_floor()
      → This is where NPCs should spawn ✗
```

#### Root Cause Hypothesis

The issue appears to be in the NPC generation phase, specifically in:
- `neural_dive/managers/npc_manager.py:121-164` - `generate_npcs_for_floor()`
- Possible causes:
  1. Level data (`PARSED_LEVELS`) may not exist for non-default content sets
  2. The `random_placement` fallback may not be triggering
  3. NPC filtering by floor may be failing
  4. Position placement may be failing for all NPCs

#### Debug Commands

```python
# Check data loading
from neural_dive.data_loader import load_all_game_data
questions, npcs, terminals = load_all_game_data('chinese-hsk6')
print(f'NPCs: {len(npcs)}')  # Should be 5

# Check game initialization
from neural_dive.game import Game
game = Game(seed=42, random_npcs=False, content_set='chinese-hsk6')
print(f'NPCs spawned: {len(game.npcs)}')  # Currently 0, should be 1+
print(f'NPC data: {list(game.npc_data.keys())}')  # Shows all NPCs
print(f'Current floor: {game.current_floor}')  # Should be 1

# Check level data
from neural_dive.data.levels import PARSED_LEVELS
print(f'Level 1 exists: {1 in PARSED_LEVELS}')  # Check if default levels work
```

#### Potential Fixes

**Option 1: Ensure Random Placement Works**
```python
# In npc_manager.py:generate_npcs_for_floor()
# Make sure random_placement fallback always triggers for content sets without level data
if level_data and "npc_positions" in level_data:
    self._generate_from_level_data(floor_npcs, level_data)
elif random_placement or True:  # ALWAYS fallback if level data missing
    self._generate_random_placement(floor_npcs, game_map, player_pos, map_width, map_height)
```

**Option 2: Create Level Files for Each Content Set**
- Add `neural_dive/data/content/chinese-hsk6/levels.py`
- Define `PARSED_LEVELS` with positions for Chinese characters
- Currently only `algorithms` content has proper level layouts

**Option 3: Debug Generation Logic**
- Add logging to see why NPCs aren't being placed
- Check if `floor_npcs` list is empty during generation
- Verify `_generate_random_placement()` is being called

#### Files to Investigate

- `neural_dive/managers/npc_manager.py:121-164` - Main generation logic
- `neural_dive/managers/npc_manager.py:166-193` - Level data generation
- `neural_dive/managers/npc_manager.py:195-239` - Random placement fallback
- `neural_dive/managers/floor_manager.py` - Floor generation orchestration
- `neural_dive/data_loader.py:116-150` - NPC data loading
- `neural_dive/data/content/*/levels.py` - Level layouts per content set

#### Workaround

Currently, no workaround exists. The default "Computer Science Algorithms" content set works correctly.

#### Next Steps

1. Add debug logging to `generate_npcs_for_floor()` to see exact execution path
2. Check if `random_npcs=True` parameter helps (default is False for testing)
3. Verify level data exists or fallback is properly triggered
4. Test with explicit parameters: `Game(random_npcs=True, content_set='chinese-hsk6')`
5. Consider creating minimal level files for all content sets

---

## Resolved Issues

### 1. Property Deleter Error on Exit (FIXED)

**Status**: ✅ Fixed
**Priority**: Medium
**Reported**: 2025-11-14
**Fixed**: 2025-11-14

#### Problem Description

When exiting the game, users saw an error:
```
Error: property '_last_answer_response' of 'Game' object has no deleter
```

This occurred when `__main__.py` tried to delete the property:
```python
del game._last_answer_response  # Line 140, 203
```

#### Root Cause

The `_last_answer_response` property in `game.py` had getter and setter methods but no deleter method, causing Python to raise an AttributeError when deletion was attempted.

#### Solution

Added deleter methods to all underscore-prefixed properties:

```python
# game.py:281-294
@property
def _last_answer_response(self) -> str | None:
    """Get last answer response from ConversationEngine."""
    return self.conversation_engine.last_answer_response

@_last_answer_response.setter
def _last_answer_response(self, value: str | None):
    """Set last answer response on ConversationEngine."""
    self.conversation_engine.last_answer_response = value

@_last_answer_response.deleter
def _last_answer_response(self):
    """Delete last answer response from ConversationEngine."""
    self.conversation_engine.last_answer_response = None
```

Similarly added deleters for `_show_greeting` property.

**Files Modified**:
- `neural_dive/game.py` - Added `@property.deleter` methods

---

### 2. Terminal Capability Error with 'dim' (FIXED)

**Status**: ✅ Fixed
**Priority**: High
**Reported**: 2025-11-14
**Fixed**: 2025-11-14

#### Problem Description

On some terminals, the game crashed on startup with:
```
Error: Unknown terminal capability, 'dim', or, TypeError for arguments ('    Learn fundamental....',): 'str' object cannot be interpreted as an integer
```

This occurred in the content selection menu when trying to use `term.dim()` to render description text.

#### Root Cause

Some terminals don't support the 'dim' text attribute, causing `term.dim()` to fail with a TypeError.

#### Solution

Added try-except fallback in `menu.py`:

```python
# menu.py:164-171
desc_text = f"    {desc}"
try:
    desc_line = term.dim(desc_text)
except (TypeError, AttributeError):
    # Fallback if terminal doesn't support dim
    desc_line = term.normal + desc_text
print(term.move_xy(x_offset, y_pos + 1) + desc_line)
```

**Files Modified**:
- `neural_dive/menu.py` - Added terminal capability fallback

---

## Reporting New Issues

If you encounter a bug:

1. **Check this document** to see if it's already known
2. **Gather information**:
   - Python version (`python3 --version`)
   - Operating system
   - Terminal emulator
   - Steps to reproduce
   - Error messages (if any)
3. **Report at**: https://github.com/qyearsley/neural-dive/issues
4. **Include**:
   - Clear description of the problem
   - Steps to reproduce
   - Expected behavior vs actual behavior
   - Screenshots (if applicable)

---

**Last Updated**: 2025-11-14
