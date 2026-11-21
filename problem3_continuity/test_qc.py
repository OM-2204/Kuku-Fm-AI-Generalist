from pathlib import Path
from tempfile import TemporaryDirectory
from continuity_checker import analyze
sample='''EPISODE NUMBER: Episode Test\nEPISODE LOGLINE: Test\nCONTINUITY NOTES: Test\nSCENE 01\nSCENE START: 00:00.00\nSCENE END: 00:10.00\n**DIALOGUE:**\nStart: (00:12.00) | End: (00:14.00)\nThis event is outside the episode.\n'''
with TemporaryDirectory() as d:
 p=Path(d)/'test.txt';p.write_text(sample)
 r=analyze(p)
 assert r['scene_count']==1
 assert any('extend beyond' in x for x in r['issues']),r
 print('PASS: synthetic timestamp-out-of-range case was flagged.')
