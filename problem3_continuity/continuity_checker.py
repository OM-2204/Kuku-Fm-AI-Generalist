"""Lightweight script QC: timestamp integrity + episode-to-episode continuity cues."""
from pathlib import Path
import re,json,csv,argparse
TS=re.compile(r'(?:Start|End):\s*\((\d{2}:\d{2}(?:\.\d+)?)\)')
EP=re.compile(r'EPISODE NUMBER:\s*(.+)'); LOG=re.compile(r'EPISODE LOGLINE:\s*(.+)'); CONT=re.compile(r'CONTINUITY NOTES:\s*(.+)')
CHARACTERS=['Juliana','Gerald','Clarissa','Duke','Matriarch','Father','soldier','soldiers']
PROPS=['locket','medallion','pendant','wedding gown','white gown','gold gown','cane','sword','ring','letter']
def sec(s):m,x=s.split(':');return int(m)*60+float(x)
def analyze(path):
 t=path.read_text(encoding='utf-8',errors='ignore'); ep=EP.search(t); log=LOG.search(t); cn=CONT.search(t)
 starts=[sec(x) for x in re.findall(r'Scene start:\s*(\d{2}:\d{2}(?:\.\d+)?)',t,re.I)]
 ends=[sec(x) for x in re.findall(r'Scene end:\s*(\d{2}:\d{2}(?:\.\d+)?)',t,re.I)]
 alltimes=[sec(x) for x in TS.findall(t)]
 issues=[]; score=100
 if not starts or not ends:issues.append('Missing scene-level start/end timestamp');score-=25
 if starts and starts[0]>0.5:issues.append(f'First scene starts at {starts[0]:.1f}s, not near zero');score-=10
 for i in range(1,min(len(starts),len(ends))):
  if starts[i] < starts[i-1]:issues.append(f'Scene start order moves backwards near scene {i+1}');score-=10
  if starts[i] < ends[i-1]-0.2:issues.append(f'Possible scene overlap: scene {i+1} starts before prior scene ends');score-=8
 if starts and ends and len(starts)==len(ends):
  for i,(a,b) in enumerate(zip(starts,ends),1):
   if b<a:issues.append(f'Scene {i} ends before it starts');score-=15
 # Compare event timestamps to declared scene envelope.
 runtime=max(ends,default=0)
 out_of_range=[x for x in alltimes if x>runtime+1]
 if out_of_range:issues.append(f'{len(out_of_range)} timed dialogue/action/camera entries extend beyond final scene end');score-=min(20,5*len(out_of_range))
 low=t.lower(); present=[x for x in CHARACTERS if x.lower() in low]; props=[x for x in PROPS if x in low]
 return {'file':path.name,'episode':ep.group(1) if ep else path.stem,'logline':log.group(1) if log else '',
         'continuity_note':cn.group(1) if cn else '', 'scene_count':len(starts),'timed_entries':len(alltimes),
         'runtime_seconds':runtime,'characters_mentioned':present,'props_mentioned':props,
         'qc_score':max(0,score),'issues':issues}
def run(input_dir,out_dir):
 files=sorted(Path(input_dir).rglob('*.txt')); rows=[analyze(p) for p in files]
 # Lightweight previous-episode cue comparison; flags terms in continuity note not found in current script.
 for i,r in enumerate(rows):
  if i and r['continuity_note']:
   terms=[x for x in re.findall(r'\b[A-Z][a-z]{3,}\b',r['continuity_note']) if x not in ['Episode','Juliana']]
   text=Path(files[i]).read_text(encoding='utf-8',errors='ignore').lower()
   missing=[x for x in terms if x.lower() not in text]
   if missing:r['continuity_review_flags']=['Continuity note names not found in script text: '+', '.join(missing[:8])]
   else:r['continuity_review_flags']=[]
  else:r['continuity_review_flags']=[]
 out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
 (out/'continuity_qc.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
 with (out/'continuity_qc.csv').open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=['episode','file','scene_count','timed_entries','runtime_seconds','qc_score','issues','continuity_review_flags','characters_mentioned','props_mentioned']);w.writeheader()
  for r in rows:w.writerow({k:('; '.join(map(str,r.get(k,[]))) if isinstance(r.get(k),list) else r.get(k,'')) for k in w.fieldnames})
 print(f'Checked {len(rows)} episodes. Potential timestamp/QC issues: {sum(bool(r["issues"]) for r in rows)}. Manual continuity flags: {sum(bool(r["continuity_review_flags"]) for r in rows)}')
 for r in rows:
  if r['issues'] or r['continuity_review_flags']:print(r['episode'],r['qc_score'],r['issues'],r['continuity_review_flags'])
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--input',default='../input_pack');ap.add_argument('--output',default='../outputs/problem3');a=ap.parse_args();run(a.input,a.output)
