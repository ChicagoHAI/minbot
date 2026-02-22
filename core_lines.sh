#!/bin/bash
# Count core lines of minbot and update README.md
cd "$(dirname "$0")" || exit 1

total=$(find minbot -name "*.py" -exec cat {} + | wc -l | tr -d ' ')
echo "minbot: $total lines"

python3 -c "
import re
readme = open('README.md').read()
block = '<!-- BEGIN LINE COUNT -->\n📏 Core bot in **${total} lines** of Python (run \`bash core_lines.sh\` to verify)\n<!-- END LINE COUNT -->'
readme = re.sub(r'<!-- BEGIN LINE COUNT -->.*?<!-- END LINE COUNT -->', block, readme, flags=re.DOTALL)
open('README.md', 'w').write(readme)
"
