import httpx
import json

print("Sending request... (may take a while for model loading)")
r = httpx.post(
    "http://localhost:8000/api/analyze",
    json={"file_path": "./uploads/test_buggy_py.py", "language": "python"},
    timeout=300,
)
data = r.json()
bugs = data.get("bugs", [])
print(f"\nTotal bugs found: {len(bugs)}\n")
for b in bugs:
    sev = b.get("severity", "?").upper()
    line = b.get("line_number", "?")
    btype = b.get("bug_type", "")
    expl = b.get("explanation", "")[:120]
    fix = b.get("suggested_fix", "")[:120]
    hist = b.get("historical_bugs", [])
    print(f"[{sev}] Line {line}: {btype}")
    print(f"  Explanation: {expl}")
    print(f"  Fix: {fix}")
    if hist:
        print(f"  Similar bugs: {len(hist)}")
    print()
