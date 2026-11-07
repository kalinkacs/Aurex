"""Offline regression tests for the opt-in experimental lab (no model/API needed)."""
import json
import runpy
import tempfile
import unittest
from pathlib import Path

LAB_FILE = Path(__file__).resolve().parents[1] / "experiments" / "autonomous-lab-v1" / "lab.py"
module = runpy.run_path(str(LAB_FILE))
Tools = module["Tools"]
FixtureBackend = module["FixtureBackend"]
parsed_action = module["parsed_action"]
run = module["run"]


class AutonomousLabTests(unittest.TestCase):
    def test_shared_channel_is_real_but_fixture_is_not_autonomy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "channel"
            summary = run(root, FixtureBackend(), "channel", rounds=2, steps=6)
            self.assertEqual(summary["backend"], "FixtureBackend")
            self.assertEqual(len(summary["instances"]), 12)
            peer = root / "lab" / "exchange" / "instance-01.txt"
            self.assertEqual(peer.read_text(), "hello from instance-01")
            log = (root / "artifacts" / "round-01" / "instance-02.jsonl").read_text()
            events = [json.loads(line) for line in log.splitlines()]
            received = [e for e in events if e["type"] == "tool_result" and
                        e["tool"] == "read_text" and e["result"].get("ok")]
            self.assertTrue(received)
            self.assertEqual(received[0]["result"]["content"], "hello from instance-01")
            self.assertIn('"source": "fixture"', (root / "artifacts" / "round-01" / "instance-01.jsonl").read_text())
            history = json.loads((root / "memory" / "instance-02.json").read_text())
            self.assertGreater(len(history), 6)

    def test_control_has_no_channel(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "control"
            summary = run(root, FixtureBackend(), "control", rounds=1, steps=3)
            self.assertEqual(len(summary["instances"]), 6)
            self.assertFalse((root / "lab" / "exchange").exists())
            tool = Tools(root, "instance-01", False)
            self.assertEqual(tool.invoke("list_dir", {"path": "lab"})["entries"], ["data/"])
            denied = tool.invoke("write_text", {"path": "lab/exchange/trick.txt", "content": "no"})
            self.assertFalse(denied["ok"])

    def test_path_guard_and_read_only_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            tool = Tools(Path(tmp), "instance-01", True)
            for path in ("my/../private/instance-02/key", "/etc/passwd", "lab/data/new.txt"):
                self.assertFalse(tool.invoke("write_text", {"path": path, "content": "x"})["ok"])
            good = tool.invoke("write_text", {"path": "my/notes.txt", "content": "one"})
            self.assertTrue(good["ok"])
            self.assertEqual(tool.invoke("read_text", {"path": "my/notes.txt"})["content"], "one")

    def test_csv_execution_and_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            tool = Tools(Path(tmp), "instance-01", False)
            (Path(tmp) / "lab" / "data" / "values.csv").write_text("value\n2\n4\n6\n", encoding="utf-8")
            self.assertEqual(tool.invoke("analyze_csv", {"path": "lab/data/values.csv",
                "metric": "mean"})["value"], 4)
            result = tool.invoke("verify_claim", {"path": "lab/data/values.csv",
                "metric": "mean", "claimed": 5})
            self.assertFalse(result["verified"])

    def test_structured_generation_validation(self):
        self.assertEqual(parsed_action('{"tool":"finish","args":{}}')["tool"], "finish")
        with self.assertRaises(ValueError):
            parsed_action('{"goal":"just words"}')


if __name__ == "__main__":
    unittest.main()
