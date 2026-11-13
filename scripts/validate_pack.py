#!/usr/bin/env python3
"""Small, dependency-free JSON format check for a PoliticsMemory study pack."""
import json
import re
import sys
from pathlib import Path


def check(path):
    obj=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    assert obj.get('schema_version')==1, 'schema_version must be 1'
    assert re.fullmatch(r'[A-Za-z0-9._-]{1,80}',obj['pack_id']), 'invalid pack_id'
    assert int(obj.get('pack_revision',1))>=1
    cards=obj['cards'];assert 1<=len(cards)<=20000
    ids=set()
    for n,c in enumerate(cards,1):
        cid=c['id']
        assert re.fullmatch(r'[A-Za-z0-9._-]{1,128}',cid), f'id {n} invalid'
        assert cid not in ids,f'duplicate id {cid}'
        ids.add(cid)
        assert int(c.get('revision',1))>0
        assert len(c['path'])==3 and all(isinstance(x,str) and x.strip() for x in c['path']),f'bad path {cid}'
        assert c.get('type','keypoint') in ('keypoint','essay')
        assert 1<=len(c['question'].strip())<=1500
        assert 1<=len(c['answer'].strip())<=25000
        assert len(c.get('source',''))<=500
    print(f'OK: {path}: {len(cards)} cards, {len({c["path"][1] for c in cards})} chapters, v{obj["pack_revision"]}')


if __name__=='__main__':
    if len(sys.argv)<2: raise SystemExit('Usage: validate_pack.py path.json [more.json]')
    for p in sys.argv[1:]: check(p)
