"""
Main entry point for Neural Dive.
Allows running as: python -m neural_dive
"""

from __future__ import annotations

import argparse
import os
import sys

from blessed import Terminal

from neural_dive.difficulty import DifficultyLevel
from neural_dive.game import Game
from neural_dive.menu import show_content_menu
from neural_dive.question_types import QuestionType
from neural_dive.rendering import draw_game, draw_victory_screen
from neural_dive.themes import get_theme


def run_interactive(game: Game, chars, colors):
    """
    Run the game in interactive mode with terminal UI.

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

    try:
        with term.cbreak(), term.hidden_cursor():
            while True:
                # Check for victory
                if game.game_won:
                    draw_victory_screen(term, game, colors)
                    while True:
                        key = term.inkey(timeout=0.1)
                        if key and key.lower() == "q":
                            break
                    break

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

                    while True:
                        key = term.inkey(timeout=0.1)
                        if key and key.lower() == "q":
                            break
                    break

                # Draw everything
                draw_game(term, game, chars, colors, redraw_all=first_draw)
                first_draw = False

                # Get input
                key = term.inkey(timeout=0.1)

                # Update NPC wandering every frame
                game.update_npc_wandering()

                if not key:
                    continue

                if key.lower() == "q" and not game.active_conversation and not game.active_terminal:
                    break

                # Save game (S key)
                if key.lower() == "s" and not game.active_conversation and not game.active_terminal:
                    if game.save_game():
                        game.message = "Game saved successfully!"
                    else:
                        game.message = "Failed to save game."
                    first_draw = True
                    continue

                # Load game (L key)
                if key.lower() == "l" and not game.active_conversation and not game.active_terminal:
                    loaded_game = Game.load_game()
                    if loaded_game:
                        game = loaded_game
                        game.message = "Game loaded successfully!"
                        first_draw = True
                    else:
                        game.message = "No save file found."
                        first_draw = True
                    continue

                # In terminal reading mode
                if game.active_terminal:
                    # Any key closes terminal
                    game.active_terminal = None
                    first_draw = True  # Force redraw to clear overlay
                    continue

                # In conversation mode
                if game.active_conversation:
                    # If showing greeting or response, any key continues
                    if hasattr(game, "show_greeting") and game.show_greeting:
                        # Dismiss greeting
                        game.show_greeting = False
                        game.text_input_buffer = ""  # Reset input buffer
                        continue

                    if hasattr(game, "last_answer_response") and game.last_answer_response:
                        # Dismiss response and continue to next question
                        game.last_answer_response = None
                        game.text_input_buffer = ""  # Reset input buffer
                        continue

                    # Check question type
                    current_question = game.active_conversation.get_current_question()
                    if current_question:
                        # Handle text-based questions (short answer, yes/no)
                        if current_question.question_type in [
                            QuestionType.SHORT_ANSWER,
                            QuestionType.YES_NO,
                        ]:
                            # Quick answer for yes/no questions (check before exit keys)
                            if current_question.question_type == QuestionType.YES_NO:
                                if key.lower() == "y":
                                    correct, response = game.answer_text_question("yes")
                                    game.last_answer_response = response
                                    game.text_input_buffer = ""
                                    first_draw = True
                                    continue
                                elif key.lower() == "n":
                                    correct, response = game.answer_text_question("no")
                                    game.last_answer_response = response
                                    game.text_input_buffer = ""
                                    first_draw = True
                                    continue

                            # Enter submits answer
                            if key.name == "KEY_ENTER" or key == "\n" or key == "\r":
                                if game.text_input_buffer.strip():
                                    correct, response = game.answer_text_question(
                                        game.text_input_buffer.strip()
                                    )
                                    game.last_answer_response = response
                                    game.text_input_buffer = ""
                                    first_draw = True
                                continue

                            # ESC/X exits conversation (Q removed - can be typed in answers)
                            # Only exit with ESC or X when buffer is empty
                            if key.name == "KEY_ESCAPE" or (
                                key.lower() == "x" and not game.text_input_buffer
                            ):
                                game.exit_conversation()
                                if hasattr(game, "last_answer_response"):
                                    del game.last_answer_response
                                if hasattr(game, "show_greeting"):
                                    del game.show_greeting
                                game.text_input_buffer = ""
                                first_draw = True
                                continue

                            # Backspace
                            if key.name == "KEY_BACKSPACE" or key == "\x7f":
                                if game.text_input_buffer:
                                    game.text_input_buffer = game.text_input_buffer[:-1]
                                # Don't force full redraw for text input - reduces flicker
                                continue

                            # Regular character input
                            if key.is_sequence:
                                # Ignore special sequences
                                continue
                            if len(key) == 1 and key.isprintable():
                                game.text_input_buffer += key
                                # Don't force full redraw for text input - reduces flicker
                                continue

                        # Handle multiple choice questions
                        elif current_question.question_type == QuestionType.MULTIPLE_CHOICE:
                            # Handle answer selection (1-4)
                            if key in ["1", "2", "3", "4"]:
                                answer_idx = int(key) - 1
                                correct, response = game.answer_question(answer_idx)
                                game.last_answer_response = response
                                game.text_input_buffer = ""
                                continue

                            # ESC/Q/X exits conversation
                            if key.name == "KEY_ESCAPE" or key.lower() in ["x", "q"]:
                                game.exit_conversation()
                                if hasattr(game, "last_answer_response"):
                                    del game.last_answer_response
                                if hasattr(game, "show_greeting"):
                                    del game.show_greeting
                                game.text_input_buffer = ""
                                first_draw = True
                                continue

                # Check if conversation just ended (we have a response but no active conversation)
                elif hasattr(game, "last_answer_response") and game.last_answer_response:
                    # Wait for user to press any key to dismiss completion message
                    game.last_answer_response = None
                    first_draw = True  # Force full redraw to clear overlay
                    continue

                # Normal movement mode
                else:
                    if key.name == "KEY_UP":
                        game.move_player(0, -1)
                    elif key.name == "KEY_DOWN":
                        game.move_player(0, 1)
                    elif key.name == "KEY_LEFT":
                        game.move_player(-1, 0)
                    elif key.name == "KEY_RIGHT":
                        game.move_player(1, 0)
                    elif key in [">", "."] or key in ["<", ","]:
                        # Try stairs first, then interact
                        if not game.use_stairs():
                            game.interact()
                        else:
                            first_draw = True  # Force redraw on floor change
                    elif key.lower() == "i" or key == " " or key.name == "KEY_ENTER":
                        # Try interaction first, then stairs
                        result = game.interact()
                        if result and game.active_conversation:
                            # Starting conversation - reset state
                            game.show_greeting = True
                            game.last_answer_response = None
                        elif not result:
                            # No NPC nearby, try stairs
                            if game.use_stairs():
                                first_draw = True  # Force redraw on floor change

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
  %(prog)s                  # Play with default settings
  %(prog)s --content chinese-hsk6  # Play with Chinese HSK6 content
  %(prog)s --list-content   # Show available content sets
  %(prog)s --light          # Light terminal background
  %(prog)s --classic        # ASCII graphics (compatibility mode)
  %(prog)s --fixed --seed 42  # Reproducible game for testing

Environment Variables:
  NEURAL_DIVE_THEME=cyberpunk|classic
  NEURAL_DIVE_BACKGROUND=dark|light

Controls:
  Arrow keys: Move  |  Space/Enter: Interact  |  >/< : Stairs
  S: Save  |  L: Load  |  Q: Quit
        """,
    )

    # Visual options
    visual = parser.add_argument_group("Visual Options")
    visual.add_argument(
        "--theme",
        "-t",
        type=str,
        choices=["cyberpunk", "classic", "hanzi"],
        metavar="THEME",
        help="Visual theme: 'cyberpunk' (Unicode), 'classic' (ASCII), or 'hanzi' (Chinese characters)",
    )
    visual.add_argument(
        "--background",
        "-b",
        type=str,
        choices=["dark", "light"],
        metavar="BG",
        help="Terminal background: 'dark' or 'light'",
    )
    visual.add_argument(
        "--light",
        action="store_const",
        const="light",
        dest="background",
        help="Shortcut for --background light",
    )
    visual.add_argument(
        "--classic",
        action="store_const",
        const="classic",
        dest="theme",
        help="Shortcut for --theme classic",
    )

    # Game options
    game_opts = parser.add_argument_group("Game Options")
    game_opts.add_argument(
        "--content",
        "-c",
        type=str,
        metavar="SET",
        help="Content set to play: 'algorithms' (default), 'chinese-hsk6', 'geography', etc.",
    )
    game_opts.add_argument(
        "--list-content",
        action="store_true",
        help="List available content sets and exit",
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

    # Handle --list-content
    if args.list_content:
        from neural_dive.data_loader import list_content_sets, load_content_metadata

        print("\n╔══════════════════════════════════════════════════════════════╗")
        print("║                   Available Content Sets                     ║")
        print("╚══════════════════════════════════════════════════════════════╝\n")

        content_sets = list_content_sets()
        for cs in content_sets:
            try:
                metadata = load_content_metadata(cs["id"])
                default_marker = " [DEFAULT]" if cs.get("default", False) else ""
                print(f"  {cs['id']}{default_marker}")
                print(f"    Name: {metadata['name']}")
                print(f"    Description: {metadata['description']}")
                print(f"    Questions: {metadata.get('question_count', 'Unknown')}")
                print(f"    Difficulty: {metadata.get('difficulty_range', 'N/A')}")
                print()
            except Exception as e:
                print(f"  {cs['id']} (error loading metadata: {e})")
                print()

        return

    # Determine content set FIRST (needed for theme selection)
    term = None
    if args.content:
        # Use specified content set
        content_set = args.content
    else:
        # Show interactive content selection menu (if not in test mode)
        if not args.test:
            term = Terminal()
            content_set = show_content_menu(term)
        else:
            from neural_dive.data_loader import get_default_content_set

            content_set = get_default_content_set()

    # Get theme from args, env var, content set default, or global default
    if args.theme:
        theme_name = args.theme
    elif os.getenv("NEURAL_DIVE_THEME"):
        theme_name = os.getenv("NEURAL_DIVE_THEME")
    else:
        # Try to get default theme from content set metadata
        try:
            from neural_dive.data_loader import load_content_metadata

            metadata = load_content_metadata(content_set)
            theme_name = metadata.get("default_theme", "cyberpunk")
        except Exception:
            theme_name = "cyberpunk"

    background = args.background or os.getenv("NEURAL_DIVE_BACKGROUND", "dark")

    # Get theme characters and colors
    chars, colors = get_theme(theme_name, background)

    if args.test:
        run_test_mode()
    else:
        if not term:  # Term may already be created for content menu
            term = Terminal()

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
