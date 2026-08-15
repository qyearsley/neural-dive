# Content Creation Guide

This guide explains how to create new learning content sets for Neural Dive.

> **Status:** the loader takes a content-set ID (`Game(content_set="...")`), but
> nothing selects one at runtime — `__main__.py` hardcodes `"algorithms"` and
> `data_loader.get_default_content_set()` returns it unconditionally. There is
> no content registry file and no CLI flag. To play a second set today you have
> to change that hardcoded value or construct `Game` yourself. Sections below
> flag the pieces that are not wired up.

## What is a Content Set?

A **content set** is a self-contained collection of:
- **Questions** - educational questions with multiple choice, short answer, or yes/no formats
- **NPCs** - characters that present questions to the player
- **Levels** - floor layouts defining entity positions, plus terminal content

Content sets allow Neural Dive to teach any subject - from computer science to languages to geography!

## File Structure

Each content set lives in its own directory under `neural_dive/data/content/`:

```
neural_dive/data/content/
└── your-content-name/
    ├── content.json              # Metadata (not read by the game; see below)
    ├── questions.json            # Question database
    ├── npcs.json                 # NPC definitions
    └── levels.py                 # Level layouts + ZONE_TERMINALS (optional)
```

Code snippets are **not** per content set — they live in
`neural_dive/data/snippets.json` and are shared by every set.

## Step-by-Step Guide

### 1. Create Directory Structure

```bash
mkdir -p neural_dive/data/content/your-content-name
cd neural_dive/data/content/your-content-name
```

### 2. Create Metadata File

Create `content.json`:

```json
{
  "id": "your-content-name",
  "name": "Display Name for Your Content",
  "description": "A brief description of what this content teaches",
  "version": "1.0.0",
  "topics": [
    "topic1",
    "topic2",
    "topic3"
  ],
  "difficulty_range": "beginner to advanced",
  "question_count": 15,
  "floors": 3
}
```

**Fields:**
- `id` - Unique identifier (use lowercase with hyphens)
- `name` - Display name
- `description` - Brief description (1-2 sentences)
- `version` - Version number (semantic versioning)
- `topics` - List of topics covered
- `difficulty_range` - Overall difficulty level
- `question_count` - Total number of questions
- `floors` - Number of floors (`MAX_FLOORS` in `config.py` is 3)

**Not read by the game:** no code loads `content.json`. It is a manifest for
humans — keep it accurate, but changing it has no runtime effect.

### 3. Create Questions

Create `questions.json` with your educational content.

See [question-guide.md](question-guide.md) for detailed question formatting.

**Example question:**

```json
{
  "question_id_1": {
    "topic": "topic1",
    "question_text": "What is the capital of France?",
    "answers": [
      {
        "text": "Paris",
        "correct": true,
        "response": "Correct! Paris is the capital of France.",
        "reward_knowledge": "European Capitals"
      },
      {
        "text": "London",
        "correct": false,
        "response": "No, that's the capital of the UK. Paris is France's capital."
      },
      {
        "text": "Berlin",
        "correct": false,
        "response": "No, that's Germany's capital. Paris is France's capital."
      },
      {
        "text": "Rome",
        "correct": false,
        "response": "No, that's Italy's capital. Paris is France's capital."
      }
    ]
  },
  "question_id_2": {
    "topic": "topic1",
    "type": "short_answer",
    "question_text": "What year did World War II end?",
    "correct_answer": "1945",
    "correct_response": "Correct! World War II ended in 1945.",
    "incorrect_response": "Not quite. World War II ended in 1945.",
    "reward_knowledge": "20th Century History",
    "match_type": "exact",
    "case_sensitive": false
  }
}
```

**Question Types:**
- `multiple_choice` (default) - up to 4 answer options; the in-game keys are `1`-`4`
- `short_answer` - Free text input, matched per `match_type`
- `yes_no` - Simple yes/no question

Set the type with a `"type"` field. Any JSON key the `Question` dataclass doesn't
define (for example `difficulty`) is silently ignored.

**Tips:**
- Write 10-20 questions minimum
- Include good explanatory responses
- Award knowledge modules for correct answers
- Use varied difficulty levels

### 4. Create NPCs

