# Known Issues

Runtime bugs in Neural Dive. Architectural debt lives in
[`tech-debt.md`](tech-debt.md).

Last reviewed: 2026-08-14.

## Active Issues

None currently known.

## Reporting a Bug

Please report at <https://github.com/qyearsley/neural-dive/issues> and include:

- Python version (`python3 --version`), OS, and terminal emulator
- Steps to reproduce
- Expected vs actual behaviour
- Any error message or screenshot

## Resolved

### Phantom walls on level transition

**Affected:** floor transitions, most visibly floor 1 → floor 2.

Walls from the previous floor stayed on screen while the new floor's walls
failed to draw, leaving the map unreadable.

The cause was `term.clear` being concatenated as an attribute rather than
called, so the terminal buffer was never actually cleared. Fixed in
`neural_dive/rendering.py` by calling `term.clear()`.

To confirm it stays fixed: `make run-debug`, walk to the stairs on floor 1,
descend, and check that no floor-1 walls remain and that the new walls render.
