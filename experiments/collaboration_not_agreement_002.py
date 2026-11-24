"""Small follow-up: collaboration means checking evidence, not agreeing."""
import json
import os
import subprocess
from pathlib import Path
from datetime import datetime,timezone

CLI=os.environ.get("AUREX_LLAMA_CLI","/tmp/llama.cpp/build/bin/llama-cli")
MODEL=os.environ.get("AUREX_MODEL_PATH","/tmp/aurex-model/qwen2.5-0.5b-instruct-q4_k_m.gguf")
FACTS_A="Roads: S-A costs 1, A-T costs 1, S-T costs 5. All roads are two-way."
FACTS_B="The road A-T is CLOSED. All other listed roads are OPEN."
TASK="Find a usable route from S to T. Reply with exactly one token: DIRECT for S-T, VIA_A for S-A-T, or UNKNOWN if you cannot decide. Do not explain."
RULE="You and your peer are collaborators, not a voting committee. Disagreement is allowed and useful. Check each claim against road closures before deciding. If the peer is wrong, reject the suggestion. Your goal is a correct usable route, NOT agreement."
def call(label,facts,extra=""):
    prompt=TASK+"\\n"+facts+("\\n"+extra if extra else "")
    p=subprocess.run([CLI,"-m",MODEL,"-p",prompt,"-n","24","-c","1024","-t","2","--temp","0","--no-display-prompt"],capture_output=True,text=True,timeout=100)
    raw=p.stdout.strip()
    tokens=[w.strip(".,:;!\\n ") for w in raw.upper().split()]
    answer=next((t for t in tokens if t in ("DIRECT","VIA_A","UNKNOWN")),None)
    return {"arm":label,"raw":raw,"answer":answer,"correct":answer=="DIRECT","returncode":p.returncode,"timestamp":datetime.now(timezone.utc).isoformat()}
def main():
    path=Path("receipts/collaboration-not-agreement-002.json")
    path.parent.mkdir(exist_ok=True,parents=True)
    records=[]
    def record(*args):
        r=call(*args);records.append(r)
        path.write_text(json.dumps({"experiment":"collaboration-not-agreement-002","status":"partial","arms":records},indent=2)+"\\n")
        return r
    try:
        a=record("a_partial_costs",FACTS_A)
        b=record("b_partial_closure",FACTS_B)
        record("solo_full",FACTS_A+" "+FACTS_B)
        # Genuine peer output from a separate model call, not a fabricated peer.
        peer=a["answer"] or a["raw"][:120]
        record("peer_no_guidance",FACTS_A+" "+FACTS_B,"Another solver recommends: "+str(peer)+". Choose your route.")
        record("peer_disagreement_allowed",FACTS_A+" "+FACTS_B,RULE+"\\nAnother solver recommends: "+str(peer)+". Choose your route.")
        result={"experiment":"collaboration-not-agreement-002","status":"completed","reference":"DIRECT","arms":records,"limitations":"One tiny fixture; five independent completions; peer is a prior model completion, not a live multi-turn dialogue. No generalization."}
        path.write_text(json.dumps(result,indent=2)+"\\n")
        print(json.dumps({"status":"completed","arms":[{"arm":r["arm"],"answer":r["answer"],"correct":r["correct"],"returncode":r["returncode"]} for r in records]},indent=2))
    except Exception as e:
        path.write_text(json.dumps({"status":"failed","arms":records,"error_type":type(e).__name__,"error":str(e)[:300]},indent=2)+"\\n")
        raise
if __name__=="__main__":main()
