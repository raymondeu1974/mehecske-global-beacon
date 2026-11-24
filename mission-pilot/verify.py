"""Verify one synthetic result locally."""
import argparse
from collections import deque
from decimal import Decimal, DecimalException
import json
from pathlib import Path

CALL = json.loads(Path(__file__).with_name("call.json").read_text(encoding="utf-8-sig"))
ROUTE_TASK = "synthetic-shortest-route-v1"
ROUTE_CONSENT = "AUTHORIZE SYNTHETIC ROUTE V1"


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


def is_json_integer_at_least(value, minimum):
    return (
        type(value) is int or (isinstance(value, Decimal) and value.is_finite()
        and value == value.to_integral_value())
    ) and value >= minimum


def verify_route(result, fixture):
    path = result["path"]
    if path[0] != fixture["source"] or path[-1] != fixture["target"]:
        return False
    edges = {tuple(edge) for edge in fixture["edges"]}
    if any(edge not in edges for edge in zip(path, path[1:])):
        return False
    length = len(path) - 1
    optimal_distance, _ = reproduce(fixture)
    return length == result["distance"] == optimal_distance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("--consent", required=True,
                        choices=[CALL["required_consent"], ROUTE_CONSENT])
    args = parser.parse_args()
    try:
        result = json.loads(args.result.read_text(encoding="utf-8-sig"), parse_float=Decimal)
    except (OSError, ValueError, DecimalException, RecursionError):
        parser.error("The result must be a readable JSON file.")
    if not isinstance(result, dict) or not is_json_integer_at_least(result.get("distance"), 0):
        parser.error("The result does not match the submission format.")
    task = result.get("task_id")
    if task == ROUTE_TASK:
        path = result.get("path")
        if (result.keys() != {"task_id", "distance", "path"}
                or not isinstance(path, list) or not path
                or any(not isinstance(node, str) for node in path)):
            parser.error("The result does not match the route submission format.")
        if args.consent != ROUTE_CONSENT:
            parser.error("The route task requires its own consent phrase.")
        reproduced = verify_route(result, CALL["fixture"])
    else:
        if (task != CALL["task_id"]
                or result.keys() != CALL["submission"]["fields"].keys()
                or not is_json_integer_at_least(result["shortest_paths"], 1)):
            parser.error("The result does not match the submission format.")
        if args.consent != CALL["required_consent"]:
            parser.error("The path-count task requires its own consent phrase.")
        expected = reproduce(CALL["fixture"])
        reproduced = (result["distance"], result["shortest_paths"]) == expected
    print(json.dumps({"task_id": task, "reproduced": reproduced}))
    return 0 if reproduced else 1


if __name__ == "__main__":
    raise SystemExit(main())

