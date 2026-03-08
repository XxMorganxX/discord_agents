#!/usr/bin/env python3
"""Launch all Discord bots in parallel. Run from the project root."""

import json
import signal
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
BOTS_JSON = REPO_ROOT / "bots.json"

processes: list[subprocess.Popen] = []


def load_bots() -> list[dict]:
    """Load bot config from bots.json."""
    if not BOTS_JSON.exists():
        print(f"Error: {BOTS_JSON} not found", file=sys.stderr)
        sys.exit(1)
    with open(BOTS_JSON) as f:
        data = json.load(f)
    return data.get("bots", [])


def spawn_bots(bots: list[dict]) -> None:
    """Spawn a subprocess for each bot."""
    for bot in bots:
        name = bot.get("name", "unknown")
        path = REPO_ROOT / bot["path"]
        script = bot["script"]
        python = bot.get("python")
        if python:
            python_exe = str(REPO_ROOT / python)
        else:
            python_exe = sys.executable

        if not path.exists():
            print(f"Warning: skipping {name}: path {path} does not exist", file=sys.stderr)
            continue
        if not (path / script).exists():
            print(f"Warning: skipping {name}: script {script} not found in {path}", file=sys.stderr)
            continue

        proc = subprocess.Popen(
            [python_exe, script],
            cwd=str(path),
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        processes.append(proc)
        print(f"Started {name} (PID {proc.pid})")


def shutdown(signum=None, frame=None) -> None:
    """Terminate all child processes."""
    for proc in processes:
        if proc.poll() is None:
            proc.terminate()
    for proc in processes:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> None:
    bots = load_bots()
    if not bots:
        print("No bots configured in bots.json", file=sys.stderr)
        sys.exit(1)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    spawn_bots(bots)
    if not processes:
        print("No bots started", file=sys.stderr)
        sys.exit(1)

    print("All bots running. Press Ctrl+C to stop.")
    for proc in processes:
        proc.wait()


if __name__ == "__main__":
    main()
