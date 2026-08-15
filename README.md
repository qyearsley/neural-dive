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

- **Computer Science learning content** - 140 questions across algorithms, systems, web, ML, and more
- **Roguelike gameplay** with wandering NPCs and procedural maps
- **Cyberpunk theme** with Unicode graphics (light/dark mode support)
- **Save/Load system** - save your progress and continue later
- **Highly configurable** themes and difficulty

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
# Play the game
./ndive

# Other options
./ndive --help
./ndive --seed 42    # Reproducible run
./ndive --load       # Resume the saved game
```

**Controls:** Arrow keys to move • Space/Enter to interact • >/< for stairs • **S to Save** • **L to Load** • Q to quit

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
./ndive --width 60 --height 30 --seed 42
./ndive --load /path/to/save.json
```

The display is fixed to the cyberpunk dark theme; there are no theme options.

Edit `neural_dive/config.py` for game parameters (NPC speed, rewards, map size, etc).

---

## Adding Content

Want to create your own learning content? See **[Content Guide](docs/content-guide.md)** for complete instructions on:

- Writing questions (see [Question Guide](docs/question-guide.md))
- Configuring NPCs and terminals
- Testing your changes

**Quick start for adding questions:**

1. Edit `neural_dive/data/content/algorithms/questions.json` (see [Question Guide](docs/question-guide.md))
2. Reference the new question's ID from one or more NPCs in `npcs.json`
3. Run `uv run validate_questions.py` to confirm every reference resolves
4. Test with `./ndive --seed 42`

---

## Development

```bash
# Setup
make dev-install   # Install package + dev dependencies
make hooks         # Install git pre-commit hooks

# Common tasks
make run           # Play game
make test          # Run tests (ARGS="-k name" to filter)
make check         # Lint + format check + typecheck
make ci            # check + test -- run before pushing
make fix           # Auto-fix lint and format
make clean         # Remove artifacts
```

This repo has no CI. `make ci` and the pre-commit hooks are the only automatic
checks, and both run the same commands.

**Project Structure:**
```
neural_dive/
├── data/
│   ├── content/              # Content sets
│   │   └── algorithms/       # CS content (default)
│   │       ├── content.json
│   │       ├── questions.json
│   │       ├── npcs.json
│   │       ├── terminals.json
│   │       └── levels.py
│   └── levels.py             # Legacy level definitions
├── managers/                 # Game state managers
│   ├── player_manager.py
│   ├── npc_manager.py
│   ├── floor_manager.py
│   └── conversation_engine.py
├── game.py                   # Core game logic
├── rendering.py              # Terminal UI
├── data_loader.py            # Load content sets
├── themes.py                 # Visual themes
├── tests/                    # pytest suite
└── ...
scripts/
└── README.md                 # Content-inspection one-liners
validate_questions.py         # Check NPC → question references resolve
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
140 questions covering algorithms, data structures, systems programming, networking, databases, security, web development, distributed systems, machine learning, design patterns, testing, DevOps, compilers, version control, and software architecture.

---

## License

MIT License - Free to use, modify, and distribute. See [LICENSE](LICENSE).

---

## Contributing

Contributions welcome! Add questions, fix bugs, improve docs. See [docs/question-guide.md](docs/question-guide.md) for question guidelines.

Personal educational project by Quinten Yearsley.
