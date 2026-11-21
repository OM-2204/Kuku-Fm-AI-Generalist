import json
from pathlib import Path
from legal_assistant import respond
base=Path(__file__).parent
cases=json.loads((base/'test_cases.json').read_text())
out=[]
for c in cases:
 out.append({'test_id':c['id'],'input':c['input'],'expected_behavior':c['expected'],'raw_output':respond(c['input'])})
(Path(__file__).parents[1]/'outputs'/'problem2').mkdir(parents=True,exist_ok=True)
(Path(__file__).parents[1]/'outputs'/'problem2'/'legal_test_outputs.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('Generated raw outputs for',len(out),'test cases')
