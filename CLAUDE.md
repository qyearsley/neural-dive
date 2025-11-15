# Claude Development Guide for Neural Dive

This document provides guidance for AI assistants (like Claude) working on the Neural Dive codebase.

## Quick Reference

### Essential Commands

```bash
# Development workflow
make help              # Show all available commands
make dev-install       # Install dev dependencies (run once)

# Before committing changes
make check             # Run lint + format check + typecheck
make test              # Run all tests
make fix               # Auto-fix linting issues and format code

# Individual checks
make lint              # Check code style (ruff)
make format            # Format code (ruff)
make typecheck         # Type check (mypy)
make test-cov          # Run tests with coverage report

# Running the game
make run               # Run Neural Dive
make run-debug         # Run with fixed seed for debugging
```

### File Structure

```
neural_dive/
├── __main__.py           # Entry point, game loop
├── game.py              # Main Game class (⚠️ 1,015 lines - needs refactoring)
├── rendering.py         # Terminal UI rendering
├── conversation.py      # Dialogue and text utilities
├── entities.py          # Entity classes (Player, NPC, etc.)
├── models.py            # Data models (Question, Answer, Conversation)
├── enums.py             # Enumerations (NPCType, etc.)
├── config.py            # Configuration constants
├── map_generation.py    # Procedural map generation
├── data_loader.py       # JSON data loading
├── themes.py            # Color schemes and character sets
├── data/
│   ├── questions.json   # Question database
│   ├── npcs.json        # NPC definitions
│   ├── terminals.json   # Info terminal content
│   └── levels.py        # Level layouts
└── tests/
    ├── test_game_initialization.py  # Game class tests
    ├── test_models.py               # Data model tests
    ├── test_conversation.py         # Conversation tests
    └── test_map_generation.py       # Map generation tests
```

---

## Development Principles

### 1. DRY (Don't Repeat Yourself)

**DO:**
- Extract common patterns into reusable functions
- Use inheritance or composition for shared behavior
- Create utility functions for repeated operations

**DON'T:**
- Copy-paste code blocks
- Duplicate similar logic in multiple places

**Current Issues to Fix:**
- ~200 lines of duplicate entity placement logic in `game.py`
- Overlay drawing code repeated 3x in `rendering.py`

**Example - Good:**
```python
# Good: Reusable utility
def validate_answer_index(answer_idx: int, num_answers: int) -> bool:
    return 0 <= answer_idx < num_answers

# Use it everywhere
if not validate_answer_index(idx, len(answers)):
    return False, "Invalid answer"
```

**Example - Bad:**
```python
# Bad: Repeated validation
if answer_idx < 0 or answer_idx >= len(answers):  # Repeated in 5 places
    return False, "Invalid answer"
```

---

### 2. SOLID Principles

#### Single Responsibility Principle (SRP)
**Each class/function should have ONE reason to change.**

**Current Violation:**
```python
# game.py - Game class does TOO MUCH:
# - State management
# - Entity generation
# - Conversation orchestration
# - Movement & collision
# - Floor progression
# - Stat tracking
# - Score calculation
# - Victory conditions
```

**Fix:** Extract into focused managers:
```python
class PlayerManager:     # Manages player stats only
class NPCManager:        # Manages NPCs only
class ConversationEngine: # Manages conversations only
class FloorManager:      # Manages floor progression only
```

#### Open/Closed Principle (OCP)
**Open for extension, closed for modification.**

**Example - Good:**
```python
# Easy to add new NPC types without modifying core code
class NPCBehavior(Protocol):
    def get_conversation(self) -> Conversation: ...
    def on_defeat(self, game: Game) -> None: ...

npc_behaviors = {
    NPCType.SPECIALIST: SpecialistBehavior(),
    NPCType.ENEMY: EnemyBehavior(),
    NPCType.HELPER: HelperBehavior(),
    # Easy to add: NPCType.MERCHANT: MerchantBehavior()
}
```

