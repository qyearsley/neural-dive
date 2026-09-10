#!/usr/bin/env python3
"""Validate the links between npcs.json and questions.json.

Two failures are fatal:

- an NPC references a question that does not exist, and
- a question no NPC references.

The second one matters as much as the first. An unreferenced question can never
appear in a run, so it is invisible to playtesting: 22% of the set had rotted
that way before this check existed. If a question is genuinely retired, delete
it rather than leaving it orphaned.
"""

import json
import sys

# Load data
with open("neural_dive/data/content/algorithms/npcs.json") as f:
    npcs = json.load(f)

with open("neural_dive/data/content/algorithms/questions.json") as f:
    questions = json.load(f)

print("=" * 70)
print("VALIDATION REPORT")
print("=" * 70)

# Validate all question IDs
errors = []
warnings = []
valid_count = 0

for npc_name, npc_data in npcs.items():
    question_ids = npc_data.get("questions", [])

    for q_id in question_ids:
        if q_id not in questions:
            errors.append(f"ERROR: {npc_name} references missing question: {q_id}")
        else:
            valid_count += 1

# Questions no NPC asks can never appear in a run.
referenced = {q_id for npc_data in npcs.values() for q_id in npc_data.get("questions", [])}
orphans = sorted(set(questions) - referenced)
for q_id in orphans:
    errors.append(f"ERROR: no NPC references question: {q_id}")

# Check for duplicate questions within same NPC
for npc_name, npc_data in npcs.items():
    question_ids = npc_data.get("questions", [])
    if len(question_ids) != len(set(question_ids)):
        duplicates = [q for q in set(question_ids) if question_ids.count(q) > 1]
        warnings.append(f"WARNING: {npc_name} has duplicate questions: {duplicates}")

print(f"\nTotal question references: {valid_count}")
print(f"Total NPCs: {len(npcs)}")
print(f"Total questions in database: {len(questions)}")
print(f"Questions reachable in a run: {len(referenced & set(questions))}")

if errors:
    print(f"\nERRORS FOUND ({len(errors)}):")
    for error in errors:
        print(f"  {error}")
else:
    print("\nAll question references are valid!")

if warnings:
    print(f"\nWARNINGS ({len(warnings)}):")
    for warning in warnings:
        print(f"  {warning}")

# Summary by floor
print("\n" + "=" * 70)
print("NPC SUMMARY BY FLOOR")
print("=" * 70)

by_floor = {}
for npc_name, npc_data in npcs.items():
    floor = npc_data.get("floor", 0)
    if floor not in by_floor:
        by_floor[floor] = []
    by_floor[floor].append((npc_name, len(npc_data.get("questions", []))))

for floor in sorted(by_floor.keys()):
    print(f"\nFloor {floor} ({len(by_floor[floor])} NPCs):")
    total_questions = sum(q_count for _, q_count in by_floor[floor])
    for npc_name, q_count in sorted(by_floor[floor]):
        print(f"  {npc_name:20s}: {q_count:2d} questions")
    print(f"  Total: {total_questions} questions")

if not errors and not warnings:
    print("\n" + "=" * 70)
    print("VALIDATION PASSED - Ready to test!")
    print("=" * 70)

# Exit non-zero on errors so this can gate a commit or a build. Errors are a
# missing question reference or an unreachable question. Warnings (duplicate
# question references within one NPC) are informational and don't fail.
if errors:
    sys.exit(1)
