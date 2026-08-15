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
- **Cyberpunk theme** with Unicode graphics
- **Save/Load system** - save your progress and continue later

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
./ndive
```

The `./ndive` launcher runs via `uv` and declares its own dependencies inline,
so it installs `blessed` on first run. If you'd rather use pip directly:
`pip3 install blessed && python3 -m neural_dive`.

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

**Layers:** (3 total, set by `MAX_FLOORS` in `config.py`)
- **Layer 1**: Introduction - 5 NPCs covering the basics, including one enemy
- **Layer 2**: Intermediate challenges - 6 specialists testing your growing knowledge
- **Layer 3**: Deep Core - three bosses; defeat one to win

**Mechanics:**
- **Coherence** = health (80/100 start, +10 correct, -25 wrong, -40 from enemies)
- **Knowledge Modules** = rewards from correct answers
- **Score** = 100 per correct answer + 50 per knowledge module + 200 per NPC
  completed + 10 per remaining coherence point

Required NPCs (specialists and enemies) glow brighter than optional ones.

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
3. Run `make validate` to confirm every reference resolves
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
make validate      # Check NPC -> question references resolve
make ci            # check + test -- run before pushing
make fix           # Auto-fix lint and format
make relock        # Regenerate uv.lock after a dependency change
make clean         # Remove artifacts
```

This repo has no CI. `make ci` and the pre-commit hooks are the only automatic
checks. They run the same linters, type check, and tests; the hooks add
whitespace/JSON fixers and a check that `uv.lock` only references public PyPI.

Use the make targets rather than calling `uv run` directly: they set
`UV_FROZEN=1`, which stops uv from re-resolving and rewriting `uv.lock` on every
invocation.

**Project Structure:**
```
neural_dive/
├── data/
│   ├── content/              # Content sets
│   │   └── algorithms/       # CS content (default, and currently the only one)
│   │       ├── content.json
│   │       ├── questions.json
│   │       ├── npcs.json
│   │       ├── terminals.json   # unused; terminal text lives in levels.py
│   │       └── levels.py
│   ├── snippets.json         # Code snippets awarded by specialists
│   └── levels.py             # Re-export shim for content/algorithms/levels.py
├── managers/                 # Game state managers
│   ├── player_manager.py
│   ├── npc_manager.py
│   ├── floor_manager.py
│   └── conversation_engine.py
├── game.py                   # Core game logic
├── input_handler.py          # Keyboard input, per game mode
├── rendering.py              # Frame composition (see *_renderer.py modules)
├── data_loader.py            # Load content sets
├── themes.py                 # Visual theme (cyberpunk dark)
├── tests/                    # pytest suite
└── ...
scripts/
├── README.md                 # Content-inspection one-liners
└── check-lockfile-index.sh   # Pre-commit: keep uv.lock on public PyPI
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
140 questions covering AI/ML, DevOps, algorithms, systems programming, web
development, databases, design patterns, security, software engineering, system
design, data structures, testing, networking, distributed systems, programming
fundamentals, version control, architecture, and computability theory.

---

## License

MIT License - Free to use, modify, and distribute. See [LICENSE](LICENSE).

---

## Contributing

Contributions welcome! Add questions, fix bugs, improve docs. See [docs/question-guide.md](docs/question-guide.md) for question guidelines.

Personal educational project by Quinten Yearsley.