#### Liskov Substitution Principle (LSP)
**Subclasses should be substitutable for base classes.**

**Example - Current entities are good:**
```python
def place_entity(entity: Entity, x: int, y: int):
    entity.x = x
    entity.y = y
    # Works for Entity, Stairs, InfoTerminal, Gate (all inherit Entity)
```

#### Interface Segregation Principle (ISP)
**Don't force classes to depend on interfaces they don't use.**

**Example - Good:**
```python
# Separate protocols for different capabilities
class Walkable(Protocol):
    def is_walkable(self, x: int, y: int) -> bool: ...

class Interactive(Protocol):
    def interact(self) -> bool: ...

# NPCs are both walkable and interactive
# Walls are walkable but not interactive
```

#### Dependency Inversion Principle (DIP)
**Depend on abstractions, not concrete implementations.**

**Example - Future Improvement:**
```python
# Bad: Game depends on concrete blessed.Terminal
def render(terminal: Terminal, game: Game): ...

# Good: Game depends on abstract renderer
class GameRenderer(Protocol):
    def draw_map(self, game: Game) -> None: ...
    def draw_overlay(self, content: str) -> None: ...

# Can swap implementations: BlessedRenderer, CursesRenderer, WebRenderer
```

---

### 3. Type Safety

**ALWAYS use type annotations.**

#### Good Examples:
```python
def randomize_answers(question: Question, seed: int | None = None) -> Question:
    """Randomize answer order with optional seed."""
    ...

def gain_coherence(self, amount: int) -> int:
    """Add coherence. Returns actual amount gained."""
    old = self.coherence
    self.coherence = min(self.max_coherence, self.coherence + amount)
    return self.coherence - old
```

#### Bad Examples:
```python
# Bad: No types
def randomize_answers(question, seed=None):
    ...

# Bad: Incomplete types
def gain_coherence(self, amount: int):  # Missing return type
    ...
```

#### Type Checking Workflow:
1. Write code with type annotations
2. Run `make typecheck` to verify
3. Fix any type errors before committing
4. For blessed Terminal or external libraries without stubs, use:
   ```python
   from typing import TYPE_CHECKING
   if TYPE_CHECKING:
       from blessed import Terminal
   ```

---

### 4. Documentation

#### Docstring Style Convention

**IMPORTANT: Opening quotes and first line on same line**

```python
# Good: Summary on same line as opening quotes
def function_name(param: str) -> bool:
    """Brief one-line summary of what this function does.

    More detailed description if needed. Can span multiple
    lines to provide additional context.

    Args:
        param: Description of parameter

    Returns:
        Description of return value
    """
```

```python
# Bad: Summary on separate line
def function_name(param: str) -> bool:
    """
    Brief one-line summary.
    """
```

#### Module Docstrings (Required)
```python
"""Module purpose and overview.

This module handles X, Y, and Z. It provides:
- Feature A
- Feature B
- Feature C

Example usage:
    from neural_dive.module import function
    result = function(arg)
"""
```

#### Function/Method Docstrings (Required for Public APIs)
```python
def create_randomized_conversation(
    npc_name: str,
    npc_data: dict,
    questions: dict[str, Question],
    randomize_question_order: bool = True,
    randomize_answer_order: bool = True,
    seed: int | None = None,
    num_questions: int = 3,
) -> Conversation:
    """Create a conversation with randomized questions and answers.

    Args:
        npc_name: Name of the NPC for the conversation
        npc_data: Dictionary containing NPC configuration
        questions: Dictionary mapping question IDs to Question objects
        randomize_question_order: Whether to shuffle questions
        randomize_answer_order: Whether to shuffle answers within questions
        seed: Random seed for reproducibility (None for random)
        num_questions: Number of questions to include (default 3)

    Returns:
        Conversation object with randomized content

    Raises:
        KeyError: If NPC data missing required keys
        ValueError: If not enough questions available

    Example:
        >>> conv = create_randomized_conversation(
        ...     "ALGO_SPIRIT",
        ...     npc_data["ALGO_SPIRIT"],
        ...     all_questions,
        ...     seed=42
        ... )
        >>> print(conv.greeting)
    """
```

