# Neural Dive

**A cyberpunk terminal roguelike learning game.**

```
╔═══════════════════════════════════════════════════════════════╗
║                        NEURAL DIVE                            ║
║        Descend through neural layers. Answer questions.       ║
║             Master new knowledge. Complete your quest.        ║
╚═══════════════════════════════════════════════════════════════╝
```

## Features

- **Multiple learning content sets** - Computer Science, Chinese HSK 6, World Geography, and more
- **227+ unique questions** across algorithms, systems, web, ML, languages, and geography
- **Roguelike gameplay** with wandering NPCs and procedural maps
- **Cyberpunk theme** with Unicode graphics (light/dark mode support)
- **Save/Load system** - save your progress and continue later
- **Highly configurable** themes, difficulty, and content

---

## Install & Play

### For Players (Easiest)

```bash
pipx install git+https://github.com/qyearsley/neural-dive.git
neural-dive
```

**That's it!** pipx handles everything automatically.

### For Contributors

```bash
git clone https://github.com/qyearsley/neural-dive.git
cd neural-dive
pip3 install blessed
./ndive
```

---

## Usage

```bash
# Play (interactive content menu)
./ndive

# Or play specific content directly
./ndive --content chinese-hsk6    # Learn Chinese
./ndive --content geography        # Learn geography
./ndive --content algorithms       # Learn CS (default)

# List available content
./ndive --list-content

# Other options
./ndive --help
./ndive --light      # Light terminal background
./ndive --classic    # ASCII graphics (compatibility mode)
```

**Controls:** Arrow keys to move • Space/Enter to interact • >/< for stairs • **S to Save** • **L to Load** • Q to quit

---

## Content Sets

Neural Dive supports multiple learning topics! Each content set includes custom questions, NPCs, and information terminals.

### Available Content Sets

| Content Set | Description | Questions | Difficulty |
|------------|-------------|-----------|------------|
| **algorithms** *(default)* | Computer Science - algorithms, data structures, systems, web, ML | 227 | Beginner to Expert |
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

Want to create your own learning content? See **[Content Guide](docs/content-guide.md)** for complete instructions on:

- Creating new content sets
- Adding questions to existing content
- Configuring NPCs and terminals
- Testing and registering your content

**Quick start for adding questions to existing content:**

1. Edit `neural_dive/data/content/algorithms/questions.json` (see [Question Guide](docs/question-guide.md))
2. Run `python3 scripts/redistribute_questions.py` to assign questions to NPCs
3. Test with `./ndive --fixed --seed 42`

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

### Computer Science (algorithms content)
227 questions covering algorithms, data structures, systems programming, networking, databases, security, web development, distributed systems, machine learning, design patterns, testing, DevOps, compilers, version control, and software architecture.

### Chinese HSK 6 (chinese-hsk6 content)
Advanced vocabulary, grammar structures, and idiomatic expressions for HSK 6 learners. Sample set with 5 questions.

### World Geography (geography content)
Capitals, physical features, countries, oceans, mountains, and deserts. Sample set with 6 questions.

---

## License

MIT License - Free to use, modify, and distribute. See [LICENSE](LICENSE).

---

## Contributing

Contributions welcome! Add questions, fix bugs, improve docs. See [docs/question-guide.md](docs/question-guide.md) for question guidelines.

**Made with love for learners everywhere**
