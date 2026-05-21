"""Compatibility shim re-exporting level data from the canonical content set.

Historically there were two parallel `levels.py` files. The canonical layouts and
constants now live under `neural_dive/data/content/algorithms/levels.py`; this
module simply re-exports the symbols still imported from `neural_dive.data.levels`
so existing call sites keep working.
"""

from neural_dive.data.content.algorithms.levels import (
    BOSS_NPCS,
    PARSED_LEVELS,
    ZONE_TERMINALS,
    parse_level,
)

__all__ = ["BOSS_NPCS", "PARSED_LEVELS", "ZONE_TERMINALS", "parse_level"]
