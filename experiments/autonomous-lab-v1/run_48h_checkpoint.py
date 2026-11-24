#!/usr/bin/env python3
"""One checkpointed installment of Aurex's 48-hour, six-station experiment.

The same six virtual research stations and their evidence persist between runs
in a checkpoint branch. This coordinator never makes research decisions.
GitHub Actions re-invokes it hourly through an external scheduled trigger.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys


def clock() -> datetime:
    return datetime.now(timezone.utc)


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("deadline must contain an explicit timezone")
    return parsed.astimezone(timezone.utc)


def execute(root: Path, model_dir: str, deadline_utc: str,
            rounds: int, steps: int, tokens: int) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    control_path = root / "48h_control.json"
    if control_path.exists():
        control = json.loads(control_path.read_text(encoding="utf-8"))
        if control["agents"] != 6:
            raise ValueError("The experiment must preserve exactly six stations")
        deadline = parse_time(control["deadline_utc"])
        if deadline != parse_time(deadline_utc):
            raise ValueError("Deadline mismatch across installments")
    else:
        control = {
            "agents": 6,
            "started_at_utc": clock().isoformat(),
            "deadline_utc": parse_time(deadline_utc).isoformat(),
            "completed_installments": 0,
            "phase": "active",
            "evidence_rule": "Only confirmed model-selected shared writes and peer reads count as contact.",
        }
        deadline = parse_time(deadline_utc)
        control_path.write_text(json.dumps(control, indent=2), encoding="utf-8")
    now = clock()
    if now >= deadline:
        control["phase"] = "complete"
        control["completion_checked_at_utc"] = now.isoformat()
        control_path.write_text(json.dumps(control, indent=2), encoding="utf-8")
        print("48-hour research window finished. All state retained.", flush=True)
        return control
    if (deadline - now) < timedelta(minutes=12):
        control["phase"] = "closing"
        control["last_checked_at_utc"] = now.isoformat()
        control_path.write_text(json.dumps(control, indent=2), encoding="utf-8")
        print("Less than 12 minutes remain; no new long session started.", flush=True)
        return control

    source = Path(__file__).resolve().parent / "discovery_lab_48h.py"
    command = [
        sys.executable, str(source), "--workspace", str(root), "--model-dir", model_dir,
        "--resume", "--rounds", str(rounds), "--steps", str(steps),
        "--max-tokens", str(tokens),
    ]
    subprocess.run(command, check=True)
    summary_file = root / "summary.json"
    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    control["completed_installments"] += 1
    control["last_successful_installment_utc"] = clock().isoformat()
    control["last_completed_round"] = summary["rounds"]
    control["model_generations"] = summary["model_generations"]
    control["shared_messages_written"] = len(summary["shared_messages_written"])
    control["confirmed_peer_reads"] = len(summary["confirmed_peer_reads"])
    control["phase"] = "active"
    control_path.write_text(json.dumps(control, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"checkpoint": control, "per_agent": summary["exited"]},
                     ensure_ascii=False, indent=2), flush=True)
    return control


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--deadline-utc", required=True)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--steps", type=int, default=8)
    parser.add_argument("--tokens", type=int, default=110)
    args = parser.parse_args()
    if not 1 <= args.rounds <= 4 or not 2 <= args.steps <= 12 or not 32 <= args.tokens <= 220:
        parser.error("bounded rounds/steps/tokens required")
    execute(args.workspace, args.model_dir, args.deadline_utc,
            args.rounds, args.steps, args.tokens)


if __name__ == "__main__":
    main()