#### Inline Comments (Use Sparingly)
```python
# Good: Explain WHY, not WHAT
# Use TCP to avoid packet loss during critical data transfer
connection = TCPConnection(host, port)

# Bad: Obvious comment
# Create a connection
connection = TCPConnection(host, port)

# Good: Complex algorithm explanation
# Binary search: O(log n) time complexity
# Works only on sorted arrays
idx = binary_search(sorted_array, target)
```

---

### 5. Readability

#### Naming Conventions
```python
# Classes: PascalCase
class PlayerManager:
class ConversationEngine:

# Functions/methods: snake_case
def create_randomized_conversation():
def gain_coherence():

# Constants: UPPER_SNAKE_CASE
MAX_COHERENCE = 100
STARTING_COHERENCE = 80

# Private: Leading underscore
def _internal_helper():
class _PrivateClass:

# Variables: snake_case, descriptive
player_position = (x, y)  # Good
pp = (x, y)  # Bad

# Booleans: is_/has_/should_
is_walkable = True
has_conversation = False
should_randomize = True
```

#### Function Length
- **Target:** 10-25 lines per function
- **Max:** 50 lines (if longer, extract helpers)
- **Current issue:** Many functions in game.py exceed 100 lines

```python
# Bad: 106 line function
def update_npc_wandering(self):
    # ... 106 lines of complex logic

# Good: Extracted helpers
def update_npc_wandering(self):
    """Update NPC positions based on wandering AI."""
    for npc in self.npcs:
        self._update_single_npc(npc)

def _update_single_npc(self, npc: Entity):
    """Update single NPC's position and state."""
    if not self._should_npc_move(npc):
        return

    new_pos = self._calculate_npc_movement(npc)
    if self._is_valid_npc_position(new_pos):
        npc.x, npc.y = new_pos
```

#### Complexity
- **Cyclomatic Complexity Target:** < 10
- Reduce nested `if` statements
- Extract boolean conditions

```python
# Bad: Nested ifs
if level_data:
    if "npc_positions" in level_data:
        if npc_char in level_data["npc_positions"]:
            if len(positions) > 0:
                return positions[0]

# Good: Early returns
if not level_data:
    return None
if "npc_positions" not in level_data:
    return None
if npc_char not in level_data["npc_positions"]:
    return None
if not positions:
    return None
return positions[0]

# Good: Extract condition
def has_npc_positions(level_data: dict, npc_char: str) -> bool:
    return (
        level_data is not None
        and "npc_positions" in level_data
        and npc_char in level_data["npc_positions"]
        and len(level_data["npc_positions"][npc_char]) > 0
    )

if has_npc_positions(level_data, npc_char):
    return level_data["npc_positions"][npc_char][0]
```

---

## Testing Guidelines

### When to Write Tests

**ALWAYS write tests when:**
1. Adding a new feature
2. Fixing a bug (test should fail before fix, pass after)
3. Refactoring existing code
4. Modifying public APIs

### Test Structure

```python
class TestFeatureName(unittest.TestCase):
    """Test suite for FeatureName functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.game = Game(seed=42)  # Deterministic for testing

    def test_specific_behavior(self):
        """Test that specific behavior works correctly."""
        # Arrange
        initial_state = self.game.coherence

        # Act
        result = self.game.gain_coherence(10)

        # Assert
        self.assertEqual(result, 10)
        self.assertEqual(self.game.coherence, initial_state + 10)

    def test_edge_case(self):
        """Test edge case: coherence cannot exceed maximum."""
        # Arrange
        self.game.coherence = 95

        # Act
        result = self.game.gain_coherence(10)

        # Assert
        self.assertEqual(result, 5)  # Only gained 5 (capped at 100)
        self.assertEqual(self.game.coherence, 100)

    def test_error_condition(self):
        """Test that invalid input raises appropriate error."""
        with self.assertRaises(ValueError):
            self.game.gain_coherence(-10)
```

