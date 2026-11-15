#!/usr/bin/env python3
"""Synthesize the three user-selected Mandarin voices, without changing the app.

PILOT only by default. This is based on the third-party edge-tts service,
which is not the paid Azure Speech API and cannot guarantee availability.
All audio files are checked before any publish. No user progress is touched.
"""
import argparse
import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path

VOICES = (
    ("yunxi", "zh-CN-YunxiNeural", "云希"),
    ("yunyang", "zh-CN-YunyangNeural", "云扬"),
    ("xiaochen", "zh-CN-XiaochenNeural", "晓辰"),
)


def spoken(card):
    title = (card.get("title") or card["path"][2]).strip()
    return title + "\n" + card["answer"].strip()


def verify(path: Path):
    assert path.is_file() and path.stat().st_size >= 500, f"empty/small audio: {path}"
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    assert p.returncode == 0 and float(p.stdout.strip()) > .25, f"invalid MP3: {path}"


async def synthesize(voice, text, dest):
    import edge_tts
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part.mp3")
    for attempt in range(3):
        try:
            if tmp.exists():
                tmp.unlink()
            communicator = edge_tts.Communicate(text=text, voice=voice, rate="+0%")
            await communicator.save(str(tmp))
            verify(tmp)
            tmp.replace(dest)
            return
        except Exception as e:
            tmp.unlink(missing_ok=True)
            if attempt == 2:
                raise RuntimeError(f"Voice {voice}: {type(e).__name__}: {e}") from e
            await asyncio.sleep(2 ** attempt + 1)


async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pack", default="data/suyi-full.json")
    p.add_argument("--out", default="private-voices")
    p.add_argument("--mode", choices=["pilot", "full"], default="pilot")
    args = p.parse_args()
    pack = json.loads(Path(args.pack).read_text(encoding="utf-8"))
    assert pack["pack_id"] == "politics-suyi-full"
    cards = pack["cards"]
    assert len(cards) == 561, len(cards)
    if args.mode == "pilot":
        # Short, medium, long answer for intelligibility and completeness checks.
        cards = sorted(cards, key=lambda c: len(spoken(c)))
        cards = [cards[25], cards[len(cards) // 2], cards[-25]]
    results = []
    for short, azure_voice, chinese in VOICES:
        base = Path(args.out) / short
        for index, card in enumerate(cards):
            cid = card["id"]
            assert re.fullmatch(r"[a-zA-Z0-9._-]{1,128}", cid)
            dst = base / (cid + ".mp3")
            if not dst.exists():
                await synthesize(azure_voice, spoken(card), dst)
                await asyncio.sleep(.35)
            verify(dst)
            results.append({"voice":short, "name":chinese, "voice_id":azure_voice,
                            "card_id":cid, "bytes":dst.stat().st_size})
            if index % 60 == 0:
                print(f"{chinese}: {index + 1}/{len(cards)}", flush=True)
    out = Path(args.out)
    (out / f"manifest-{args.mode}.json").write_text(
        json.dumps({"mode":args.mode,"voices":VOICES,"audio_count":len(results),"files":results},ensure_ascii=False,indent=2)+"\n")
    print(f"PASS: generated {len(results)} individually decoded MP3 files", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
