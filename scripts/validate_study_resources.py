#!/usr/bin/env python3
"""Validate exact annotation spans and unchanged baseline knowledge/audio contracts."""
import hashlib,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
pack=json.loads((root/'data/suyi-full.json').read_text());res=json.loads((root/'data/study-resources.json').read_text());ids={c['id'] for c in pack['cards']}
assert len(ids)==len(pack['cards'])==561
assert set(res['annotations'])==ids
cloze=0;context=0
for c in pack['cards']:
    a=res['annotations'][c['id']];answer=c['answer'];assert hashlib.sha256(answer.encode()).hexdigest()==a['answer_sha256'];end=0;blanks=0
    for m in a['marks']:
        assert m['start']>=end and m['end']>m['start'];assert answer.encode('utf-16-le')[m['start']*2:m['end']*2].decode('utf-16-le')==m['text'];end=m['end']
        assert m['kind'] in ('core','confusion','condition');blanks+=bool(m.get('cloze'));context+=bool(m.get('course_context'))
    assert blanks;cloze+=blanks
assert (root/'app/src/main/assets/study-resources.json').read_bytes()==(root/'data/study-resources.json').read_bytes()
# The runtime sidecar must not alter text or existing scoring/gesture functions.
base='f9b0d727abb2b59aabe4cf4e4ce6e7260f2d0cc7'
try:subprocess.check_output(['git','cat-file','-e',base],cwd=root,stderr=subprocess.DEVNULL)
except subprocess.CalledProcessError:base='HEAD'
for name in ['data/suyi-full.json','app/src/main/java/org/vector/politicsmemory/ReviewLogic.java','app/src/main/java/org/vector/politicsmemory/SwipePagerLayout.java','web-preview/audio-index.json']:
    assert subprocess.check_output(['git','show',base+':'+name],cwd=root)==(root/name).read_bytes(),name+' changed outside agreed scope'
print(f'PASS: 561 exact annotation sets; {cloze} cloze anchors; {context} related course contexts; original text/scoring/gestures/audio index unchanged')
