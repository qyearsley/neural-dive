"""
Main entry point for Neural Dive.
Allows running as: python -m neural_dive
"""

from __future__ import annotations

import argparse
import sys
import time

from blessed import Terminal

from neural_dive.backends import BlessedBackend
from neural_dive.data_loader import load_questions
from neural_dive.difficulty import DifficultyLevel
from neural_dive.game import Game
from neural_dive.input_handler import (
    ConversationHandler,
    EndGameHandler,
    NormalModeHandler,
    OverlayHandler,
    overlay_is_open,
)
from neural_dive.player_profile import PlayerProfile, format_profile_summary
from neural_dive.rendering import (
    ResizeWatcher,
    draw_game,
    draw_game_over_screen,
    draw_too_small_screen,
    draw_victory_screen,
    required_terminal_size,
    terminal_is_too_small,
)
from neural_dive.themes import get_theme


def print_history(content_set: str) -> None:
    """Print the player's cross-run question history to stdout.

    Args:
        content_set: Content set whose history to show
    """
    profile = PlayerProfile.load(content_set)
    try:
        questions = load_questions(content_set)
    except (OSError, ValueError, KeyError):
        # Without the content set we can still show counts, just not text.
        questions = {}

    for line in format_profile_summary(profile, questions):
        print(line)


def run_interactive(game: Game, chars, colors):
    """Run the game in interactive mode with terminal UI.

    Args:
        game: Game instance to run
        chars: Character set for rendering
        colors: Color scheme for rendering
    """
    term = Terminal()
    backend = BlessedBackend(term)
    first_draw = True

    # Terminal size is polled once per frame rather than handled through
    # SIGWINCH. Any change forces a full redraw, because a partial repaint
    # leaves the old status panel painted at the old row; and a window that
    # drops below the required size pauses the game behind a resize prompt
    # instead of scribbling off the edge of the screen.
    required = required_terminal_size(game)
    resize_watcher = ResizeWatcher(backend)

    # Initialize input handlers
    end_game_handler = EndGameHandler()
    overlay_handler = OverlayHandler()
    conversation_handler = ConversationHandler()
    normal_handler = NormalModeHandler()

    try:
        with term.cbreak(), term.hidden_cursor():
            while True:
                if resize_watcher.poll():
                    first_draw = True

                # Too small: pause, prompt, and recover when it grows again.
                if terminal_is_too_small(backend, required):
                    if first_draw:
                        draw_too_small_screen(backend, required)
                        first_draw = False
                    key = term.inkey(timeout=0.2)
                    if key and key.lower() == "q":
                        break
                    continue

                # Update NPC wandering every frame
                game.update_npc_wandering()

                # Check for victory
                if game.game_won:
                    draw_victory_screen(backend, game, colors)
                    key = term.inkey(timeout=0.1)
                    if key:
                        result = end_game_handler.handle(key, game, term)
                        if result.should_quit:
                            break
                    continue

                # Check for game over
                if game.player_manager.coherence <= 0:
                    draw_game_over_screen(backend, game, colors)

                    key = term.inkey(timeout=0.1)
                    if key:
                        result = end_game_handler.handle(key, game, term)
                        if result.should_quit:
                            break
                    continue

                # Draw everything
                draw_game(backend, game, chars, colors, redraw_all=first_draw)
                first_draw = False

                # Get input
                key = term.inkey(timeout=0.1)
                if not key:
                    continue

                # Try handlers in priority order
                # 1. Check overlay mode (help, inventory, snippets, terminals)
                if overlay_is_open(game):
                    result = overlay_handler.handle(key, game, term)

                # 2. Check conversation mode
                elif (
                    game.conversation_engine.active_conversation
                    or game.conversation_engine.last_answer_response
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
                        required = required_terminal_size(game)
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
  %(prog)s --stats           # Show your cross-run question history and exit

Controls:
  Arrow keys: Move  |  Space/Enter: Interact  |  >/< : Stairs
  V: Inventory  |  S: Save  |  L: Load  |  ?: Help  |  Q: Quit
  Q and L ask for confirmation first; press Y to go ahead.
  In a conversation: 1-4 answer, Y/N for yes-no, H hint, S snippet, ESC/X leave

Terminal Size:
  The map does not scroll. The game refuses to start in a window smaller than
  the tallest floor plus the status panel, and pauses if you shrink it below
  that mid-run.

Save Location:
  Games are saved to ~/.neural_dive/save.json by default
  Use --load to resume a saved game at startup
  Press 'S' in-game to save, 'L' to load

Question History:
  Per-question results accumulate in ~/.neural_dive/profile.json across runs,
  and questions you have missed before are likelier to come up again.
  Use --stats to review them, or --no-history to neither read nor write them.
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

    # Question history options
    history = parser.add_argument_group("Question History")
    history.add_argument(
        "--stats",
        action="store_true",
        help="Print your cross-run question history and exit",
    )
    history.add_argument(
        "--no-history",
        action="store_true",
        help="Do not read or write ~/.neural_dive/profile.json this run",
    )

    # Developer options
    dev = parser.add_argument_group("Developer Options")
    dev.add_argument("--test", action="store_true", help="Test mode: read commands from stdin")

    args = parser.parse_args()

    # Always use algorithms content set and cyberpunk dark theme
    content_set = "algorithms"
    chars, colors = get_theme()

    if args.stats:
        print_history(content_set)
        return

    # Cross-run question history. Loading never raises: a missing or unreadable
    # profile comes back empty, which leaves the game playing exactly as it did
    # before profiles existed.
    profile = None if args.no_history else PlayerProfile.load(content_set)

    if args.test:
        run_test_mode()
    else:
        term = Terminal()

        # Check if user wants to load a game
        if args.load is not None:
            from neural_dive.game_serializer import GameSerializer

            # Load game from specified path or default location
            load_path = args.load if args.load else None
            game = Game.load_game(load_path, profile=profile)

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

            # --width/--height only affect procedurally generated floors.
            # FloorManager._create_map_for_floor overwrites map_width and
            # map_height from the authored layout whenever one exists, and the
            # shipped content authors every floor -- so these are not a way to
            # fit the game into a small window. There used to be a
            # min(args.width, term.width) clamp here that looked like one; it
            # never had any effect.
            random_npcs = not args.fixed

            game = Game(
                map_width=args.width,
                map_height=args.height,
                random_npcs=random_npcs,
                seed=args.seed,
                difficulty=difficulty,
                content_set=content_set,
                profile=profile,
            )

        required_width, required_height = required_terminal_size(game)
        if term.width < required_width or term.height < required_height:
            print(term.clear)
            print(
                f"Neural Dive needs a terminal of at least "
                f"{required_width} columns by {required_height} rows."
            )
            print(f"This one is {term.width} by {term.height}.")
            print("The map does not scroll, so resize the window and start again.")
            sys.exit(1)

        run_interactive(game, chars, colors)


if __name__ == "__main__":
    main()
