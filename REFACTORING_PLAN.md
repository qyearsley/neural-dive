# Neural Dive Refactoring Plan

This document outlines potential refactoring opportunities identified after the recent simplification work (algorithms-only content, NORMAL difficulty, cyberpunk theme).

**Status:** Planning Document
**Created:** 2026-01-24
**Priority:** Medium (no immediate action required - codebase is stable)

---

## Overview

The codebase has been successfully simplified from multi-content/multi-theme/multi-difficulty to a focused CS education game. However, this simplification revealed a new maintenance burden: **the Game class became a large proxy layer** with 100+ properties delegating to 4 manager classes.

**Current State:**
- ✅ All 197 tests pass
- ✅ Single content set (algorithms)
- ✅ Single difficulty (NORMAL)
- ✅ Single theme (cyberpunk dark)
- ✅ Expanded question variety (227 questions, NPCs use full topic pools)

**Key Issue:** Code was refactored for extensibility (managers pattern), but now that extensibility is gone, we have abstraction overhead without the benefit.

---

## High-Impact Refactoring Opportunities

### 1. Remove Game Property Proxy Layer (HIGHEST IMPACT)

**Problem:** Game class has 38 @property decorators that just delegate to managers (140+ lines of boilerplate).

**Current Pattern:**
```python
# game.py:172-335
@property
def coherence(self) -> int:
    """Get coherence from PlayerManager."""
    return self.player_manager.coherence

@property
def max_coherence(self) -> int:
    """Get max coherence from PlayerManager."""
    return self.player_manager.max_coherence

# ... 36 more properties like this
```

**Options:**

**Option A: Direct Manager Access (Recommended)**
- Remove all proxy properties
- Update callers to use `game.player_manager.coherence` instead of `game.coherence`
- **Benefit:** Removes 140+ lines, makes code flow clearer
- **Effort:** 4-6 hours (need to update ~50 call sites)
- **Risk:** Low (tests will catch any missed updates)

**Option B: Keep Properties, Document Decision**
- Keep properties as intentional API
- Add clear comments explaining backward compatibility
- **Benefit:** No code changes needed
- **Effort:** 30 minutes (documentation only)
- **Risk:** None

**Recommendation:** Option B for now (stable codebase), Option A if adding new features

---

### 2. Consolidate Overlay Rendering

**Problem:** 5 overlay functions (conversation, completion, terminal, inventory, snippet) follow identical setup patterns.

**Current Pattern:**
```python
# rendering.py has 5 similar functions:
def draw_conversation_overlay(...)  # 80 lines
def draw_completion_overlay(...)     # 70 lines
def draw_terminal_overlay(...)       # 60 lines
def draw_inventory_overlay(...)      # 55 lines
def draw_snippet_overlay(...)        # 50 lines

# Each does:
# 1. Calculate dimensions
# 2. Create OverlayRenderer
# 3. Draw border and background
# 4. Render specific content
```

**Solution:**
```python
class OverlayRenderer:
    """Base class for rendering overlays."""

    def render(self, content_lines: list[str], title: str | None = None):
        """Unified rendering logic."""
        # Shared setup, border, background
        self._draw_content(content_lines)

def draw_conversation_overlay(...):
    """Render conversation - delegates to OverlayRenderer."""
    content = _format_conversation_content(...)
    OverlayRenderer(term, game, chars, colors).render(content, "Conversation")
```

**Benefit:** Reduces ~200 lines of duplicated setup code
**Effort:** 3-4 hours
**Risk:** Medium (overlay rendering is UI-critical, needs careful testing)

---

### 3. Simplify Input Handling State Checks

**Problem:** `__main__.py:314-470` has fragile `hasattr()` checks throughout input handlers.

**Current Pattern:**
```python
# Multiple places checking:
if hasattr(game, '_show_greeting') and game._show_greeting:
    # Show greeting
if hasattr(game, '_last_answer_response') and game._last_answer_response:
    # Show response
```

**Solution:**
```python
# Add to ConversationEngine:
@dataclass
class ConversationUIState:
    show_greeting: bool = False
    last_response: str | None = None
    awaiting_input: bool = False

# In ConversationEngine:
self.ui_state = ConversationUIState()

# In handlers:
if game.conversation_engine.ui_state.show_greeting:
    # Show greeting
```

**Benefit:** Centralizes conversation UI state, removes fragile hasattr checks
**Effort:** 2-3 hours
**Risk:** Low (state already exists, just needs better organization)

---

### 4. Consider Merging Small Managers

**Problem:** 4 manager classes totaling 1,417 lines have varying cohesion levels.

**Current Structure:**
```
managers/
├── conversation_engine.py  (213 lines) - manages active conversation
├── floor_manager.py        (245 lines) - manages floors/maps
├── npc_manager.py          (551 lines) - manages NPCs
└── player_manager.py       (390 lines) - manages player stats
```

