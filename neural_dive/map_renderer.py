"""Map and entity drawing.

The dungeon floor itself: tiles, the entities standing on them, and the
tile-repainting that erases whatever moved since the last frame.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from neural_dive.render_helpers import get_color_func

if TYPE_CHECKING:
    from neural_dive.backends import RenderBackend
    from neural_dive.game import Game
    from neural_dive.themes import CharacterSet, ColorScheme


def draw_map(backend: RenderBackend, game: Game, chars: CharacterSet, colors: ColorScheme) -> None:
    """Draw the game map tiles to the terminal.

    Args:
        backend: Render backend instance for output
        game: Game instance containing map data
        chars: Character set for rendering tiles
        colors: Color scheme for tile colors
    """
    for y in range(len(game.game_map)):
        for x in range(len(game.game_map[0])):
            char = game.game_map[y][x]
            if char == "#":
                backend.draw_text(x, y, chars.wall, colors.wall, bold=True)
            elif char == ".":
                backend.draw_text(x, y, chars.floor, colors.floor)


def clear_old_player_position(
    backend: RenderBackend, game: Game, chars: CharacterSet, colors: ColorScheme
) -> None:
    """Clear the old player position by redrawing the floor tile.

    Args:
        backend: Render backend instance for output
        game: Game instance with player position data
        chars: Character set for rendering tiles
        colors: Color scheme for tile colors
    """
    if game.old_player_pos:
        old_x, old_y = game.old_player_pos
        char = game.game_map[old_y][old_x]
        if char == ".":
            backend.draw_text(old_x, old_y, chars.floor, colors.floor)


def _is_position_occupied(game: Game, x: int, y: int) -> bool:
    """Check if a position is occupied by any entity.

    Args:
        game: Game instance containing entity data
        x: X coordinate to check
        y: Y coordinate to check

    Returns:
        True if position is occupied by player, NPC, terminal, or stairs
    """
    # Check player
    if game.player.x == x and game.player.y == y:
        return True

    # Check NPCs, terminals, and stairs
    return (
        any(npc.x == x and npc.y == y for npc in game.npc_manager.npcs)
        or any(terminal.x == x and terminal.y == y for terminal in game.terminals)
        or any(stair.x == x and stair.y == y for stair in game.stairs)
    )


def clear_old_npc_positions(
    backend: RenderBackend, game: Game, chars: CharacterSet, colors: ColorScheme
) -> None:
    """
    Clear old NPC positions by redrawing floor tiles where NPCs have moved from.

    Args:
        backend: Render backend instance for output
        game: Game instance with NPC position data
        chars: Character set for rendering tiles
        colors: Color scheme for tile colors
    """
    for _npc_name, (old_x, old_y) in game.npc_manager.movement.old_positions.items():
        # If not occupied, redraw the floor tile
        if not _is_position_occupied(game, old_x, old_y):
            char = game.game_map[old_y][old_x]
            if char == ".":
                color_func = get_color_func(backend, colors.floor, "cyan")
                print(backend.move_xy(old_x, old_y) + color_func(chars.floor), end="")
            elif char == "#":
                color_func = get_color_func(backend, f"bold_{colors.wall}", "bold_blue")
                print(backend.move_xy(old_x, old_y) + color_func(chars.wall), end="")

    # Clear the tracking dictionary after processing
    game.npc_manager.movement.old_positions.clear()


def draw_entities(
    backend: RenderBackend, game: Game, chars: CharacterSet, colors: ColorScheme
) -> None:
    """Draw all game entities including NPCs, terminals, stairs, and player.

    Args:
        backend: Render backend instance for output
        game: Game instance containing entity data
        chars: Character set for rendering entities
        colors: Color scheme for entity colors
    """
    from neural_dive.entity_renderers import EntityType, get_entity_renderer

    # Get required NPCs for current floor (computed dynamically from NPC data)
    required_npcs = game.floor_manager.floor_requirements.get(
        game.floor_manager.current_floor, set()
    )

    # Draw NPCs using NPCRenderer
    npc_renderer = get_entity_renderer(EntityType.NPC)
    for npc in game.npc_manager.npcs:
        is_required = npc.name in required_npcs
        npc_renderer.render(backend, npc, chars, colors, is_required=is_required)

    # Draw terminals using TerminalRenderer
    terminal_renderer = get_entity_renderer(EntityType.TERMINAL)
    for terminal in game.terminals:
        terminal_renderer.render(backend, terminal, chars, colors)

    # Draw stairs using StairsRenderer
    stairs_renderer = get_entity_renderer(EntityType.STAIRS)
    for stair in game.stairs:
        stairs_renderer.render(backend, stair, chars, colors)

    # Draw item pickups using ItemPickupRenderer
    item_renderer = get_entity_renderer(EntityType.ITEM_PICKUP)
    for pickup in game.item_pickups:
        item_renderer.render(backend, pickup, chars, colors)

    # Draw player using PlayerRenderer
    player_renderer = get_entity_renderer(EntityType.PLAYER)
    player_renderer.render(backend, game.player, chars, colors)