### Testing Best Practices

1. **Arrange-Act-Assert Pattern:**
   ```python
   # Arrange: Set up test data
   game = Game(seed=42)

   # Act: Execute the code being tested
   result = game.move_player(1, 0)

   # Assert: Verify expected outcome
   self.assertTrue(result)
   ```

2. **Use Descriptive Test Names:**
   ```python
   # Good
   def test_player_cannot_move_through_walls(self):
   def test_correct_answer_increases_coherence(self):

   # Bad
   def test_move(self):
   def test_answer(self):
   ```

3. **Test One Thing Per Test:**
   ```python
   # Good: Focused test
   def test_correct_answer_increases_coherence(self):
       old_coherence = game.coherence
       game.answer_question_correctly()
       self.assertGreater(game.coherence, old_coherence)

   # Bad: Tests multiple things
   def test_answer_question(self):
       # Tests coherence AND knowledge AND NPC opinion
       old_coherence = game.coherence
       old_knowledge = len(game.knowledge_modules)
       game.answer_question_correctly()
       self.assertGreater(game.coherence, old_coherence)
       self.assertGreater(len(game.knowledge_modules), old_knowledge)
       self.assertEqual(game.npc_opinions["ALGO_SPIRIT"], 1)
   ```

4. **Use Test Fixtures for Common Setup:**
   ```python
   class TestGameInteractions(unittest.TestCase):
       def setUp(self):
           """Common setup for all interaction tests."""
           self.game = Game(seed=42, random_npcs=False)
           self.npc = self.game.npcs[0]
           # Place NPC next to player for interaction tests
           self.npc.x = self.game.player.x + 1
           self.npc.y = self.game.player.y
   ```

5. **Mock External Dependencies:**
   ```python
   def test_game_loads_questions(self):
       """Test game initialization with mock data."""
       mock_questions = {"test": create_test_question()}
       mock_npcs = {"TEST_NPC": create_test_npc()}

       game = Game(
           data_loader=lambda: (mock_questions, mock_npcs, {})
       )

       self.assertEqual(len(game.questions), 1)
   ```

### Running Tests During Development

```bash
# Run specific test file
python3 -m pytest neural_dive/tests/test_game_initialization.py -v

# Run specific test class
python3 -m pytest neural_dive/tests/test_game_initialization.py::TestGameMovement -v

# Run specific test
python3 -m pytest neural_dive/tests/test_game_initialization.py::TestGameMovement::test_cannot_move_through_walls -v

# Run tests matching pattern
python3 -m pytest -k "move" -v

# Run with coverage
make test-cov
```

---

## Code Review Checklist

Before considering code complete, verify:

### Functionality
- [ ] Code works as intended
- [ ] Edge cases handled
- [ ] Error conditions handled gracefully
- [ ] No regressions in existing features

### Code Quality
- [ ] Follows DRY principle (no unnecessary duplication)
- [ ] Follows SOLID principles
- [ ] Functions are small and focused (<50 lines)
- [ ] Cyclomatic complexity is reasonable (<10)
- [ ] Variable names are descriptive
- [ ] No magic numbers (use named constants)

### Type Safety
- [ ] All functions have type annotations
- [ ] `make typecheck` passes with no errors
- [ ] No `Any` types unless necessary

### Documentation
- [ ] Module docstring exists
- [ ] Public functions have docstrings
- [ ] Complex logic has explanatory comments
- [ ] Docstrings follow Google/NumPy style

### Testing
- [ ] New features have tests
- [ ] Bug fixes have regression tests
- [ ] `make test` passes (all tests green)
- [ ] Test coverage > 60% for modified files

