"""Run the Python test suite with one process per test module, in parallel.

Use this instead of a serial ``unittest discover``. Rendering-heavy modules
dominate the suite, so running modules side by side cuts a ~16 minute serial
run to roughly the length of the slowest module (~3.5 minutes).

Usage (from the repository root):
    .\\.venv\\Scripts\\python.exe run_tests.py                       # every test/*_test.py
    .\\.venv\\Scripts\\python.exe run_tests.py eye_positioning radial  # selected modules
    .\\.venv\\Scripts\\python.exe run_tests.py --workers 8

Each module runs exactly as ``python -m unittest discover -s test -p <module>.py``
would. Modules are started slowest-first using durations remembered from earlier
runs in ``test/.test_timings.json`` (gitignored). Output from failing modules is
printed in full at the end, and the exit code is non-zero if any module fails.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import sys
import time


PROJECT_ROOT = Path(__file__).resolve().parent
TEST_FOLDER = PROJECT_ROOT / "test"
TIMINGS_PATH = TEST_FOLDER / ".test_timings.json"
DEFAULT_WORKERS = min(16, os.cpu_count() or 4)
# unittest exits with 5 when a module matches *_test.py but defines no tests
# (for example the sizing_test.py review-sheet script).
NO_TESTS_EXIT_CODE = 5


@dataclass(frozen=True, slots=True)
class ModuleResult:
    module: str
    exit_code: int
    seconds: float
    output: str

    @property
    def status(self) -> str:
        if self.exit_code == 0:
            return "ok"
        return "no tests" if self.exit_code == NO_TESTS_EXIT_CODE else "FAILED"


def _selected_modules(names: list[str]) -> list[str]:
    available = sorted(path.stem for path in TEST_FOLDER.glob("*_test.py"))
    if not names:
        return available
    selected = []
    for name in names:
        module = Path(name).stem
        module = module if module.endswith("_test") else f"{module}_test"
        if module not in available:
            raise SystemExit(f"Unknown test module: {name} (expected test/{module}.py)")
        selected.append(module)
    return selected


def _load_timings() -> dict[str, float]:
    try:
        return json.loads(TIMINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _run_module(module: str) -> ModuleResult:
    # Tracked __pycache__ files would otherwise be rewritten by every run.
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
    started = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "test", "-p", f"{module}.py"],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
    )
    return ModuleResult(module, completed.returncode, time.perf_counter() - started, completed.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run test/*_test.py modules in parallel processes.")
    parser.add_argument("modules", nargs="*", help="module names such as eye_positioning or flying_v_test (default: all)")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help=f"parallel processes (default: {DEFAULT_WORKERS})")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")

    timings = _load_timings()
    # Unknown modules sort first so new (possibly slow) tests do not start last.
    modules = sorted(_selected_modules(args.modules), key=lambda module: -timings.get(module, float("inf")))
    print(f"Running {len(modules)} test modules with {args.workers} workers...", flush=True)

    started = time.perf_counter()
    results: list[ModuleResult] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        for future in as_completed(executor.submit(_run_module, module) for module in modules):
            result = future.result()
            results.append(result)
            print(f"[{len(results):>3}/{len(modules)}] {result.status:<8} {result.seconds:6.1f}s  {result.module}", flush=True)
    wall_seconds = time.perf_counter() - started

    timings.update({result.module: round(result.seconds, 1) for result in results})
    TIMINGS_PATH.write_text(json.dumps(dict(sorted(timings.items())), indent=2) + "\n", encoding="utf-8")

    failed = sorted((result for result in results if result.status == "FAILED"), key=lambda result: result.module)
    for result in failed:
        print(f"\n{'=' * 30} {result.module} (exit {result.exit_code}) {'=' * 30}\n{result.output.rstrip()}")

    serial_seconds = sum(result.seconds for result in results)
    slowest = ", ".join(f"{result.module} {result.seconds:.0f}s" for result in sorted(results, key=lambda result: -result.seconds)[:3])
    print(f"\nWall time {wall_seconds:.0f}s (serial total {serial_seconds:.0f}s). Slowest: {slowest}.")
    if failed:
        print(f"FAILED modules ({len(failed)}): {', '.join(result.module for result in failed)}")
        return 1
    print("All test modules passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
