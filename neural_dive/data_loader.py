"""Data loading utilities for Neural Dive.

Loads questions, NPCs, and terminals from JSON files.
Supports multiple content sets for different learning topics.
"""

from __future__ import annotations

import json
from pathlib import Path

from neural_dive.enums import NPCType
from neural_dive.models import Answer, Conversation, Question
from neural_dive.question_types import QuestionType


def get_data_dir() -> Path:
    """Get the data directory path."""
    return Path(__file__).parent / "data"


def get_content_dir(content_set: str = "algorithms") -> Path:
    """Get the directory path for a specific content set."""
    return get_data_dir() / "content" / content_set


def list_content_sets() -> list[dict]:
    """List all available content sets."""
    registry_file = get_data_dir() / "content_registry.json"

    if not registry_file.exists():
        # Fallback: return algorithms as default.
        return [{
            "id": "algorithms",
            "path": "content/algorithms",
            "enabled": True,
            "default": True
        }]

    with open(registry_file) as f:
        registry = json.load(f)

    return [cs for cs in registry.get("content_sets", []) if cs.get("enabled", True)]


def get_default_content_set() -> str:
    """Get the default content set ID."""
    content_sets = list_content_sets()

    for cs in content_sets:
        if cs.get("default", False):
            return cs["id"]

    # Fallback to first available or algorithms.
    return content_sets[0]["id"] if content_sets else "algorithms"


def load_content_metadata(content_set: str) -> dict:
    """Load metadata for a specific content set."""
    metadata_file = get_content_dir(content_set) / "content.json"
    if not metadata_file.exists():
        raise FileNotFoundError(f"Content set '{content_set}' not found")
    with open(metadata_file) as f:
        return json.load(f)


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
    """Load all NPCs from npcs.json for a specific content set."""
    data_file = get_content_dir(content_set) / "npcs.json"

    with open(data_file) as f:
        data = json.load(f)

    npcs = {}
    for npc_name, npc_data in data.items():
        # Parse NPC type
        npc_type = NPCType(npc_data["npc_type"])

        # Get questions for this NPC
        npc_questions = []
        for question_id in npc_data.get("questions", []):
            if question_id in questions:
                npc_questions.append(questions[question_id])

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
            "conversation": conversation,
        }

    return npcs


def load_terminals(content_set: str = "algorithms") -> dict[str, dict]:
    """Load all terminals from terminals.json for a specific content set."""
    data_file = get_content_dir(content_set) / "terminals.json"
    with open(data_file) as f:
        data = json.load(f)
    return dict(data)


def load_all_game_data(content_set: str | None = None):
    """Load all game data (questions, NPCs, terminals) for a specific content set."""
    if content_set is None:
        content_set = get_default_content_set()

    questions = load_questions(content_set)
    npcs = load_npcs(questions, content_set)
    terminals = load_terminals(content_set)

    return questions, npcs, terminals
