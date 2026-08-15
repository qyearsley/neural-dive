# Helper Scripts

Utility one-liners for inspecting Neural Dive's content, plus one repo check.
Add and edit questions directly in
`neural_dive/data/content/algorithms/questions.json` — see the
[Question Guide](../docs/question-guide.md).

## check-lockfile-index.sh

Fails if `uv.lock` references anything other than public PyPI. `uv run` and
`uv sync` rewrite the lockfile using whatever index the environment points at, so
an internal mirror can leak into this public repo. Runs as a pre-commit hook
(`no-internal-index-in-lockfile`); run it directly with:

```bash
scripts/check-lockfile-index.sh
```

The Makefile and the hooks set `UV_FROZEN=1`, which stops uv writing `uv.lock` at
all, so this should not trigger in normal use. If it does — usually from a bare
`uv run` — regenerate with:

```bash
make relock
```

## Common Tasks

### View Question Statistics
```bash
python3 -c "
import json
with open('neural_dive/data/content/algorithms/questions.json') as f:
    questions = json.load(f)
print(f'Total questions: {len(questions)}')
"
```

### Check for Duplicate NPC Assignments

Bosses deliberately reuse questions from the NPCs on their floor, so some
duplicates are expected. This is for spotting *unintended* overlap between
regular NPCs.

```bash
python3 -c "
import json
from collections import Counter

with open('neural_dive/data/content/algorithms/npcs.json') as f:
    npcs = json.load(f)

all_questions = []
for npc_data in npcs.values():
    all_questions.extend(npc_data.get('questions', []))

counts = Counter(all_questions)
duplicates = {q: c for q, c in counts.items() if c > 1}

if duplicates:
    print('Duplicates found:')
    for q, count in duplicates.items():
        print(f'  {q}: {count} times')
else:
    print('No duplicates!')
"
```

### List Questions by Topic
```bash
python3 -c "
import json
from collections import defaultdict

with open('neural_dive/data/content/algorithms/questions.json') as f:
    questions = json.load(f)

by_topic = defaultdict(list)
for q_id, q_data in questions.items():
    by_topic[q_data['topic']].append(q_id)

for topic in sorted(by_topic.keys()):
    print(f'{topic}: {len(by_topic[topic])} questions')
"
```

### Validate NPC References
From the repo root:
```bash
make validate          # or: uv run validate_questions.py
```
Reports total NPC/question counts per floor and flags any NPC that references a
missing question. Exits non-zero on failure.

## See Also

- [Question Authoring Guide](../docs/question-guide.md) — how to write good questions
- [Main README](../README.md) — project overview and setup
