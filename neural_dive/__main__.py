"""
Main entry point for Neural Dive.
Allows running as: python -m neural_dive
"""

from __future__ import annotations

import argparse
import sys
import time

from blessed import Terminal

from neural_dive.difficulty import DifficultyLevel
from neural_dive.game import Game
from neural_dive.input_handler import (
    ConversationHandler,
    EndGameHandler,
    NormalModeHandler,
    OverlayHandler,
)
from neural_dive.rendering import draw_game, draw_victory_screen
from neural_dive.themes import get_theme


def run_interactive(game: Game, chars, colors):
    """Run the game in interactive mode with terminal UI.

    Args:
        game: Game instance to run
        chars: Character set for rendering
        colors: Color scheme for rendering
    """
    term = Terminal()
    first_draw = True

    # Initialize text input buffer on game object
    if not hasattr(game, "text_input_buffer"):
        game.text_input_buffer = ""

    # Initialize input handlers
    end_game_handler = EndGameHandler()
    overlay_handler = OverlayHandler()
    conversation_handler = ConversationHandler()
    normal_handler = NormalModeHandler()

    try:
        with term.cbreak(), term.hidden_cursor():
            while True:
                # Update NPC wandering every frame
                game.update_npc_wandering()

                # Check for victory
                if game.game_won:
                    draw_victory_screen(term, game, colors)
                    key = term.inkey(timeout=0.1)
                    if key:
                        result = end_game_handler.handle(key, game, term)
                        if result.should_quit:
                            break
                    continue

                # Check for game over
                if game.coherence <= 0:
                    draw_game(term, game, chars, colors, redraw_all=first_draw)
                    print(
                        term.move_xy(0, term.height // 2)
                        + term.center(term.bold_red("SYSTEM FAILURE - COHERENCE LOST")).rstrip()
                    )
                    print(
                        term.move_xy(0, term.height // 2 + 2)
                        + term.center("Press Q to quit").rstrip()
                    )
                    sys.stdout.flush()
                    first_draw = False

                    key = term.inkey(timeout=0.1)
                    if key:
                        result = end_game_handler.handle(key, game, term)
                        if result.should_quit:
                            break
                    continue

                # Draw everything
                draw_game(term, game, chars, colors, redraw_all=first_draw)
                first_draw = False

                # Get input
                key = term.inkey(timeout=0.1)
                if not key:
                    continue

                # Try handlers in priority order
                # 1. Check overlay mode (inventory, snippets, terminals)
                if game.active_inventory or game.active_snippet or game.active_terminal:
                    result = overlay_handler.handle(key, game, term)

                # 2. Check conversation mode
                elif game.active_conversation or (
                    hasattr(game, "last_answer_response") and game.last_answer_response
                ):
                    result = conversation_handler.handle(key, game, term)

                # 3. Normal mode (movement, interactions, save/load)
                else:
                    result = normal_handler.handle(key, game, term)

                # Process result
                if result.handled:
                    if result.should_quit:
                        break
                    if result.needs_redraw:
                        first_draw = True
                    if result.message:
                        game.message = result.message
                    if result.new_game:
                        game = result.new_game
                        first_draw = True

    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        pass
    finally:
        # Clear screen on exit
        print(term.home + term.clear)


def run_test_mode():
    """Run in test mode - process commands from stdin"""
    # Use fixed NPC positions and seed for reproducible testing
    game = Game(random_npcs=False, seed=42)

    print("# Neural Dive Test Mode")
    print(f"# Initial state: {game.get_state()}")
    print("#")

    for line in sys.stdin:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        success, info = game.process_command(line)
        state = game.get_state()
        print(f"Command: {line}")
        print(f"Success: {success}")
        print(f"Info: {info}")
        print(f"State: {state}")
        print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="ndive",
        description="""
╔═══════════════════════════════════════════════════════════════╗
║                        NEURAL DIVE                            ║
║        Cyberpunk Terminal Roguelike • Learning Game           ║
╚═══════════════════════════════════════════════════════════════╝

Descend through neural layers, answer questions, master new knowledge.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                  # Play game
  %(prog)s --load            # Load saved game from ~/.neural_dive/save.json
  %(prog)s --load /path/to/save.json  # Load from specific file
  %(prog)s --fixed --seed 42  # Reproducible game for testing

Controls:
  Arrow keys: Move  |  Space/Enter: Interact  |  >/< : Stairs
  V: Inventory  |  S: Save  |  L: Load  |  Q: Quit

Save Location:
  Games are saved to ~/.neural_dive/save.json by default
  Use --load to resume a saved game at startup
  Press 'S' in-game to save, 'L' to load
        """,
    )

    # Game options
    game_opts = parser.add_argument_group("Game Options")
    game_opts.add_argument(
        "--load",
        nargs="?",
        const="",  # Use default location if --load is used without a path
        metavar="PATH",
        help="Load game from save file (defaults to ~/.neural_dive/save.json if no path given)",
    )
    game_opts.add_argument(
        "--width", type=int, default=50, metavar="N", help="Map width in tiles (default: 50)"
    )
    game_opts.add_argument(
        "--height", type=int, default=25, metavar="N", help="Map height in tiles (default: 25)"
    )
    game_opts.add_argument(
        "--seed", type=int, metavar="N", help="Random seed for reproducible gameplay"
    )
    game_opts.add_argument(
        "--fixed", action="store_true", help="Use fixed NPC positions (for testing)"
    )

    # Developer options
    dev = parser.add_argument_group("Developer Options")
    dev.add_argument("--test", action="store_true", help="Test mode: read commands from stdin")

    args = parser.parse_args()

    # Always use algorithms content set and cyberpunk dark theme
    content_set = "algorithms"
    chars, colors = get_theme("cyberpunk", "dark")

    if args.test:
        run_test_mode()
    else:
        term = Terminal()

        # Check if user wants to load a game
        if args.load is not None:
            from neural_dive.game_serializer import GameSerializer

            # Load game from specified path or default location
            load_path = args.load if args.load else None
            game = Game.load_game(load_path)

            if game:
                actual_path = load_path if load_path else GameSerializer.get_default_save_path()
                print(term.clear)
                print(f"Loaded game from {actual_path}")
                print("Starting in 2 seconds...")
                time.sleep(2)
            else:
                actual_path = load_path if load_path else GameSerializer.get_default_save_path()
                print(term.clear)
                print(f"Error: Could not load game from {actual_path}")
                print("Starting new game instead...")
                time.sleep(2)
                game = None

        else:
            game = None

        # If no game loaded, create a new one
        if game is None:
            # Always use NORMAL difficulty
            difficulty = DifficultyLevel.NORMAL

            # Adjust map size to terminal if needed
            map_width = min(args.width, term.width)
            map_height = min(args.height, term.height - 6)
            random_npcs = not args.fixed

            game = Game(
                map_width=map_width,
                map_height=map_height,
                random_npcs=random_npcs,
                seed=args.seed,
                difficulty=difficulty,
                content_set=content_set,
            )

        run_interactive(game, chars, colors)


if __name__ == "__main__":
    main()
