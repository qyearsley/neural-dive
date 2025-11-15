# Neural Dive 🎮

**A cyberpunk terminal roguelike learning game.**

```
╔═══════════════════════════════════════════════════════════════╗
║                        NEURAL DIVE                            ║
║        Descend through neural layers. Answer questions.       ║
║             Master new knowledge. Complete your quest.        ║
╚═══════════════════════════════════════════════════════════════╝
```

## Features

- 📚 **Multiple learning content sets** - Computer Science, Chinese HSK 6, World Geography, and more!
- 🎓 **220+ unique questions** across algorithms, systems, web, ML, languages, and geography
- 🎮 **Roguelike gameplay** with wandering NPCs and procedural maps
- 🎨 **Cyberpunk theme** with Unicode graphics (light/dark mode support)
- 🏆 **Boss battles** to win, score tracking, and unique question sets per NPC
- 💾 **Save/Load system** - save your progress and continue later
- ⚙️ **Highly configurable** themes, difficulty, and content

---

## Quick Start

```bash
# Install
pip install -e .

# Play (choose content and difficulty from menus)
./ndive

# Or play specific content directly
./ndive --content chinese-hsk6    # Learn Chinese
./ndive --content geography        # Learn geography
./ndive --content algorithms       # Learn CS (default)

# List available content
./ndive --list-content

# Other options
./ndive --help
./ndive --light      # Light terminal
./ndive --classic    # ASCII graphics
```

**Controls:** Arrow keys to move • Space/Enter to interact • >/< for stairs • **S to Save** • **L to Load** • Q to quit

---

## Content Sets

Neural Dive supports multiple learning topics! Each content set includes custom questions, NPCs, and information terminals.

### Available Content Sets

| Content Set | Description | Questions | Difficulty |
|------------|-------------|-----------|------------|
| **algorithms** *(default)* | Computer Science - algorithms, data structures, systems, web, ML | 220+ | Beginner to Expert |
| **chinese-hsk6** | Advanced Chinese vocabulary, grammar, and idioms for HSK 6 | 5 (sample) | Advanced to Expert |
| **geography** | World geography - capitals, landmarks, physical features | 6 (sample) | Beginner to Advanced |

**View all available content:**
```bash
./ndive --list-content
```

**Select content:**
- **Interactive menu**: Just run `./ndive` and select from the menu
- **Command line**: `./ndive --content chinese-hsk6`
- **Skip menu**: `./ndive --no-menu` (uses default content)

---

## Save & Load

**Save your progress:**
- Press **S** during gameplay to save
- Saves to `~/.neural_dive/save.json`
- Includes all progress, stats, and selected content set

**Load saved game:**
- Press **L** during gameplay to load
- Or load from command line: `./ndive --load` *(feature can be added)*

Your save file location: `~/.neural_dive/save.json`

---

## Gameplay

**Objective:** Descend through neural layers, answer questions, gain knowledge, defeat challenging NPCs.

**Layers:**
- **Layer 1**: Introduction - learn the basics and meet friendly NPCs
- **Layer 2**: Intermediate challenges - test your growing knowledge
- **Layer 3**: Deep Core - face the final challenges and achieve victory!

**Mechanics:**
- **Coherence** = health (80/100 start, +8 correct, -30 wrong, -45 from enemies)
- **Knowledge Modules** = rewards from correct answers
- **Score** = correct answers + NPCs defeated + knowledge + remaining coherence

Required NPCs glow brighter than optional ones.

---

## Configuration

```bash
# Command line
./ndive --theme cyberpunk --background dark
./ndive -t classic -b light
./ndive --width 60 --height 30 --seed 42

# Environment variables
export NEURAL_DIVE_THEME=cyberpunk      # or 'classic'
export NEURAL_DIVE_BACKGROUND=dark      # or 'light'
```

Edit `neural_dive/config.py` for game parameters (NPC speed, rewards, map size, etc).

---

## Adding Content

### Creating a New Content Set

Want to create your own learning content? Here's how:

**1. Create content directory:**
```bash
mkdir -p neural_dive/data/content/my-topic
```

**2. Create metadata file** (`content.json`):
```json
{
  "id": "my-topic",
  "name": "My Learning Topic",
  "description": "Learn about...",
  "version": "1.0.0",
  "topics": ["topic1", "topic2"],
  "difficulty_range": "beginner to advanced",
  "question_count": 10,
  "floors": 5
}
```

