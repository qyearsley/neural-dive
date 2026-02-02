#!/usr/bin/env python3
"""Validate that all NPC question references exist in questions.json."""

import json

# Load data
with open('neural_dive/data/npcs.json') as f:
    npcs = json.load(f)

with open('neural_dive/data/questions.json') as f:
    questions = json.load(f)

print("=" * 70)
print("VALIDATION REPORT")
print("=" * 70)

# Validate all question IDs
errors = []
warnings = []
valid_count = 0

for npc_name, npc_data in npcs.items():
    question_ids = npc_data.get('questions', [])

    for q_id in question_ids:
        if q_id not in questions:
            errors.append(f"ERROR: {npc_name} references missing question: {q_id}")
        else:
            valid_count += 1

# Check for duplicate questions within same NPC
for npc_name, npc_data in npcs.items():
    question_ids = npc_data.get('questions', [])
    if len(question_ids) != len(set(question_ids)):
        duplicates = [q for q in set(question_ids) if question_ids.count(q) > 1]
        warnings.append(f"WARNING: {npc_name} has duplicate questions: {duplicates}")

print(f"\nTotal question references: {valid_count}")
print(f"Total NPCs: {len(npcs)}")
print(f"Total questions in database: {len(questions)}")

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
    floor = npc_data.get('floor', 0)
    if floor not in by_floor:
        by_floor[floor] = []
    by_floor[floor].append((npc_name, len(npc_data.get('questions', []))))

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
