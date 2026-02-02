"""Data loading utilities for Neural Dive.

Loads questions, NPCs, and terminals from JSON files.
Supports multiple content sets for different learning topics.
"""

from __future__ import annotations

import importlib
import json
import logging
from pathlib import Path

from neural_dive.enums import NPCType
from neural_dive.models import Answer, Conversation, Question
from neural_dive.question_types import QuestionType

logger = logging.getLogger(__name__)


def get_data_dir() -> Path:
    """Get the data directory path."""
    return Path(__file__).parent / "data"


def get_content_dir(content_set: str = "algorithms") -> Path:
    """Get the directory path for a specific content set.

    Args:
        content_set: ID of the content set (default: "algorithms")

    Returns:
        Path to the content set directory
    """
    return get_data_dir() / "content" / content_set


def list_content_sets() -> list[dict]:
    """List available content sets (hardcoded to algorithms only)."""
    return [{"id": "algorithms", "path": "content/algorithms", "enabled": True, "default": True}]


def get_default_content_set() -> str:
    """Get the default content set ID (always algorithms)."""
    return "algorithms"


def load_content_metadata(content_set: str) -> dict:
    """Load metadata for a specific content set.

    Args:
        content_set: ID of the content set to load metadata for

    Returns:
        Dictionary containing content set metadata from content.json

    Raises:
        FileNotFoundError: If content set directory or content.json not found
    """
    metadata_file = get_content_dir(content_set) / "content.json"
    if not metadata_file.exists():
        raise FileNotFoundError(f"Content set '{content_set}' not found")
    with open(metadata_file) as f:
        result: dict = json.load(f)
        return result


def load_questions(content_set: str = "algorithms") -> dict[str, Question]:
    """Load all questions from questions.json for a specific content set."""
    data_file = get_content_dir(content_set) / "questions.json"

    with open(data_file) as f:
        data = json.load(f)

    questions = {}
    for question_id, q_data in data.items():
        # Determine question type
        question_type_str = q_data.get("type", "multiple_choice")
        question_type = QuestionType(question_type_str)

        if question_type == QuestionType.MULTIPLE_CHOICE:
            # Parse answers for multiple choice
            answers = []
            for ans_data in q_data["answers"]:
                answer = Answer(
                    text=ans_data["text"],
                    correct=ans_data["correct"],
                    response=ans_data["response"],
                    reward_knowledge=ans_data.get("reward_knowledge"),
                    enemy_penalty=ans_data.get("enemy_penalty", 35),  # default from config
                )
                answers.append(answer)

            # Create multiple choice question
            question = Question(
                question_text=q_data["question_text"],
                answers=answers,
                topic=q_data["topic"],
                question_type=question_type,
            )
        else:
            # Short answer or yes/no question
            question = Question(
                question_text=q_data["question_text"],
                topic=q_data["topic"],
                question_type=question_type,
                correct_answer=q_data["correct_answer"],
                correct_response=q_data["correct_response"],
                incorrect_response=q_data["incorrect_response"],
                reward_knowledge=q_data.get("reward_knowledge"),
                match_type=q_data.get("match_type", "exact"),
                case_sensitive=q_data.get("case_sensitive", False),
            )

        questions[question_id] = question

    return questions


def load_npcs(questions: dict[str, Question], content_set: str = "algorithms") -> dict[str, dict]:
    """Load all NPCs from npcs.json for a specific content set.

    Args:
        questions: Dictionary of available questions
        content_set: Content set identifier

    Returns:
        Dictionary mapping NPC names to NPC data

    Logs warnings if NPCs reference non-existent questions.
    """
    data_file = get_content_dir(content_set) / "npcs.json"

    with open(data_file) as f:
        data = json.load(f)

    npcs = {}
    for npc_name, npc_data in data.items():
        # Parse NPC type
        npc_type = NPCType(npc_data["npc_type"])

        # Get questions for this NPC
        npc_questions = []
        missing_questions = []
        for question_id in npc_data.get("questions", []):
            if question_id in questions:
                npc_questions.append(questions[question_id])
            else:
                # Track missing questions for validation warning
                missing_questions.append(question_id)

        # Warn about missing questions
        if missing_questions:
            logger.warning(
                "NPC '%s' references non-existent questions: %s",
                npc_name,
                ", ".join(missing_questions),
            )

        # Warn if NPC has no valid questions
        if not npc_questions and npc_data.get("questions"):
            logger.warning(
                "NPC '%s' has no valid questions (all %d referenced questions are missing)",
                npc_name,
                len(npc_data.get("questions", [])),
            )

        # Create conversation
        conversation = Conversation(
            npc_name=npc_name,
            greeting=npc_data["greeting"],
            questions=npc_questions,
            npc_type=npc_type,
        )

        # Store NPC data
        npcs[npc_name] = {
            "char": npc_data["char"],
            "color": npc_data["color"],
            "floor": npc_data["floor"],
            "npc_type": npc_data["npc_type"],
            "conversation": conversation,
        }

    return npcs


