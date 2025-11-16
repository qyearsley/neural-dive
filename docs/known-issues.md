# Known Issues

This document tracks known bugs and issues in Neural Dive.

---

## Active Issues

### Phantom Walls on Level Transition

**Severity:** High
**Affects:** Level transitions (Floor 1 → Floor 2)
**Status:** Fix Applied (Needs Testing)

**Description:**
When transitioning to the second level, visual artifacts from the first level persist:
- Walls from the first level appear as "phantom" walls
- Actual walls on the new level are not rendered correctly
- This creates a confusing/unplayable state

**Fix Applied:**
Modified `rendering.py:104` to use `term.clear()` as a method call instead of attribute concatenation. This ensures the terminal display buffer is completely cleared before rendering the new floor.

**Location:** `neural_dive/rendering.py:104`

**Testing Instructions:**
1. Run: `make run-debug`
2. Navigate to stairs on floor 1
3. Descend to floor 2
4. Verify: No phantom walls from floor 1 remain
5. Verify: New floor walls render correctly

If you encounter any problems, please report them at: https://github.com/qyearsley/neural-dive/issues

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
