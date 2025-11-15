# Content Creation Guide

This guide explains how to create new learning content sets for Neural Dive.

## What is a Content Set?

A **content set** is a self-contained collection of:
- **Questions** - educational questions with multiple choice or short answer formats
- **NPCs** - characters that present questions to the player
- **Terminals** - information displays with reference material
- **Levels** - floor layouts defining entity positions
- **Metadata** - description and configuration

Content sets allow Neural Dive to teach any subject - from computer science to languages to geography!

## File Structure

Each content set lives in its own directory under `neural_dive/data/content/`:

```
neural_dive/data/content/
├── content_registry.json          # Registry of all content sets
└── your-content-name/
    ├── content.json               # Metadata
    ├── questions.json             # Question database
    ├── npcs.json                  # NPC definitions
    ├── terminals.json             # Info terminal content
    └── levels.py                  # Level layouts (optional)
```

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
  "floors": 5
}
```

**Fields:**
- `id` - Unique identifier (use lowercase with hyphens)
- `name` - Display name shown in menus
- `description` - Brief description (1-2 sentences)
- `version` - Version number (semantic versioning)
- `topics` - List of topics covered
- `difficulty_range` - Overall difficulty level
- `question_count` - Total number of questions
- `floors` - Number of floors/levels (typically 3-5)

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
- `multiple_choice` (default) - 2-4 answer options
- `short_answer` - Free text input, exact match
- `yes_no` - Simple yes/no question

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
    "char": "!",
    "color": "red",
    "floor": 5,
    "npc_type": "enemy",
    "greeting": "Face me in the final challenge! Only masters may pass!",
    "questions": ["question_id_7", "question_id_8", "question_id_9"]
  }
}
```

**NPC Fields:**
- `char` - Single character displayed on map
- `color` - Color name (cyan, green, yellow, red, magenta, blue, white)
- `floor` - Which floor this NPC appears on (1-5)
- `npc_type` - Type of NPC:
  - `specialist` - Standard knowledge test
  - `helper` - Gives bonus rewards
  - `enemy` - Harder questions, higher penalties
- `greeting` - Message shown when conversation starts
- `questions` - List of question IDs this NPC asks

**NPC Distribution Guidelines:**
- **Floor 1-2**: Easy questions, friendly NPCs (specialists/helpers)
- **Floor 3-4**: Medium difficulty, mixed types
- **Floor 5**: Boss fight, enemy type, hardest questions
- **Typical setup**: 3-5 NPCs per floor, 2-4 questions per NPC

### 5. Create Information Terminals

Create `terminals.json` for reference material:

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

**Terminal Tips:**
- Use box drawing characters for visual appeal
- Keep content concise (10-20 lines max)
- Provide helpful reference information
- Use ASCII art for visual interest
- Create 2-4 terminals per content set

### 6. Create Level Layouts (Optional)

Copy the template from the algorithms content:

```bash
cp ../algorithms/levels.py .
```

Then customize NPC positions and terminal placements for each floor.

**Simple approach:** Let the game randomize positions (no levels.py needed)

**Custom approach:** Define exact positions in levels.py for curated experience

### 7. Register Content Set

Add your content to `neural_dive/data/content_registry.json`:

```json
{
  "content_sets": [
    {
      "id": "algorithms",
      "path": "content/algorithms",
      "enabled": true,
      "default": true
    },
    {
      "id": "your-content-name",
      "path": "content/your-content-name",
      "enabled": true,
      "default": false
    }
  ],
  "version": "1.0.0"
}
```

**Fields:**
- `id` - Must match your content's metadata id
- `path` - Relative path from data/ directory
- `enabled` - Whether this content appears in menus
- `default` - Whether this is the default content (only one should be true)

### 8. Test Your Content

```bash
# List all content to verify registration
./ndive --list-content

# Play your content
./ndive --content your-content-name

# Test with fixed seed for reproducibility
./ndive --content your-content-name --seed 42 --fixed
```

**Testing Checklist:**
- [ ] All questions load without errors
- [ ] NPCs appear on correct floors
- [ ] Conversations work properly
- [ ] Terminals display correctly
- [ ] Knowledge rewards work
- [ ] Content appears in --list-content
- [ ] Save/load preserves content selection

## Example Content Sets

Study these examples in `neural_dive/data/content/`:

- **algorithms/** - Computer science (default, complex)
- **chinese-hsk6/** - Language learning (simple, sample)
- **geography/** - World knowledge (simple, sample)

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
- Use boss NPCs sparingly (1-2 per content set)
- Distribute questions evenly across NPCs

### Content Organization
- Start easy, end hard (floor 1 → floor 5)
- Group related questions by topic
- Provide reference materials in terminals
- Use consistent naming conventions

### Visual Design
- Choose distinct NPC characters
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

### Content Not Appearing in Menu
- Check `content_registry.json` for correct ID and path
- Verify `enabled: true` in registry
- Ensure `content.json` exists with valid JSON

### Questions Not Loading
- Validate JSON syntax in `questions.json`
- Check question IDs match NPC references
- Verify all required fields present

### NPCs Not Spawning
- Check floor numbers (1-5)
- Verify `npcs.json` syntax
- Ensure NPC type is valid (specialist/helper/enemy)

### Save/Load Issues
- Content set must be in registry
- Old saves may not have content_set field
- Delete `~/.neural_dive/save.json` to reset

## Advanced Topics

### Custom Question Types
See [question-guide.md](question-guide.md) for advanced question formats.

### Dynamic Content
Content is loaded at game start. For dynamic content, modify `data_loader.py`.

### Localization
Create multiple content sets for different languages:
- `french-grammar/`
- `spanish-vocab/`
- `german-basics/`

### Collaborative Content
Multiple authors can create complementary content sets that work together.

## Need Help?

- Check existing content sets for examples
- Read [QUESTION_GUIDE.md](QUESTION_GUIDE.md) for question formats
- Review game code in `neural_dive/data_loader.py`
- Open an issue on GitHub with questions

Happy content creating! 🎓
