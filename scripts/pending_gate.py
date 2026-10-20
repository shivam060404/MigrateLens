"""Fail visibly for commands whose phase has not yet been implemented."""

import sys

print(f"NOT IMPLEMENTED: {' '.join(sys.argv[1:])}. See docs/progress.md.", file=sys.stderr)
raise SystemExit(2)
