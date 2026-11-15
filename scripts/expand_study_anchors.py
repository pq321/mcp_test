#!/usr/bin/env python3
"""Reconstruct the reviewed v0.12 sidecar, without editing any source knowledge text."""
import json,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1]
raw=(root/'data/suyi-full.json').read_bytes();pack=json.loads(raw);spec=json.loads((root/'data/study-anchors-v012.json').read_text())
assert hashlib.sha256(raw).hexdigest()==spec['baseline_pack_sha256'],'Anchor source differs; author a new sidecar instead of guessing positions'
assert len(spec['rows'])==len(pack['cards'])
result={'schema_version':1,'sources':{'politics-suyi-full':{'revision':1,'name':'苏一'}},'voices':{'default':{'revision':1,'name':'默认声音','items':{}}},'annotations':{}}
for card,row in zip(pack['cards'],spec['rows']):
    marks=[];answer=card['answer'];utf16=answer.encode('utf-16-le')
    for entry in row:
        start,length,flags,basis=entry[:4];end=start+length
        m={'start':start,'end':end,'text':utf16[2*start:2*end].decode('utf-16-le'),'kind':['core','confusion','condition'][flags&3],'cloze':bool(flags&4),'basis':spec['basis'][basis]}
        if len(entry)>4:
            course,time=spec['contexts'][entry[4]];m['course_context']={'course':course,'time':time,'relationship':'related_course_context','transcript_status':'RAW_ASR_UNVERIFIED'}
        marks.append(m)
    result['annotations'][card['id']]={'revision':1,'answer_sha256':hashlib.sha256(answer.encode()).hexdigest(),'marks':marks,'status':'EDITOR_SELECTED_WITH_COURSE_CONTEXT_NOT_WORD_BY_WORD_CERTIFIED'}
encoded=(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n').encode()
for name in ('data/study-resources.json','app/src/main/assets/study-resources.json'):
    target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(encoded)
(root/'preview/study-resources.js').write_text('window.POLITICS_STUDY_RESOURCES='+json.dumps(result,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')+';\n',encoding='utf-8')
print('PASS: reconstructed 561 reviewed annotation groups; original knowledge text untouched')
