"""Rule-based promo candidate finder for timestamped microdrama screenplays.
Uses only screenplay timestamps and text; outputs candidates for human review."""
from pathlib import Path
import re, json, csv, argparse

TS = re.compile(r'Start:\s*\((\d{2}:\d{2}(?:\.\d+)?)\)\s*\|\s*End:\s*\((\d{2}:\d{2}(?:\.\d+)?)\)')
EP = re.compile(r'EPISODE NUMBER:\s*(.+)')
LOGLINE = re.compile(r'EPISODE LOGLINE:\s*(.+)')
HOOK = ['cannot','betray','kill','dead','marry','marrying','why','no','stop','help','please','secret','truth','never','leave','turn around','not anymore','you are','i am']
CLIFF = ['who are you','what happened','will you','is he','is she','you are','i am','marry me','one condition','the truth','not yet','wait','unless','but','however','suddenly','gun','blood','alive','dead','kneel','proposal']

def sec(t):
    m,s=t.split(':'); return int(m)*60+float(s)
def stamp(x):
    m=int(x//60); s=x-m*60
    return f'{m:02d}:{s:05.2f}'
def parse(path):
    txt=path.read_text(encoding='utf-8',errors='ignore')
    ep=EP.search(txt); lg=LOGLINE.search(txt)
    events=[]; current=''; lines=txt.splitlines()
    for i,line in enumerate(lines):
        st=TS.search(line)
        if st:
            start,end=map(sec,st.groups())
            # Timestamp line follows a section label; the next non-empty line normally
            # contains the actual dialogue, action or shot description.
            detail=''
            for nxt in lines[i+1:i+5]:
                if TS.search(nxt): break
                if nxt.strip() and not nxt.strip().startswith(('SCENE','Scene heading:','Scene start:','Scene end:')):
                    detail=nxt.strip(); break
            label=re.sub(r'\*\*','',current).strip(': ')
            context=(label+' — '+detail).strip(' —')
            if end>=start:
                events.append({'start':start,'end':end,'context':context, 'raw':line.strip()})
        elif line.strip() and not line.strip().startswith(('---','SCENE','Scene heading:','Scene start:','Scene end:')):
            current=line.strip()
    # Runtime from scene-end declarations (mm:ss.xx)
    scene_ends=re.findall(r'Scene end:\s*(\d{2}:\d{2}(?:\.\d+)?)',txt,re.I)
    runtime=max([sec(x) for x in scene_ends],default=max((e['end'] for e in events),default=0))
    return {'episode': ep.group(1) if ep else path.stem, 'logline':lg.group(1) if lg else '', 'events':events,'runtime':runtime}

def text_for(events): return ' '.join(e['context'] for e in events).lower()
def score_candidate(events, start, end, logline):
    inside=[e for e in events if e['end']>=start and e['start']<=end]
    if not inside:return None
    opening=[e for e in inside if e['start']<=start+3 and e['end']>=start]
    closing=[e for e in inside if e['end']>=end-6]
    first=text_for(opening or inside[:2]); last=text_for(closing or inside[-2:])
    full=text_for(inside)
    hook_hits=[w for w in HOOK if w in first]
    cliff_hits=[w for w in CLIFF if w in last]
    # Score transparent heuristics: hook, unresolved ending cue, conflict, self-contained context.
    hook_score=min(30, len(hook_hits)*12 + (12 if any(w in first for w in ['slap','shock','betray','abandon','gun','blood','scream','cannot','not anymore']) else 0))
    cliff_score=min(30, len(cliff_hits)*12 + (12 if any(w in last for w in ['who are you','marry me','what','unless','but','suddenly','proposal']) else 0))
    conflict_score=min(20, sum(w in full for w in ['betray','humiliat','threat','secret','revenge','kill','marry','refuse','abandon','shout','cry','shock'])*3)
    standalone=10 if any(w in full for w in ['juliana','gerald','clarissa','duke','father','sister']) else 4
    duration=end-start
    duration_score=10 if 25<=duration<=45 else 6
    score=hook_score+cliff_score+conflict_score+standalone+duration_score
    hook_text=next((e['context'] for e in opening if e['context'] and 'CAMERA' not in e['context'].upper()), opening[0]['context'] if opening else inside[0]['context'])
    cliff_text=next((e['context'] for e in reversed(closing) if e['context'] and 'CAMERA' not in e['context'].upper()), closing[-1]['context'] if closing else inside[-1]['context'])
    return {'start':stamp(start),'end':stamp(end),'duration_seconds':round(duration,1),'score':score,
            'hook':hook_text[:220], 'cliffhanger':cliff_text[:220],
            'context_excerpt':'\n'.join(e['context'] for e in inside)[:12000],
            'why_it_works':'Opens with a high-conflict beat and ends near an unresolved reveal; human review should confirm that the selected stretch is understandable without prior episodes.',
            'segments':[{'start':stamp(start),'end':stamp(end)}],
            'quality_flags':(['Hook is keyword-inferred; verify first 3 seconds'] if hook_score<18 else []) + (['Cliffhanger is weak/uncertain; verify ending'] if cliff_score<18 else [])}

def find(path, per_episode=2):
    data=parse(path); ev=data['events']; candidates=[]
    if not ev:return data,[]
    # Start near event boundaries, test a small set of 20-60s durations.
    starts=sorted(set(max(0,e['start']) for e in ev))
    for s in starts:
        for d in (20,25,30,35,40,45,50,55,60):
            en=s+d
            if en<=data['runtime'] and any(e['end']>=en-6 for e in ev):
                c=score_candidate(ev,s,en,data['logline'])
                if c:candidates.append(c)
    candidates.sort(key=lambda x:x['score'],reverse=True)
    chosen=[]
    for c in candidates:
        a,b=sec(c['start']),sec(c['end'])
        if all(min(b,sec(x['end']))-max(a,sec(x['start']))<12 for x in chosen):
            chosen.append(c)
        if len(chosen)>=per_episode:break
    return data,chosen

def run(input_dir,out_dir):
    out=Path(out_dir); out.mkdir(parents=True,exist_ok=True)
    files=sorted(Path(input_dir).rglob('*.txt'))
    all_rows=[]; audits=[]
    for p in files:
        d,cs=find(p)
        audits.append({'source_file':p.name,'episode':d['episode'],'events_parsed':len(d['events']),'runtime_seconds':d['runtime'],'candidates_found':len(cs)})
        for rank,c in enumerate(cs,1):
            all_rows.append({'episode':d['episode'],'episode_logline':d['logline'],'rank_in_episode':rank,**c,'source_file':p.name})
    all_rows.sort(key=lambda x:x['score'],reverse=True)
    for i,r in enumerate(all_rows,1):r['overall_rank']=i
    (out/'promo_candidates.json').write_text(json.dumps(all_rows,indent=2),encoding='utf-8')
    with (out/'promo_candidates.csv').open('w',newline='',encoding='utf-8') as f:
        cols=['overall_rank','episode','rank_in_episode','start','end','duration_seconds','score','hook','cliffhanger','why_it_works','source_file','quality_flags']
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
        for r in all_rows:w.writerow({k:('; '.join(r[k]) if isinstance(r.get(k),list) else r.get(k,'')) for k in cols})
    (out/'promo_run_audit.json').write_text(json.dumps(audits,indent=2),encoding='utf-8')
    print(f'Processed {len(files)} episodes; parsed {sum(x["events_parsed"] for x in audits)} timed events; generated {len(all_rows)} candidates.')
    print('Top 10 candidates:')
    for r in all_rows[:10]:print(r['overall_rank'],r['episode'],r['start'],r['end'],r['score'],r['hook'],'->',r['cliffhanger'])
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--input',default='../input_pack');ap.add_argument('--output',default='../outputs/problem1');a=ap.parse_args()
    run(a.input,a.output)
