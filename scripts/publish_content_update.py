#!/usr/bin/env python3
"""Codex publishing utility: signed-by-hash, minimal-delta MP3 + authoritative full pack.

The *only* file Codex needs to replace on Drive is content-update.zip. Do not
change its Drive file ID: the phone's persisted document grant depends on it.
"""
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def spoken(card: dict) -> str:
    return (card.get('title') or card['path'][2]).strip() + '\n' + card['answer'].strip()

def load(path: Path) -> dict:
    doc = json.loads(path.read_text(encoding='utf-8'))
    if doc.get('schema_version') != 1 or doc.get('pack_id') != 'politics-suyi-full':
        raise ValueError(f'{path}: not a PoliticsMemory knowledge pack')
    cards = doc.get('cards')
    if not isinstance(cards, list) or not cards or len(cards) > 20000:
        raise ValueError('Expected 1..20,000 cards')
    ids = [c['id'] for c in cards]
    if len(set(ids)) != len(ids) or any(not ID.fullmatch(cid) for cid in ids):
        raise ValueError('Duplicate or invalid stable card IDs')
    return doc

def main():
    parser = argparse.ArgumentParser(description='Build a Drive-ready manual content update')
    parser.add_argument('--before', required=True, type=Path, help='Previously published source pack')
    parser.add_argument('--after', required=True, type=Path, help='New full authoritative source pack')
    parser.add_argument('--audio-dir', required=True, type=Path, help='Changed MP3 files only')
    parser.add_argument('--out', required=True, type=Path)
    a = parser.parse_args()
    before,after=load(a.before),load(a.after)
    if after['pack_revision'] <= before['pack_revision']:
        raise ValueError('pack_revision must increase for every published release')
    old={c['id']:c for c in before['cards']}
    new={c['id']:c for c in after['cards']}
    added=sorted(set(new)-set(old))
    removed=sorted(set(old)-set(new))
    updated=sorted(id for id in set(new)&set(old) if new[id]!=old[id])
    for cid in updated:
        if new[cid]['revision'] <= old[cid]['revision']:
            raise ValueError(f'{cid}: update card revision when content/metadata changes')
    need_audio=sorted(cid for cid in set(added+updated)
                      if cid in added or spoken(new[cid])!=spoken(old[cid]))
    manifest={'schema_version':1,'pack_id':after['pack_id'],
              'speech_format':'title-answer-v1','items':{}}
    for cid in need_audio:
        path=a.audio_dir/f'{cid}.mp3'
        if not path.is_file() or not 500 <= path.stat().st_size <= 16*1024*1024:
            raise ValueError(f'{cid}: missing/invalid new audio at {path}')
        raw=path.read_bytes()
        manifest['items'][cid]={'file':f'audio/{cid}.mp3',
            'text_sha256':sha(spoken(new[cid]).encode('utf-8')),
            'audio_sha256':sha(raw),'size_bytes':len(raw)}
    desc={'kind':'politics-memory-content-update','schema_version':1,
          'pack_id':after['pack_id'],'pack_revision':after['pack_revision'],
          'release_id':f"revision-{after['pack_revision']}",
          'added_ids':added,'updated_ids':updated,'deleted_ids':removed,
          'audio_ids':need_audio,'pack_sha256':sha(a.after.read_bytes())}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(a.out,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('update.json',json.dumps(desc,ensure_ascii=False,indent=2)+'\n')
        z.writestr('pack.json',json.dumps(after,ensure_ascii=False,separators=(',',':'))+'\n')
        z.writestr('audio-index.json',json.dumps(manifest,ensure_ascii=False,separators=(',',':'))+'\n')
        for cid in need_audio:z.write(a.audio_dir/f'{cid}.mp3',f'audio/{cid}.mp3')
    print(json.dumps({'artifact':str(a.out),'sha256':sha(a.out.read_bytes()),
          'added':len(added),'updated':len(updated),'retired':len(removed),
          'new_audio':len(need_audio)},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
