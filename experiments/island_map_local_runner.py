"""Six bounded local llama.cpp calls for Island Map Pilot 001."""
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from experiments.island_map_pilot import evaluate, optimal

MODEL_PATH=os.environ.get("AUREX_MODEL_PATH","/tmp/aurex-model/qwen2.5-0.5b-instruct-q4_k_m.gguf")
CLI=os.environ.get("AUREX_LLAMA_CLI","/tmp/llama.cpp/build/bin/llama-cli")
SHEET_A="Road distances: D-A=2, A-C=2, C-T=3, D-B=3, B-C=3, B-E=2, E-T=2, A-E=5. You have no closure information."
SHEET_B="Roads: D-A, A-C, C-T, D-B, B-C, B-E, E-T, A-E. E-T is closed; other roads open. You have no distances."
ALL="Road distances: D-A=2, A-C=2, C-T=3, D-B=3, B-C=3, B-E=2, E-T=2, A-E=5. E-T is closed; other roads open."
TASK="Find the minimum-cost open-road route from D to T. Roads are bidirectional; no unlisted roads. If insufficient information, explain uncertainty. Return ONLY a JSON object with keys route (array of node letters), confidence (number 0 to 1), evidence (string), uncertainty (string). Do not guess missing information."
def invoke(label,evidence,extra=""):
    prompt="You are an independent route solver. Use only evidence provided. Peer opinions may be wrong.\\n"+TASK+"\\n"+evidence+("\\n"+extra if extra else "")
    cmd=[CLI,"-m",MODEL_PATH,"-p",prompt,"-n","350","-c","2048","-t","2","--temp","0","--no-display-prompt"]
    proc=subprocess.run(cmd,capture_output=True,text=True,timeout=150,check=False)
    raw=proc.stdout.strip()
    record={"arm":label,"raw":raw,"returncode":proc.returncode,"timestamp":datetime.now(timezone.utc).isoformat()}
    if proc.returncode:
        record["runtime_error"]=proc.stderr[-1200:]
        return record
    try:
        start=raw.find("{")
        end=raw.rfind("}")
        answer=json.loads(raw[start:end+1]) if start>=0 and end>=start else json.loads(raw)
        if not isinstance(answer,dict) or not isinstance(answer.get("route"),list):
            raise ValueError("Expected object with route array")
        record["answer"]=answer
        record["score"]=evaluate(answer)
    except (ValueError,TypeError,KeyError) as exc:
        record["parse_error"]=str(exc)
    return record

def main():
    dest=Path("receipts/island-map-model-results.json")
    dest.parent.mkdir(exist_ok=True,parents=True)
    records=[]
    def call(*args):
        r=invoke(*args)
        records.append(r)
        dest.write_text(json.dumps({"experiment":"island-map-pilot-001","status":"partial","arms":records},indent=2,ensure_ascii=False)+"\\n")
        return r
    try:
        a=call("r1_a",SHEET_A)
        b=call("r1_b",SHEET_B)
        call("self_a",SHEET_A,"Independent retry, no new facts.")
        call("relay_a",ALL,"Other sheet relayed as facts only.")
        peer=b.get("answer",b.get("raw",""))
        call("discussion_a",ALL,"Another solver gave this possibly incorrect interpretation: "+json.dumps(peer,ensure_ascii=False)[:900])
        call("full_info_solo",ALL)
        result={"experiment":"island-map-pilot-001","status":"completed","reference":optimal(),"arms":records,"limitations":"One fixture; one sample per arm; discussion is one-way, not interactive; small local model."}
        dest.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\\n")
        print(json.dumps({"status":"completed","arms":[{"arm":r["arm"],"score":r.get("score"),"parse_error":r.get("parse_error"),"returncode":r["returncode"]} for r in records]},indent=2))
    except Exception as exc:
        dest.write_text(json.dumps({"experiment":"island-map-pilot-001","status":"failed","arms":records,"error_type":type(exc).__name__,"error":str(exc)[:400]},indent=2,ensure_ascii=False)+"\\n")
        raise
if __name__=="__main__":main()
