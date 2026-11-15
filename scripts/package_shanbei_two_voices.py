#!/usr/bin/env python3
"""Build optional two-voice phone sync ZIP without changing cards, marks, or progress."""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from publish_study_resources import publish

PACK_SHA="20b2236109e35b69244b7826da3e239a67b4f735e54f84977b5a6af0fa73d9e4"
RESOURCES_SHA="30221709478c3001637544e2571bf5feceea1fef05c631b92859141a4a7bdc1a"
VOICE_INFO={
    "default":(2,"云扬（默认）","zh-CN-YunyangNeural"),
    "yunxi":(1,"云希","zh-CN-YunxiNeural"),
}

def sha(data):return hashlib.sha256(data).hexdigest()
def spoken(c):return (c.get("title") or c["path"][2]).strip()+"\n"+c["answer"].strip()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--audio-root",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    rawpack=(ROOT/"data/suyi-full.json").read_bytes()
    rawres=(ROOT/"data/study-resources.json").read_bytes()
    assert sha(rawpack)==PACK_SHA,"Changed knowledge source; halt"
    assert sha(rawres)==RESOURCES_SHA,"Changed R2 annotations; halt"
    pack=json.loads(rawpack)
    cards=pack["cards"];assert len(cards)==561
    old=json.loads(rawres)
    out=copy.deepcopy(old)
    audio_root=Path(args.audio_root).resolve()
    manifest={"schema":"shanbei_two_voices_20261115",
              "original_pack_sha256":sha(rawpack),
              "unchanged_annotations_sha256":sha(json.dumps(old["annotations"],sort_keys=True,ensure_ascii=False).encode()),
              "voices":{}}
    referenced=set()
    for voice,(rev,name,sourcevoice) in VOICE_INFO.items():
        items={}
        seconds=0
        bytes_total=0
        for card in cards:
            cid=card["id"]
            rel=f"audio/{voice}/{rev}/{cid}.mp3"
            file=audio_root/rel
            assert file.is_file(),f"Missing {rel}"
            content=file.read_bytes()
            assert 500<=len(content)<=16*1024*1024,f"Invalid audio size {rel}"
            text=spoken(card)
            items[cid]={"file":rel,
                        "text_sha256":sha(text.encode()),
                        "audio_sha256":sha(content),
                        "size_bytes":len(content)}
            referenced.add(rel)
            bytes_total+=len(content)
        assert len(items)==561
        out["voices"][voice]={"revision":rev,"name":name,"items":items}
        manifest["voices"][voice]={"name":name,"azure_voice":sourcevoice,
                                   "tracks":len(items),"audio_bytes":bytes_total}
    expected=set(f"audio/{v}/{rev}/{c['id']}.mp3" for v,(rev,_,_) in VOICE_INFO.items() for c in cards)
    actual=set(str(p.relative_to(audio_root)).replace("\\","/") for p in (audio_root/"audio").rglob("*.mp3"))
    assert actual==expected, f"Unexpected audio files: extra {len(actual-expected)}, missing {len(expected-actual)}"
    assert len(referenced)==1122
    assert out["annotations"]==old["annotations"]
    assert out["sources"]==old["sources"]
    assert out["voices"]["default"]["revision"]>old["voices"]["default"]["revision"]
    target=Path(args.out)
    target.parent.mkdir(parents=True,exist_ok=True)
    result=publish(out,[],audio_root,target,old)
    assert result["voices"]==2
    assert target.stat().st_size<1000*1024*1024,"Beyond 1GB Android importer limit"
    patchfile=target.parent/"study-resources-with-two-voices.json"
    patchfile.write_text(json.dumps(out,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    manifest["update_sha256"]=sha(target.read_bytes())
    manifest["update_bytes"]=target.stat().st_size
    manifest["cards_changed"]=0
    manifest["ratings_and_progress_touched"]=False
    manifest["annotations_changed"]=False
    manifest["voices_expected"]=1122
    mf=target.parent/"two-voice-manifest.json"
    mf.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("READY: 1122 audio tracks; Yunyang default, Yunxi selectable; no card/annotation/progress changes")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
