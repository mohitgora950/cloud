import json

transcript_path = r'C:/Users/Mohit Gora/.gemini/antigravity/brain/56c690af-046d-4db5-8451-fc4239b78c0b/.system_generated/logs/transcript_full.jsonl'
with open(transcript_path, encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'Task 7' in line or 'rate_card' in line or 'Review table' in line or 'handwritten' in line.lower():
            obj = json.loads(line)
            content = obj.get('content', '')
            thinking = obj.get('thinking', '')
            combined = content + '\n' + thinking
            for kw in ['Task 7', 'rate_card', 'Review table', 'handwritten']:
                if kw.lower() in combined.lower():
                    idx = combined.lower().find(kw.lower())
                    print(f"=== Line {i}, Step {obj.get('step_index')} ===")
                    print(combined[max(0, idx-100):idx+500])
                    print('-'*50)
                    break

