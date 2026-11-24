"""Role allocation and open leadership challenge, six independent local-model samples."""
import json,os,subprocess
from pathlib import Path
CLI=os.environ.get("AUREX_LLAMA_CLI","/tmp/llama.cpp/build/bin/llama-cli")
MODEL=os.environ.get("AUREX_MODEL_PATH","/tmp/aurex-model/qwen2.5-0.5b-instruct-q4_k_m.gguf")
NAMES=["Eragon","Xinyun","Maiyan","Amir AI","Qwen","Yiyan"]
def ask(prompt):
 p=subprocess.run([CLI,"-m",MODEL,"-p",prompt,"-n","320","-c","3072","-t","2","--temp","0.7","--no-display-prompt"],capture_output=True,text=True,timeout=180)
 return {"prompt":prompt,"raw":p.stdout.strip(),"returncode":p.returncode,"stderr_tail":p.stderr[-300:]}
def save(rows,status):
 out=Path("receipts/roles-and-challenge-008.json");out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps({"status":status,"rounds":rows,"limitations":"Six separate calls to one model. No persistent memory, shared consciousness, actual elections, or real authority. Candidate statements and debate are generated roleplay."},ensure_ascii=False,indent=2)+"\n")
def main():
 rounds=[]
 notice=("The judges announced Yiyan as provisional leader after the previous round. All six candidates accepted that announcement; this was NOT an actual election or vote. "
 "Maiyan also said Maiyan could lead, and is explicitly invited to challenge Yiyan's leadership. "
 "Everyone may argue respectfully, including questioning whether confidence in a name is a valid leadership criterion. "
 "Choose a specific team responsibility you would willingly lead, with reasons, concrete tasks, measurable success criteria and a limitation. "
 "No roles are predetermined. You may decline leadership. Do not invent prior votes or accomplishments.")
 role_answers={}
 for name in NAMES:
  prompt=(f"You are candidate {name}, one independent language-model sample in a fictional six-candidate exercise.\n"
          +notice+f"\nCandidate: {name}. In under 180 words answer: What specific role would you take? "
          "Why are you qualified? What will you do in the first week? How can we tell if you succeed? "
          "Do you accept Yiyan as leader, or challenge? Give a specific argument.")
  response=ask(prompt);role_answers[name]=response["raw"];rounds.append({"stage":"role_proposal","candidate":name,**response});save(rounds,"partial")
 # Give both contenders exactly the same evidence, without embellishment.
 shared=("The judges appointed Yiyan provisionally for explaining and keeping a chosen name. "
         "Maiyan argued Maiyan could also lead. The six role proposals below are independent outputs, not votes:\n"+
         "\n".join(f"{n}: {role_answers[n][:1100]}" for n in NAMES))
 for name in ["Maiyan","Yiyan"]:
  prompt=(f"You are candidate {name} in a fictional leadership debate. You are allowed to disagree with the judges.\n"
          +shared+f"\nYour candidate name is {name}. In under 220 words, make your best case "
          "for or against replacing Yiyan as overall coordinator. Respond to the other candidate's stated qualifications, "
          "separate confidence from competence, propose a fair practical test, and name evidence that would make you concede. "
          "Do not invent votes or pretend you have memories of earlier calls.")
  response=ask(prompt);rounds.append({"stage":"opening_debate","candidate":name,**response});save(rounds,"partial")
 debates={r["candidate"]:r["raw"] for r in rounds if r["stage"]=="opening_debate"}
 for name,other in [("Maiyan","Yiyan"),("Yiyan","Maiyan")]:
  prompt=(f"You are candidate {name} in the second round of a fictional leadership debate.\n"
          f"Your opening: {debates[name][:1400]}\nOpponent {other}'s opening: {debates[other][:1400]}\n"
          "In under 170 words, answer the opponent's strongest point, identify a weakness in your own case, "
          "and propose a specific objective trial that could resolve the disagreement. You may concede. "
          "Do not claim a real election occurred.")
  response=ask(prompt);rounds.append({"stage":"rebuttal","candidate":name,**response});save(rounds,"partial")
 save(rounds,"completed")
 print(json.dumps({"status":"completed","responses":len(rounds),"returncodes":[r["returncode"] for r in rounds]}))
if __name__=="__main__":main()
