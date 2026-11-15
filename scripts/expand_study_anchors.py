#!/usr/bin/env python3
"""Rebuild exact-source annotation and presentation metadata; never rewrite card text."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    raw=(ROOT/'data/suyi-full.json').read_bytes()
    spec=json.loads((ROOT/'data/study-cloze-r2.json').read_text(encoding='utf-8'))
    assert spec['schema_version']==1
    assert hashlib.sha256(raw).hexdigest()==spec['baseline_pack_sha256'],'Source changed: re-review cards before moving blanks'
    pack=json.loads(raw);cards=pack['cards'];rows=spec['rows']
    assert len(cards)==len(rows)==561
    destination=ROOT/'data/study-resources.json'
    result=json.loads(destination.read_text(encoding='utf-8'))
    assert result['schema_version']==1
    revision=spec['annotation_revision'];assert revision>=3
    for card,(goal,cues,spans) in zip(cards,rows):
        answer=card['answer'];utf16=answer.encode('utf-16-le');marks=[];previous=0
        assert goal and cues
        for start,length,kind in spans:
            end=start+length
            assert isinstance(start,int) and isinstance(length,int) and length>0
            assert start>=previous and end*2<=len(utf16) and kind in (0,1,2)
            quote=utf16[start*2:end*2].decode('utf-16-le');assert quote
            marks.append({'start':start,'end':end,'text':quote,'kind':['core','confusion','condition'][kind],'cloze':kind!=2,'basis':spec['basis']})
            previous=end
        assert any(m['cloze'] for m in marks)
        annotation={'revision':revision,'answer_sha256':hashlib.sha256(answer.encode()).hexdigest(),
                    'marks':marks,'recall_goal':goal,'retained_cues':cues,
                    'status':'CARD_BY_CARD_EDITORIAL_SOURCE_GROUNDED'}
        old=result.get('annotations',{}).get(card['id'])
        if old is not None:
            assert old.get('answer_sha256')==annotation['answer_sha256']
            assert old.get('marks')==marks,'Refuse to silently replace a different set of exam marks'
        result.setdefault('annotations',{})[card['id']]=annotation
    # Full view preserves all source words; the short view uses only exact source spans.
    sidecar=ROOT/'data/study-presentations-r3.json'
    if sidecar.is_file():
        presentation=json.loads(sidecar.read_text(encoding='utf-8'))
        assert presentation['schema_version']==1
        assert presentation['source_pack_sha256']==hashlib.sha256(raw).hexdigest()
        assert set(presentation['annotations'])==set(result['annotations'])
        for card_id,item in presentation['annotations'].items():
            base=result['annotations'][card_id]
            assert item['answer_sha256']==base['answer_sha256']
            base['revision']=4
            base['full_layout']=item['full_layout']
            base['brief_layout']=item['brief_layout']
            base['presentation_status']='EXTRACTIVE_SOURCE_SPANS_FULL_UNALTERED_BRIEF_SUBSET'
    encoded=(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n').encode()
    for name in ('data/study-resources.json','app/src/main/assets/study-resources.json'):
        p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(encoded)
    (ROOT/'preview/study-resources.js').write_text('window.POLITICS_STUDY_RESOURCES='+encoded.decode().strip().replace('</','<\\/')+';\n',encoding='utf-8')
    print('PASS: 561 source-anchored views; original text and non-annotation resources unchanged')
if __name__=='__main__':main()