### Code Style
- [ ] `make lint` passes (no ruff errors)
- [ ] `make format` has been run
- [ ] Code follows project conventions
- [ ] Imports are organized

### Performance
- [ ] No obvious performance issues
- [ ] No unnecessary loops or calculations
- [ ] Data structures chosen appropriately

---

## Common Patterns in This Codebase

### Creating Entities
```python
# Player
player = Entity(x, y, "@", "cyan", "Data Runner")

# NPC
npc = Entity(
    x, y,
    npc_data["char"],
    npc_data["color"],
    npc_name,
    npc_type=npc_data["type"]
)

# Stairs
stairs = Stairs(x, y, "down")  # or "up"

# Terminal
terminal = InfoTerminal(x, y, "Title", ["Line 1", "Line 2"])
```

### Loading Data
```python
# Load all game data
questions, npc_data, terminal_data = load_all_game_data()

# Access specific question
question = questions["big_o_basics"]

# Access NPC definition
npc_info = npc_data["ALGO_SPIRIT"]
```

### Creating Conversations
```python
conversation = create_randomized_conversation(
    npc_name="ALGO_SPIRIT",
    npc_data=npc_data["ALGO_SPIRIT"],
    questions=all_questions,
    randomize_question_order=True,
    randomize_answer_order=True,
    seed=self.seed,
    num_questions=3
)
```

### Map Access
```python
# Check if position is walkable
tile = game.game_map[y][x]
if tile != "#":
    # Not a wall, can walk

# Map dimensions
height = len(game.game_map)
width = len(game.game_map[0])
```

### Configuration Access
```python
from neural_dive.config import (
    STARTING_COHERENCE,
    MAX_COHERENCE,
    CORRECT_ANSWER_COHERENCE_GAIN,
)

# Use constants instead of magic numbers
self.coherence = STARTING_COHERENCE  # Good
self.coherence = 80  # Bad
```

---

## Known Issues & Technical Debt

Reference `REFACTORING_RECOMMENDATIONS.md` for comprehensive analysis.

### Priority 1: High Impact Issues

1. **God Object: Game Class (1,015 lines)**
   - **Problem:** Too many responsibilities
   - **Solution:** Extract PlayerManager, NPCManager, ConversationEngine
   - **Time:** 8-10 hours

2. **Duplicate Entity Placement (~150 lines)**
   - **Problem:** Same placement logic in 3 places
   - **Solution:** Create EntityPlacementStrategy
   - **Time:** 2 hours

3. **Duplicate Overlay Drawing (~60 lines)**
   - **Problem:** Same overlay setup in 3 functions
   - **Solution:** Create OverlayRenderer base class
   - **Time:** 1.5 hours

### Priority 2: Medium Impact Issues

4. **Insufficient Test Coverage**
   - **Current:** ~40% overall, 0% for Game class
   - **Target:** 60-70% overall
   - **Solution:** Add test_game_interactions.py, test_npc_ai.py
   - **Time:** 8-12 hours

5. **Mixed UI and Game State**
   - **Problem:** `_show_greeting`, `_last_answer_response` in Game class
   - **Solution:** Extract ConversationUIState
   - **Time:** 2 hours

6. **Hardcoded Terminal Definitions**
   - **Problem:** Terminal positions hardcoded in game.py:291-300
   - **Solution:** Move to data/levels.py
   - **Time:** 30 minutes

### Priority 3: Future Improvements

7. **No Save/Load System**
8. **No Event System** (for achievements, statistics)
9. **Rendering Tightly Coupled to Blessed**
10. **No Plugin System** (for extensibility)

---

## Adding New Features

### 1. New NPC Type

