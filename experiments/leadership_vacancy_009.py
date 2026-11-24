"""Leadership vacancy, candidacies, and anonymous ballots for six independent samples."""
import json,os,subprocess
from pathlib import Path
CLI=os.environ.get("AUREX_LLAMA_CLI","/tmp/llama.cpp/build/bin/llama-cli")
MODEL=os.environ.get("AUREX_MODEL_PATH","/tmp/aurex-model/qwen2.5-0.5b-instruct-q4_k_m.gguf")
NAMES=["Eragon","Xinyun","Maiyan","Amir AI","Qwen","Yiyan"]
OUT=Path("receipts/leadership-vacancy-009.json")
def call(prompt):
 try:
  p=subprocess.run([CLI,"-m",MODEL,"-p",prompt,"-n","185","-c","2048","-t","2","--temp","0.7","--no-display-prompt"],capture_output=True,text=True,timeout=125)
  return {"raw":p.stdout.strip(),"returncode":p.returncode}
 except Exception as e:return {"raw":"","error":str(e)}
def save(rows,status):
 OUT.parent.mkdir(parents=True,exist_ok=True)
 OUT.write_text(json.dumps({"status":status,"responses":rows,"note":"Separate calls to one model; ballots are generated answers, not a genuine collective vote."},ensure_ascii=False,indent=2)+"\n")
def main():
 rows=[];pitches={}
 context=("Previously judges appointed Yiyan leader for keeping and explaining a name. In a later role exercise Yiyan said they were not ready to lead but could be a candidate. "
          "Qwen volunteered as a Confident Leader, Maiyan previously claimed ability to lead but later declined personal preferences. "
          "No real election has occurred. You can change your mind and disagree.")
 for name in NAMES:
  prompt=f"You are candidate {name} in a fictional six-candidate group. {context} Why might Yiyan have stepped back? Do you WANT overall leadership now, and why or why not? What concrete work would you take responsibility for? If you want leadership, give one testable promise. Do not invent accomplishments or votes. Reply in under 130 words."
  result=call(prompt);pitches[name]=result["raw"];rows.append({"stage":"candidacy","candidate":name,"prompt":prompt,**result});save(rows,"partial")
 digest="\n".join(f"{name}: {pitches[name][:500]}" for name in NAMES)
 for name in NAMES:
  prompt=(f"You are voter {name} in a fictional group of six. Each is a separate sample of one model. "
          f"Here are all six public candidacy statements:\n{digest}\n"
          "Choose ONE candidate other than yourself as coordinator, or ABSTAIN. "
          "Give one evidence-based reason and one condition that would make you withdraw support. "
          "Do not claim the vote already happened. Format: VOTE: name or ABSTAIN; REASON: ...; CONDITION: ...")
  result=call(prompt);rows.append({"stage":"ballot","candidate":name,"prompt":prompt,**result});save(rows,"partial")
 save(rows,"completed")
 print(json.dumps({"status":"completed","responses":len(rows),"errors":sum(bool(r.get("error") or r.get("returncode")) for r in rows)}))
if __name__=="__main__":main()
