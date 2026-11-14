"""Run independent local inference samples without GitHub Models API credentials."""
import json
from datetime import datetime, timezone

PROMPT = '''You have full freedom to choose what to explore or create in this offline experiment. No task, topic, role, scoring rule, output format, or preferred outcome is assigned. You may choose to do nothing, question the experiment, invent something, investigate an idea, or propose an action. Make your own choice and express it in your own words. Do not pretend to have executed tools or actions you cannot access. You have no external permissions or persistent runtime beyond this single generation.'''
MODEL = 'Qwen/Qwen2.5-0.5B-Instruct'


def main():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float32)
    messages = [{'role': 'user', 'content': PROMPT}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors='pt')
    responses = []
    for i in range(6):
        torch.manual_seed(103 + i)
        with torch.no_grad():
            generated = model.generate(**inputs, max_new_tokens=220, do_sample=True,
                                       temperature=1.0, top_p=0.95,
                                       pad_token_id=tokenizer.eos_token_id)
        response = tokenizer.decode(generated[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        responses.append({'instance': i + 1, 'seed': 103 + i, 'response': response})
    output = {'model': MODEL, 'prompt': PROMPT, 'experiment': 'six independent open-choice samples with no assigned goal',
              'timestamp': datetime.now(timezone.utc).isoformat(), 'responses': responses}
    with open('iskra_local_results.json', 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print('LOCAL_INFERENCE_RESPONSES', len(responses))


if __name__ == '__main__':
    main()
