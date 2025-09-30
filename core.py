# core.py — readme-patcher (robust fences)
import re
from pathlib import Path
from typing import List, Dict, Optional

# Aceita ``` ou ~~~, CRLF/LF, espaços após fences, e EOF sem newline
FENCE_RE = re.compile(
    r"(?ms)^"
    r"(?P<fence>```|~~~)"                 # abertura
    r"(?P<header>[^\r\n]*)\r?\n"          # header na mesma linha
    r"(?P<body>.*?)(?:\r?\n)"             # corpo não-greedy
    r"(?P=fence)[ \t]*(?:\r?\n|$)"        # fecho (permite espaços e EOF)
)

def _parse_header(header: str) -> Dict[str, str]:
    tokens = [t for t in header.strip().split() if t]
    res: Dict[str, str] = {}
    for t in tokens:
        low = t.lower()
        if low in ("from", "to"):
            res["mode"] = low
        elif t.startswith("file="):
            res["file"] = t[len("file="):]
        # resto ignorado (linguagem etc.)
    return res

def parse_instructions(md_text: str, doc_name: str = "DOC") -> List[Dict[str, str]]:
    writes: List[Dict[str, str]] = []
    pairs: Dict[str, Dict[str, str]] = {}

    for m in FENCE_RE.finditer(md_text):
        header = m.group("header")
        body = m.group("body")
        meta = _parse_header(header)
        if "file" not in meta:
            continue
        file_path = meta["file"]
        mode = meta.get("mode")
        if mode in ("from", "to"):
            pair = pairs.setdefault(file_path, {})
            pair[mode] = body
        else:
            writes.append({"kind": "write", "file": file_path, "content": body, "doc": doc_name})

    replaces: List[Dict[str, str]] = []
    for f, kv in pairs.items():
        if "from" in kv and "to" in kv:
            replaces.append({"kind": "replace", "file": f, "from": kv["from"], "to": kv["to"], "doc": doc_name})

    return writes + replaces

def _replace_once(text: str, old: str, new: str) -> Optional[str]:
    idx = text.find(old)
    if idx == -1:
        # tenta normalizar CRLF
        old_crlf = old.replace("\n", "\r\n")
        if old_crlf in text:
            return text.replace(old_crlf, new.replace("\n", "\r\n"), 1)
        return None
    return text[:idx] + new + text[idx + len(old):]

def _simple_diff(before: str, after: str, name: str) -> str:
    b = before.splitlines()
    a = after.splitlines()
    out = [f"@@ {name} @@"]
    mx = max(len(b), len(a))
    for i in range(mx):
        bl = b[i] if i < len(b) else ""
        al = a[i] if i < len(a) else ""
        if bl != al:
            out.append(f"- {bl}")
            out.append(f"+ {al}")
    if len(out) == 1:
        out.append("(no changes)")
    return "\n".join(out)

def preview_plan(plan, root: Path, verbose: bool = False) -> None:
    for item in plan:
        target = (root / item["file"]).resolve()
        if item["kind"] == "write":
            before = target.read_text(encoding="utf-8-sig") if target.exists() else ""
            after = item["content"]
            print(_simple_diff(before, after, f"{target} (write preview)"))
        else:
            if not target.exists():
                print(f"!! {target} does not exist (replace preview)")
                continue
            before = target.read_text(encoding="utf-8-sig")
            after = _replace_once(before, item["from"], item["to"])
            if after is None:
                print(f"!! No match for 'from' in {target}")
            else:
                print(_simple_diff(before, after, f"{target} (replace preview)"))

def apply_plan(plan, root: Path, encoding: str = "utf-8", verbose: bool = False) -> bool:
    ok = True
    for item in plan:
        target = (root / item["file"]).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            if item["kind"] == "write":
                target.write_text(item["content"], encoding=encoding)
                if verbose: print(f"Wrote {target}")
            else:
                if not target.exists():
                    print(f"ERROR replace {target}: file not found"); ok = False; continue
                before = target.read_text(encoding="utf-8-sig")
                after = _replace_once(before, item["from"], item["to"])
                if after is None:
                    print(f"ERROR replace {target}: 'from' snippet not found"); ok = False; continue
                target.write_text(after, encoding=encoding)
                if verbose: print(f"Patched {target}")
        except Exception as e:
            print(f"ERROR {target}: {e}"); ok = False
    return ok
