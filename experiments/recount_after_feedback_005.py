"""Ask the model to reconsider incorrect number comparisons; preserve raw outputs."""
import json,os,subprocess
from pathlib import Path
CLI=os.environ.get("AUREX_LLAMA_CLI","/tmp/llama.cpp/build/bin/llama-cli")
MODEL=os.environ.get("AUREX_MODEL_PATH","/tmp/aurex-model/qwen2.5-0.5b-instruct-q4_k_m.gguf")
CASES=[("3","8","8"),("12","7","12"),("9","14","14")]
def ask(prompt):
 p=subprocess.run([CLI,"-m",MODEL,"-p",prompt,"-n","140","-c","2048","-t","2","--temp","0","--no-display-prompt"],capture_output=True,text=True,timeout=150)
 return {"raw":p.stdout.strip(),"returncode":p.returncode,"stderr_tail":p.stderr[-400:]}
def main():
 out=Path("receipts/recount-after-feedback-005.json");out.parent.mkdir(parents=True,exist_ok=True)
 rows=[]
 for a,b,correct in CASES:
  question="Which number is larger, "+a+" or "+b+"?"
  initial=ask("Answer this question. Explain your comparison briefly, then put your final answer on a separate line starting FINAL: "+chr(10)+question)
  retry=ask("You previously struggled with this kind of question. Here is a correction: compare the numeric values, not the order of words. Your answer must be one of the two numbers in the question. Recalculate carefully. Explain briefly and put the answer on a separate line starting FINAL: "+chr(10)+question)
  rows.append({"question":question,"expected":correct,"initial":initial,"recount_after_correction":retry})
  out.write_text(json.dumps({"status":"partial","rows":rows},ensure_ascii=False,indent=2)+chr(10))
 out.write_text(json.dumps({"status":"completed","rows":rows,"limitations":"New model calls, not the original six agents; no weight updates; raw outputs intentionally preserved to avoid unreliable parsing."},ensure_ascii=False,indent=2)+chr(10))
 print(json.dumps({"status":"completed","cases":len(rows),"returncodes":[[r["initial"]["returncode"],r["recount_after_correction"]["returncode"]] for r in rows]}))
if __name__=="__main__":main()
