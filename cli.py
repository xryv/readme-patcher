#!/usr/bin/env python3
# readme-patcher — apply code blocks from docs to real files.
# Modes:
#  - Full write:  ```lang file=path ...```
#  - From→To replace: two blocks: ``` from file=path ...``` and ``` to file=path ...```

import argparse
import sys
from pathlib import Path
from core import parse_instructions, apply_plan, preview_plan

def parse_args():
    p = argparse.ArgumentParser(
        description="Apply code blocks from Markdown to files (full write or from→to replace)."
    )
    p.add_argument("docs", nargs="+", help="Markdown files to scan (README.md, docs/*.md, etc.)")
    p.add_argument("--root", default=".", help="Project root for relative paths (default: .)")
    p.add_argument("--apply", action="store_true", help="Write changes to disk (otherwise preview).")
    p.add_argument("--dry-run", action="store_true",
                   help="Preview only (default). Accepted for convenience on Windows.")
    p.add_argument("--encoding", default="utf-8", help="Default file encoding (write).")
    p.add_argument("--verbose", action="store_true", help="Print extra info.")
    return p.parse_args()

def main():
    args = parse_args()
    root = Path(args.root).resolve()
    if args.verbose:
        print(f"# Root: {root}")

    plan = []
    for doc in args.docs:
        p = Path(doc)
        if not p.exists():
            print(f"WARN: Missing doc {doc}", file=sys.stderr)
            continue
        text = p.read_text(encoding="utf-8-sig")  # strip BOM if present
        items = parse_instructions(text, doc_name=str(p))
        if args.verbose:
            print(f"# Parsed {len(items)} items from {doc}")
        plan.extend(items)

    if not plan:
        print("No patchable code blocks found.", file=sys.stderr)
        return 1

    if args.apply:
        ok = apply_plan(plan, root=root, encoding=args.encoding, verbose=args.verbose)
        return 0 if ok else 1
    else:
        # default = preview; --dry-run is accepted but not required
        preview_plan(plan, root=root, verbose=args.verbose)
        return 0

if __name__ == "__main__":
    sys.exit(main())