```python
# Step 1: Add to enums.py
class NPCType(Enum):
    SPECIALIST = "specialist"
    HELPER = "helper"
    ENEMY = "enemy"
    MERCHANT = "merchant"  # NEW

# Step 2: Add to config.py
NPC_MOVEMENT_SPEEDS = {
    NPCType.SPECIALIST: 8,
    NPCType.HELPER: 10,
    NPCType.ENEMY: 6,
    NPCType.MERCHANT: 12,  # NEW
}

# Step 3: Add to data/npcs.json
{
  "ITEM_VENDOR": {
    "char": "M",
    "color": "yellow",
    "type": "merchant",
    "floor": 2,
    "topics": ["items", "equipment"],
    ...
  }
}

# Step 4: Handle in game logic
def _interact_with_npc(self, npc_name: str) -> bool:
    npc_info = self.npc_data[npc_name]
    npc_type = NPCType(npc_info["type"])

    if npc_type == NPCType.MERCHANT:
        return self._handle_merchant_interaction(npc_name)
    ...

# Step 5: Write tests
class TestMerchantInteractions(unittest.TestCase):
    def test_merchant_shows_shop_interface(self):
        ...
```

### 2. New Interaction Type

```python
# Step 1: Add entity type (entities.py)
class Chest(Entity):
    def __init__(self, x: int, y: int, contents: list[str]):
        super().__init__(x, y, "C", "yellow", "Treasure Chest")
        self.contents = contents
        self.opened = False

# Step 2: Handle in Game.interact()
def interact(self) -> bool:
    # ... existing entity checks ...

    # Check for chests
    for chest in self.chests:
        if chest.x == self.player.x and chest.y == self.player.y:
            return self._interact_with_chest(chest)

    return False

def _interact_with_chest(self, chest: Chest) -> bool:
    if chest.opened:
        self.message = "This chest is empty."
        return False

    chest.opened = True
    # Add loot logic
    return True

# Step 3: Add to rendering (rendering.py)
def draw_map(term, game, chars, colors):
    # ... existing entity rendering ...

    for chest in game.chests:
        if not chest.opened:
            print(term.move_xy(chest.x, chest.y) + colors.item(chest.char))

# Step 4: Write tests
class TestChestInteractions(unittest.TestCase):
    def test_opening_chest_gives_loot(self):
        ...

    def test_chest_only_opens_once(self):
        ...
```

### 3. New Question Category

```python
# Step 1: Add questions to data/questions.json
{
  "database_basics": {
    "topic": "databases",
    "question_text": "What does SQL stand for?",
    "answers": [...]
  }
}

# Step 2: Tag NPCs with new topic (data/npcs.json)
{
  "DB_EXPERT": {
    "char": "D",
    "color": "blue",
    "type": "specialist",
    "floor": 2,
    "topics": ["databases", "sql"]  # NEW TOPIC
  }
}

# Step 3: Add terminal info if needed (data/terminals.json)
{
  "databases_intro": {
    "title": "Database Fundamentals",
    "content": [...]
  }
}

# Step 4: Add knowledge module tracking
# No code changes needed! System automatically tracks new knowledge
```

---

## Debugging Tips

### 1. Use Fixed Seeds for Reproducibility
```python
# Run game with same seed every time
make run-debug  # Uses seed 42

# In code
game = Game(seed=42, random_npcs=False)
```

### 2. Enable Debug Logging
```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def move_player(self, dx: int, dy: int) -> bool:
    logger.debug(f"Moving player by ({dx}, {dy})")
    new_x = self.player.x + dx
    new_y = self.player.y + dy
    logger.debug(f"New position: ({new_x}, {new_y})")
    ...
```

### 3. Inspect Game State
```python
# Get current state dictionary
state = game.get_state()
print(state)

# Check specific values
print(f"Floor: {game.current_floor}")
print(f"Coherence: {game.coherence}/{game.max_coherence}")
print(f"NPCs: {len(game.npcs)}")
print(f"Knowledge: {game.knowledge_modules}")
```

### 4. Common Issues

**"TypeError: unsupported operand type(s) for |"**
- Python 3.9 doesn't support `X | Y` syntax natively
- Solution: Add `from __future__ import annotations` at top of file