**Analysis:**
- `ConversationEngine` (213 lines) could move into `Game` class directly (it's mostly orchestration)
- `PlayerManager` (390 lines) is well-sized and cohesive - keep as is
- `FloorManager` (245 lines) is well-sized and cohesive - keep as is
- `NPCManager` (551 lines) is largest but handles complex NPC AI - keep as is

**Recommendation:**
- **Option A (Conservative):** Keep all managers separate (current state is good)
- **Option B (Simplify):** Merge ConversationEngine into Game class (saves one abstraction layer)

**Effort:** 3-4 hours for Option B
**Benefit:** Reduces manager count from 4 to 3, slightly simpler architecture
**Risk:** Low (ConversationEngine is mostly delegating to conversation objects)

---

### 5. Inline Entity Placement Logic

**Problem:** With fixed theme/content/difficulty, entity placement could be simpler.

**Current:** `EntityPlacementStrategy` class (192 lines) with 3 modes (level-based, random, default)

**Analysis:**
- Level-based placement is used (good)
- Random placement is used for testing
- Default positions are fallbacks

**Recommendation:** Keep as-is. The placement strategy is clean and handles edge cases well. Simplifying would save ~50 lines but lose flexibility for testing.

---

## Low-Priority Improvements

### 6. Remove Unused CYBERPUNK_LIGHT Color Scheme

Since we hardcoded to dark theme, `CYBERPUNK_LIGHT` is unused (saves ~30 lines).

**Effort:** 15 minutes
**Benefit:** Minor code cleanup

### 7. Simplify load_content_metadata()

Since only algorithms content exists, this function could be simplified or inlined.

**Effort:** 30 minutes
**Benefit:** Minor cleanup

### 8. Remove Theme/CharacterSet/ColorScheme Classes

Since only cyberpunk dark is used, these dataclasses could be replaced with constants.

**Effort:** 2 hours
**Benefit:** ~100 lines saved, but loses structure
**Risk:** High (rendering code assumes these structures)

---

## Implementation Strategy

### Phase 1: Documentation & Monitoring (Now)
- ✅ Document current architecture decisions
- Monitor for pain points in development
- **No code changes**

### Phase 2: If Adding New Features (Future)
Consider these refactorings if/when:
- Adding new gameplay mechanics (overlay rendering consolidation would help)
- Expanding conversation system (state management improvement would help)
- Needing to understand code flow (removing proxy layer would help)

### Phase 3: Major Refactoring (Optional, 1-2 weeks)
If undertaking major work:
1. Remove Game property proxy layer (4-6 hours) ← HIGHEST IMPACT
2. Consolidate overlay rendering (3-4 hours)
3. Simplify input handling state (2-3 hours)
4. Consider merging ConversationEngine into Game (3-4 hours)

**Total Effort:** 12-17 hours
**Total Benefit:** ~400-500 lines removed, clearer code flow

---

## Risk Assessment

**Low Risk:**
- Removing proxy properties (tests catch everything)
- Simplifying state checks (well-defined behavior)
- Merging ConversationEngine (small, focused class)

**Medium Risk:**
- Consolidating overlay rendering (UI-critical, needs visual testing)

**High Risk:**
- Removing theme infrastructure (deeply embedded in rendering)

---

## Decision: Keep Current Architecture

**Recommendation:** Keep the current architecture as-is for now.

**Rationale:**
1. All 197 tests pass
2. Code is stable and maintainable
3. The "proxy layer problem" is real but not blocking development
4. Refactoring now would be premature optimization
5. Better to wait until adding new features to see what actually needs changing

**When to Revisit:**
- If adding significant new features (conversation system, new NPC types, etc.)
- If finding the proxy layer confusing during development
- If performance becomes an issue (unlikely for this game)

---

## Quick Wins Already Completed ✅

These were identified and completed 2026-01-24:

1. ✅ Removed dead `_localize()` method (~20 lines)
2. ✅ Fixed duplicate `time` imports in `__main__.py`
3. ✅ Removed unused CLASSIC theme (~80 lines)
4. ✅ Simplified content set abstraction
5. ✅ Simplified difficulty system helpers
6. ✅ Removed HANZI theme (~110 lines)
7. ✅ Removed BEGINNER/ADVANCED/EXPERT difficulties (~60 lines)
8. ✅ Removed content selection UI (~118 lines)
9. ✅ Removed chinese-hsk6 and geography content (~350+ files)

**Total Removed:** ~750+ lines and 350+ files

---

## Conclusion

The Neural Dive codebase is in excellent shape after recent simplifications:
- ✅ Focused on core CS education
- ✅ All tests passing
- ✅ Code is maintainable
- ✅ Question variety greatly expanded

The identified refactoring opportunities are **optional optimizations**, not critical issues. The current architecture works well. Consider these refactorings only when:
1. Adding new features that would benefit from the changes
2. Finding the current structure confusing during development
3. Having dedicated time for improvement work

**Remember:** Working code > perfect code. Don't refactor for the sake of refactoring.
