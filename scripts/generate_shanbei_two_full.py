#!/usr/bin/env python3
"""Generate only the two approved voices; no app or study progress changes.

Voice default is rendered by Yunyang and becomes the phone's default sound.
Voice yunxi is a separate global option. No sample-only or fake assets.
"""
import argparse
import asyncio
import hashlib
import json
import random
import re
import subprocess
from pathlib import Path

PACK_SHA = "20b2236109e35b69244b7826da3e239a67b4f735e54f84977b5a6af0fa73d9e4"
VOICES = {"default": "zh-CN-YunyangNeural", "yunxi": "zh-CN-YunxiNeural"}
REVISIONS = {"default": 2, "yunxi": 1}

def say(card):
    return (card.get("title") or card["path"][2]).strip() + "\n" + card["answer"].strip()

def duration_and_format(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=codec_name,sample_rate,channels",
         "-select_streams", "a:0", "-of", "json", str(path)],
        capture_output=True, text=True, timeout=30, check=True
    )
    info = json.loads(result.stdout)
    st = info["streams"][0]
    assert st["codec_name"] == "mp3" and int(st["channels"]) == 1, (path, st)
    seconds = float(info["format"]["duration"])
    assert seconds > 1, (path, seconds)
    return seconds

def validate(path, text):
    assert path.exists() and 500 <= path.stat().st_size <= 16*1024*1024, path
    seconds = duration_and_format(path)
    min_seconds = max(1.5, len(re.sub(r"\s+","",text)) * .070)
    assert seconds >= min_seconds, (str(path), seconds, min_seconds, len(text))
    return seconds

async def synthesize(voice, text, output):
    import edge_tts
    source = output.with_suffix(".original.mp3")
    staging = output.with_suffix(".pending.mp3")
    for attempt in range(6):
        try:
            for p in (source,staging): p.unlink(missing_ok=True)
            await edge_tts.Communicate(text=text, voice=voice, rate="+0%").save(str(source))
            validate(source,text)
            subprocess.run(
                ["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(source),
                 "-vn","-ac","1","-ar","24000","-c:a","libmp3lame","-b:a","32k",
                 "-map_metadata","-1",str(staging)], check=True,timeout=95
            )
            seconds = validate(staging,text)
            staging.replace(output)
            source.unlink(missing_ok=True)
            return seconds
        except Exception as e:
            for p in (source,staging): p.unlink(missing_ok=True)
            if attempt == 5:
                raise RuntimeError(f"Cannot synthesize {voice} after 6 tries: {e}") from e
            await asyncio.sleep(min(16, 2**attempt)+random.uniform(0,.6))

async def main():
    p=argparse.ArgumentParser()
    p.add_argument("--pack",default="data/suyi-full.json")
    p.add_argument("--voice",required=True,choices=sorted(VOICES))
    p.add_argument("--shard",type=int,required=True)
    p.add_argument("--shard-count",type=int,default=8)
    p.add_argument("--out",default="output")
    args=p.parse_args()
    assert 0 <= args.shard < args.shard_count <= 16
    source=Path(args.pack).read_bytes()
    assert hashlib.sha256(source).hexdigest()==PACK_SHA,"Source pack changed: abort"
    cards=json.loads(source)["cards"]
    assert len(cards)==561
    targets=[c for i,c in enumerate(cards) if i%args.shard_count==args.shard]
    output=Path(args.out)
    total_duration=0
    manifest=[]
    for i,c in enumerate(targets):
        cid=c["id"]
        assert re.fullmatch(r"[a-zA-Z0-9._-]{1,128}",cid)
        text=say(c)
        destination=output/f"audio/{args.voice}/{REVISIONS[args.voice]}/{cid}.mp3"
        destination.parent.mkdir(parents=True,exist_ok=True)
        if not destination.exists():
            seconds=await synthesize(VOICES[args.voice],text,destination)
            await asyncio.sleep(.30)
        else:
            seconds=validate(destination,text)
        total_duration+=seconds
        manifest.append({"id":cid,"voice":args.voice,"text_sha256":hashlib.sha256(text.encode()).hexdigest(),
                         "audio_sha256":hashlib.sha256(destination.read_bytes()).hexdigest(),
                         "seconds":round(seconds,3),"bytes":destination.stat().st_size})
        if (i+1)%10==0 or i+1==len(targets):
            print(f"PROGRESS {args.voice} shard={args.shard}: {i+1}/{len(targets)} completed",flush=True)
    path=output/f"manifest-{args.voice}-part{args.shard}.json"
    path.write_text(json.dumps({"voice":args.voice,"shard":args.shard,"count":len(manifest),
                                "duration_seconds":round(total_duration,2),"files":manifest},
                               ensure_ascii=False,indent=2)+"\n")
    assert len(manifest)==len(targets)
    print(f"PASS voice={args.voice}, shard={args.shard}, cards={len(targets)}, minutes={total_duration/60:.1f}",flush=True)

if __name__=="__main__":asyncio.run(main())
