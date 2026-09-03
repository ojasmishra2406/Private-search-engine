import json

found = False
with open(r'C:\Users\mishr\.gemini\antigravity\brain\78c48645-cd75-42a9-829c-292a3f81fa24\.system_generated\logs\transcript.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        if 'AUTHORITATIVE ROADMAP' in line and 'Phase 10' in line:
            data = json.loads(line)
            print(data.get('content', ''))
            found = True
            break

if not found:
    print("Could not find Phase 10 roadmap entry.")
