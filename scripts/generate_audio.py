#!/usr/bin/env python3
"""Build-time-only Mandarin TTS. Model and network are never shipped to the phone.

Examples:
  python scripts/generate_audio.py --pack data/starter-sixiu-k.json --model .voice/zh_CN-chaowen-medium.onnx --out app/src/main/assets
  python scripts/generate_audio.py --pack additional.json --model ... --out staging --zip additional-audio-pack.zip
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import wave
import zipfile


from spoken_text import spoken_text


def text_hash(card):
    return hashlib.sha256(spoken_text(card).encode('utf-8')).hexdigest()


def render_pack(args):
    from piper import PiperVoice
    root = json.loads(Path(args.pack).read_text(encoding='utf-8'))
    assert root['schema_version'] == 1
    cards = root['cards']
    audio_dir = Path(args.out) / 'audio'
    audio_dir.mkdir(parents=True, exist_ok=True)
    voice = PiperVoice.load(args.model)
    manifest = {'schema_version': 1, 'pack_id': root['pack_id'], 'generator': 'piper-tts:zh_CN-chaowen-medium',
        'speech_format': 'title-answer-v1', 'items': {}}
    failures=[]
    for n, card in enumerate(cards,1):
        item_id = card['id']
        if not item_id or not all(c.isascii() and (c.isalnum() or c in '._-') for c in item_id):
            raise ValueError('Unsafe id: ' + item_id)
        sha = text_hash(card)
        rel = f'audio/{item_id}.mp3'
        output = audio_dir / f'{item_id}.mp3'
        spoken = spoken_text(card)
        with tempfile.TemporaryDirectory(prefix='piper-') as tmp:
            wav = Path(tmp) / 'spoken.wav'
            with wave.open(str(wav), 'wb') as f:
                voice.synthesize_wav(spoken, f)
            # Constant-quality, mono MP3. Android decodes it without bundled codecs.
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
                 '-i',str(wav),'-vn','-ar','24000','-ac','1','-codec:a','libmp3lame',
                 '-b:a','32k','-write_xing','0',str(output)],check=True)
        if not output.is_file() or output.stat().st_size < 500:
            failures.append(item_id)
        else:
            manifest['items'][item_id] = {
              'file': rel, 'text_sha256': sha,
              'audio_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
              'size_bytes': output.stat().st_size
            }
        print(f'{n}/{len(cards)} {item_id} {output.stat().st_size if output.exists() else 0} bytes', flush=True)
    if failures:raise RuntimeError(f'failed to generate audio: {failures}')
    (Path(args.out)/'audio-index.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if args.zip:
        with zipfile.ZipFile(args.zip,'w',compression=zipfile.ZIP_STORED) as z:
            z.write(args.pack,'pack.json')
            z.write(Path(args.out)/'audio-index.json','audio-index.json')
            for entry in manifest['items'].values(): z.write(Path(args.out)/entry['file'],entry['file'])
    print(f'COMPLETE: {len(manifest["items"])} MP3 clips, {sum(x["size_bytes"] for x in manifest["items"].values())} bytes',flush=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--pack',required=True);p.add_argument('--model',required=True)
    p.add_argument('--out',required=True);p.add_argument('--zip');render_pack(p.parse_args())
