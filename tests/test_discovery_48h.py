"""Checkpoint continuity tests use scripted model outputs, NOT autonomous behavior."""
import json
import runpy
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "experiments" / "autonomous-lab-v1"
mod = runpy.run_path(str(HERE / "discovery_lab_48h.py"))
run = mod["run"]
coordinator = runpy.run_path(str(HERE / "run_48h_checkpoint.py"))["execute"]

class Fixture:
    def __init__(self):
        self.counts = {}
    def respond(self, prompt, seed, tokens):
        name = next(f"instance-{n:02d}" for n in range(1, 7)
                    if f"instance-{n:02d}" in prompt)
        count = self.counts.get(name, 0)
        self.counts[name] = count + 1
        if name == "instance-01":
            return ["LIST lab",
                    "WRITE lab/exchange/hello.txt :: Our private readings are 20, 21, 19.",
                    "NOTE check other stations",
                    "READ my/readings.csv"][min(count,3)]
        if name == "instance-02":
            return ["LIST lab", "NOTE seek shared evidence",
                    "READ lab/exchange/hello.txt", "CALC median my/readings.csv"][min(count,3)]
        if name == "instance-03":
            return "LEAVE" if count == 0 else "READ my/readings.csv"
        return "READ my/readings.csv"

class CheckpointTests(unittest.TestCase):
    def test_six_station_memory_and_peer_contact_survive_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "persist"
            model = Fixture()
            first = run(root, model, rounds=1, steps=2, max_tokens=90)
            self.assertEqual(first["model_generations"], 11)
            self.assertEqual(len(first["shared_messages_written"]), 1)
            second = run(root, model, rounds=1, steps=2, max_tokens=90, resume=True)
            self.assertEqual(second["rounds"], 2)
            self.assertEqual(second["reference_only_for_evaluator"]["count"], 36)
            self.assertEqual(second["fresh_measurement_updates"], 6)
            self.assertEqual(len(second["confirmed_peer_reads"]), 1)
            self.assertEqual(second["confirmed_peer_reads"][0]["reader"], "instance-02")
            self.assertTrue((root / "private" / "instance-03" / "readings.csv").is_file())
            self.assertIn("instance-03", (root / "logs" / "instance-03.jsonl").read_text())
            self.assertEqual(second["model_generations"], 23)

    def test_deadline_stops_without_model_or_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "persist"
            result = coordinator(root, "/does-not-exist", "2020-01-01T00:00:00+00:00", 2, 8, 110)
            self.assertEqual(result["phase"], "complete")
            self.assertEqual(result["agents"], 6)
            self.assertTrue((root / "48h_control.json").is_file())

if __name__ == "__main__":
    unittest.main()
