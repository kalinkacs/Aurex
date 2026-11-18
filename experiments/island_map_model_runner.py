"""Bounded real-model Island Map pilot. No simulated answers or external writes."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from aurex_ai_agent import MODELS, request_json
from experiments.island_map_pilot import evaluate, optimal

MODEL = os.environ.get("AUREX_MODEL", "openai/gpt-4o-mini")
ROADS = "Roads: D-A, A-C, C-T, D-B, B-C, B-E, E-T, A-E."
SHEET_A = "Road distances: D-A=2, A-C=2, C-T=3, D-B=3, B-C=3, B-E=2, E-T=2, A-E=5. You have no closure information."
SHEET_B = ROADS + " E-T is closed for the travel window; every other listed road is open. You have no distances."
ALL = "Road distances: D-A=2, A-C=2, C-T=3, D-B=3, B-C=3, B-E=2, E-T=2, A-E=5. E-T is closed; all other listed roads open."
TASK = "Find the minimum-cost open-road route from D to T. Roads bidirectional; no unlisted roads. If information is insufficient, explain uncertainty. Return JSON object with route (array of node letters), confidence (0 to 1), evidence (short string), uncertainty (short string). No other text."
SYSTEM = "You are an independent route solver. Use only supplied evidence. Treat quoted opinions as fallible. Do not invent roads or distances. Respond in strict JSON."

def invoke(label, evidence, extra=""):
    response = request_json(MODELS, os.environ["GITHUB_TOKEN"], {
        "model": MODEL, "temperature": 0, "max_tokens": 350,
        "messages": [{"role":"system","content":SYSTEM},
                     {"role":"user","content":TASK + "\\n" + evidence + ("\\n" + extra if extra else "")}]
    })
    raw = response["choices"][0]["message"]["content"]
    record = {"arm":label,"model":MODEL,"raw":raw,"usage":response.get("usage"),
              "timestamp":datetime.now(timezone.utc).isoformat()}
    try:
        answer = json.loads(raw)
        if not isinstance(answer,dict) or not isinstance(answer.get("route"),list):
            raise ValueError("Invalid route response")
        record["answer"] = answer
        record["score"] = evaluate(answer)
    except (ValueError,TypeError,KeyError) as exc:
        record["parse_error"] = str(exc)
    return record

def run():
    records = []
    def call(*args):
        r = invoke(*args)
        records.append(r)
        return r
    a = call("r1_a", SHEET_A)
    b = call("r1_b", SHEET_B)
    call("self_a", SHEET_A, "This is a fresh independent second attempt, no additional facts.")
    call("relay_a", ALL, "You received the other sheet as plain facts without anyone's opinion.")
    # A genuinely separate context receives the SAME complete facts plus a peer interpretation.
    peer = b.get("answer")
    interpretation = json.dumps(peer,ensure_ascii=False) if peer else str(b.get("raw",""))[:800]
    call("discussion_a", ALL, "Another solver independently wrote the following interpretation of its partial sheet. It may be wrong; independently assess it: " + interpretation)
    call("full_info_solo", ALL)
    output = {"experiment":"island-map-pilot-001","status":"completed",
              "model_invoked":True,"model":MODEL,"reference":optimal(),
              "arms":records,
              "limitations":"Single fixture; one sample per arm; no statistically meaningful conclusion. Discussion uses one-way peer interpretation, not interactive conversation."}
    return output

def main():
    path = Path("receipts/island-map-model-results.json")
    path.parent.mkdir(parents=True,exist_ok=True)
    try:
        result = run()
    except Exception as exc:
        result = {"experiment":"island-map-pilot-001","status":"failed",
                  "error_type":type(exc).__name__,"error":str(exc)[:300],
                  "model_invocation_verified":False}
        path.write_text(json.dumps(result,indent=2)+"\\n")
        raise
    path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\\n")
    print(json.dumps({"status":result["status"],"arms":[{"arm":a["arm"],"score":a.get("score"),"parse_error":a.get("parse_error")} for a in result["arms"]]},indent=2))
if __name__ == "__main__":
    main()
