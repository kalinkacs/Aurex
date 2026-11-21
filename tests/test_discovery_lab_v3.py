"""Tests for discovery v3: peer exchange and loop suppression are real events."""
import runpy
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = runpy.run_path(str(ROOT / "experiments" / "autonomous-lab-v1" / "discovery_lab_v3.py"))
run = MODULE["run"]
VirtualLab = MODULE["VirtualLab"]

class PlannedFixture:
    def __init__(self):
        self.calls = {}
    def respond(self, prompt, seed, tokens):
        name = next(f"instance-{i:02d}" for i in range(1, 7) if f"instance-{i:02d}" in prompt)
        n = self.calls.get(name, 0)
        self.calls[name] = n + 1
        if name == "instance-01":
            return ["LIST lab", "WRITE lab/exchange/first.txt :: my readings are 20 21 19",
                    "NOTE continuing investigation"][min(n, 2)]
        if name == "instance-02":
            return ["LIST lab/exchange", "READ lab/exchange/first.txt",
                    "NOTE peer message received"][min(n, 2)]
        return "READ my/readings.csv"

class RepeatFixture:
    def respond(self, prompt, seed, tokens):
        return "READ my/readings.csv"

class DiscoveryV3Tests(unittest.TestCase):
    def test_real_peer_contact_and_fresh_batches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "trial"
            summary = run(root, PlannedFixture(), rounds=2, steps=3, max_tokens=90)
            self.assertEqual(len(summary["shared_messages_written"]), 1)
            self.assertEqual(len(summary["confirmed_peer_reads"]), 1)
            self.assertEqual(summary["confirmed_peer_reads"][0]["reader"], "instance-02")
            self.assertEqual(summary["fresh_measurement_updates"], 6)
            self.assertEqual(summary["reference_only_for_evaluator"]["count"], 36)
            self.assertEqual(len((root / "private" / "instance-01" / "readings.csv").read_text().splitlines()), 7)

    def test_duplicate_read_gets_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "trial"
            summary = run(root, RepeatFixture(), rounds=1, steps=3, max_tokens=90)
            self.assertEqual(summary["model_generations"], 18)
            self.assertEqual(summary["duplicate_actions_suppressed"], 12)
            self.assertEqual(summary["tool_successes"], 6)

if __name__ == "__main__":
    unittest.main()
