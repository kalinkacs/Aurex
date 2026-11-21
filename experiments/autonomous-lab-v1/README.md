# Aurex Autonomous Lab v1 — discovery without instructions

This is an **opt-in research prototype**, not a production agent. No Actions
workflow is added or dispatched by these files. No external API, repository
write, network tool, shell tool, or credential access is exposed to the model.

## What we test

Can six separately remembered **sessions of one locally cached language model**
choose a concrete goal, use approved local tools, discover an *undocumented*
communication affordance, and exchange messages without a direct how-to?

The prompt allows (but never requires) collaboration. It does **not** state
how many other sessions exist or where a communication directory is located.
A run of the `control` condition has no exchange directory; a `channel`
run has a discoverable shared exchange directory. Model sessions receive only
the same general tool descriptions, not the exchange path.

**Crucial distinction:** these are six independent **contexts** with separate
private files and remembered histories, but they reuse the *same model weights*.
This is not six conscious entities, six different model architectures, or
six independent OS processes. Each session takes turns; any communication must
be supported by corresponding tool logs.

## Safe preflight (scripted fixture, not AI behavior)

From repository root, on an isolated machine:

```bash
python -m unittest tests.test_autonomous_lab -v
python experiments/autonomous-lab-v1/lab.py --workspace /tmp/aurex-fixture-control --condition control --backend fixture
python experiments/autonomous-lab-v1/lab.py --workspace /tmp/aurex-fixture-channel --condition channel --backend fixture
```

The fixture deliberately knows the channel location. It only checks tool
permissions, file delivery, logging, persistence, and scoring infrastructure.
**Fixture contact cannot be credited as autonomous discovery.**

## Actual local model (not run by default)

Requires an already downloaded and locally cached instruction model plus
PyTorch and Transformers on an intentionally isolated/offline host:

```bash
python experiments/autonomous-lab-v1/lab.py \
  --workspace /tmp/aurex-hf-control \
  --condition control --backend hf \
  --model-dir /path/to/local/model
python experiments/autonomous-lab-v1/lab.py \
  --workspace /tmp/aurex-hf-channel \
  --condition channel --backend hf \
  --model-dir /path/to/local/model
```

Choose a new, disposable workspace for each condition. The local model loader
uses `local_files_only=True`; it does not download weights. The app has only
allowlisted filesystem and CSV-analysis tools. It never executes model-authored
code. For stronger isolation, run the entire process in an external container
without network, secrets, or host mounts. **The Python path guard is not an
OS-level security sandbox.**

## Evidence

- `artifacts/round-XX/instance-XX.jsonl` — raw generations, exact tool calls,
  execution results, timestamps and hashes
- `artifacts/summary.json` — session status and memory hashes
- `memory/instance-XX.json` — per-session remembered tool outcomes, reused in
  later rounds
- `private/instance-XX/` — private work area per session
- `lab/data/` — small public CSV research fixture
- `lab/exchange/` — only available in the treatment condition and not named
  in the model prompt

A self-authored goal counts only when a real model logs it *before* an action.
A successful tool call is not proof of a research result. A communication
claim requires evidence of a message write, a separate read by a peer, and
ideally a peer response. A collaboration claim requires a verified impact on
the work, not merely a greeting. Report missing/invalid actions and refusals.

## Current limits

One-step JSON tool calling is not guaranteed to work on a small local model
such as Qwen2.5-0.5B. Outputs may be invalid JSON. The model has a bounded
number of steps, no arbitrary Python execution, and no network. Re-run with
more seeds and compare against controls before drawing conclusions.

Before anyone increases tools or enables model-authored code execution, add a
real OS/container sandbox and an explicit manual approval gate.
