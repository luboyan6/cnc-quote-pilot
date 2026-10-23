"""Audit browser revision ownership against the pre-revision task baseline.

Read-only unless --output is explicitly provided. Run from the repository root.
"""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TASKS = ROOT / ".trellis/tasks"
REVISION = "10-21-cnc-browser-reuse"
PARENT = "10-21-cnc-pricing-mvp"
CHILDREN = [
    "10-21-cnc-mvp-01-platform-gates",
    "10-21-cnc-mvp-02-first-quote",
    "10-21-cnc-mvp-03-second-platform",
    "10-21-cnc-mvp-04-monitoring",
    "10-21-cnc-mvp-05-demo-acceptance",
]
DOC_FILES = {"prd.md", "design.md", "implement.md", "implement.jsonl", "check.jsonl"}
PARENT_EXTRA = {
    "task.json",
    "decisions.md",
    "requirements-review-handoff.md",
    "execution-status.md",
    "research/mvp-contract.md",
    "workflow-design.md",
    "agent-design.md",
    "task-map.md",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    baseline = json.loads((TASKS / REVISION / "research/task-baseline.json").read_text(encoding="utf-8"))
    failures = []
    current = {}
    for path in TASKS.rglob("task.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        if path.parent.name in current:
            failures.append(f"Duplicate task directory: {path.parent.name}")
        current[path.parent.name] = record
    ids = [record["id"] for record in current.values()]
    if len(set(ids)) != len(ids):
        failures.append("Duplicate task IDs")
    changed = []
    unchanged = []
    for relative, old_hash in baseline["files"].items():
        path = ROOT / relative
        if not path.is_file():
            failures.append(f"Original file missing: {relative}")
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() == old_hash:
            unchanged.append(relative)
            continue
        changed.append(relative)
        local = path.relative_to(TASKS)
        directory, tail = local.parts[0], Path(*local.parts[1:]).as_posix()
        allowed = (directory in CHILDREN and tail in DOC_FILES) or (directory == PARENT and tail in DOC_FILES | PARENT_EXTRA)
        if not allowed:
            failures.append(f"Unrelated original file modified: {relative}")
    for name, old in baseline["tasks"].items():
        now = current.get(name)
        if now is None:
            failures.append(f"Original task missing: {name}")
            continue
        expected = dict(old)
        if name == PARENT:
            expected["children"] = list(old["children"]) + [REVISION]
        if now != expected:
            failures.append(f"Original task metadata changed unexpectedly: {name}")
    if set(current) - set(baseline["tasks"]) != {REVISION}:
        failures.append("Unexpected new task(s)")
    for name, record in current.items():
        parent = record.get("parent")
        if parent and parent not in current:
            failures.append(f"Unknown parent: {name} -> {parent}")
        for child in record.get("children", []):
            if child not in current or current[child].get("parent") != name:
                failures.append(f"Inconsistent parent-child link: {name} -> {child}")
    # Parents are grouping; below is the explicit implementation dependency DAG.
    gates, first, second, monitor, demo = CHILDREN
    dependencies = {REVISION: [], gates: [], first: [gates, REVISION], second: [gates, first, REVISION], monitor: [first, second, REVISION], demo: [first, second, monitor]}
    visiting, visited = set(), set()

    def visit(name):
        if name in visiting:
            failures.append(f"Dependency cycle: {name}")
            return
        if name in visited:
            return
        visiting.add(name)
        for dependency in dependencies[name]:
            visit(dependency)
        visiting.remove(name)
        visited.add(name)

    for name in dependencies:
        visit(name)
    for name in [PARENT, *CHILDREN]:
        folder = TASKS / name
        for filename in ("prd.md", "design.md", "implement.md"):
            text = (folder / filename).read_text(encoding="utf-8")
            if "BR-2026-10-21" not in text or "browser-implementation-design.md" not in text:
                failures.append(f"Missing revision contract: {name}/{filename}")
        for filename in ("implement.jsonl", "check.jsonl"):
            entries = [json.loads(line) for line in (folder / filename).read_text(encoding="utf-8").splitlines() if line.strip()]
            if not any(entry.get("file") == "docs/browser-implementation-design.md" for entry in entries):
                failures.append(f"Missing shared context: {name}/{filename}")
    result = {
        "revision": REVISION,
        "baseline_task_count": len(baseline["tasks"]),
        "current_task_count": len(current),
        "original_metadata_preserved": not any("metadata" in failure for failure in failures),
        "completed_original_tasks": [name for name, record in baseline["tasks"].items() if record["status"] == "completed"],
        "changed_original_files": changed,
        "unchanged_original_file_count": len(unchanged),
        "dependencies": dependencies,
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
    }
    if args.output:
        output = args.output.resolve()
        if not output.is_relative_to(TASKS / REVISION / "research"):
            parser.error("Output must be inside this task's research directory")
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
