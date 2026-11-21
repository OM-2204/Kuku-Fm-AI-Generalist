from pathlib import Path
from tempfile import TemporaryDirectory
from promo_finder import find
sample='''EPISODE NUMBER: Episode Test\nEPISODE LOGLINE: A betrayal.\nSCENE 01\nScene start: 00:00.00\nScene end: 01:00.00\n**VILLAIN (Cold):**\nStart: (00:00.00) | End: (00:04.00)\nI will kill you.\n**HERO (Terrified):**\nStart: (00:45.00) | End: (00:50.00)\nWho are you?\n'''
with TemporaryDirectory() as d:
 p=Path(d)/'test.txt';p.write_text(sample)
 data,candidates=find(p)
 assert candidates and all(20<=x['duration_seconds']<=60 for x in candidates)
 print('PASS: generated candidate duration stays within 20–60 seconds.')
