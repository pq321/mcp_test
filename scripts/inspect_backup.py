#!/usr/bin/env python3
"""Codex/PC can inspect a backup with Python; never requires opening the Android database."""
import collections,json,sys
from pathlib import Path

def inspect(path):
    data=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if data.get('kind')!='politics-memory-backup':raise ValueError('Not a politics-memory-backup file')
    cards={c['id']:c for p in data['packs'] for c in p['cards']}
    reviews={r['card_id']:r for r in data.get('reviews',[])}
    rows=collections.defaultdict(lambda: [0,0,0,0])
    for card in cards.values():
        r=reviews.get(card['id'],{})
        key=tuple(card['path'])
        total,covered,mastered,score=rows[key]
        rows[key]=[total+1,covered+(r.get('review_count',0)>0),
                   mastered+(r.get('score',0)>=3 and r.get('last_rating')=='yes' and not r.get('needs_review',False)),
                   score+r.get('score',0)]
    print(f'素材包: {len(data["packs"])}; 知识点: {len(cards)}; 评级事件: {len(data.get("events",[]))}')
    for path,(total,covered,mastered,score) in rows.items():
        print(' / '.join(path),f'已背{covered}/{total}, 掌握{mastered}/{total}, 均值{score/total:.2f}/4')

if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Usage: inspect_backup.py "政治背诵-完整备份.json"')
    inspect(sys.argv[1])
