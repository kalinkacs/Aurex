"""Probe GitHub Models endpoints without logging secrets or response bodies."""
import json
import os
import urllib.request
import urllib.error
from pathlib import Path

ENDPOINTS = [
    ("models.github.ai", "https://models.github.ai/inference/chat/completions"),
    ("models.inference.ai.azure.com", "https://models.inference.ai.azure.com/chat/completions"),
]
def probe(name, url):
    payload = json.dumps({"model":"openai/gpt-4o-mini","messages":[{"role":"user","content":"Reply with JSON: {\\\"ok\\\":true}"}],"max_tokens":40}).encode()
    req=urllib.request.Request(url,data=payload,headers={
        "Authorization":"Bearer "+os.environ["GITHUB_TOKEN"],
        "Accept":"application/vnd.github+json",
        "Content-Type":"application/json",
        "User-Agent":"Aurex-model-probe"
    },method="POST")
    try:
        with urllib.request.urlopen(req,timeout=25) as response:
            body=response.read()
            return {"endpoint":name,"status":response.status,"content_type":response.headers.get("Content-Type"),"bytes":len(body),"json_valid":is_json(body)}
    except urllib.error.HTTPError as exc:
        body=exc.read()
        return {"endpoint":name,"status":exc.code,"content_type":exc.headers.get("Content-Type"),"bytes":len(body),"json_valid":is_json(body)}
    except Exception as exc:
        return {"endpoint":name,"error_type":type(exc).__name__}

def is_json(data):
    try: json.loads(data); return True
    except (ValueError,UnicodeError): return False

def main():
    result={"diagnostics":[probe(name,url) for name,url in ENDPOINTS]}
    Path("receipts").mkdir(exist_ok=True)
    Path("receipts/model-endpoint-probe.json").write_text(json.dumps(result,indent=2)+"\\n")
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
