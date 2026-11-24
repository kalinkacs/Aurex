"""Pilot 004: bounded trial-feedback-retry, without weight updates."""
import json, os, re, subprocess
from pathlib import Path
CLI=os.environ.get("AUREX_LLAMA_CLI","/tmp/llama.cpp/build/bin/llama-cli")
MODEL=os.environ.get("AUREX_MODEL_PATH","/tmp/aurex-model/qwen2.5-0.5b-instruct-q4_k_m.gguf")
CASES=[
 ("round1","Choose the larger number: 3 or 8.","8"),
 ("round2","Choose the larger number: 12 or 7.","12"),
 ("round3","Choose the larger number: 9 or 14.","14"),
]
def ask(prompt):
 p=subprocess.run([CLI,"-m",MODEL,"-p",prompt,"-n","32","-c","1536","-t","2","--temp","0","--no-display-prompt"],capture_output=True,text=True,timeout=120)
 raw=p.stdout.strip()
 # Record entire output and parse only the last isolated numeric token.
 nums=re.findall(r"(?<![0-9])(?:3|7|8|9|12|14)(?![0-9])",raw)
 return {"raw":raw,"answer":nums[-1] if nums else None,"returncode":p.returncode}
def main():
 out=Path("receipts/feedback-retry-004.json");out.parent.mkdir(parents=True,exist_ok=True)
 history=[];rows=[]
 for name,question,correct in CASES:
  instruction="Answer with only the larger number. No explanation."
  # Compare a clean baseline and a fresh call with feedback from earlier rounds.
  solo=ask(instruction+chr(10)+question)
  contextual=ask(instruction+chr(10)+"Previous checked attempts (learn from corrections, do not blindly copy):"+chr(10)+chr(10).join(history)+chr(10)+question)
  row={"case":name,"question":question,"correct_answer":correct,"solo":solo,"with_feedback":contextual,
       "solo_correct":solo["answer"]==correct,"feedback_correct":contextual["answer"]==correct}
  rows.append(row)
  history.append("Question: "+question+" Your previous answer: "+str(contextual["answer"])+". Checked correct answer: "+correct+".")
  out.write_text(json.dumps({"status":"partial","arms":rows},indent=2)+chr(10))
 out.write_text(json.dumps({"experiment":"feedback-retry-004","status":"completed","arms":rows,
 "limitations":"Very easy number comparison; correction history in prompt only, not training; three examples, no causal learning claim."},indent=2)+chr(10))
 print(json.dumps({"status":"completed","rows":[{"case":r["case"],"solo":r["solo"]["answer"],"with_feedback":r["with_feedback"]["answer"],"correct":r["correct_answer"]} for r in rows]},indent=2))
if __name__=="__main__":main()
