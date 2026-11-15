#!/usr/bin/env python3
"""Publish metadata, source packs and Codex-recorded voices on the existing manual channel.

The archive contains the complete current optional voice set, NOT the 561 built-in MP3s.
Keeping that optional set avoids missing recordings when a phone skips a release.
No cloud credentials or user progress are read/written by this command.
"""
import argparse,copy,hashlib,json,sys,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from study_resource_bundle import inspect_bundle,ident,integer

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(data):return hashlib.sha256(data).hexdigest()
def encode(obj):return (json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'\n').encode()

def publish(resources,packs,audio_root,out,previous=None):
    if previous:
        for section in ('sources','voices','annotations'):
            for key,item in resources.get(section,{}).items():
                old=previous.get(section,{}).get(key)
                if old and item!=old and item['revision']<=old['revision']:raise ValueError(f'{section}/{key}: changed content requires a higher revision')
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);temp=out.with_suffix(out.suffix+'.pending')
    try:
        with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('update.json',encode({'kind':'politics-memory-content-update','schema_version':1,'resource_update':True}))
            z.writestr('study-resources.json',encode(resources))
            seen=set()
            for pack in packs:
                pid=ident(pack['pack_id'])
                if pid in seen:raise ValueError('Duplicate source pack')
                seen.add(pid);z.writestr('packs/'+pid+'.json',encode(pack))
            for voice in resources.get('voices',{}).values():
                for item in voice.get('items',{}).values():
                    name=item['file'];path=(Path(audio_root)/name).resolve()
                    if not path.is_relative_to(Path(audio_root).resolve()) or not path.is_file():raise ValueError('Missing optional recording: '+name)
                    if sha(path.read_bytes())!=item['audio_sha256']:raise ValueError('Optional recording hash mismatch: '+name)
                    z.write(path,name)
        with zipfile.ZipFile(temp) as z:inspect_bundle(z)
        temp.replace(out)
    finally:
        if temp.exists():temp.unlink()
    return {'file':str(out),'sha256':sha(out.read_bytes()),'bytes':out.stat().st_size,'sources':len(packs),'voices':len(resources.get('voices',{}))}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--resources',required=True,help='Complete current metadata JSON')
    p.add_argument('--previous-resources',help='Previous published metadata; enforce revision changes')
    p.add_argument('--pack',action='append',default=[],help='Full authoritative source pack; repeat for multiple sources')
    p.add_argument('--audio-root',required=True,help='Private publisher cache containing audio/voice/revision/id.mp3')
    p.add_argument('--out',required=True)
    p.add_argument('--voice-id');p.add_argument('--voice-name');p.add_argument('--voice-revision',type=int);p.add_argument('--voice-dir',help='Codex generated MP3 directory, filenames card-id.mp3')
    p.add_argument('--text-pack',action='append',default=[],help='Reference pack to bind recordings; does not change phone text')
    p.add_argument('--save-resources',help='Write resulting metadata here for future publishing')
    a=p.parse_args();resources=copy.deepcopy(read(a.resources));packs=[read(x) for x in a.pack]
    if any([a.voice_id,a.voice_name,a.voice_revision,a.voice_dir]):
        if not all([a.voice_id,a.voice_name,a.voice_revision,a.voice_dir]):p.error('All four --voice-* arguments are needed')
        vid=ident(a.voice_id);rev=integer(a.voice_revision);cards={c['id']:c for pk in packs+[read(x) for x in a.text_pack] for c in pk['cards']}
        items={}
        for src in sorted(Path(a.voice_dir).glob('*.mp3')):
            cid=ident(src.stem)
            if cid not in cards:raise ValueError('No text record for '+cid)
            c=cards[cid];text=(c.get('title') or c['path'][2]).strip()+'\n'+c['answer'].strip();data=src.read_bytes()
            if not 500<=len(data)<=16*1024*1024:raise ValueError('Invalid MP3 size: '+src.name)
            name=f'audio/{vid}/{rev}/{cid}.mp3';target=Path(a.audio_root)/name;target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists() and target.read_bytes()!=data:raise ValueError('Same voice revision already has different bytes')
            target.write_bytes(data);items[cid]={'file':name,'text_sha256':sha(text.encode()),'audio_sha256':sha(data),'size_bytes':len(data)}
        if not items:raise ValueError('No MP3 recordings found')
        resources.setdefault('voices',{})[vid]={'revision':rev,'name':a.voice_name,'items':items}
    result=publish(resources,packs,a.audio_root,a.out,read(a.previous_resources) if a.previous_resources else None)
    if a.save_resources:Path(a.save_resources).write_bytes(encode(resources))
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