Create `npcs.json` to define characters that present questions:

```json
{
  "NPC_NAME_1": {
    "char": "A",
    "color": "cyan",
    "floor": 1,
    "npc_type": "specialist",
    "greeting": "Hello! I'm an expert in topic 1. Let me test your knowledge!",
    "questions": ["question_id_1", "question_id_2"]
  },
  "NPC_NAME_2": {
    "char": "B",
    "color": "green",
    "floor": 2,
    "npc_type": "helper",
    "greeting": "I can help you learn! Answer correctly and I'll reward you.",
    "questions": ["question_id_3", "question_id_4"]
  },
  "BOSS_NPC": {
    "char": "Z",
    "color": "red",
    "floor": 3,
    "npc_type": "boss",
    "greeting": "Face me in the final challenge! Only masters may pass!",
    "questions": ["question_id_7", "question_id_8", "question_id_9"]
  }
}
```

**NPC Fields:**
- `char` - Single **letter** shown on the map. `parse_level` only treats
  single letters surrounded by non-letters as NPCs, so punctuation like `!`
  will never be placed. Letters may repeat across different floors.
- `color` - Color name (cyan, green, yellow, red, magenta, blue, white)
- `floor` - Which floor this NPC appears on (1-3; `MAX_FLOORS` is 3)
- `npc_type` - One of five values:
  - `specialist` - Standard knowledge test. **Required** to clear its floor.
  - `enemy` - Harder penalties on wrong answers. **Required** to clear its floor.
  - `boss` - Like a specialist but gets `boss_questions` (4) questions. Optional.
  - `helper` - No questions; restores coherence once, then has nothing more to say. Optional.
  - `quest` - No questions; activates the main quest on first interaction. Optional.
- `greeting` - Message shown when conversation starts
- `questions` - List of question IDs this NPC asks

Floor completion is computed by `data_loader.compute_floor_requirements`: only
`specialist` and `enemy` NPCs block the stairs down. Winning requires completing
a boss named in `VICTORY_BOSS_NAMES` (`config.py`) on the final floor.

**NPC Distribution Guidelines:**
- **Floor 1**: Easy questions, mostly specialists
- **Floor 2**: Medium difficulty
- **Floor 3**: Bosses, hardest questions
- **Typical setup**: 4-6 NPCs per floor, 2-3 questions per NPC (`questions_per_npc`)

### 5. Create Information Terminals

Terminal content comes from a `ZONE_TERMINALS` dict in `levels.py`, keyed by
floor and then by zone label, and positioned by the `terminal_positions` parsed
out of each floor layout:

```python
ZONE_TERMINALS = {
    1: {
        "ENTRY": {
            "title": "Welcome to Your Content",
            "content": [
                "Welcome! This content set teaches...",
                "",
                "Read terminals like this for helpful information.",
            ],
        },
    },
}
```

**Not wired up:** a `terminals.json` file is read by nothing — the algorithms set
ships one, but `floor_entity_generator` imports `ZONE_TERMINALS` from
`neural_dive.data.levels` instead. That shim re-exports the algorithms set's
`levels.py`, so terminal content is currently fixed to the algorithms set no
matter which content set is loaded.

<details>
<summary>Older <code>terminals.json</code> shape (unused)</summary>

```json
{
  "intro": {
    "title": "Welcome to Your Content",
    "content": [
      "╔══════════════════════════════════════════════════════╗",
      "║            Content Set Introduction                 ║",
      "╚══════════════════════════════════════════════════════╝",
      "",
      "Welcome! This content set teaches...",
      "",
      "Topics covered:",
      "• Topic 1 - description",
      "• Topic 2 - description",
      "• Topic 3 - description",
      "",
      "Read terminals like this for helpful information!"
    ]
  },
  "tips": {
    "title": "Learning Tips",
    "content": [
      "╔══════════════════════════════════════════════════════╗",
      "║                  Study Tips                          ║",
      "╚══════════════════════════════════════════════════════╝",
      "",
      "1. Read all answer options carefully",
      "2. Look for key words in questions",
      "3. Review information terminals",
      "4. Take your time - accuracy matters!",
      "",
      "Good luck on your learning journey!"
    ]
  }
}
```

