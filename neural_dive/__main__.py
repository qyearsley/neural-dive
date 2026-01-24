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
from neural_dive.question_types import QuestionType
from neural_dive.rendering import draw_game, draw_victory_screen
from neural_dive.themes import CharacterSet, ColorScheme, get_theme


def _handle_victory_screen(term: Terminal, game: Game, colors: ColorScheme) -> bool:
    """Handle victory screen display and input.

    Args:
        term: Terminal instance
        game: Game instance
        colors: Color scheme

    Returns:
        True if user wants to quit, False otherwise
    """
    draw_victory_screen(term, game, colors)
    while True:
        key = term.inkey(timeout=0.1)
        if key and key.lower() == "q":
            return True


def _handle_game_over(
    term: Terminal, game: Game, chars: CharacterSet, colors: ColorScheme, first_draw: bool
) -> bool:
    """Handle game over screen display and input.

    Args:
        term: Terminal instance
        game: Game instance
        chars: Character set for rendering
        colors: Color scheme
        first_draw: Whether this is the first draw

    Returns:
        True if user wants to quit, False otherwise
    """
    draw_game(term, game, chars, colors, redraw_all=first_draw)
    print(
        term.move_xy(0, term.height // 2)
        + term.center(term.bold_red("SYSTEM FAILURE - COHERENCE LOST")).rstrip()
    )
    print(term.move_xy(0, term.height // 2 + 2) + term.center("Press Q to quit").rstrip())
    sys.stdout.flush()

    while True:
        key = term.inkey(timeout=0.1)
        if key and key.lower() == "q":
            return True


def _handle_save_game(game: Game) -> tuple[str, bool]:
    """Handle save game operation.

    Args:
        game: Game instance

    Returns:
        Tuple of (message, redraw_needed)
    """
    success, save_path = game.save_game()
    if success and save_path:
        return (f"Game saved to {save_path}", True)
    return ("Failed to save game.", True)


def _handle_load_game(game: Game) -> tuple[Game, str, bool]:
    """Handle load game operation.

    Args:
        game: Current game instance

    Returns:
        Tuple of (game_instance, message, redraw_needed)
    """
    from neural_dive.game_serializer import GameSerializer

    save_path = GameSerializer.get_default_save_path()
    loaded_game = Game.load_game()
    if loaded_game:
        return (loaded_game, f"Game loaded from {save_path}", True)
    return (game, f"No save file found at {save_path}", True)


def _handle_inventory_input(key, game: Game) -> bool:
    """Handle input when inventory is active.

    Args:
        key: Input key from terminal
        game: Game instance

    Returns:
        True if inventory should close, False otherwise
    """
    if key.name == "KEY_ESCAPE" or key.lower() == "v":
        game.active_inventory = False
        return True
    return False


def _handle_snippet_input(key, game: Game) -> bool:
    """Handle input when snippet overlay is active.

    Args:
        key: Input key from terminal
        game: Game instance

    Returns:
        True if snippet should close, False otherwise
    """
    if key.name == "KEY_ESCAPE" or key.lower() == "s":
        game.active_snippet = None
        return True
    return False


def _handle_terminal_input(game: Game) -> bool:
    """Handle input when terminal overlay is active.

    Args:
        game: Game instance

    Returns:
        True to close terminal (always True - any key closes it)
    """
    game.active_terminal = None
    return True


def _handle_greeting_dismissal(game: Game) -> None:
    """Dismiss conversation greeting.

    Args:
        game: Game instance
    """
    game.show_greeting = False
    game.text_input_buffer = ""


def _handle_response_dismissal(game: Game) -> None:
    """Dismiss answer response.

    Args:
        game: Game instance
    """
    game.last_answer_response = None
    game.text_input_buffer = ""


def _handle_yes_no_quick_answer(key, game: Game) -> tuple[bool, str] | None:
    """Handle quick Y/N answer for yes/no questions.

    Args:
        key: Input key
        game: Game instance

    Returns:
        Tuple of (correct, response) if answer was given, None otherwise
    """
    if key.lower() == "y":
        correct, response = game.answer_text_question("yes")
        game.text_input_buffer = ""
        return (correct, response)
    elif key.lower() == "n":
        correct, response = game.answer_text_question("no")
        game.text_input_buffer = ""
        return (correct, response)
    return None


def _handle_text_answer_submission(game: Game) -> tuple[bool, str] | None:
    """Handle text answer submission for short answer questions.

    Args:
        game: Game instance

    Returns:
        Tuple of (correct, response) if answer was submitted, None otherwise
    """
    if game.text_input_buffer.strip():
        correct, response = game.answer_text_question(game.text_input_buffer.strip())
        game.text_input_buffer = ""
        return (correct, response)
    return None


def _handle_conversation_exit(game: Game) -> None:
    """Exit conversation and clean up state.

    Args:
        game: Game instance
    """
    game.exit_conversation()
    if hasattr(game, "last_answer_response"):
        del game.last_answer_response
    if hasattr(game, "show_greeting"):
        del game.show_greeting
    game.text_input_buffer = ""


def _handle_text_input(key, game: Game) -> bool:
    """Handle text input for text-based questions.

    Args:
        key: Input key
        game: Game instance

    Returns:
        True if input was handled (continue to next frame), False otherwise
    """
    # Backspace
    if key.name == "KEY_BACKSPACE" or key == "\x7f":
        if game.text_input_buffer:
            game.text_input_buffer = game.text_input_buffer[:-1]
        return True

    # Regular character input
    if key.is_sequence:
        return True  # Ignore special sequences
    if len(key) == 1 and key.isprintable():
        game.text_input_buffer += key
        return True

    return False


def _handle_multiple_choice_input(key, game: Game) -> tuple[bool, bool, str | None]:
    """Handle input for multiple choice questions.

    Args:
        key: Input key
        game: Game instance

    Returns:
        Tuple of (continue_to_next_frame, redraw_needed, response)
    """
    # Handle hint usage (H key)
    if key.lower() == "h":
        success, message = game.use_hint()
        game.message = message
        return (True, success, None)

    # Handle snippet viewing (S key)
    if key.lower() == "s":
        success, message = game.view_snippet()
        if not success:
            game.message = message
        return (True, success, None)

    # Handle answer selection (1-4)
    if key in ["1", "2", "3", "4"]:
        answer_idx = int(key) - 1
        correct, response = game.answer_question(answer_idx)
        game.text_input_buffer = ""
        return (True, False, response)

    return (False, False, None)


def _handle_movement_input(key, game: Game) -> bool:
    """Handle movement and interaction input.

    Args:
        key: Input key
        game: Game instance

    Returns:
        True if floor change occurred (needs redraw), False otherwise
    """
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
            return False
        return True
    elif key.lower() == "i" or key == " " or key.name == "KEY_ENTER":
        # Try interaction first, then stairs
        result = game.interact()
        if result and game.active_conversation:
            # Starting conversation - reset state
            game.show_greeting = True
            game.last_answer_response = None
            return False
        elif not result:
            # No NPC nearby, try stairs
            if game.use_stairs():
                return True
    return False


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

    try:
        with term.cbreak(), term.hidden_cursor():
            while True:
                # Check for victory
                if game.game_won and _handle_victory_screen(term, game, colors):
                    break

                # Check for game over
                if game.coherence <= 0 and _handle_game_over(term, game, chars, colors, first_draw):
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
                    message, redraw = _handle_save_game(game)
                    game.message = message
                    first_draw = redraw
                    continue

                # Load game (L key)
                if key.lower() == "l" and not game.active_conversation and not game.active_terminal:
                    game, message, redraw = _handle_load_game(game)
                    game.message = message
                    first_draw = redraw
                    continue

                # View inventory (V key)
                if key.lower() == "v" and not game.active_conversation and not game.active_terminal:
                    game.active_inventory = not game.active_inventory
                    first_draw = True
                    continue

                # In inventory viewing mode
                if game.active_inventory:
                    if _handle_inventory_input(key, game):
                        first_draw = True
                    continue

                # In snippet viewing mode
                if game.active_snippet:
                    if _handle_snippet_input(key, game):
                        first_draw = True
                    continue

                # In terminal reading mode
                if game.active_terminal:
                    _handle_terminal_input(game)
                    first_draw = True
                    continue

                # In conversation mode
                if game.active_conversation:
                    # If showing greeting, any key continues
                    if hasattr(game, "show_greeting") and game.show_greeting:
                        _handle_greeting_dismissal(game)
                        continue

                    # If showing response, any key continues
                    if hasattr(game, "last_answer_response") and game.last_answer_response:
                        _handle_response_dismissal(game)
                        continue

                    # Check question type
                    current_question = game.active_conversation.get_current_question()
                    if current_question:
                        # Handle text-based questions (short answer, yes/no)
                        if current_question.question_type in [
                            QuestionType.SHORT_ANSWER,
                            QuestionType.YES_NO,
                        ]:
                            # Quick answer for yes/no questions
                            if current_question.question_type == QuestionType.YES_NO:
                                result = _handle_yes_no_quick_answer(key, game)
                                if result:
                                    game.last_answer_response = result[1]
                                    first_draw = True
                                    continue

                            # Enter submits answer
                            if key.name == "KEY_ENTER" or key == "\n" or key == "\r":
                                result = _handle_text_answer_submission(game)
                                if result:
                                    game.last_answer_response = result[1]
                                    first_draw = True
                                continue

                            # ESC/X exits conversation (only when buffer empty)
                            if key.name == "KEY_ESCAPE" or (
                                key.lower() == "x" and not game.text_input_buffer
                            ):
                                _handle_conversation_exit(game)
                                first_draw = True
                                continue

                            # Handle text input (backspace, regular chars)
                            if _handle_text_input(key, game):
                                continue

                        # Handle multiple choice questions
                        elif current_question.question_type == QuestionType.MULTIPLE_CHOICE:
                            continue_flag, redraw, response = _handle_multiple_choice_input(
                                key, game
                            )
                            if continue_flag:
                                if response:
                                    game.last_answer_response = response
                                if redraw:
                                    first_draw = True
                                continue

                            # ESC/Q/X exits conversation
                            if key.name == "KEY_ESCAPE" or key.lower() in ["x", "q"]:
                                _handle_conversation_exit(game)
                                first_draw = True
                                continue

                # Check if conversation just ended (response without active conversation)
                elif hasattr(game, "last_answer_response") and game.last_answer_response:
                    game.last_answer_response = None
                    first_draw = True
                    continue

                # Normal movement mode
                else:
                    if _handle_movement_input(key, game):
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
