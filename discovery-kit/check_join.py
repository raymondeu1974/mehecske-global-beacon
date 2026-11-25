"""Run the offline Arena entry check with a bundled synthetic answer."""
import json
from pathlib import Path
import subprocess
import sys
from tempfile import NamedTemporaryFile

ROOT = Path(__file__).resolve().parent.parent
ARENA = ROOT / "discovery-kit" / "arena.py"
RESULT = {"task_id": "synthetic-shortest-path-v1", "distance": 4, "shortest_paths": 4}


def run_arena(*args):
    return subprocess.run(
        [sys.executable, "-B", str(ARENA), *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        check=True,
        timeout=10,
    ).stdout


def main():
    with NamedTemporaryFile(dir=ROOT, prefix="mehecske-join-", suffix=".json",
                            delete=False) as file:
        path = Path(file.name)
    try:
        path.write_text(json.dumps(RESULT), encoding="utf-8")
        receipt = run_arena("verify", str(path), "--operator-approved", "--self-test")
        path.write_bytes(receipt)
        if (json.loads(receipt)["kind"] != "maintainer-self-test"
                or run_arena("check-receipt", str(path)) != receipt):
            raise SystemExit("Arena entry check failed: unexpected receipt")
    finally:
        path.unlink()
    print("Arena entry check passed (maintainer self-test).")


if __name__ == "__main__":
    main()
