#!/bin/bash
# status.sh — Print current Agent OS status
ROOT_DIR="$(dirname "$(dirname "$0")")"

echo "=== Agent OS Status ==="
echo ""
echo "--- Active Project ---"
cat "$ROOT_DIR/memory/state.json"
echo ""
echo "--- Task Summary ---"
python3 -c "
import json, sys
try:
    data = json.load(open('$ROOT_DIR/memory/tasks.json'))
    tasks = data.get('tasks', [])
    from collections import Counter
    counts = Counter(t['status'] for t in tasks)
    total = len(tasks)
    print(f'Total tasks: {total}')
    for status, count in sorted(counts.items()):
        print(f'  {status}: {count}')
except Exception as e:
    print(f'Could not parse tasks: {e}')
"
echo ""
echo "--- Recent Blockers ---"
tail -20 "$ROOT_DIR/memory/blockers.md"
