"""Quick local test — calls parser + bug detector directly."""
import sys
sys.path.insert(0, '.')

from agents.parser_agent import parse_code
from agents.bug_detector_agent import detect_bugs

with open("./uploads/test_buggy_py.py", "r") as f:
    code = f.read()

parsed = parse_code(code, "python")
print(f"Parsed: {len(parsed['functions'])} functions, {len(parsed['variables'])} variables, {len(parsed['risks'])} risks\n")

print("=== Parser Risks ===")
for r in parsed["risks"]:
    print(f"  [{r['type']}] Line {r['line']}: {r['message'][:100]}")
print()

bugs = detect_bugs(code, parsed, [], "python")
print(f"=== Total Bugs: {len(bugs)} ===\n")
for b in bugs:
    sev = b.get("severity", "?").upper()
    line = b.get("line_number", "?")
    btype = b.get("bug_type", "")
    expl = b.get("explanation", "")[:120]
    fix = b.get("suggested_fix", "")[:120]
    print(f"[{sev}] Line {line}: {btype}")
    print(f"  Explanation: {expl}")
    print(f"  Fix: {fix}")
    print()
