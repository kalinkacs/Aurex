"""Fixture tests: prove chat delivery plumbing, not AI collaboration."""
import runpy
import tempfile
import unittest
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "experiments" / "autonomous-lab-v1" / "team_chat.py"
mod = runpy.run_path(str(p))
calculator = mod["calculator"]
run = mod["run"]


class ScriptedTransportFixture:
    def __init__(self):
        self.calls = []

    def respond(self, system, history, seed, max_tokens):
        self.calls.append({"system": system, "history": list(history), "seed": seed})
        return "Hello peers, I have a question." if len(self.calls) == 1 else "Received."


class TeamChatTests(unittest.TestCase):
    def test_calculator_is_real_math(self):
        self.assertEqual(calculator("CALC: mean 20,21,19")["value"], 20)
        self.assertEqual(calculator("CALC: median 20,86,21")["value"], 21)
        self.assertEqual(calculator("ordinary text"), None)

    def test_all_six_receive_earlier_chat(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ScriptedTransportFixture()
            summary = run(Path(tmp) / "test", fixture, rounds=2, max_tokens=100)
            self.assertEqual(summary["model_generated_messages"], 12)
            self.assertTrue(any("instance-01" in call["system"] for call in fixture.calls))
            self.assertEqual(fixture.calls[0]["history"], [])
            self.assertEqual(fixture.calls[1]["history"][0]["speaker"], "instance-01")
            self.assertEqual(fixture.calls[6]["history"][0]["text"], "Hello peers, I have a question.")
            self.assertEqual(summary["reference_for_human_evaluator_only"]["count"], 18)
            self.assertEqual(summary["reference_for_human_evaluator_only"]["maximum"], 86)
            self.assertTrue((Path(tmp) / "test" / "room.jsonl").is_file())


if __name__ == "__main__":
    unittest.main()
