#!/usr/bin/env python3
"""Check all prerecorded clips against each current card before Android packaging."""
import hashlib,json,pathlib,sys
source=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))
root=pathlib.Path(sys.argv[2])
index=json.loads((root/'audio-index.json').read_text(encoding='utf-8'))
assert index['schema_version']==1 and index['pack_id']==source['pack_id']
assert len(index['items']) == len(source['cards'])
for card in source['cards']:
    entry=index['items'][card['id']]
    assert entry['file']=='audio/'+card['id']+'.mp3'
    assert entry['text_sha256']==hashlib.sha256((card['question']+'\n'+card['answer']).encode('utf-8')).hexdigest()
    path=root/entry['file'];b=path.read_bytes()
    assert len(b)>500 and hashlib.sha256(b).hexdigest()==entry['audio_sha256']
print('PASS: verified',len(source['cards']),'MP3 clips with audio and text hashes')
