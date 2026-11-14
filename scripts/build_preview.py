#!/usr/bin/env python3
"""Build a self-contained desktop/mobile preview with the current pack and verified audio."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def spoken_text(card):
    title = (card.get('title') or card['path'][2]).strip()
    parts = [
        '知识点位置。' + '，'.join(card['path']),
        '知识点名称。' + title,
        '问题。' + card['question'].strip(),
        '答案。' + card['answer'].strip(),
    ]
    note = (card.get('notes') or '').strip()
    if note:
        parts.append('备注。' + note)
    return '\n'.join(parts)


def safe_json(value):
    # A JSON string inside a script tag must not be able to terminate that tag.
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--pack', required=True)
    p.add_argument('--audio-index', required=True)
    p.add_argument('--audio-dir', required=True)
    p.add_argument('--out', required=True)
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    pack = json.loads(Path(args.pack).read_text(encoding='utf-8'))
    index = json.loads(Path(args.audio_index).read_text(encoding='utf-8'))
    if index.get('pack_id') != pack.get('pack_id'):
        raise SystemExit('Audio manifest pack_id mismatch')
    cards = {c['id']: c for c in pack['cards']}
    items = index.get('items', {})
    if set(items) != set(cards):
        raise SystemExit(f'Audio manifest coverage mismatch: {len(items)}/{len(cards)}')
    for card_id, card in cards.items():
        entry = items[card_id]
        if entry.get('file') != f'audio/{card_id}.mp3':
            raise SystemExit(f'Unsafe audio path for {card_id}')
        text_hash = hashlib.sha256(spoken_text(card).encode('utf-8')).hexdigest()
        if entry.get('text_sha256') != text_hash:
            raise SystemExit(f'Stale audio text hash for {card_id}')
        audio_path = Path(args.audio_dir) / f'{card_id}.mp3'
        if not audio_path.is_file() or audio_path.stat().st_size < 500:
            raise SystemExit(f'Missing audio file: {audio_path}')
        audio_hash = hashlib.sha256(audio_path.read_bytes()).hexdigest()
        if entry.get('audio_sha256') != audio_hash:
            raise SystemExit(f'Corrupt audio file: {audio_path}')
    css = (root / 'preview' / 'app.css').read_text(encoding='utf-8')
    js = (root / 'preview' / 'app.js').read_text(encoding='utf-8')
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    site_audio = out / 'audio'
    shutil.copytree(args.audio_dir, site_audio)
    html = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#ffffff"><title>政治背诵 · 苏一全科</title>
<style>{css}</style></head><body>
<div id="app"><header id="toolbar"></header><main id="main"></main><section id="ratings"></section><section id="player" hidden aria-label="播放器"></section><nav id="nav"></nav></div>
<div id="toast" role="status" aria-live="polite"></div><dialog id="dialog"></dialog>
<input id="import" type="file" accept=".json,application/json" hidden>
<script>window.POLITICS_PACK={safe_json(pack)};window.POLITICS_AUDIO_INDEX={safe_json(index)};</script>
<script>{js}</script></body></html>'''
    (out / 'index.html').write_text(html, encoding='utf-8')
    (out / 'audio-index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (out / 'README.txt').write_text(
        'PoliticsMemory v0.9 desktop preview\n'
        'Open index.html in a modern browser. Keep the audio/ folder beside it for offline speech.\n'
        'For browser localStorage persistence, use the same browser profile. Export a JSON backup before clearing site data.\n',
        encoding='utf-8')
    print(f'PASS: built self-contained preview for {len(cards)} cards and {len(items)} verified audio clips')


if __name__ == '__main__':
    main()