def load_levels(content_set: str = "algorithms") -> dict:
    """Load level layouts for a specific content set.

    Args:
        content_set: Content set identifier

    Returns:
        Dictionary of parsed level data, or empty dict if no levels file exists
    """
    import importlib.util

    # Try to load content-specific levels.py
    levels_file = get_content_dir(content_set) / "levels.py"

    if not levels_file.exists():
        # Fallback to default levels if content-specific file doesn't exist
        from neural_dive.data.levels import PARSED_LEVELS

        return PARSED_LEVELS

    # Dynamically import the levels module
    spec = importlib.util.spec_from_file_location(f"levels_{content_set}", levels_file)
    if spec and spec.loader:
        levels_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(levels_module)
        return getattr(levels_module, "PARSED_LEVELS", {})

    return {}


def load_snippets() -> dict[str, dict]:
    """Load code snippets for reference during questions.

    Returns:
        Dictionary mapping snippet IDs to snippet data
    """
    import json

    snippets_file = Path(__file__).parent / "data" / "snippets.json"

    if not snippets_file.exists():
        return {}

    try:
        with open(snippets_file, encoding="utf-8") as f:
            data: dict[str, dict] = json.load(f)
            return data
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Error loading snippets: %s", e)
        return {}


def load_all_game_data(content_set: str | None = None):
    """Load all game data (questions, NPCs, levels, snippets) for a content set.

    Args:
        content_set: Content set ID (None to use default)

    Returns:
        Tuple of (questions, npcs, levels, snippets)
    """
    # Use default content set if not specified
    if content_set is None:
        content_set = get_default_content_set()

    questions = load_questions(content_set)
    npcs = load_npcs(questions, content_set)
    levels = load_levels(content_set)
    snippets = load_snippets()

    # Validate NPC/layout consistency and warn about issues
    # Try to import validation function dynamically for this content set
    try:
        # Import validation function from content set's levels module
        module_path = f"neural_dive.data.content.{content_set}.levels"
        levels_module = importlib.import_module(module_path)
        validate_func = getattr(levels_module, "validate_npc_layout_consistency", None)

        if validate_func:
            warnings = validate_func(npcs, levels)
            if warnings:
                logger.warning("NPC/Layout Validation Warnings:")
                for warning in warnings:
                    logger.warning("  - %s", warning)
    except (ImportError, AttributeError):
        # Content set doesn't have validation - that's okay
        pass

    return questions, npcs, levels, snippets


def compute_floor_requirements(npc_data: dict) -> dict[int, set[str]]:
    """Compute required NPCs per floor based on loaded NPC data.

    NPCs with types 'specialist' or 'enemy' are required to complete their floor.
    NPCs with type 'helper', 'quest', or 'boss' are optional.

    Args:
        npc_data: Dictionary mapping NPC names to their data

    Returns:
        Dictionary mapping floor numbers to sets of required NPC names
    """
    floor_requirements: dict[int, set[str]] = {}

    for npc_name, npc_info in npc_data.items():
        floor = npc_info.get("floor", 1)
        npc_type = npc_info.get("npc_type", "specialist")

        # Require specialists and enemies only
        # Helpers, quest NPCs, and bosses are optional
        if npc_type in ["specialist", "enemy"]:
            if floor not in floor_requirements:
                floor_requirements[floor] = set()
            floor_requirements[floor].add(npc_name)

    return floor_requirements
