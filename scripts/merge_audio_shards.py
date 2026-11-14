#!/usr/bin/env python3
"""Merge independently generated subject audio shards and verify all 561 groups."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


from spoken_text import spoken_text


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--pack', required=True)
    p.add_argument('--shards', required=True)
    p.add_argument('--out', required=True)
    args = p.parse_args()
    pack = json.loads(Path(args.pack).read_text(encoding='utf-8'))
    cards = {c['id']: c for c in pack['cards']}
    out = Path(args.out)
    audio_dir = out / 'audio'
    audio_dir.mkdir(parents=True, exist_ok=True)
    items = {}
    shard_dirs = sorted(Path(args.shards).glob('grouped-audio-*'))
    if not shard_dirs:
        raise SystemExit('No grouped-audio-* artifacts were downloaded')
    for shard in shard_dirs:
        manifest_path = shard / 'audio-index.json'
        if not manifest_path.is_file():
            raise SystemExit(f'Missing audio-index.json in {shard}')
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if manifest.get('pack_id') != pack['pack_id']:
            raise SystemExit(f'Pack mismatch in {shard}: {manifest.get("pack_id")}')
        if manifest.get('speech_format') != 'title-answer-v1':
            raise SystemExit(f'Wrong speech format in {shard}')
        if manifest.get('pack_sha256') != hashlib.sha256(Path(args.pack).read_bytes()).hexdigest():
            raise SystemExit(f'Changed source pack in {shard}')
        scripts = json.loads((shard / 'spoken-texts.json').read_text(encoding='utf-8'))
        for card_id, entry in manifest.get('items', {}).items():
            if card_id not in cards:
                raise SystemExit(f'Unknown card in shard {shard}: {card_id}')
            if card_id in items:
                raise SystemExit(f'Duplicate audio shard item: {card_id}')
            if entry.get('file') != f'audio/{card_id}.mp3':
                raise SystemExit(f'Unsafe audio path for {card_id}')
            if scripts.get(card_id) != spoken_text(cards[card_id]):
                raise SystemExit(f'Unexpected narration script for {card_id}')
            expected = hashlib.sha256(spoken_text(cards[card_id]).encode('utf-8')).hexdigest()
            if entry.get('text_sha256') != expected:
                raise SystemExit(f'Text checksum mismatch for {card_id}')
            src = shard / entry['file']
            if not src.is_file() or src.stat().st_size < 500:
                raise SystemExit(f'Missing/short audio for {card_id}: {src}')
            actual = hashlib.sha256(src.read_bytes()).hexdigest()
            if entry.get('audio_sha256') != actual:
                raise SystemExit(f'Audio checksum mismatch for {card_id}')
            shutil.copy2(src, audio_dir / f'{card_id}.mp3')
            items[card_id] = entry
    missing = sorted(set(cards) - set(items))
    extra = sorted(set(items) - set(cards))
    if missing or extra:
        raise SystemExit(f'Audio coverage mismatch: missing={len(missing)} extra={len(extra)}')
    combined = {
        'schema_version': 1,
        'pack_id': pack['pack_id'],
        'generator': 'piper-tts:zh_CN-chaowen-medium',
        'speech_format': 'title-answer-v1',
        'items': items,
    }
    (out / 'audio-index.json').write_text(json.dumps(combined, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'PASS: merged {len(items)} audio files, {sum(x["size_bytes"] for x in items.values())} bytes')


if __name__ == '__main__':
    main()
