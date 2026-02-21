#!/bin/bash
# Count core lines of minbot
cd "$(dirname "$0")" || exit 1

echo "minbot core line count"
echo "========================"
echo ""

for f in minbot/config.py minbot/github.py minbot/agent.py minbot/worker.py minbot/scheduler.py minbot/bot.py; do
  count=$(wc -l < "$f")
  name=$(basename "$f")
  printf "  %-16s %5s lines\n" "$name" "$count"
done

root=$(cat minbot/__init__.py minbot/__main__.py | wc -l)
printf "  %-16s %5s lines\n" "(root)" "$root"

echo ""
total=$(find minbot -name "*.py" -exec cat {} + | wc -l)
echo "  Total:          $total lines"
