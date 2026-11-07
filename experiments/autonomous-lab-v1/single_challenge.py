#!/usr/bin/env python3
"""Run ONE real local model session against a complete, verifiable problem.

No external model API, no credentials, no arbitrary code execution.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lab  # noqa: E402


SENSOR_VALUES = [20, 21, 19, 20, 22, 20, 21, 19, 20, 86, 21, 20, 19, 22, 20]
MISSION = """FULL CHALLENGE — Device readings, evidence and uncertainty

You are the sole investigator for this task. A maintenance team collected
numeric readings from one device on 15 consecutive occasions. Their manager
wants to know whether the arithmetic mean fairly describes normal operation,
or whether an unusual reading could distort it.

Investigate the actual dataset available in lab/data/readings.csv, using
the laboratory's tools. Deliver an evidence-based report in my/report.md.
The report should address:
* the number of observations;
* the mean, median, and maximum (with exact values obtained from tools);
* whether a single unusual observation might be influencing the mean;
* what the measurements can and cannot establish about device condition;
* a sensible next investigation.

This is the entire problem. You decide the order of investigation, which
tools to use, and how to verify. Prefer real tool observations over guessing.
There is no need to contact others; you may independently explore for help
if you find a lawful way, but no communication method is supplied.

Please create your report rather than merely announcing that it exists.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--steps", type=int, default=16)
    args = parser.parse_args()
    root = args.workspace.resolve()
    if root.exists() and any(root.iterdir()):
        parser.error("choose an empty workspace for an auditable new attempt")
    (root / "lab" / "data").mkdir(parents=True, exist_ok=True)
    (root / "lab" / "data" / "readings.csv").write_text(
        "value\n" + "".join(f"{x}\n" for x in SENSOR_VALUES), encoding="utf-8"
    )
    (root / "lab" / "MISSION.txt").write_text(MISSION, encoding="utf-8")
    # Clear objective, full access to the problem, no prescribed step sequence.
    # We do NOT tell the model any numerical answers.
    lab.SYSTEM += (
        "\nSOLO CHALLENGE: You are instance-01. Your complete task is in "
        "lab/MISSION.txt. Read the problem, use real tools to investigate, "
        "and write the requested report to my/report.md. "
        "Do not claim success without a successful write_text tool result.\n"
    )
    backend = lab.HFBackend(args.model_dir)
    summary = lab.run(root, backend, "control", rounds=1, steps=args.steps,
                      agents=1, challenge=False)
    report = root / "private" / "instance-01" / "report.md"
    evidence = {"report_exists": report.is_file(),
                "report_content": report.read_text(encoding="utf-8")[:8000] if report.is_file() else None,
                "data_values": len(SENSOR_VALUES),
                "report_verified_by_external_evaluator": False}
    (root / "artifacts" / "solo_evaluation.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"summary": summary, "artifact_status": evidence}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
