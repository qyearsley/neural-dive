# Question Authoring Guide

This guide will help you create high-quality educational questions for Neural Dive.

## Table of Contents
1. [Quick Start](#quick-start)
2. [Question Types](#question-types)
3. [Question Structure](#question-structure)
4. [Best Practices](#best-practices)
5. [Common Pitfalls](#common-pitfalls)
6. [Difficulty Guidance](#difficulty-guidance)
7. [Examples](#examples)

---

## Quick Start

Questions are stored in `neural_dive/data/content/algorithms/questions.json`. Neural Dive supports three question types, all fully playable:
- **Multiple Choice** (4 options) - Best for teaching through wrong answers
- **Short Answer** (type-in) - Best for interview prep, complexity questions
- **Yes/No** (true/false) - Best for quick knowledge checks

### Current Question Type Mix

The algorithms set is currently 124 multiple choice, 11 yes/no, and 5 short
answer. Multiple choice dominates; adding short-answer and yes/no questions is
the easiest way to add variety.

**Minimal Multiple Choice Example:**
```json
"example_question": {
  "type": "multiple_choice",
  "question_text": "What is the time complexity of binary search?",
  "topic": "algorithms",
  "answers": [
    {"text": "O(n)", "correct": false, "response": "Not quite. Binary search is more efficient."},
    {"text": "O(log n)", "correct": true, "response": "Correct! Binary search halves the search space each step.", "reward_knowledge": "binary_search"},
    {"text": "O(n²)", "correct": false, "response": "That's too slow!"},
    {"text": "O(1)", "correct": false, "response": "Only if you're very lucky!"}
  ]
}
```

**Short Answer Example:**
```json
"binary_search_complexity": {
  "type": "short_answer",
  "question_text": "What is the time complexity of binary search?",
  "topic": "algorithms",
  "correct_answer": "O(log n)|O(logn)|log n|logn|logarithmic",
  "match_type": "complexity",
  "correct_response": "Correct! Binary search is O(log n) - it halves the search space each step.",
  "incorrect_response": "Not quite. Think about how the search space shrinks with each comparison.",
  "reward_knowledge": "binary_search"
}
```

**Yes/No Example:**
```json
"python_dynamic_typing": {
  "type": "yes_no",
  "question_text": "Is Python a dynamically typed language?",
  "topic": "programming_fundamentals",
  "correct_answer": "yes|true|y",
  "correct_response": "Correct! Python is dynamically typed - types are checked at runtime.",
  "incorrect_response": "Actually, Python IS dynamically typed. Types are determined at runtime."
}
```

---

## Question Types

### 1. Multiple Choice (124 of 140 questions)

**Best for:**
- Teaching through wrong answers
- Complex scenarios with multiple considerations
- Questions where explanation of wrong answers adds value
- Beginner-level questions

**Structure:**
- Exactly 4 answers
- One clearly correct answer
- Three plausible wrong answers

**When to use:**
- You want to teach through common misconceptions
- The wrong answers themselves are educational
- Multiple concepts could be confused
- Beginner to medium difficulty

### 2. Short Answer (5 of 140 questions)

**Best for:**
- Big-O complexity (most common in interviews!)
- Algorithm names (DFS, BFS, Dijkstra, etc.)
- Data structure names (Hash Table, Binary Heap, etc.)
- Protocol names (TCP, UDP, HTTP, etc.)
- Fill-in-the-blank with one right answer
- Interview preparation
- Advanced difficulty questions

**Match Types:**
- `"complexity"` - Big-O notation (O(n), O(log n), etc.)
- `"exact"` - Exact text matching with alternatives
- `"numeric"` - Numbers within tolerance

**Matching Guidelines:**
Accept ALL correct variations that show understanding:
- **Complexity**: `O(n log n)` = `O(nlogn)` = `n log n` = `nlogn` = `linearithmic` = `quasilinear`
- **Algorithms**: `DFS` = `Depth-First Search` = `depth first search` = `depth-first`
- **Multiple names**: Separate with `|` (pipe): `"DFS|Depth-First Search|depth first"`

**When to use:**
- One clear, concise correct answer
- Testing recall of specific facts
- Interview-style questions
- Medium to hard difficulty

### 3. Yes/No (11 of 140 questions)

**Best for:**
- True/false facts
- Simple comparisons
- Clear best practices
- Quick knowledge checks
- Easy difficulty questions

**When to use:**
- Answer is unambiguously yes or no
- No nuance or "it depends"
- Testing fundamental understanding
- Warm-up or quick checks

**When NOT to use:**
- Nuanced topics ("Is quicksort always faster?" - depends!)
- Complex trade-offs
- Context-dependent answers
- Too many yes/no questions in a row (mix it up!)

---

## Question Structure

### Question ID
- Use `snake_case`
- Be descriptive but concise
- Examples: `hash_table_lookup`, `rest_vs_graphql`, `mutex_deadlock`

The ID is also the key for cross-run question history: `data_loader` copies it
onto `Question.question_id`, and `neural_dive/player_profile.py` records each
player's attempts against it in `~/.neural_dive/profile.json`. Two consequences
for authors:

- **Renaming an ID orphans its history.** Every player's record for that
  question stops matching, so the question looks fresh again and drops back to
  base selection weight. Rewording `question_text` is free; changing the key is
  not. If you must rename one, treat it as deleting a question and adding a new
  one.
- **Deleting a question is safe.** Stale records are inert -- the weighting only
  looks up IDs that still exist, and `ndive --stats` labels the strays rather
  than crashing or dropping them.

### Question Text
**✅ DO:**
- Keep it under 100 characters when possible
- Be clear and unambiguous
- Focus on one concept
- Use simple language

**❌ DON'T:**
- Use overly technical jargon without context
- Ask multi-part questions
- Make it too verbose
- Assume specific framework knowledge

**Good Examples:**
- "What is the purpose of a mutex?"
- "Which sorting algorithm is most efficient for nearly-sorted data?"
- "What does the CAP theorem state?"

**Bad Examples:**
- "In the context of distributed systems using eventual consistency with vector clocks, what..." (too complex)
- "What are the differences between REST, GraphQL, and gRPC, and when would you use each?" (multi-part)
- "What does React's useEffect hook do?" (framework-specific)

### Topic Categories

The `topic` field is free text — nothing validates it — so reuse an existing
value rather than inventing a near-duplicate. Topics currently in use, with
question counts:

- `ai_ml` (19) - ML and AI concepts, models
- `devops` (12) - CI/CD, deployment, monitoring
- `algorithms` (10) - Algorithm analysis, complexity
- `systems` (9) - Operating systems, memory, processes
- `web_development` (9) - HTTP, REST, APIs
- `databases` (8) - SQL, NoSQL, transactions
- `design_patterns` (8) - Software design patterns
- `security` (8) - Cryptography, auth, vulnerabilities
- `software_engineering` (8) - SOLID, refactoring
- `system_design` (8) - Scaling, caching, trade-offs
- `data_structures` (7) - Arrays, trees, graphs, etc.
- `testing` (7) - Test strategies, TDD
- `networking` (6) - Protocols, HTTP, TCP/IP
- `distributed_systems` (5) - CAP, consensus, replication
- `programming_fundamentals` (5) - Basics, paradigms
- `version_control` (4) - Git, branching, history
- `architecture` (3) - System and software architecture
- `theory` (3) - Computability, complexity theory
- `machine_learning` (1) - Overlaps `ai_ml`; prefer `ai_ml`

### Answers

Multiple choice questions use an `answers` list; short answer and yes/no use
`correct_answer` instead. Every multiple choice question in the set has
**exactly 4 answers**, and the in-game keys are only `1`-`4`, so don't exceed
four.

#### Correct Answer
```json
{
  "text": "O(log n)",
  "correct": true,
  "response": "Correct! Binary search halves the search space.",
  "reward_knowledge": "binary_search"  // Optional
}
```

**Response Guidelines:**
- Start with "Correct!" or "Yes!"
- Explain WHY it's correct in 1-2 sentences
- Keep it under 100 characters
- Be encouraging

**reward_knowledge:** Optional. Grants a knowledge module on correct answer.

#### Wrong Answers
```json
{
  "text": "O(n)",
  "correct": false,
  "response": "Not quite. Binary search is more efficient."
}
```

**Wrong Answer Guidelines:**
- Make them plausible! (common misconceptions)
- Give helpful feedback
- Explain what concept they might be confusing
- Don't be condescending
- Keep responses under 80 characters

**Good wrong answers:**
- Common misconceptions ("O(n)" for binary search)
- Off-by-one concept ("POST" when asking about idempotent methods)
- Related but different ("TCP" when answer is "UDP")
- Extreme values ("O(1)" for something that's O(n))

**Bad wrong answers:**
- Obviously ridiculous ("Purple" as an HTTP method)
- Completely unrelated ("Sorting" when asking about databases)
- Joke answers (keep it professional)

---

## Best Practices

### 1. Focus on Understanding, Not Memorization

**✅ Good:**
```json
"question_text": "Why are B-trees commonly used in databases?",
"answers": [
  {"text": "Minimize disk I/O", "correct": true, ...},
  {"text": "Use less memory", "correct": false, ...},
  ...
]
```

**❌ Bad:**
```json
"question_text": "In what year was the B-tree invented?"
```

### 2. One Clear Right Answer

**✅ Good:**
```json
"question_text": "What time complexity does a hash table provide for average-case lookups?"
// Clear answer: O(1)
```

**❌ Bad:**
```json
"question_text": "Which is the best sorting algorithm?"
// Depends on context!
```

### 3. Balanced Difficulty

Make wrong answers tempting but not misleading:

**✅ Good:**
```json
"question_text": "What does SOLID's Single Responsibility Principle state?",
"answers": [
  {"text": "A class should have one reason to change", "correct": true},
  {"text": "A class should do only one thing", "correct": false}, // Close!
  {"text": "A class should have one method", "correct": false}, // Clearly wrong
  {"text": "A class should inherit from one parent", "correct": false}
]
```

### 4. Inclusive Language

- Avoid gendered pronouns ("they" instead of "he/she")
- Don't assume cultural knowledge
- Use universal examples
- Be respectful and professional

### 5. Appropriate Scope

**✅ Good:**
- Core CS concepts (data structures, algorithms)
- Widely-used technologies (HTTP, SQL, Git)
- Fundamental principles (SOLID, DRY)

**❌ Avoid:**
- Obscure libraries/frameworks
- Version-specific features
- Company-specific terminology
- Cutting-edge research (unless fundamental)

---

## Common Pitfalls

### ❌ Too Specific
```json
"question_text": "In PostgreSQL 14.2, what is the default value of work_mem?"
```
**Problem:** Too specific to one version of one database.

**Better:**
```json
"question_text": "What is the purpose of database query planning?"
```

### ❌ Trick Questions
```json
"question_text": "Is Python compiled or interpreted?"
"answers": [
  {"text": "Interpreted", "correct": false},  // Wait, what?
  {"text": "Both", "correct": true}  // Trick!
]
```
**Problem:** Confusing rather than educational.

### ❌ Requires Outside Knowledge
```json
"question_text": "What does the React useState hook return?"
```
**Problem:** Assumes React experience.

**Better:**
```json
"question_text": "What is the purpose of state in UI frameworks?"
```

### ❌ Multiple Correct Answers
```json
"question_text": "Which data structure provides O(1) access?",
"answers": [
  {"text": "Array", "correct": true},  // True!
  {"text": "Hash Table", "correct": false}  // Also true!
]
```
**Problem:** Ambiguous.

**Better:**
```json
"question_text": "Which data structure provides O(1) indexed access by integer position?"
// Now "Array" is clearly the answer
```

---

## Difficulty Guidance

There is no `difficulty` field. `data_loader` reads only the fields on the
`Question` dataclass (`question_text`, `topic`, `type`, `answers`,
`correct_answer`, `correct_response`, `incorrect_response`, `reward_knowledge`,
`match_type`, `case_sensitive`); anything else in the JSON is silently ignored,
and no question in the set carries a difficulty rating today. (`question_id` is
also on the dataclass, but it comes from the entry's key rather than a field
inside it.)

Difficulty is instead expressed by which NPC and floor a question is assigned to
(floor 1 easiest, floor 3 bosses hardest). Use these characterizations to decide
where a question belongs:

**Easy:**
- Basic definitions
- Simple true/false concepts
- Common knowledge
- Example: "What does HTTP stand for?"

**Medium:**
- Requires understanding
- Application of concepts
- Common patterns
- Example: "When should you use a hash table vs. a binary search tree?"

**Hard:**
- Deep understanding required
- Complex scenarios
- Trade-offs and edge cases
- Example: "What are the implications of the CAP theorem for database design?"

---

## Examples

### ✅ Excellent Question
```json
"mutex_purpose": {
  "question_text": "What is the primary purpose of a mutex?",
  "topic": "systems",
  "answers": [
    {
      "text": "Prevent race conditions",
      "correct": true,
      "response": "Correct! Mutexes ensure exclusive access to shared resources.",
      "reward_knowledge": "concurrency"
    },
    {
      "text": "Speed up code execution",
      "correct": false,
      "response": "Mutexes actually add overhead for safety."
    },
    {
      "text": "Allocate memory",
      "correct": false,
      "response": "Memory allocation is separate from synchronization."
    },
    {
      "text": "Handle errors",
      "correct": false,
      "response": "Mutexes are for synchronization, not error handling."
    }
  ]
}
```

**Why it's good:**
- Clear, focused question
- One unambiguous correct answer
- Plausible wrong answers (common misconceptions)
- Helpful, educational responses
- Scoped to one concept, so it suits an early floor

### ❌ Poor Question
```json
"react_question": {
  "question_text": "In React 18, when using Suspense with startTransition, how does useTransition affect the rendering behavior of nested components when combined with useDeferredValue?",
  "topic": "web_development",
  "answers": [...]
}
```

**Problems:**
- Too specific (React 18)
- Too complex (multiple concepts)
- Too long
- Framework-specific
- Requires deep framework knowledge

---

## Testing Your Questions

Before submitting questions, ask yourself:

1. **Can someone answer without Googling?**
   - If they know the concept, yes
   - If they need to look up syntax, no

2. **Is there exactly one right answer?**
   - No ambiguity
   - No "depends on context"

3. **Are the wrong answers helpful?**
   - Do they teach something?
   - Are they common mistakes?

4. **Is it universally relevant?**
   - Not specific to one company/framework/version
   - Applicable to most developers

5. **Would a beginner understand what's being asked?**
   - Clear terminology
   - Focused on one concept

---

## Contributing

To add questions:

1. Edit `neural_dive/data/content/algorithms/questions.json`
2. Follow this guide
3. Ensure unique question IDs
4. Reference each new ID from one or more NPCs in `npcs.json`
5. Run `make validate` to confirm every reference resolves
6. Test in-game with `./ndive --seed 42`

For major additions (10+ questions), consider:
- Copying an existing entry of the same `type` as a template
- Opening an issue first to discuss
- Creating a pull request with explanations

---

## Questions About Questions?

- Check existing questions in `neural_dive/data/content/algorithms/questions.json` for examples
- Open an issue on GitHub for clarification
- Refer to this guide when in doubt

**Remember:** Good questions are clear, educational, and fun! 🎮

---

**Quick Checklist:**
- [ ] Question is clear and under 100 chars
- [ ] Topic is appropriate
- [ ] Exactly 4 answers
- [ ] One clear correct answer
- [ ] Wrong answers are plausible
- [ ] Responses are helpful and concise
- [ ] No framework-specific details
- [ ] No trick questions
- [ ] Tested in-game