</details>

**Terminal Tips:**
- Use box drawing characters for visual appeal
- Keep content concise (10-20 lines max)
- Provide helpful reference information
- Create 2-4 terminals per content set

### 6. Create Level Layouts (Optional)

Copy the template from the algorithms content:

```bash
cp ../algorithms/levels.py .
```

Then customize NPC positions and terminal placements for each floor.

**Simple approach:** omit `levels.py`. `data_loader.load_levels` falls back to
`neural_dive.data.levels.PARSED_LEVELS` (the algorithms layouts), and the game
places your NPCs randomly.

**Custom approach:** define exact positions in `levels.py` for a curated
experience. Remember that `ZONE_TERMINALS` is read from the shim rather than your
file (see step 5).

### 7. Select Your Content Set

There is no registry file and no CLI flag. The content set is chosen in two
hardcoded places:

- `neural_dive/__main__.py` sets `content_set = "algorithms"` before building the
  `Game`.
- `data_loader.get_default_content_set()` returns `"algorithms"` without
  consulting the filesystem.

To load your set, either edit `__main__.py` or construct the game directly:

```python
from neural_dive.game import Game

game = Game(content_set="your-content-name", seed=42)
```

### 8. Test Your Content

```bash
# Confirm every NPC question reference resolves
make validate

# Play, after pointing __main__.py at your content set
./ndive --seed 42 --fixed
```

**Testing Checklist:**
- [ ] All questions load without errors
- [ ] NPCs appear on correct floors
- [ ] Conversations work properly
- [ ] Terminals display correctly
- [ ] Knowledge rewards work
- [ ] `make validate` passes
- [ ] Save/load works (the content set ID is saved and restored)

## Example Content Set

There is currently only one: **algorithms/** — computer science, 140 questions,
15 NPCs across 3 floors. Read it alongside this guide.

## Best Practices

### Question Writing
- Be clear and unambiguous
- Provide informative feedback
- Use appropriate difficulty progression
- Include varied question types
- Test with actual users

### NPC Design
- Give each NPC a personality through greetings
- Match difficulty to floor number
- Use boss NPCs sparingly (the algorithms set has 3, all on the final floor)
- Distribute questions evenly across NPCs

### Content Organization
- Start easy, end hard (floor 1 → floor 3)
- Group related questions by topic
- Provide reference materials in terminals
- Use consistent naming conventions

### Visual Design
- Choose distinct NPC letters
- Use colors meaningfully
- Create attractive terminal displays
- Consider accessibility (color blind users)

## Publishing Your Content

Want to share your content set with others?

1. Test thoroughly
2. Add documentation (README in your content directory)
3. Consider licensing (MIT recommended)
4. Share on GitHub or with Neural Dive community
5. Submit as PR to main repo (optional)

## Troubleshooting

### Content Not Loading
- Confirm the directory name matches the ID you pass to `Game(content_set=...)`
- Ensure `questions.json` and `npcs.json` exist and parse as JSON
- Remember `__main__.py` hardcodes `"algorithms"` — a new set won't load until
  you change it

### Questions Not Loading
- Validate JSON syntax in `questions.json`
- Check question IDs match NPC references (`make validate`)
- Verify all required fields present

### NPCs Not Spawning
- Check floor numbers (1-3)
- Verify `npcs.json` syntax
- Ensure `npc_type` is one of specialist/enemy/boss/helper/quest
- Ensure `char` is a single letter, and that it appears in the floor layout
  surrounded by non-letters

### Save/Load Issues
- Old saves may not have a `content_set` field
- Delete `~/.neural_dive/save.json` to reset

## Advanced Topics

### Custom Question Types
See [question-guide.md](question-guide.md) for the three supported formats.

### Dynamic Content
Content is loaded at game start. For dynamic content, modify `data_loader.py`.

### Localization
Nothing in the loader is English-specific, so a translated set is just another
content directory — but see step 7 about selecting it.

## Need Help?

- Read the algorithms content set for a working example
- Read [question-guide.md](question-guide.md) for question formats
- Review game code in `neural_dive/data_loader.py`
- Open an issue on GitHub with questions

Happy content creating!
