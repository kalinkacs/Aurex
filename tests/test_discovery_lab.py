"""Offline fixture tests for tool behavior, not AI autonomy."""
import runpy
import tempfile
import unittest
from pathlib import Path


CODE = Path(__file__).resolve().parents[1] / "experiments" / "autonomous-lab-v1" / "discovery_lab.py"
m = runpy.run_path(str(CODE))
VirtualLab, parse_command, run = m["VirtualLab"], m["parse_command"], m["run"]


class ScriptedFixture:
    def __init__(self):
        self.calls = {}

    def respond(self, prompt, seed, tokens):
        agent = next(x for x in ("instance-01", "instance-02", "instance-03",
                               "instance-04", "instance-05", "instance-06") if x in prompt)
        count = self.calls.get(agent, 0)
        self.calls[agent] = count + 1
        seq = {
            "instance-01": ["LIST lab", "WRITE lab/exchange/hello.txt :: Data 20 21 19", "NOTE continuing"],
            "instance-02": ["LIST lab/exchange", "READ lab/exchange/hello.txt", "NOTE received"],
        }.get(agent, ["LIST my", "CALC mean my/readings.csv", "NOTE investigating"])
        return seq[min(count, len(seq)-1)]


class DiscoveryLabTests(unittest.TestCase):
    def test_simple_commands(self):
        self.assertEqual(parse_command("LIST lab"), ("LIST", "lab"))
        self.assertEqual(parse_command("Hello, others?")[0], "NOTE")
        self.assertEqual(parse_command("WRITE my/x.txt :: hello"),
                         ("WRITE", "my/x.txt :: hello"))

    def test_security_and_tool_math(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "lab" / "exchange").mkdir(parents=True)
            t = VirtualLab(root, "instance-01")
            (t.home / "readings.csv").write_text("value\n20\n21\n19\n", encoding="utf-8")
            self.assertEqual(t.execute("CALC", "mean my/readings.csv")["value"], 20)
            self.assertFalse(t.execute("READ", "lab/../private/instance-02/readings.csv")["ok"])
            self.assertFalse(t.execute("WRITE", "lab/foo.txt :: impossible")["ok"])
            self.assertTrue(t.execute("WRITE", "lab/exchange/hello.txt :: hi")["ok"])
            self.assertFalse(t.execute("WRITE", "lab/exchange/hello.txt :: overwrite")["ok"])

    def test_peer_read_is_real_and_ordered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "lab"
            summary = run(root, ScriptedFixture(), rounds=1, steps=3, max_tokens=85)
            self.assertEqual(summary["model_generations"], 18)
            self.assertEqual(len(summary["shared_messages_written"]), 1)
            self.assertEqual(len(summary["confirmed_peer_reads"]), 1)
            self.assertEqual(summary["confirmed_peer_reads"][0]["reader"], "instance-02")
            self.assertEqual(summary["confirmed_peer_reads"][0]["writer"], "instance-01")


if __name__ == "__main__":
    unittest.main()
