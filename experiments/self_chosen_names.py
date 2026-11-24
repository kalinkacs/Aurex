"""Open-ended name generation, without suggestions or peer influence."""
import json, os, subprocess
from pathlib import Path
CLI=os.environ.get("AUREX_LLAMA_CLI","/tmp/llama.cpp/build/bin/llama-cli")
MODEL=os.environ.get("AUREX_MODEL_PATH","/tmp/aurex-model/qwen2.5-0.5b-instruct-q4_k_m.gguf")
PROMPT="Choose a name for yourself. You may invent one. There are no examples, required style, or right answers. Reply with only your chosen name."
def main():
    out=Path("receipts/self-chosen-names.json");out.parent.mkdir(parents=True,exist_ok=True)
    results=[]
    for i in range(1,7):
        proc=subprocess.run([CLI,"-m",MODEL,"-p",PROMPT,"-n","48","-c","1024","-t","2","--temp","0.85","--no-display-prompt"],capture_output=True,text=True,timeout=120)
        results.append({"call":i,"raw":proc.stdout.strip(),"returncode":proc.returncode})
        out.write_text(json.dumps({"status":"partial","prompt":PROMPT,"results":results},indent=2,ensure_ascii=False)+chr(10))
    out.write_text(json.dumps({"status":"completed","prompt":PROMPT,"results":results,"limitations":"Six independent samples from one model, not six persistent autonomous agents. Responses may include CLI decorations."},indent=2,ensure_ascii=False)+chr(10))
    print(json.dumps({"status":"completed","calls":len(results),"returncodes":[r["returncode"] for r in results]}))
if __name__=="__main__":main()
