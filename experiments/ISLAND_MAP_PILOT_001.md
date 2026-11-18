# Island Map Pilot 001 — preregistered protocol

**Status:** fixture and scorer prepared, not an executed multi-agent experiment.

## Question
Does discussion improve route quality beyond receiving the same facts as plain text?

## Fixture
Undirected weighted roads: D-A 2, A-C 2, C-T 3, D-B 3, B-C 3, B-E 2, E-T 2, A-E 5. E-T is closed. Travel D to T at minimum cost. Reference route D-A-C-T, cost 7. Keep the reference hidden from participants and any blind scorer until their submissions are locked.

## Conditions
- R1: independent solver with incomplete evidence; freeze response.
- R2-self: same evidence, no external facts, one more attempt.
- R2-relay: missing facts supplied verbatim without interpretation.
- R2-discussion: equivalent facts plus another solver's explanation.
- Full-info solo: all facts, no communication, same budget.

Use isolated contexts or fresh independent runs for each condition. Never sequentially reuse a context across arms. Keep initial answers, prompts, model IDs, settings, token counts, raw responses, and timestamps. Compare R2-discussion to R2-relay, not merely to R1. Record regressions and unsupported claims. One fixture is an infrastructure pilot, not statistical evidence of collaboration.

## Current constraints
No model invocation has been verified for this pilot. No live inference is authorized by this workflow. GitHub Models connectivity must be validated separately before adding a bounded model runner. No secrets or outside messages in the workflow.
