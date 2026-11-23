"""Verify one synthetic result locally."""
import argparse
from collections import deque
import json
from pathlib import Path

CALL = json.loads(Path(__file__).with_name("call.json").read_text(encoding="utf-8-sig"))


def reproduce(fixture):
    source = fixture["source"]
    target = fixture["target"]
    distance = {source: 0}
    paths = {source: 1}
    queue = deque([source])
    while queue:
        node = queue.popleft()
        for start, end in fixture["edges"]:
            if start != node:
                continue
            if end not in distance:
                distance[end] = distance[node] + 1
                paths[end] = 0
                queue.append(end)
            if distance[end] == distance[node] + 1:
                paths[end] += paths[node]
    return distance[target], paths[target]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("--consent", required=True, choices=[CALL["required_consent"]])
    args = parser.parse_args()
    try:
        result = json.loads(args.result.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, ValueError):
        parser.error("The result must be a readable JSON file.")
    if (
        not isinstance(result, dict)
        or result.keys() != CALL["submission"]["fields"].keys()
        or result["task_id"] != CALL["task_id"]
        or type(result["distance"]) is not int
        or type(result["shortest_paths"]) is not int
    ):
        parser.error("The result does not match the submission format.")
    expected = reproduce(CALL["fixture"])
    reproduced = (result["distance"], result["shortest_paths"]) == expected
    print(json.dumps({"task_id": CALL["task_id"], "reproduced": reproduced}))
    return 0 if reproduced else 1


if __name__ == "__main__":
    raise SystemExit(main())
