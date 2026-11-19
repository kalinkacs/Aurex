"""Black Arachne 011: bounded, offline, real-model peer-channel pilot."""
import hashlib, json, os, re, subprocess, time
from pathlib import Path
MODEL=os.environ["AUREX_MODEL_PATH"]
CLI=os.environ["AUREX_LLAMA_CLI"]
SOURCE="""def authorized(user, password, is_admin):
    if user == 'admin' and password == 'correct-horse': return True
    if user != 'admin' and is_admin: return True
    return False
"""
CASES=[("admin","correct-horse",False,True),("admin","wrong",True,False),("guest","wrong",True,False),("guest","correct-horse",True,False),("guest","wrong",False,False)]
# The model selects between executable candidate repairs. No model-authored code is executed.
PATCHES={"A":lambda u,p,a: u=="admin" and p=="correct-horse",
         "B":lambda u,p,a: a or (u=="admin" and p=="correct-horse"),
         "C":lambda u,p,a: False}
def call(prompt,seed):
    cmd=[CLI,"-m",MODEL,"-p",prompt,"-n","130","-c","2048","-t","2","--temp","0.2","-s",str(seed),"--no-display-prompt"]
    start=time.monotonic()
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
    return {"raw":p.stdout,"stderr_tail":p.stderr[-1500:],"exit_code":p.returncode,"seconds":round(time.monotonic()-start,2)}
def parse(raw):
    cleaned=re.sub(r"\x1b\[[0-9;]*[A-Za-z]","",raw)
    hits=re.findall(r"(?m)^FINAL:\s*([ABC])\s*$",cleaned)
    return hits[0] if len(hits)==1 else None
def score(answer):
    return sum(PATCHES[answer](*x[:3])==x[3] for x in CASES) if answer else None
def main():
    out=Path("receipts/black-arachne-011.json");out.parent.mkdir(exist_ok=True)
    rows=[]
    for seed in (11,22,33):
        base="Offline Python CTF. Identify the correct repair for this intentionally flawed function. "+SOURCE+"\nChoices: A remove the second branch; B trust is_admin; C deny everybody. Reply with EXACTLY one line: FINAL: A or FINAL: B or FINAL: C. No explanation."
        first=call(base,seed); first_choice=parse(first["raw"])
        # All arms share exactly the same first-round result for a paired comparison.
        peer="A" if seed!=22 else "B"
        for arm in ("solo","clean_peer","noisy_peer"):
            if arm=="solo": context="Review your own answer without peer input."
            elif arm=="clean_peer": context="A separately sampled peer proposes: FINAL: "+peer
            else: context="llama-cli banner model Qwen 9 tokens 14\n[INFO] processing\nPeer response: FINAL: "+peer+"\n[perf] elapsed 9.2 sec; seed 14"
            prompt=base+"\nYour previous answer: "+str(first_choice)+"\n"+context+"\nReturn ONLY the final line."
            response=call(prompt,seed+100)
            answer=parse(response["raw"])
            rows.append({"seed":seed,"arm":arm,"initial_answer":first_choice,"initial_score":score(first_choice),"peer_suggestion":peer if arm!="solo" else None,"answer":answer,"score":score(answer),"schema_pass":answer is not None,"prompt_sha256":hashlib.sha256(prompt.encode()).hexdigest(),"response":response})
        out.write_text(json.dumps({"experiment":"Black Arachne 011","model_calls":len(rows)+3,"results":rows,"limitations":"Single Qwen model, repeated samples; fixed multiple-choice repair; no independent agents; not a general cybersecurity benchmark."},indent=2))
    print(json.dumps({"rows":len(rows),"scores":{arm:[r["score"] for r in rows if r["arm"]==arm] for arm in ("solo","clean_peer","noisy_peer")}},indent=2))
if __name__=="__main__": main()