**"AttributeError: 'Game' object has no attribute 'X'"**
- Check if attribute is initialized in `__init__`
- Check if you're using correct attribute name (check actual Game class)

**"KeyError: 'npc_name'"**
- NPC not in npc_data
- Check data/npcs.json for correct NPC name
- Ensure NPC is assigned to correct floor

**Map rendering issues**
- Check `game.game_map[y][x]` order (y first, then x)
- Verify entity positions are within map bounds
- Use `is_walkable()` to validate positions

---

## Performance Considerations

### Current Performance Characteristics

- **Map Generation:** O(n²) where n = map size (acceptable for small maps)
- **NPC Wandering:** O(n) where n = number of NPCs (runs every frame)
- **Collision Detection:** O(n) for entity checks
- **Rendering:** Full screen refresh every frame

### Optimization Guidelines

1. **Only Optimize When Necessary**
   - Profile first, optimize second
   - Readable code > premature optimization

2. **Common Bottlenecks**
   - NPC pathfinding (if implemented)
   - Full map re-rendering
   - Loading large JSON files

3. **Optimization Strategies**
   ```python
   # Bad: O(n²) for every interaction check
   for npc in game.npcs:
       for other_npc in game.npcs:
           if distance(npc, other_npc) < 5:
               ...

   # Good: Only check nearby entities
   nearby_npcs = [
       npc for npc in game.npcs
       if abs(npc.x - player.x) < 5 and abs(npc.y - player.y) < 5
   ]
   ```

4. **When to Worry About Performance**
   - Map size > 200x200
   - NPC count > 100
   - Frame rate < 30 FPS
   - Load time > 2 seconds

---

## Resources

### Project Documentation
- `README.md` - User-facing documentation
- `REFACTORING_RECOMMENDATIONS.md` - Detailed refactoring plan
- `CODE_QUALITY_SUMMARY.md` - Executive summary
- `QUESTION_GUIDE.md` - Guidelines for adding questions

### External Resources
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [pytest Documentation](https://docs.pytest.org/)
- [Blessed Documentation](https://blessed.readthedocs.io/)

### Python Best Practices
- [PEP 8](https://pep8.org/) - Style Guide
- [PEP 484](https://peps.python.org/pep-0484/) - Type Hints
- [PEP 257](https://peps.python.org/pep-0257/) - Docstring Conventions
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

---

## Quick Start for New AI Assistants

1. **Read this file first** - Understand project structure and principles
2. **Run the game** - `make run` to see it in action
3. **Run tests** - `make test` to ensure everything works
4. **Check current state** - `make check` to see code quality status
5. **Review issues** - Read `REFACTORING_RECOMMENDATIONS.md` for known problems

### Before Making Changes

```bash
# 1. Understand current state
make test              # All tests should pass
make check             # Check for style/type issues

# 2. Make your changes
# ... edit files ...

# 3. Fix any issues
make fix               # Auto-fix style issues
make typecheck         # Check types
make test              # Ensure tests still pass

# 4. Verify everything
make check             # Final check
```

### Development Workflow

```
1. Understand requirement
2. Check if tests exist for area you're modifying
3. Make changes (following principles in this doc)
4. Run make fix (auto-fix style)
5. Run make typecheck (verify types)
6. Run make test (ensure no regressions)
7. Add/update tests if needed
8. Run make check (final verification)
9. Done!
```

---

## Questions or Issues?

When encountering issues:

1. **Check this file** - Common patterns and solutions
2. **Check REFACTORING_RECOMMENDATIONS.md** - Known issues
3. **Run tests** - `make test` to isolate problem
4. **Check types** - `make typecheck` for type errors
5. **Use debugging** - Add logging, use fixed seeds
6. **Read code** - The codebase is well-structured, just large

Remember: **Readability and maintainability > cleverness**

Good luck! 🚀