**3. Create questions** (`questions.json`) - see [docs/question-guide.md](docs/question-guide.md):
```json
{
  "question_id": {
    "topic": "topic1",
    "question_text": "What is...?",
    "answers": [
      {
        "text": "Correct answer",
        "correct": true,
        "response": "Great job!",
        "reward_knowledge": "Knowledge Module Name"
      },
      {
        "text": "Wrong answer",
        "correct": false,
        "response": "Not quite..."
      }
    ]
  }
}
```

**4. Create NPCs** (`npcs.json`):
```json
{
  "NPC_NAME": {
    "char": "N",
    "color": "cyan",
    "floor": 1,
    "npc_type": "specialist",
    "greeting": "Hello! I'm an NPC.",
    "questions": ["question_id"]
  }
}
```

**5. Create terminals** (`terminals.json`):
```json
{
  "terminal_id": {
    "title": "Help Topic",
    "content": ["Line 1", "Line 2", "..."]
  }
}
```

**6. Copy levels template:**
```bash
cp neural_dive/data/content/algorithms/levels.py neural_dive/data/content/my-topic/
```

**7. Register your content set** in `neural_dive/data/content_registry.json`:
```json
{
  "content_sets": [
    {
      "id": "my-topic",
      "path": "content/my-topic",
      "enabled": true,
      "default": false
    }
  ]
}
```

**8. Test your content:**
```bash
./ndive --content my-topic
```

### Adding Questions to Existing Content

**For algorithms content (default):**

1. Edit `neural_dive/data/content/algorithms/questions.json` following [docs/question-guide.md](docs/question-guide.md):
   ```json
   "my_question": {
     "question_text": "What is...?",
     "topic": "algorithms",
     "answers": [...]
   }
   ```

2. Run redistribution to assign to NPCs:
   ```bash
   python3 scripts/redistribute_questions.py
   ```
   This ensures each NPC gets unique questions (no duplicates).

3. Test: `./ndive --fixed --seed 42`

### Adding NPCs to Existing Content

Edit the appropriate `npcs.json` file in your content directory, then run `redistribute_questions.py` if needed.

---

## Development

```bash
# Setup
pip install -e ".[dev]"
uv run prek install

# Common tasks
make run           # Play game
make lint          # Check code quality
make format        # Auto-format
make test          # Run tests
make clean         # Remove artifacts
```

**Project Structure:**
```
neural_dive/
├── data/
│   ├── content/              # Content sets (NEW!)
│   │   ├── algorithms/       # CS content (default)
│   │   │   ├── content.json
│   │   │   ├── questions.json
│   │   │   ├── npcs.json
│   │   │   ├── terminals.json
│   │   │   └── levels.py
│   │   ├── chinese-hsk6/     # Chinese learning
│   │   └── geography/        # Geography learning
│   ├── content_registry.json # Available content sets
│   └── levels.py             # (legacy, still used)
├── game.py                   # Core game logic
├── rendering.py              # Terminal UI
├── menu.py                   # Content & difficulty menus
├── data_loader.py            # Load content sets
├── themes.py                 # Visual themes
└── ...
scripts/
└── redistribute_questions.py # Assign questions to NPCs uniquely
ndive                         # Launcher
```

---

## Documentation

- **[Question Guide](docs/question-guide.md)** - How to write good questions
- **[Content Guide](docs/content-guide.md)** - How to create new content sets
- **[Development Guide](CLAUDE.md)** - For AI assistants and contributors
- **[Known Issues](docs/known-issues.md)** - Bug tracker
- **[Scripts README](scripts/README.md)** - Helper utilities

---

## Topics Covered

**Computer Science (algorithms):** 220+ questions across: Algorithms • Data Structures • Systems • Networking • Databases • Security • Web Dev • Distributed Systems • Machine Learning • Design Patterns • Testing • DevOps • Programming Fundamentals • Software Engineering • Theory • Architecture • Compilers • Version Control • AI/ML

**Chinese HSK 6 (chinese-hsk6):** Advanced vocabulary, grammar structures, idiomatic expressions (sample set - 5 questions)

**World Geography (geography):** Capitals, physical features, countries, oceans, mountains, deserts (sample set - 6 questions)

---

## License

MIT License - Free to use, modify, and distribute. See [LICENSE](LICENSE).

---

## Contributing

Contributions welcome! Add questions, fix bugs, improve docs. See [docs/question-guide.md](docs/question-guide.md) for question guidelines.

**Made with ❤️ for CS learners everywhere**
# neural-dive
