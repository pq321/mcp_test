#!/usr/bin/env python3
"""Content publisher must distinguish deletion from re-rating and require new audio only for changed speech."""
import json,os,subprocess,sys,tempfile,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'scripts'))
import publish_content_update as pub
pack_path=root/'data/suyi-full.json'
if not pack_path.is_file():pack_path=Path('/mnt/data/politics_full/repo/data/suyi-full.json')
pack=json.loads(pack_path.read_text())
with tempfile.TemporaryDirectory() as temp:
    t=Path(temp);a=t/'old.json';b=t/'new.json';audio=t/'audio';audio.mkdir();archive=t/'content-update.zip'
    a.write_text(json.dumps(pack,ensure_ascii=False),encoding='utf-8')
    next=dict(pack);next['cards']=pack['cards'][:-1];next['pack_revision']=pack['pack_revision']+1
    b.write_text(json.dumps(next,ensure_ascii=False),encoding='utf-8')
    cmd=[sys.executable,str(root/'scripts/publish_content_update.py'),'--before',str(a),'--after',str(b),'--audio-dir',str(audio),'--out',str(archive)]
    subprocess.run(cmd,check=True,capture_output=True)
    with zipfile.ZipFile(archive) as z:
        assert set(z.namelist())=={'pack.json','audio-index.json','update.json'}
        meta=json.loads(z.read('update.json'))
        assert meta['deleted_ids']==[pack['cards'][-1]['id']]
        assert not meta['audio_ids']
    # New speech must force a new MP3; omission is an error, never silently uses an old recording.
    next['cards']=[dict(c) for c in pack['cards']]
    next['cards'][0]['title']=next['cards'][0]['title']+'（更新）'
    next['cards'][0]['revision']=pack['cards'][0]['revision']+1
    b.write_text(json.dumps(next,ensure_ascii=False),encoding='utf-8')
    result=subprocess.run(cmd,capture_output=True,text=True)
    assert result.returncode and 'missing/invalid new audio' in result.stderr
print('PASS: deletion archives cards without audio re-download; edited text requires fresh audio')
