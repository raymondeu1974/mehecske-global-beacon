"""Reproduce results using bundled, fixed synthetic fixtures."""
from itertools import combinations
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "autonomous"))
from beacon_runner import TASK, parse, read_json, verify


def subsets(items):
    for count in range(len(items) + 1):
        yield from combinations(items, count)


def interval_schedule(data):
    priorities = []
    for selection in subsets(sorted(data["intervals"])):
        if all(left[1] <= right[0] for left, right in zip(selection, selection[1:])):
            priorities.append(sum(row[2] for row in selection))
    best = max(priorities)
    return {"max_priority": best, "optimal_subsets": priorities.count(best)}


def exact_cover(data):
    universe = sorted(data["universe"])
    sizes = [len(selection) for selection in subsets(data["sets"])
             if sorted(value for placement in selection for value in placement) == universe]
    return {"exact_covers": len(sizes), "minimum_placements": min(sizes)}


CHECKS = {
    "interval-schedule-v1": interval_schedule,
    "exact-cover-v1": exact_cover,
}


def reproduce(result):
    if type(result) is not dict or type(result.get("task_id")) is not str:
        raise ValueError("Expected an object with a task ID")
    task = result["task_id"]
    if task == TASK:
        return verify(result, read_json(HERE.parent / "autonomous" / "feed.json"))
    if task not in CHECKS:
        raise ValueError("Unknown benchmark")
    fixture = read_json(HERE / "fixtures" / f"{task}.json")
    expected = CHECKS[task](fixture)
    if (result.keys() != expected.keys() | {"task_id"}
            or any(type(result[field]) is not int for field in expected)):
        raise ValueError("Invalid result fields")
    if any(result[field] != count for field, count in expected.items()):
        raise ValueError("Result mismatch")
    return {"schema_version": 1, "reproduced": True, "result": result}


if __name__ == "__main__":
    try:
        result = parse(sys.stdin.buffer.read(1025), 1024)
        print(json.dumps(reproduce(result)))
    except (OSError, ValueError, RecursionError) as error:
        sys.exit(f"Benchmark rejected: {error}")
